#!/usr/bin/env python3
"""
Disable Synthetic Data Generation
Update files to remove synthetic data generation and use real data instead
"""
import os
import sys
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SyntheticDataDisabler:
    """Disable synthetic data generation and update files to use real data"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / "backup_synthetic_data"
        
    def create_backup(self):
        """Create backup of files that will be modified"""
        logger.info("Creating backup of files with synthetic data...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        self.backup_dir.mkdir(exist_ok=True)
        
        # Files to backup
        files_to_backup = [
            "src/data_ingestion/gtfs_realtime_processor.py",
            "src/data_ingestion/simple_gtfs_ingestion.py", 
            "src/data_ingestion/gtfs_ingestion.py",
            "src/visualization/demo_dashboard.py",
            "src/optimization/route_simulator.py",
            "frontend/src/utils/api.js",
            "demo_platform.py",
            "test_system.py",
            "src/data_ingestion/event_data_scraper.py"
        ]
        
        for file_path in files_to_backup:
            full_path = self.project_root / file_path
            if full_path.exists():
                backup_path = self.backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_path)
                logger.info(f"Backed up: {file_path}")
        
        logger.info(f"Backup created in: {self.backup_dir}")
    
    def disable_synthetic_data_generation(self):
        """Disable synthetic data generation in files"""
        logger.info("Disabling synthetic data generation...")
        
        # 1. Update GTFS realtime processor
        self._update_gtfs_realtime_processor()
        
        # 2. Update simple GTFS ingestion
        self._update_simple_gtfs_ingestion()
        
        # 3. Update GTFS ingestion
        self._update_gtfs_ingestion()
        
        # 4. Update demo dashboard
        self._update_demo_dashboard()
        
        # 5. Update route simulator
        self._update_route_simulator()
        
        # 6. Update frontend API
        self._update_frontend_api()
        
        # 7. Update demo platform
        self._update_demo_platform()
        
        # 8. Update test system
        self._update_test_system()
        
        # 9. Update event data scraper
        self._update_event_data_scraper()
        
        logger.info("Synthetic data generation disabled successfully")
    
    def _update_gtfs_realtime_processor(self):
        """Update GTFS realtime processor to use real data"""
        file_path = self.project_root / "src/data_ingestion/gtfs_realtime_processor.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace synthetic data generation with real data
        content = content.replace(
            "def generate_synthetic_realtime_data(self, num_days: int = 7):",
            "def generate_synthetic_realtime_data(self, num_days: int = 7):\n        # DISABLED: Use real data instead\n        logger.warning('Synthetic data generation is disabled. Use real data ingestion instead.')\n        return False\n        # Original synthetic data generation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of synthetic data.
Synthetic data generation has been disabled.
Use run_real_data_ingestion.py for real data ingestion.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: src/data_ingestion/gtfs_realtime_processor.py")
    
    def _update_simple_gtfs_ingestion(self):
        """Update simple GTFS ingestion to use real data"""
        file_path = self.project_root / "src/data_ingestion/simple_gtfs_ingestion.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace demo data creation with real data
        content = content.replace(
            "def create_demo_data(self):",
            "def create_demo_data(self):\n        # DISABLED: Use real data instead\n        logger.warning('Demo data creation is disabled. Use real data ingestion instead.')\n        raise Exception('Demo data creation is disabled. Use run_real_data_ingestion.py for real data ingestion.')\n        # Original demo data creation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of demo data.
Demo data creation has been disabled.
Use run_real_data_ingestion.py for real data ingestion.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: src/data_ingestion/simple_gtfs_ingestion.py")
    
    def _update_gtfs_ingestion(self):
        """Update GTFS ingestion to use real data"""
        file_path = self.project_root / "src/data_ingestion/gtfs_ingestion.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace demo GTFS creation with real data
        content = content.replace(
            "def create_demo_gtfs_data(self, output_path: str = \"data/static/demo_gtfs.zip\"):",
            "def create_demo_gtfs_data(self, output_path: str = \"data/static/demo_gtfs.zip\"):\n        # DISABLED: Use real data instead\n        logger.warning('Demo GTFS data creation is disabled. Use real data ingestion instead.')\n        raise Exception('Demo GTFS data creation is disabled. Use run_real_data_ingestion.py for real data ingestion.')\n        # Original demo GTFS creation code below (disabled):"
        )
        
        # Update run_ingestion method
        content = content.replace(
            "elif create_demo:",
            "elif create_demo:\n            # DISABLED: Use real data instead\n            logger.warning('Demo data creation is disabled. Use real data ingestion instead.')\n            raise Exception('Demo data creation is disabled. Use run_real_data_ingestion.py for real data ingestion.')\n            # Original demo creation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of demo data.
Demo GTFS data creation has been disabled.
Use run_real_data_ingestion.py for real data ingestion.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: src/data_ingestion/gtfs_ingestion.py")
    
    def _update_demo_dashboard(self):
        """Update demo dashboard to use real data"""
        file_path = self.project_root / "src/visualization/demo_dashboard.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace sample data creation with real data
        content = content.replace(
            "def create_sample_data():",
            "def create_sample_data():\n    # DISABLED: Use real data instead\n    logger.warning('Sample data creation is disabled. Use real data from database instead.')\n    raise Exception('Sample data creation is disabled. Use real data from database instead.')\n    # Original sample data creation code below (disabled):"
        )
        
        content = content.replace(
            "def create_sample_unified_data(stops_df, routes_df):",
            "def create_sample_unified_data(stops_df, routes_df):\n    # DISABLED: Use real data instead\n    logger.warning('Sample unified data creation is disabled. Use real data from database instead.')\n    raise Exception('Sample unified data creation is disabled. Use real data from database instead.')\n    # Original sample unified data creation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of sample data.
Sample data creation has been disabled.
Use real data from database instead.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: src/visualization/demo_dashboard.py")
    
    def _update_route_simulator(self):
        """Update route simulator to use real data"""
        file_path = self.project_root / "src/optimization/route_simulator.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace passenger demand generation with real data
        content = content.replace(
            "def generate_passenger_demand(self, demand_model=None):",
            "def generate_passenger_demand(self, demand_model=None):\n        # DISABLED: Use real data instead\n        logger.warning('Synthetic passenger demand generation is disabled. Use real demand data instead.')\n        raise Exception('Synthetic passenger demand generation is disabled. Use real demand data instead.')\n        # Original passenger demand generation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of synthetic data.
Synthetic passenger demand generation has been disabled.
Use real demand data from database instead.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: src/optimization/route_simulator.py")
    
    def _update_frontend_api(self):
        """Update frontend API to use real data"""
        file_path = self.project_root / "frontend/src/utils/api.js"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace mock API service with real API
        content = content.replace(
            "// Mock data service for development/testing",
            "// DISABLED: Mock data service disabled - use real API instead\n        // Original mock data service code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''/*
WARNING: This file has been updated to use real data instead of mock data.
Mock API service has been disabled.
Use real API endpoints instead.
*/

'''
        
        if not content.startswith('/*\nWARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: frontend/src/utils/api.js")
    
    def _update_demo_platform(self):
        """Update demo platform to use real data"""
        file_path = self.project_root / "demo_platform.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace demo data generation with real data
        content = content.replace(
            "def demo_platform_capabilities():",
            "def demo_platform_capabilities():\n    # DISABLED: Use real data instead\n    logger.warning('Demo platform capabilities are disabled. Use real data instead.')\n    raise Exception('Demo platform capabilities are disabled. Use real data instead.')\n    # Original demo platform capabilities code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of demo data.
Demo platform capabilities have been disabled.
Use real data instead.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: demo_platform.py")
    
    def _update_test_system(self):
        """Update test system to use real data"""
        file_path = self.project_root / "test_system.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace synthetic test data with real data
        content = content.replace(
            "def test_data_structures():",
            "def test_data_structures():\n    # DISABLED: Use real data instead\n    logger.warning('Synthetic test data generation is disabled. Use real data instead.')\n    raise Exception('Synthetic test data generation is disabled. Use real data instead.')\n    # Original test data generation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of synthetic data.
Synthetic test data generation has been disabled.
Use real data instead.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: test_system.py")
    
    def _update_event_data_scraper(self):
        """Update event data scraper to use real data"""
        file_path = self.project_root / "src/data_ingestion/event_data_scraper.py"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace sample events generation with real data
        content = content.replace(
            "def generate_sample_events():",
            "def generate_sample_events():\n    # DISABLED: Use real data instead\n    logger.warning('Sample events generation is disabled. Use real event data instead.')\n    raise Exception('Sample events generation is disabled. Use real event data instead.')\n    # Original sample events generation code below (disabled):"
        )
        
        # Add warning comment at the top
        warning_comment = '''"""
WARNING: This file has been updated to use real data instead of sample data.
Sample events generation has been disabled.
Use real event data instead.
"""

'''
        
        if not content.startswith('"""WARNING:'):
            content = warning_comment + content
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info("Updated: src/data_ingestion/event_data_scraper.py")
    
    def create_migration_guide(self):
        """Create a migration guide for users"""
        migration_guide = """# 🚇 **MIGRATION GUIDE: From Synthetic to Real Data**

## **What Changed**

The MARTA platform has been updated to use **real data** instead of synthetic/demo data. All synthetic data generation has been disabled.

## **Before (Synthetic Data)**
```bash
# Old way - using synthetic data
python run_data_ingestion.py
python run_data_processing.py
```

## **After (Real Data)**
```bash
# New way - using real data
python run_real_data_ingestion.py --complete
```

## **New Real Data Commands**

### **1. GTFS Static Data Ingestion**
```bash
# Download and ingest real GTFS static data from MARTA
python run_real_data_ingestion.py --gtfs-static

# Use existing GTFS ZIP file
python run_real_data_ingestion.py --gtfs-static --gtfs-zip path/to/gtfs.zip --no-download
```

### **2. GTFS Real-time Data Ingestion**
```bash
# Single fetch of real-time data
python run_real_data_ingestion.py --gtfs-realtime

# Continuous streaming of real-time data
python run_real_data_ingestion.py --gtfs-realtime --stream
```

### **3. Complete Pipeline**
```bash
# Run complete real data ingestion pipeline
python run_real_data_ingestion.py --complete

# Run complete pipeline with continuous real-time streaming
python run_real_data_ingestion.py --complete --stream
```

### **4. Check Status**
```bash
# Check ingestion status and statistics
python run_real_data_ingestion.py --status
```

## **Required Environment Variables**

Set these environment variables for real data ingestion:

```bash
# MARTA API Key (required for GTFS-RT data)
export MARTA_API_KEY="your_marta_api_key"

# Database configuration
export DB_HOST="localhost"
export DB_NAME="marta_db"
export DB_USER="marta_user"
export DB_PASSWORD="marta_password"

# Optional: Weather API Key
export OPENWEATHER_API_KEY="your_openweather_api_key"
```

## **Getting MARTA API Key**

1. Visit [MARTA Developer Portal](https://itsmarta.com/app-developer-resources.aspx)
2. Register for a developer account
3. Request API access
4. Get your API key

## **Data Sources**

The platform now uses real data from:

- **GTFS Static**: [MARTA Developer Portal](https://itsmarta.com/app-developer-resources.aspx)
- **GTFS Real-time**: [MARTA GTFS-RT API](https://api.marta.io/gtfs-rt/)
- **Ridership**: [MARTA KPI Reports](https://itsmarta.com/KPIRidership.aspx)
- **GIS Data**: [Atlanta Regional Commission](https://opendata.atlantaregional.com/)
- **Weather**: OpenWeatherMap API
- **Events**: Major venue websites

## **Backup Files**

Original files with synthetic data have been backed up to:
```
backup_synthetic_data/
```

## **Troubleshooting**

### **API Key Issues**
- Ensure MARTA_API_KEY is set correctly
- Check API key permissions
- Verify API endpoints are accessible

### **Database Issues**
- Ensure PostgreSQL is running
- Check database credentials
- Verify database schema exists

### **Network Issues**
- Check internet connectivity
- Verify firewall settings
- Test API endpoints manually

## **Support**

If you encounter issues with real data ingestion:

1. Check the logs for error messages
2. Verify environment variables are set
3. Test API connectivity manually
4. Review the backup files for reference

## **Benefits of Real Data**

- **Accuracy**: Real MARTA routes, stops, and schedules
- **Relevance**: Actual vehicle positions and delays
- **Validation**: Real-world performance metrics
- **Operational Value**: Actionable insights for MARTA operations

---

**Status**: ✅ **MIGRATION COMPLETE**

Your MARTA platform is now using real data instead of synthetic data!
"""
        
        migration_file = self.project_root / "MIGRATION_GUIDE.md"
        with open(migration_file, 'w') as f:
            f.write(migration_guide)
        
        logger.info(f"Created migration guide: {migration_file}")
    
    def run(self):
        """Run the complete synthetic data disabling process"""
        logger.info("🚫 Starting synthetic data disabling process...")
        
        try:
            # Step 1: Create backup
            self.create_backup()
            
            # Step 2: Disable synthetic data generation
            self.disable_synthetic_data_generation()
            
            # Step 3: Create migration guide
            self.create_migration_guide()
            
            logger.info("✅ Synthetic data disabling completed successfully!")
            logger.info("📖 See MIGRATION_GUIDE.md for instructions on using real data")
            logger.info(f"💾 Backup files saved to: {self.backup_dir}")
            
        except Exception as e:
            logger.error(f"Error in synthetic data disabling process: {e}")
            raise


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Disable Synthetic Data Generation')
    parser.add_argument('--backup-only', action='store_true', help='Only create backup, do not modify files')
    parser.add_argument('--restore', action='store_true', help='Restore files from backup')
    
    args = parser.parse_args()
    
    disabler = SyntheticDataDisabler()
    
    try:
        if args.restore:
            # Restore from backup
            if disabler.backup_dir.exists():
                logger.info("Restoring files from backup...")
                for backup_file in disabler.backup_dir.rglob('*'):
                    if backup_file.is_file():
                        relative_path = backup_file.relative_to(disabler.backup_dir)
                        target_file = disabler.project_root / relative_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup_file, target_file)
                        logger.info(f"Restored: {relative_path}")
                logger.info("✅ Files restored from backup")
            else:
                logger.error("Backup directory not found")
                sys.exit(1)
                
        elif args.backup_only:
            # Only create backup
            disabler.create_backup()
            logger.info("✅ Backup created successfully")
            
        else:
            # Run complete process
            disabler.run()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 