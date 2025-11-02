# Najaf Cemetery Management System - Complete Pipeline

Automated system for processing daily deceased records from government establishments and maintaining an up-to-date cemetery map.

## System Architecture

This system processes **1000+ deceased records daily** through a microservices pipeline:

```
Government FTP → Python Monitor → Rust Processor → PostgreSQL → Map Updates
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture diagrams and explanations.

## 📦 Project Components

### 1. Python FTP Monitor Service
**File**: `ftp_monitor.py`  
**Purpose**: Downloads and extracts daily ZIP files from government FTP server

- Monitors FTP/SFTP every 30 minutes
- Downloads new ZIP files automatically
- Extracts and validates files
- Triggers Rust microservice
- Maintains processing history

### 2. Rust Data Processor Microservice
**Directory**: `rust-processor/`  
**Purpose**: High-performance processing of deceased records

- Parses CSV/JSON files (1000+ records/file)
- Validates all data fields
- Geocodes burial locations
- Stores in PostgreSQL with PostGIS
- Generates GeoJSON features

### 3. Python GeoJSON Sync Service
**File**: `najaf_cemetery_sync.py`  
**Purpose**: Updates public map 3 times daily

- Exports data from PostgreSQL
- Publishes to geojson.io or map API
- Scheduled: 8 AM, 2 PM, 8 PM

### 4. PostgreSQL + PostGIS Database
**Setup**: `init_db.sql`  
**Purpose**: Central data storage with spatial capabilities

- Stores deceased records
- Manages GeoJSON features
- Tracks processing history
- Maintains cemetery sections

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Or: Python 3.8+, Rust 1.75+, PostgreSQL 12+

### Option 1: Docker Deployment (Recommended)

1. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

2. **Start all services**:
```bash
docker-compose up -d
```

3. **Verify services**:
```bash
# Check Rust processor
curl http://localhost:8080/health

# View logs
docker-compose logs -f
```

### Option 2: Manual Deployment

#### Setup PostgreSQL
```bash
# Install PostgreSQL and PostGIS
sudo apt-get install postgresql postgis

# Create database
sudo -u postgres psql -f init_db.sql
```

#### Setup Python Services
```bash
# Install dependencies
pip install -r requirements_updated.txt

# Configure
cp config.example.py config.py
# Edit config.py

# Run FTP Monitor
python ftp_monitor.py &

# Run GeoJSON Sync (scheduled)
python scheduler.py &
```

#### Setup Rust Service
```bash
cd rust-processor

# Build
cargo build --release

# Configure
export DATABASE_URL="postgresql://user:pass@localhost/najaf_cemetery"

# Run
cargo run --release
```

## 📊 Data Flow

### Daily Processing Cycle

1. **00:00-08:00**: Government generates daily deceased records
2. **08:00**: ZIP file uploaded to FTP server (filename: `deceased_YYYY-MM-DD.zip`)
3. **08:30**: Python FTP Monitor detects and downloads file
4. **08:31**: File extracted to staging directory
5. **08:32**: Rust microservice processes records
6. **08:35**: ~1000 records processed and stored in PostgreSQL
7. **09:00**: First GeoJSON sync updates public map
8. **14:00**: Second sync (catches any updates)
9. **20:00**: Third sync (end-of-day final update)

### File Format Requirements

The government ZIP file should contain CSV or JSON files:

**CSV Format** (`deceased_records.csv`):
```csv
record_id,deceased_name,deceased_name_arabic,death_date,burial_date,burial_location,latitude,longitude,section,row,plot
2024001,محمد علي حسن,,2024-10-31,2024-11-01,وادي السلام,32.0175,44.3142,A,12,45
2024002,فاطمة أحمد,,2024-10-31,2024-11-01,وادي السلام,32.0176,44.3143,A,12,46
```

**JSON Format** (`deceased_records.json`):
```json
{
  "records": [
    {
      "record_id": "2024001",
      "deceased_name": "محمد علي حسن",
      "death_date": "2024-10-31",
      "burial_date": "2024-11-01",
      "burial_location": "وادي السلام",
      "coordinates": {"latitude": 32.0175, "longitude": 44.3142},
      "location": {"section": "A", "row": 12, "plot": 45}
    }
  ]
}
```

## 🗄️ Database Schema

### Main Tables

- **deceased_records**: Deceased person records with geospatial data
- **najaf_cemetery_features**: GeoJSON features for map display
- **file_processing_log**: Processing history and statistics
- **sync_history**: Map update history
- **burial_sections**: Cemetery layout and capacity

See `init_db.sql` for complete schema.

### Useful Queries

```sql
-- View recent burials
SELECT * FROM recent_burials LIMIT 10;

-- Check section occupancy
SELECT * FROM section_occupancy;

-- Daily statistics
SELECT * FROM daily_burial_stats WHERE burial_date >= CURRENT_DATE - 7;

-- Total records
SELECT COUNT(*) FROM deceased_records WHERE processing_status = 'completed';
```

## 📁 Project Structure

```
najaf-cemetery-system/
├── ARCHITECTURE.md                 # Detailed architecture docs
├── docker-compose.yml              # Docker orchestration
├── .env.example                    # Environment variables template
├── init_db.sql                     # Database initialization
│
├── Python Services/
│   ├── ftp_monitor.py             # FTP monitoring service
│   ├── najaf_cemetery_sync.py     # GeoJSON sync service
│   ├── scheduler.py               # Task scheduler
│   ├── config.example.py          # Configuration template
│   ├── requirements_updated.txt   # Python dependencies
│   ├── Dockerfile.ftp_monitor     # FTP monitor container
│   └── Dockerfile.geojson_sync    # GeoJSON sync container
│
└── rust-processor/                # Rust microservice
    ├── Cargo.toml                 # Rust dependencies
    ├── Dockerfile                 # Rust container
    ├── README.md                  # Rust service docs
    └── src/
        ├── main.rs                # HTTP server
        ├── models.rs              # Data structures
        ├── parser.rs              # CSV/JSON parsing
        ├── database.rs            # PostgreSQL ops
        └── processor.rs           # Processing logic
```

## 🔧 Configuration

### Environment Variables

Edit `.env` file:

```bash
# Database
DB_PASSWORD=your_secure_password

# FTP/SFTP Server
FTP_HOST=ftp.government-establishment.iq
FTP_PORT=22
FTP_USERNAME=najaf_cemetery
FTP_PASSWORD=your_ftp_password
FTP_REMOTE_PATH=/deceased_records

# GeoJSON API
GEOJSON_URL=https://api.geojson.io/features/your-id

# Monitoring
MONITOR_INTERVAL=30  # minutes
```

## 📈 Monitoring & Logs

### Log Files
```bash
# FTP Monitor
tail -f ftp_monitor.log

# Rust Processor
docker logs -f najaf_rust_processor

# GeoJSON Sync
tail -f najaf_cemetery_sync.log
```

### Metrics to Track
- Files processed today
- Records processed per file
- Processing time per file
- Failed records percentage
- Map sync success rate

### Health Checks
```bash
# Check all services
docker-compose ps

# Rust service health
curl http://localhost:8080/health

# Database connection
psql -h localhost -U cemetery_user -d najaf_cemetery -c "SELECT COUNT(*) FROM deceased_records;"
```

## 🔒 Security Considerations

1. **Credentials**: Never commit `.env` or `config.py` files
2. **FTP**: Use SFTP (SSH) instead of plain FTP when possible
3. **Database**: Use strong passwords and limit network access
4. **API**: Consider adding authentication to Rust endpoints
5. **Backups**: Regular database backups (daily recommended)

## 🚦 Troubleshooting

### FTP Connection Issues
```bash
# Test FTP connection
sftp user@ftp.server.com

# Check firewall
sudo ufw status
```

### Rust Service Won't Start
```bash
# Check database connection
psql postgresql://user:pass@host/db

# View detailed logs
RUST_LOG=debug cargo run
```

### Database Issues
```bash
# Check PostGIS
psql -d najaf_cemetery -c "SELECT PostGIS_Version();"

# Verify tables
psql -d najaf_cemetery -c "\dt"
```

## 📊 Performance Benchmarks

- **FTP Download**: ~10 MB/s (varies by network)
- **File Extraction**: ~1 second for 10MB ZIP
- **Rust Processing**: ~500-1000 records/second
- **Database Insert**: ~300-500 records/second
- **GeoJSON Export**: ~2000 features/second

## 🔄 Maintenance

### Daily Tasks (Automated)
- ✅ Monitor FTP for new files
- ✅ Process deceased records
- ✅ Update map 3 times daily

### Weekly Tasks (Manual)
- Check log files for errors
- Verify all services are running
- Review processing statistics

### Monthly Tasks (Manual)
- Database maintenance (VACUUM, ANALYZE)
- Review and clean archive directory
- Update dependencies if needed
- Rotate FTP credentials

## 🎯 Future Enhancements

- [ ] Add authentication to Rust API
- [ ] Implement message queue (RabbitMQ/Kafka)
- [ ] Add caching layer (Redis)
- [ ] Create admin dashboard
- [ ] Add email notifications for failures
- [ ] Implement data retention policies
- [ ] Add support for more file formats (XML, Excel)

## 📞 Support

For issues or questions:
1. Check logs in respective `.log` files
2. Review `ARCHITECTURE.md` for system design
3. Check database with `database_info` view
4. Verify all services are running with `docker-compose ps`

## 📄 License

MIT License - Feel free to modify and use as needed.

---

**Note**: This system is designed to handle 1000+ deceased records daily. For significantly higher volumes (5000+), consider implementing the future enhancements section for better scalability.
