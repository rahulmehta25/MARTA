"""
GTFS Data Downloader for MARTA Transit Data
Downloads and extracts GTFS static data from MARTA
"""
import os
import zipfile
import requests
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GTFSDownloader:
    """Downloads and manages GTFS data from MARTA"""
    
    def __init__(self, data_dir: str = "data/gtfs"):
        self.gtfs_url = "https://itsmarta.com/google_transit.zip"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def download_gtfs(self) -> bool:
        """
        Download GTFS data from MARTA
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading GTFS data from {self.gtfs_url}")
            
            # Download the file
            response = requests.get(self.gtfs_url, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            temp_file = self.data_dir / "google_transit_temp.zip"
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded GTFS data to {temp_file}")
            
            # Extract the zip file
            self.extract_gtfs(temp_file)
            
            # Clean up temp file
            temp_file.unlink()
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error downloading GTFS data: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def extract_gtfs(self, zip_path: Path):
        """
        Extract GTFS zip file
        
        Args:
            zip_path: Path to the zip file
        """
        extract_dir = self.data_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Create symlink to latest
        latest_link = self.data_dir / "latest"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(extract_dir.name)
        
        logger.info(f"Extracted GTFS data to {extract_dir}")
        
        # List extracted files
        for file in extract_dir.iterdir():
            logger.info(f"  - {file.name}: {file.stat().st_size:,} bytes")
    
    def get_latest_data_path(self) -> Path:
        """Get path to the latest GTFS data"""
        return self.data_dir / "latest"
    
    def validate_gtfs(self) -> bool:
        """
        Validate that required GTFS files exist
        
        Returns:
            bool: True if all required files exist
        """
        required_files = [
            "agency.txt",
            "stops.txt",
            "routes.txt",
            "trips.txt",
            "stop_times.txt",
            "calendar.txt"
        ]
        
        latest_dir = self.get_latest_data_path()
        if not latest_dir.exists():
            logger.error("No GTFS data found")
            return False
        
        missing_files = []
        for file in required_files:
            if not (latest_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"Missing required GTFS files: {missing_files}")
            return False
        
        logger.info("All required GTFS files present")
        return True


if __name__ == "__main__":
    downloader = GTFSDownloader()
    
    if downloader.download_gtfs():
        if downloader.validate_gtfs():
            logger.info("GTFS data downloaded and validated successfully")
        else:
            logger.error("GTFS validation failed")
    else:
        logger.error("Failed to download GTFS data")