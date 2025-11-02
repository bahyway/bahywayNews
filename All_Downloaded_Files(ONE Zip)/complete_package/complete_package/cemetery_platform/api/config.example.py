# Configuration file for Najaf Cemetery Sync
# Copy this to config.py and update with your actual values

# GeoJSON Source URL
# Replace with your actual geojson.io URL
GEOJSON_URL = "https://api.geojson.io/features/your-geojson-id"

# PostgreSQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'najaf_cemetery',
    'user': 'postgres',
    'password': 'your_secure_password',
    'port': 5432
}

# Sync Schedule (hours in 24-hour format)
SYNC_HOURS = [8, 14, 20]  # 8 AM, 2 PM, 8 PM

# Table name for storing cemetery data
TABLE_NAME = 'najaf_cemetery_features'
