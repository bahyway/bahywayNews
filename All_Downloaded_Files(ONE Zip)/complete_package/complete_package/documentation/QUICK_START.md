# Quick Setup Guide - Najaf Cemetery System

Get the system running in under 30 minutes!

## 🎯 Overview

This system automatically processes 1000+ daily deceased records from a government FTP server and updates a cemetery map.

**What it does:**
1. Downloads ZIP files from FTP server
2. Extracts and processes deceased records
3. Stores data in PostgreSQL with geospatial features
4. Updates public map 3 times daily

## 🚀 Fastest Way to Deploy (Docker)

### Step 1: Prerequisites

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin
```

### Step 2: Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required settings in `.env`:**
```bash
DB_PASSWORD=choose_secure_password

FTP_HOST=your.ftp.server.com
FTP_PORT=22
FTP_USERNAME=your_username
FTP_PASSWORD=your_password
FTP_REMOTE_PATH=/deceased_records

GEOJSON_URL=https://api.geojson.io/features/your-map-id
```

### Step 3: Launch Everything

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 4: Verify

```bash
# Check Rust processor
curl http://localhost:8080/health

# Check PostgreSQL
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery -c "SELECT COUNT(*) FROM deceased_records;"
```

## ✅ That's it! Your system is running.

## 📋 What's Running?

After `docker-compose up -d`, you have:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL + PostGIS | 5432 | Database |
| Rust Processor | 8080 | Data processing API |
| FTP Monitor | - | Background service |
| GeoJSON Sync | - | Background scheduler |
| Redis | 6379 | Optional cache |
| Nginx | 80/443 | Optional proxy |

## 🔍 Monitoring

### Check logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f rust_processor
docker-compose logs -f ftp_monitor
docker-compose logs -f geojson_sync
```

### Check database:
```bash
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery

# Inside psql:
SELECT * FROM recent_burials LIMIT 5;
SELECT * FROM section_occupancy;
SELECT * FROM database_info;
```

## 🛠️ Common Tasks

### Restart a service:
```bash
docker-compose restart rust_processor
```

### Update configuration:
```bash
# Edit .env
nano .env

# Restart services to pick up changes
docker-compose down
docker-compose up -d
```

### View processed files:
```bash
# List processed files
ls -lh data/archive/

# Check processing log
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery \
  -c "SELECT * FROM file_processing_log ORDER BY created_at DESC LIMIT 10;"
```

### Manual trigger:
```bash
# Manually trigger FTP scan
docker-compose exec ftp_monitor python -c "
from ftp_monitor import FTPMonitor
import json

config = json.load(open('/app/config/config.json'))
monitor = FTPMonitor(config)
monitor.scan_and_process()
"
```

## 🐛 Troubleshooting

### Services won't start:
```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

### FTP connection fails:
```bash
# Test FTP manually
sftp username@ftp.server.com

# Check firewall
sudo ufw status
sudo ufw allow 22/tcp
```

### Database connection fails:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check PostgreSQL logs
docker-compose logs postgres
```

### Rust service returns errors:
```bash
# Check Rust logs with verbose output
docker-compose logs rust_processor | grep ERROR

# Restart Rust service
docker-compose restart rust_processor

# Test health endpoint
curl http://localhost:8080/health
```

## 📊 Testing the System

### Test with sample data:

1. Create a test CSV file:
```bash
cat > test_deceased.csv << EOF
record_id,deceased_name,deceased_name_arabic,death_date,burial_date,burial_location,latitude,longitude,section,row,plot
TEST001,Test Person,شخص اختبار,2024-11-01,2024-11-02,وادي السلام,32.0175,44.3142,A,1,1
EOF
```

2. Create a ZIP file:
```bash
zip test_deceased.zip test_deceased.csv
```

3. Upload to your FTP server or place in the FTP monitor's download directory:
```bash
cp test_deceased.zip data/downloads/
```

4. Trigger processing:
```bash
# Process will happen automatically, or trigger manually
docker-compose exec rust_processor curl -X POST http://localhost:8080/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "/app/data/downloads",
    "metadata": {
      "filename": "test_deceased.zip",
      "file_hash": "abc123",
      "size": 1024,
      "download_time": "2024-11-01T08:00:00Z"
    },
    "timestamp": "2024-11-01T08:00:00Z",
    "source": "test"
  }'
```

5. Verify in database:
```bash
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery \
  -c "SELECT * FROM deceased_records WHERE record_id = 'TEST001';"
```

## 🔐 Security Checklist

- [ ] Changed default database password in `.env`
- [ ] Using SFTP instead of FTP (port 22)
- [ ] FTP credentials stored securely
- [ ] Database only accessible from localhost
- [ ] Log files have appropriate permissions
- [ ] `.env` file not committed to version control

## 📈 Performance Tuning

### For high volume (5000+ records/day):

```yaml
# In docker-compose.yml, increase resources:
rust_processor:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

### For faster processing:

```bash
# Increase database connections
# Edit init_db.sql and add:
ALTER SYSTEM SET max_connections = '200';
ALTER SYSTEM SET shared_buffers = '256MB';

# Restart PostgreSQL
docker-compose restart postgres
```

## 📞 Getting Help

1. **Check logs**: `docker-compose logs -f`
2. **Review MASTER_README.md**: Comprehensive documentation
3. **Check ARCHITECTURE.md**: System design details
4. **Database queries**: Use the provided views for insights

## 🎉 Success Indicators

Your system is working correctly if:

✅ All services show as "Up" in `docker-compose ps`  
✅ Rust health endpoint returns `{"status": "healthy"}`  
✅ Files appear in `data/archive/` after processing  
✅ `deceased_records` table contains records  
✅ No ERROR messages in logs  
✅ Map updates 3 times daily (check `sync_history` table)

## 🔄 Next Steps

After the system is running:

1. Monitor logs for first 24 hours
2. Verify first file is processed correctly
3. Check map updates are working
4. Set up daily backup schedule
5. Configure monitoring/alerting (optional)

---

**Need more details?** See `MASTER_README.md` for comprehensive documentation.
