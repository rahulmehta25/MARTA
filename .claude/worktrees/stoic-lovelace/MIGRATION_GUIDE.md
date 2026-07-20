# 🚇 **MIGRATION GUIDE: From Synthetic to Real Data**

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
