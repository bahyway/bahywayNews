# Najaf Cemetery GeoJSON Sync Module

This Python module automatically downloads GeoJSON data from geojson.io and syncs it to a PostgreSQL/PostGIS database three times daily.

## Features

- Downloads GeoJSON data from geojson.io
- Stores spatial data in PostgreSQL with PostGIS
- Automated scheduling (3 times daily)
- Comprehensive logging
- Error handling and sync history tracking
- Multiple scheduling options (APScheduler, systemd, cron)

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher with PostGIS extension
- pip (Python package manager)

## Installation

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgis python3-pip python3-venv
```

**macOS (using Homebrew):**
```bash
brew install postgresql postgis python3
```

### 2. Set Up PostgreSQL Database

```bash
# Login to PostgreSQL
sudo -u postgres psql

# Create database
CREATE DATABASE najaf_cemetery;

# Connect to the database
\c najaf_cemetery

# Enable PostGIS extension
CREATE EXTENSION postgis;

# Create a user (optional)
CREATE USER cemetery_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE najaf_cemetery TO cemetery_user;

# Exit
\q
```

### 3. Set Up Python Environment

```bash
# Create project directory
mkdir najaf-cemetery-sync
cd najaf-cemetery-sync

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure the Module

Copy the example configuration file and update it with your settings:

```bash
cp config.example.py config.py
```

Edit `config.py` and update:
- `GEOJSON_URL`: Your actual geojson.io URL
- `DB_CONFIG`: Your PostgreSQL connection details

## Usage

### Manual Sync

Run a single sync manually:

```bash
python najaf_cemetery_sync.py
```

### Automated Scheduling

You have three options for automated scheduling:

#### Option 1: APScheduler (Recommended for Development)

Run the scheduler script (keeps running in foreground):

```bash
python scheduler.py
```

This will sync at 8:00 AM, 2:00 PM, and 8:00 PM daily.

#### Option 2: Systemd Service (Recommended for Production)

1. Edit the service file with your paths and user:
```bash
sudo nano /etc/systemd/system/najaf-cemetery-sync.service
```

2. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable najaf-cemetery-sync.service
sudo systemctl start najaf-cemetery-sync.service
```

3. Check status:
```bash
sudo systemctl status najaf-cemetery-sync.service
```

4. View logs:
```bash
sudo journalctl -u najaf-cemetery-sync.service -f
```

#### Option 3: Cron Jobs

Edit your crontab:
```bash
crontab -e
```

Add these lines (update paths):
```cron
0 8 * * * /path/to/venv/bin/python /path/to/najaf_cemetery_sync.py >> /var/log/najaf-sync.log 2>&1
0 14 * * * /path/to/venv/bin/python /path/to/najaf_cemetery_sync.py >> /var/log/najaf-sync.log 2>&1
0 20 * * * /path/to/venv/bin/python /path/to/najaf_cemetery_sync.py >> /var/log/najaf-sync.log 2>&1
```

## Database Schema

The module creates two tables:

### najaf_cemetery_features
Stores the GeoJSON features with spatial data:
- `id`: Primary key
- `feature_id`: Feature identifier from GeoJSON
- `geometry`: PostGIS geometry (supports all geometry types)
- `properties`: JSONB field for feature properties
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last update

### sync_history
Tracks sync operations:
- `id`: Primary key
- `sync_time`: When the sync occurred
- `features_count`: Number of features synced
- `status`: Success or failure status
- `error_message`: Error details if failed

## Querying the Data

Example SQL queries:

```sql
-- Get all features
SELECT * FROM najaf_cemetery_features;

-- Get features within a bounding box
SELECT feature_id, properties, ST_AsText(geometry)
FROM najaf_cemetery_features
WHERE ST_Intersects(
    geometry,
    ST_MakeEnvelope(44.3, 32.0, 44.4, 32.1, 4326)
);

-- Count features by type (if you have a 'type' property)
SELECT properties->>'type' as feature_type, COUNT(*)
FROM najaf_cemetery_features
GROUP BY properties->>'type';

-- View sync history
SELECT * FROM sync_history ORDER BY sync_time DESC LIMIT 10;

-- Check last successful sync
SELECT * FROM sync_history 
WHERE status = 'success' 
ORDER BY sync_time DESC 
LIMIT 1;
```

## Logging

Logs are written to:
- `najaf_cemetery_sync.log` - Main sync operations
- `najaf_cemetery_scheduler.log` - Scheduler operations
- Console output (stdout)

## Customization

### Change Sync Times

Edit `scheduler.py` and modify the CronTrigger:

```python
# Current: 8 AM, 2 PM, 8 PM
scheduler.add_job(
    run_sync,
    CronTrigger(hour='8,14,20', minute='0'),
    ...
)

# Example: Every 4 hours
scheduler.add_job(
    run_sync,
    CronTrigger(hour='*/4', minute='0'),
    ...
)

# Example: 6 AM, 12 PM, 6 PM, 12 AM
scheduler.add_job(
    run_sync,
    CronTrigger(hour='0,6,12,18', minute='0'),
    ...
)
```

### Upsert Instead of Replace

To update existing features instead of replacing all data, modify the `save_to_database` method:

```python
# Replace the TRUNCATE with an upsert:
for feature in features:
    cursor.execute("""
        INSERT INTO najaf_cemetery_features (feature_id, geometry, properties)
        VALUES (%s, ST_GeomFromGeoJSON(%s), %s)
        ON CONFLICT (feature_id) DO UPDATE SET
            geometry = EXCLUDED.geometry,
            properties = EXCLUDED.properties,
            updated_at = CURRENT_TIMESTAMP
    """, (feature_id, geometry_json, properties_json))
```

## Troubleshooting

### PostGIS Extension Error
```bash
# Install PostGIS if not already installed
sudo apt-get install postgresql-XX-postgis-3
# Replace XX with your PostgreSQL version (e.g., 14)
```

### Connection Refused
- Check if PostgreSQL is running: `sudo systemctl status postgresql`
- Verify pg_hba.conf allows connections
- Check firewall settings

### GeoJSON Download Fails
- Verify the geojson.io URL is correct and accessible
- Check network connectivity
- Ensure the URL returns valid GeoJSON format

### Permission Issues
- Ensure the database user has necessary privileges
- Check file permissions for log files

## Security Considerations

1. **Never commit credentials**: Keep `config.py` in `.gitignore`
2. **Use environment variables**: Consider using environment variables for sensitive data
3. **Limit database permissions**: Grant only necessary privileges to the database user
4. **Secure the GeoJSON URL**: If possible, use authentication for the data source

## Contributing

To extend this module:
1. Add custom processing in the `save_to_database` method
2. Implement custom validation in the `download_geojson` method
3. Add monitoring hooks in the `sync` method

## License

MIT License - Feel free to modify and use as needed.

## Support

For issues or questions:
1. Check the log files for detailed error messages
2. Verify database connectivity
3. Ensure all dependencies are installed
4. Check that PostGIS is properly enabled
