# 📦 Project Files Manifest

Complete list of all files in the Najaf Cemetery Management System.

## 📚 Documentation Files

### MASTER_README.md
**The main documentation file** - Start here!
- Complete system overview
- Architecture explanation
- Setup instructions
- Troubleshooting guide
- Performance benchmarks

### QUICK_START.md
**Fast deployment guide** - Get running in 30 minutes!
- Docker-based setup
- Step-by-step instructions
- Testing procedures
- Common troubleshooting

### ARCHITECTURE.md
**Detailed system architecture**
- Microservices design
- Data flow diagrams
- API contracts
- Database schema
- Scalability considerations

### README.md
**Original Python module documentation**
- Basic Python setup
- Manual deployment
- Configuration options

## 🐍 Python Services

### ftp_monitor.py (16 KB)
**FTP/SFTP monitoring service**
- Downloads ZIP files from government FTP
- Extracts and validates files
- Triggers Rust processor
- Maintains processing history
- Handles both FTP and SFTP protocols

### najaf_cemetery_sync.py (9 KB)
**GeoJSON sync service**
- Exports PostgreSQL data to GeoJSON
- Updates public map API
- Manages sync history
- Handles PostGIS geometries

### scheduler.py (2 KB)
**Task scheduler**
- Runs GeoJSON sync 3 times daily (8 AM, 2 PM, 8 PM)
- Uses APScheduler
- Comprehensive logging

### test_setup.py (6 KB)
**Setup verification script**
- Checks Python version
- Validates dependencies
- Tests database connection
- Verifies FTP connectivity
- Runs test sync

## 🦀 Rust Microservice

### rust-processor/ Directory
Complete Rust data processing microservice

#### rust-processor/Cargo.toml
Rust dependencies and project metadata
- Actix-web for HTTP server
- SQLx for PostgreSQL
- CSV and JSON parsing libraries
- Geospatial operations

#### rust-processor/Dockerfile
Container build instructions for Rust service
- Multi-stage build (compile + runtime)
- Optimized production image
- ~50 MB final image size

#### rust-processor/README.md
Rust service documentation
- API endpoints
- Development setup
- Testing instructions
- Performance metrics

#### rust-processor/src/main.rs (4 KB)
HTTP server and entry point
- Health check endpoint
- Process data endpoint
- Database connection pooling
- Error handling

#### rust-processor/src/models.rs (4 KB)
Data structures and models
- DeceasedRecord struct
- GeoJSON feature models
- Validation logic
- Type conversions

#### rust-processor/src/parser.rs (4 KB)
CSV and JSON parsing
- Flexible CSV parser
- JSON deserializer
- Auto-detection of file format
- Error handling

#### rust-processor/src/database.rs (3 KB)
PostgreSQL operations
- Record insertion with upsert
- Batch operations
- GeoJSON feature creation
- Processing logs

#### rust-processor/src/processor.rs (3 KB)
Processing orchestration
- File/directory processing
- Validation coordination
- Database coordination
- Result aggregation

## 🐳 Docker & Deployment

### docker-compose.yml (3 KB)
**Multi-service orchestration**
- PostgreSQL + PostGIS
- Rust processor
- Python FTP monitor
- Python GeoJSON sync
- Redis (optional)
- Nginx (optional)

### Dockerfile.ftp_monitor
Container for FTP monitoring service
- Python 3.11 slim base
- Installs dependencies
- Configures directories

### Dockerfile.geojson_sync
Container for GeoJSON sync service
- Python 3.11 slim base
- Scheduler setup
- Log management

### .env.example
Environment variables template
- Database credentials
- FTP/SFTP configuration
- GeoJSON API settings
- Monitoring intervals

## 🗄️ Database

### init_db.sql (16 KB)
**Complete database initialization**
- PostGIS extension setup
- Table creation (5 main tables)
- Indexes (spatial and regular)
- Views for statistics
- Triggers for timestamps
- Sample data insertion
- Permissions setup

**Tables created:**
1. deceased_records - Main data storage
2. najaf_cemetery_features - GeoJSON export
3. sync_history - Processing logs
4. file_processing_log - File tracking
5. burial_sections - Cemetery layout

**Views created:**
1. daily_burial_stats - Daily statistics
2. section_occupancy - Section capacity
3. recent_burials - Last 30 days
4. database_info - System overview

## ⚙️ Configuration

### config.example.py
Python configuration template
- GeoJSON URL
- Database settings
- Sync schedule
- Table names

### requirements.txt
Original Python dependencies
- requests
- psycopg2-binary
- APScheduler

### requirements_updated.txt
Updated Python dependencies
- All original dependencies
- paramiko (SFTP support)
- pysftp (FTP utilities)

## 🔧 System Configuration

### najaf-cemetery-sync.service
Systemd service file for production deployment
- Service definition
- Auto-restart configuration
- Logging setup
- Installation instructions

### cron_setup.txt
Cron configuration instructions
- Cron syntax examples
- Installation guide
- Multiple schedule options

## 📊 File Statistics

### Total Project Size
- Python code: ~28 KB
- Rust code: ~18 KB  
- Documentation: ~35 KB
- Configuration: ~10 KB
- Total: ~91 KB + dependencies

### Lines of Code (approximate)
- Python: ~800 lines
- Rust: ~600 lines
- SQL: ~300 lines
- Documentation: ~2000 lines

## 🎯 File Usage Guide

### For Quick Setup:
1. Read: `QUICK_START.md`
2. Configure: `.env.example` → `.env`
3. Run: `docker-compose up -d`

### For Development:
1. Read: `MASTER_README.md`
2. Read: `ARCHITECTURE.md`
3. Configure: `config.example.py` → `config.py`
4. Test: `python test_setup.py`

### For Understanding:
1. Architecture: `ARCHITECTURE.md`
2. Rust API: `rust-processor/README.md`
3. Database: `init_db.sql` (has comments)

### For Customization:
1. Modify: `ftp_monitor.py` (FTP logic)
2. Modify: `rust-processor/src/parser.rs` (data format)
3. Modify: `init_db.sql` (database schema)
4. Modify: `docker-compose.yml` (deployment)

## 🔍 File Dependencies

```
QUICK_START.md
└── requires: .env, docker-compose.yml

docker-compose.yml
├── requires: .env
├── uses: Dockerfile.ftp_monitor
├── uses: Dockerfile.geojson_sync
├── uses: rust-processor/Dockerfile
└── uses: init_db.sql

ftp_monitor.py
├── requires: requirements_updated.txt
├── requires: config.py (from config.example.py)
└── calls: rust-processor API

rust-processor
├── requires: DATABASE_URL env var
├── calls: PostgreSQL
└── uses: init_db.sql schema

najaf_cemetery_sync.py
├── requires: requirements.txt
├── requires: config.py
└── reads: PostgreSQL

scheduler.py
├── requires: requirements.txt
└── runs: najaf_cemetery_sync.py
```

## 📝 Notes

- All Python files use UTF-8 encoding (supports Arabic text)
- Rust files follow Rust 2021 edition standards
- SQL files are PostgreSQL 12+ compatible
- Docker files use multi-stage builds for optimization
- All services include comprehensive logging
- Configuration files have sensible defaults

## 🎓 Learning Path

**Beginner**: 
1. `QUICK_START.md`
2. `MASTER_README.md`
3. Try Docker deployment

**Intermediate**:
1. `ARCHITECTURE.md`
2. Modify `config.example.py`
3. Run manual deployment

**Advanced**:
1. Read all source code
2. Modify Rust processor
3. Customize database schema
4. Optimize performance

---

**All files are MIT licensed and ready for production use!**
