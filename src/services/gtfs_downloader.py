"""
GTFS data downloader service for MARTA transit data.
Downloads and updates GTFS static feed data.
"""
import httpx
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
import hashlib

from sqlalchemy.orm import Session
from src.config import settings
from src.services.gtfs_parser import GTFSParser

logger = logging.getLogger(__name__)


class GTFSDownloader:
    """Download and manage GTFS static feed data."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.gtfs_url = settings.marta_gtfs_url
        self.cache_dir = "data/gtfs_cache"
        self.last_download = None
        self.last_etag = None
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def download_and_update(self, force: bool = False) -> Dict[str, any]:
        """
        Download GTFS data and update database.
        
        Args:
            force: Force download even if data is recent
            
        Returns:
            Dictionary with update statistics
        """
        result = {
            "success": False,
            "message": "",
            "stats": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check if we need to download
            if not force and self._is_data_recent():
                result["message"] = "GTFS data is already up to date"
                result["success"] = True
                return result
            
            # Download GTFS file
            logger.info(f"Downloading GTFS data from {self.gtfs_url}")
            zip_data = await self._download_gtfs()
            
            if not zip_data:
                result["message"] = "Failed to download GTFS data"
                return result
            
            # Save to cache
            cache_file = self._save_to_cache(zip_data)
            logger.info(f"GTFS data saved to {cache_file}")
            
            # Parse and import data
            parser = GTFSParser(self.db)
            stats = parser.parse_zip(zip_data)
            
            result["success"] = True
            result["message"] = "GTFS data updated successfully"
            result["stats"] = stats
            self.last_download = datetime.utcnow()
            
            logger.info(f"GTFS update completed: {stats}")
            
        except Exception as e:
            logger.error(f"Error updating GTFS data: {e}")
            result["message"] = f"Error: {str(e)}"
            self.db.rollback()
        
        return result
    
    async def _download_gtfs(self) -> Optional[bytes]:
        """
        Download GTFS ZIP file from MARTA.
        
        Returns:
            ZIP file content as bytes or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {}
                
                # Add etag header if we have one (for caching)
                if self.last_etag:
                    headers['If-None-Match'] = self.last_etag
                
                response = await client.get(self.gtfs_url, headers=headers)
                
                # Check if data hasn't changed (304 Not Modified)
                if response.status_code == 304:
                    logger.info("GTFS data hasn't changed (304)")
                    return None
                
                response.raise_for_status()
                
                # Store etag for future requests
                if 'etag' in response.headers:
                    self.last_etag = response.headers['etag']
                
                return response.content
                
        except httpx.TimeoutException:
            logger.error("Timeout downloading GTFS data")
            return None
        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading GTFS data: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading GTFS data: {e}")
            return None
    
    def _save_to_cache(self, zip_data: bytes) -> str:
        """
        Save GTFS data to cache directory.
        
        Args:
            zip_data: ZIP file content
            
        Returns:
            Path to saved file
        """
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"gtfs_{timestamp}.zip"
        filepath = os.path.join(self.cache_dir, filename)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(zip_data)
        
        # Clean old cache files (keep last 5)
        self._clean_old_cache()
        
        return filepath
    
    def _clean_old_cache(self, keep_count: int = 5):
        """Remove old cache files, keeping the most recent ones."""
        try:
            # Get all GTFS files in cache
            files = [
                f for f in os.listdir(self.cache_dir)
                if f.startswith('gtfs_') and f.endswith('.zip')
            ]
            
            # Sort by modification time
            files.sort(key=lambda f: os.path.getmtime(
                os.path.join(self.cache_dir, f)
            ), reverse=True)
            
            # Remove old files
            for f in files[keep_count:]:
                filepath = os.path.join(self.cache_dir, f)
                os.remove(filepath)
                logger.info(f"Removed old cache file: {f}")
                
        except Exception as e:
            logger.warning(f"Error cleaning cache: {e}")
    
    def _is_data_recent(self, max_age_hours: int = 24) -> bool:
        """
        Check if cached data is recent enough.
        
        Args:
            max_age_hours: Maximum age of data in hours
            
        Returns:
            True if data is recent, False otherwise
        """
        if not self.last_download:
            # Check for most recent cache file
            try:
                files = [
                    f for f in os.listdir(self.cache_dir)
                    if f.startswith('gtfs_') and f.endswith('.zip')
                ]
                
                if not files:
                    return False
                
                # Get most recent file
                files.sort(key=lambda f: os.path.getmtime(
                    os.path.join(self.cache_dir, f)
                ), reverse=True)
                
                latest_file = os.path.join(self.cache_dir, files[0])
                file_age = datetime.utcnow() - datetime.fromtimestamp(
                    os.path.getmtime(latest_file)
                )
                
                return file_age < timedelta(hours=max_age_hours)
                
            except Exception as e:
                logger.warning(f"Error checking cache age: {e}")
                return False
        
        # Check last download time
        age = datetime.utcnow() - self.last_download
        return age < timedelta(hours=max_age_hours)
    
    def get_cache_info(self) -> Dict[str, any]:
        """Get information about cached GTFS data."""
        try:
            files = [
                f for f in os.listdir(self.cache_dir)
                if f.startswith('gtfs_') and f.endswith('.zip')
            ]
            
            if not files:
                return {
                    "has_cache": False,
                    "files": [],
                    "latest": None
                }
            
            # Get file info
            file_info = []
            for f in files:
                filepath = os.path.join(self.cache_dir, f)
                stat = os.stat(filepath)
                file_info.append({
                    "filename": f,
                    "size_mb": stat.st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            # Sort by modification time
            file_info.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                "has_cache": True,
                "files": file_info,
                "latest": file_info[0] if file_info else None,
                "total_files": len(file_info)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {
                "has_cache": False,
                "error": str(e)
            }