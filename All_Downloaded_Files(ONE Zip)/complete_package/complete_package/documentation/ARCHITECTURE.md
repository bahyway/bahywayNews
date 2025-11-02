# Najaf Cemetery Data Pipeline - Microservices Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GOVERNMENT ESTABLISHMENT                          │
│                  Daily Deceased Records System                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ ZIP Files (~1000+ records/day)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FTP/SFTP SERVER                                 │
│                    (FileZilla Landing Zone)                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SERVICE 1: Python FTP Monitor (ftp_monitor.py)                     │
│  - Monitors FTP/SFTP for new ZIP files                              │
│  - Downloads and extracts files                                      │
│  - Validates and logs file metadata                                  │
│  - Triggers Rust processing service                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP POST /api/process
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SERVICE 2: Rust Data Processor (Your Microservice)                 │
│  - Parses deceased records (CSV/JSON/XML)                            │
│  - Validates data integrity                                          │
│  - Geocodes burial locations                                         │
│  - Transforms to GeoJSON format                                      │
│  - Stores in PostgreSQL/PostGIS                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PostgreSQL + PostGIS Database                           │
│  - najaf_cemetery_features (GeoJSON features)                        │
│  - deceased_records (detailed person records)                        │
│  - burial_locations (grave coordinates)                              │
│  - sync_history (processing logs)                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SERVICE 3: Python GeoJSON Sync (najaf_cemetery_sync.py)            │
│  - Exports PostgreSQL data to GeoJSON                                │
│  - Updates geojson.io/public map API                                 │
│  - Runs 3x daily                                                     │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PUBLIC MAP INTERFACE                              │
│              (geojson.io or Custom Web Map)                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Service Details

### Service 1: Python FTP Monitor
**Technology:** Python 3.8+
**Purpose:** File ingestion from government FTP server
**Schedule:** Continuous monitoring (every 30 minutes)

**Responsibilities:**
- Monitor FTP/SFTP for new ZIP files
- Download files to local staging area
- Extract and validate ZIP contents
- Track processed files to avoid duplicates
- Trigger Rust microservice via HTTP API
- Archive processed files

**APIs Exposed:** None (initiator service)

### Service 2: Rust Data Processor
**Technology:** Rust (Actix-web/Rocket)
**Purpose:** High-performance data processing and validation
**Why Rust?** 
- Handle 1000+ records per file efficiently
- Memory safety for critical government data
- Concurrent processing capabilities
- Fast CSV/JSON parsing

**Responsibilities:**
- Parse deceased person records
- Validate data fields (names, dates, IDs)
- Geocode burial locations
- Generate GeoJSON features
- Store in PostgreSQL
- Return processing status

**API Endpoint:**
```
POST /api/process
Content-Type: application/json

Request:
{
  "data_path": "/path/to/extracted/data",
  "metadata": {
    "filename": "deceased_2024-11-01.zip",
    "file_hash": "sha256...",
    "size": 1048576,
    "download_time": "2024-11-01T08:30:00Z"
  },
  "timestamp": "2024-11-01T08:30:00Z",
  "source": "ftp_monitor"
}

Response (200 OK):
{
  "success": true,
  "records_processed": 1247,
  "records_failed": 3,
  "processing_time_seconds": 45.2,
  "geojson_features_created": 1244,
  "errors": [
    {
      "record_id": "123456",
      "error": "Invalid coordinates"
    }
  ]
}

Response (500 Error):
{
  "success": false,
  "error": "Database connection failed",
  "details": "..."
}
```

### Service 3: Python GeoJSON Sync
**Technology:** Python 3.8+
**Purpose:** Publish data to public map interface
**Schedule:** 3 times daily (8 AM, 2 PM, 8 PM)

**Responsibilities:**
- Query PostgreSQL for latest cemetery data
- Generate comprehensive GeoJSON
- Update geojson.io or public API
- Maintain version history

## Data Flow

### Daily Processing Cycle

1. **00:00 - 08:00:** Government establishment generates daily deceased records
2. **08:00:** Zip file uploaded to FTP server
3. **08:30:** Python FTP Monitor detects new file
4. **08:31:** File downloaded and extracted
5. **08:32:** Rust microservice triggered for processing
6. **08:35:** Processing complete (1000+ records in ~3 minutes)
7. **08:36:** Data stored in PostgreSQL
8. **09:00:** GeoJSON Sync exports and publishes to map (scheduled)
9. **14:00:** Second GeoJSON sync (in case of updates)
10. **20:00:** Third GeoJSON sync (end of day)

### File Format Expectations

The government ZIP file should contain:

**Option 1: CSV Format**
```csv
record_id,deceased_name,death_date,burial_date,burial_location,latitude,longitude,section,row,plot
2024001,محمد علي حسن,2024-10-31,2024-11-01,وادي السلام,32.0175,44.3142,A,12,45
2024002,فاطمة أحمد,2024-10-31,2024-11-01,وادي السلام,32.0176,44.3143,A,12,46
```

**Option 2: JSON Format**
```json
{
  "records": [
    {
      "record_id": "2024001",
      "deceased_name": "محمد علي حسن",
      "death_date": "2024-10-31",
      "burial_date": "2024-11-01",
      "burial_location": "وادي السلام",
      "coordinates": {
        "latitude": 32.0175,
        "longitude": 44.3142
      },
      "location": {
        "section": "A",
        "row": 12,
        "plot": 45
      }
    }
  ]
}
```

## Database Schema

### Table: deceased_records
```sql
CREATE TABLE deceased_records (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(50) UNIQUE NOT NULL,
    deceased_name VARCHAR(255) NOT NULL,
    death_date DATE NOT NULL,
    burial_date DATE NOT NULL,
    burial_location VARCHAR(255),
    section VARCHAR(50),
    row_number INTEGER,
    plot_number INTEGER,
    coordinates GEOMETRY(Point, 4326),
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file VARCHAR(255),
    processing_status VARCHAR(50)
);

CREATE INDEX idx_deceased_coordinates ON deceased_records USING GIST (coordinates);
CREATE INDEX idx_deceased_burial_date ON deceased_records (burial_date);
CREATE INDEX idx_deceased_record_id ON deceased_records (record_id);
```

### Table: najaf_cemetery_features (GeoJSON export)
```sql
CREATE TABLE najaf_cemetery_features (
    id SERIAL PRIMARY KEY,
    feature_id VARCHAR(255),
    geometry GEOMETRY(Geometry, 4326),
    properties JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Deployment Architecture

### Development Environment
```yaml
services:
  - Python FTP Monitor (localhost:5000)
  - Rust Processor (localhost:8080)
  - PostgreSQL (localhost:5432)
  - Python GeoJSON Sync (scheduled tasks)
```

### Production Environment
```yaml
services:
  - Python FTP Monitor (Docker container)
  - Rust Processor (Docker container)
  - PostgreSQL + PostGIS (Docker container or managed service)
  - Redis (for job queue - optional)
  - Nginx (reverse proxy)
```

## Monitoring & Logging

### Log Files
- `ftp_monitor.log` - FTP download and extraction logs
- `rust_processor.log` - Data processing logs
- `geojson_sync.log` - Map update logs

### Metrics to Track
- Files processed per day
- Records processed per file
- Processing time per file
- Failed records count
- API response times
- Database query performance

### Alerts
- FTP connection failures
- Rust service unavailable
- Database connection errors
- Processing failures > 5%
- Disk space < 10%

## Scalability Considerations

### Current Volume: ~1000 records/day
- Single Rust instance sufficient
- Standard PostgreSQL adequate

### Future Growth: 5000+ records/day
- Horizontal scaling of Rust processor
- Message queue (RabbitMQ/Kafka)
- Read replicas for PostgreSQL
- Caching layer (Redis)

## Security

### Data Protection
- Encrypted FTP/SFTP connections (TLS/SSH)
- Database encryption at rest
- Secure credential management (environment variables)
- Audit logs for all processing

### Access Control
- FTP credentials rotation every 90 days
- Database role-based access
- API authentication tokens
- Network segmentation

## Rust Microservice Recommendations

### Suggested Crates
```toml
[dependencies]
actix-web = "4.4"           # Web framework
tokio = "1.35"              # Async runtime
sqlx = "0.7"                # Database driver
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
csv = "1.3"                 # CSV parsing
geo = "0.27"                # Geospatial operations
chrono = "0.4"              # Date/time handling
log = "0.4"                 # Logging
env_logger = "0.11"         # Logger implementation
```

### Project Structure
```
rust-processor/
├── Cargo.toml
├── src/
│   ├── main.rs
│   ├── api/
│   │   └── process.rs
│   ├── parser/
│   │   ├── csv_parser.rs
│   │   └── json_parser.rs
│   ├── models/
│   │   ├── deceased_record.rs
│   │   └── geojson_feature.rs
│   ├── database/
│   │   └── postgres.rs
│   ├── geocoder/
│   │   └── location_service.rs
│   └── validator/
│       └── data_validator.rs
```

## Benefits of This Architecture

1. **Separation of Concerns:** Each service has a single responsibility
2. **Language Optimization:** Python for I/O, Rust for computation
3. **Scalability:** Services can scale independently
4. **Maintainability:** Clear boundaries between components
5. **Reliability:** Failure in one service doesn't crash entire system
6. **Performance:** Rust handles bulk processing efficiently
7. **Flexibility:** Easy to replace or upgrade individual services

## Next Steps

1. ✅ Deploy Python FTP Monitor
2. 🔨 Build Rust Data Processor (your microservice)
3. ✅ Configure PostgreSQL schema
4. ✅ Set up GeoJSON Sync
5. 🔧 Integrate all services
6. 🧪 End-to-end testing
7. 🚀 Production deployment
