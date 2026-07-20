"""
MARTA Platform - Database Migration Manager
Manages Alembic migrations with safety checks and rollback capabilities
"""
import os
import sys
import subprocess
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import structlog

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from config.settings import settings
from .connection_pool import get_db_pool

# Configure logging
logger = structlog.get_logger(__name__)

class MigrationManager:
    """
    Comprehensive database migration manager with safety features
    """
    
    def __init__(self, alembic_cfg_path: Optional[str] = None):
        self.alembic_cfg_path = alembic_cfg_path or os.path.join(os.getcwd(), 'alembic.ini')
        self.config = self._load_alembic_config()
        self.script_dir = ScriptDirectory.from_config(self.config)
        
    def _load_alembic_config(self) -> Config:
        """Load Alembic configuration"""
        if not os.path.exists(self.alembic_cfg_path):
            raise FileNotFoundError(f"Alembic configuration file not found: {self.alembic_cfg_path}")
        
        config = Config(self.alembic_cfg_path)
        
        # Override database URL with current settings
        config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
        
        return config
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision"""
        try:
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error("Failed to get current revision", error=str(e))
            return None
    
    def get_head_revision(self) -> str:
        """Get the latest available revision"""
        return self.script_dir.get_current_head()
    
    def get_revision_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get migration revision history"""
        revisions = []
        
        try:
            for rev in self.script_dir.walk_revisions():
                revisions.append({
                    'revision': rev.revision,
                    'down_revision': rev.down_revision,
                    'description': rev.doc,
                    'create_date': getattr(rev.module, 'create_date', None),
                    'branch_labels': rev.branch_labels,
                    'depends_on': rev.depends_on
                })
                
                if len(revisions) >= limit:
                    break
                    
        except Exception as e:
            logger.error("Failed to get revision history", error=str(e))
        
        return revisions
    
    def check_migration_safety(self, target_revision: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform safety checks before running migrations
        Returns safety report with recommendations
        """
        safety_report = {
            'safe_to_migrate': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        try:
            # Check database connection
            db_pool = get_db_pool()
            health_check = db_pool.health_check()
            
            if health_check['status'] != 'healthy':
                safety_report['errors'].append("Database is not healthy")
                safety_report['safe_to_migrate'] = False
            
            # Check active connections
            connection_stats = db_pool.get_connection_stats()
            active_connections = connection_stats.get('active_connections', 0)
            
            if active_connections > 10:
                safety_report['warnings'].append(
                    f"High number of active connections: {active_connections}"
                )
                safety_report['recommendations'].append(
                    "Consider running migrations during low-traffic periods"
                )
            
            # Check current vs target revision
            current_rev = self.get_current_revision()
            target_rev = target_revision or self.get_head_revision()
            
            if current_rev == target_rev:
                safety_report['warnings'].append("Database is already at target revision")
            
            # Check for data-affecting migrations
            if current_rev and target_rev:
                pending_migrations = self.get_pending_migrations()
                for migration in pending_migrations:
                    if self._is_destructive_migration(migration):
                        safety_report['warnings'].append(
                            f"Migration {migration['revision']} may affect data"
                        )
                        safety_report['recommendations'].append(
                            "Consider backing up data before proceeding"
                        )
            
            # Check disk space (migrations might create indexes)
            import psutil
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb < 5:
                safety_report['errors'].append(
                    f"Low disk space: {free_gb:.1f}GB free"
                )
                safety_report['safe_to_migrate'] = False
            elif free_gb < 10:
                safety_report['warnings'].append(
                    f"Limited disk space: {free_gb:.1f}GB free"
                )
            
        except Exception as e:
            safety_report['errors'].append(f"Safety check failed: {str(e)}")
            safety_report['safe_to_migrate'] = False
        
        return safety_report
    
    def _is_destructive_migration(self, migration: Dict[str, Any]) -> bool:
        """Check if migration might be destructive"""
        # Read migration file and check for destructive operations
        destructive_keywords = [
            'drop_table', 'drop_column', 'drop_index',
            'DROP TABLE', 'DROP COLUMN', 'DROP INDEX',
            'ALTER TABLE', 'DELETE FROM', 'TRUNCATE'
        ]
        
        try:
            migration_file = self.script_dir.get_revision(migration['revision']).path
            with open(migration_file, 'r') as f:
                content = f.read()
                return any(keyword in content for keyword in destructive_keywords)
        except Exception:
            # If we can't read the file, assume it might be destructive
            return True
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of pending migrations"""
        current_rev = self.get_current_revision()
        head_rev = self.get_head_revision()
        
        if current_rev == head_rev:
            return []
        
        pending = []
        for rev in self.script_dir.walk_revisions(
            base=current_rev, head=head_rev
        ):
            if rev.revision != current_rev:
                pending.append({
                    'revision': rev.revision,
                    'description': rev.doc,
                    'down_revision': rev.down_revision
                })
        
        return list(reversed(pending))  # Return in execution order
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create database backup before migration"""
        if not backup_name:
            backup_name = f"pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_file = f"/tmp/{backup_name}.sql"
        
        try:
            # Use pg_dump for backup
            cmd = [
                'pg_dump',
                '-h', settings.DB_HOST,
                '-p', str(settings.DB_PORT),
                '-U', settings.DB_USER,
                '-d', settings.DB_NAME,
                '-f', backup_file,
                '--no-password',
                '--verbose'
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = settings.DB_PASSWORD
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Database backup created", backup_file=backup_file)
                return backup_file
            else:
                raise Exception(f"Backup failed: {result.stderr}")
                
        except Exception as e:
            logger.error("Failed to create backup", error=str(e))
            raise
    
    def migrate_up(self, revision: Optional[str] = None, 
                   create_backup: bool = True,
                   safety_check: bool = True) -> Dict[str, Any]:
        """
        Run database migrations with safety checks
        
        Args:
            revision: Target revision (None for latest)
            create_backup: Whether to create backup before migration
            safety_check: Whether to perform safety checks
        """
        result = {
            'success': False,
            'backup_file': None,
            'applied_migrations': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Safety checks
            if safety_check:
                safety_report = self.check_migration_safety(revision)
                result['warnings'].extend(safety_report['warnings'])
                
                if not safety_report['safe_to_migrate']:
                    result['errors'].extend(safety_report['errors'])
                    return result
            
            # Create backup
            if create_backup:
                try:
                    result['backup_file'] = self.create_backup()
                except Exception as e:
                    result['warnings'].append(f"Backup failed: {str(e)}")
            
            # Get pending migrations for tracking
            pending_migrations = self.get_pending_migrations()
            
            # Run migrations
            if revision:
                command.upgrade(self.config, revision)
            else:
                command.upgrade(self.config, 'head')
            
            result['success'] = True
            result['applied_migrations'] = pending_migrations
            
            logger.info("Database migration completed successfully",
                       applied_migrations=len(pending_migrations))
            
        except Exception as e:
            error_msg = str(e)
            result['errors'].append(error_msg)
            logger.error("Database migration failed", error=error_msg)
        
        return result
    
    def migrate_down(self, revision: str, 
                     create_backup: bool = True) -> Dict[str, Any]:
        """
        Downgrade database to specific revision
        
        Args:
            revision: Target revision to downgrade to
            create_backup: Whether to create backup before downgrade
        """
        result = {
            'success': False,
            'backup_file': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Create backup
            if create_backup:
                try:
                    result['backup_file'] = self.create_backup(
                        f"pre_downgrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                except Exception as e:
                    result['warnings'].append(f"Backup failed: {str(e)}")
            
            # Run downgrade
            command.downgrade(self.config, revision)
            
            result['success'] = True
            logger.info("Database downgrade completed", target_revision=revision)
            
        except Exception as e:
            error_msg = str(e)
            result['errors'].append(error_msg)
            logger.error("Database downgrade failed", error=error_msg)
        
        return result
    
    def generate_migration(self, message: str, 
                          autogenerate: bool = True) -> Dict[str, Any]:
        """
        Generate a new migration
        
        Args:
            message: Migration description
            autogenerate: Whether to use autogenerate feature
        """
        result = {
            'success': False,
            'revision_id': None,
            'migration_file': None,
            'errors': []
        }
        
        try:
            if autogenerate:
                revision = command.revision(
                    self.config, 
                    message=message, 
                    autogenerate=True
                )
            else:
                revision = command.revision(
                    self.config,
                    message=message
                )
            
            result['success'] = True
            result['revision_id'] = revision.revision
            result['migration_file'] = revision.path
            
            logger.info("Migration generated successfully",
                       revision_id=revision.revision,
                       message=message)
            
        except Exception as e:
            error_msg = str(e)
            result['errors'].append(error_msg)
            logger.error("Migration generation failed", error=error_msg)
        
        return result
    
    def validate_database_schema(self) -> Dict[str, Any]:
        """Validate current database schema against models"""
        validation_result = {
            'valid': True,
            'issues': [],
            'suggestions': []
        }
        
        try:
            # Use Alembic's autogenerate to compare schema
            from alembic.autogenerate import compare_metadata
            from src.database.models import Base
            
            engine = create_engine(settings.DATABASE_URL)
            
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                diff = compare_metadata(context, Base.metadata)
                
                if diff:
                    validation_result['valid'] = False
                    for change in diff:
                        validation_result['issues'].append(str(change))
                    
                    validation_result['suggestions'].append(
                        "Consider generating a new migration to sync schema"
                    )
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['issues'].append(f"Validation failed: {str(e)}")
        
        return validation_result
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status"""
        current_rev = self.get_current_revision()
        head_rev = self.get_head_revision()
        pending_migrations = self.get_pending_migrations()
        
        return {
            'current_revision': current_rev,
            'head_revision': head_rev,
            'is_up_to_date': current_rev == head_rev,
            'pending_migrations_count': len(pending_migrations),
            'pending_migrations': pending_migrations,
            'revision_history': self.get_revision_history(10),
            'schema_validation': self.validate_database_schema()
        }

# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None

def get_migration_manager() -> MigrationManager:
    """Get or create global migration manager"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager

# Convenience functions
def migrate_database(revision: Optional[str] = None, 
                    create_backup: bool = True,
                    safety_check: bool = True) -> Dict[str, Any]:
    """Run database migrations"""
    return get_migration_manager().migrate_up(revision, create_backup, safety_check)

def rollback_database(revision: str, 
                     create_backup: bool = True) -> Dict[str, Any]:
    """Rollback database to revision"""
    return get_migration_manager().migrate_down(revision, create_backup)

def generate_migration(message: str, 
                      autogenerate: bool = True) -> Dict[str, Any]:
    """Generate new migration"""
    return get_migration_manager().generate_migration(message, autogenerate)

def get_migration_status() -> Dict[str, Any]:
    """Get migration status"""
    return get_migration_manager().get_migration_status()

def check_migration_safety(target_revision: Optional[str] = None) -> Dict[str, Any]:
    """Perform migration safety check"""
    return get_migration_manager().check_migration_safety(target_revision)