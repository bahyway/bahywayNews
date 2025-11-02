# Najaf Cemetery Data Processor - Rust Microservice

High-performance data processing microservice for handling deceased person records from government establishments.

## Features

- **Fast CSV/JSON Parsing**: Efficiently processes 1000+ records per file
- **Data Validation**: Comprehensive validation of all fields
- **PostGIS Integration**: Stores geospatial data with proper indexing
- **GeoJSON Generation**: Automatic conversion to map-ready format
- **Error Handling**: Robust error tracking and reporting
- **REST API**: Simple HTTP API for integration

## Technology Stack

- **Language**: Rust 1.75+
- **Web Framework**: Actix-web
- **Database**: PostgreSQL with PostGIS (via SQLx)
- **Async Runtime**: Tokio

## API Endpoints

### Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "service": "najaf-cemetery-processor",
  "version": "0.1.0"
}
```

### Process Data
```
POST /api/process
Content-Type: application/json

Request Body:
{
  "data_path": "/path/to/extracted/data",
  "metadata": {
    "filename": "deceased_2024-11-01.zip",
    "file_hash": "abc123...",
    "size": 1048576,
    "download_time": "2024-11-01T08:30:00Z"
  },
  "timestamp": "2024-11-01T08:30:00Z",
  "source": "ftp_monitor"
}

Response (Success):
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

Response (Error):
{
  "success": false,
  "error": "Database connection failed",
  "details": "..."
}
```

## Development

### Prerequisites

- Rust 1.75 or higher
- PostgreSQL 12+ with PostGIS
- Cargo

### Setup

1. Install dependencies:
```bash
cargo build
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost/najaf_cemetery"
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="8080"
export RUST_LOG="info"
```

3. Run the service:
```bash
cargo run
```

### Development with Auto-reload

```bash
cargo install cargo-watch
cargo watch -x run
```

## Docker Deployment

### Build
```bash
docker build -t najaf-cemetery-processor .
```

### Run
```bash
docker run -p 8080:8080 \
  -e DATABASE_URL="postgresql://user:pass@host/db" \
  najaf-cemetery-processor
```

## Testing

### Unit Tests
```bash
cargo test
```

### Integration Tests
```bash
cargo test --test '*'
```

### Manual Testing
```bash
# Health check
curl http://localhost:8080/health

# Process data
curl -X POST http://localhost:8080/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "/path/to/data",
    "metadata": {
      "filename": "test.zip",
      "file_hash": "abc123",
      "size": 1024,
      "download_time": "2024-11-01T08:00:00Z"
    },
    "timestamp": "2024-11-01T08:00:00Z",
    "source": "test"
  }'
```

## Data Format Support

### CSV Format
```csv
record_id,deceased_name,deceased_name_arabic,death_date,burial_date,burial_location,latitude,longitude,section,row,plot
2024001,John Doe,جون دو,2024-10-31,2024-11-01,Wadi al-Salam,32.0175,44.3142,A,12,45
```

### JSON Format
```json
{
  "records": [
    {
      "record_id": "2024001",
      "deceased_name": "John Doe",
      "deceased_name_arabic": "جون دو",
      "death_date": "2024-10-31",
      "burial_date": "2024-11-01",
      "burial_location": "Wadi al-Salam",
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

## Performance

- **Throughput**: ~500-1000 records/second
- **Memory**: ~50MB base + ~1MB per 1000 records
- **Concurrency**: Handles multiple requests simultaneously

## Project Structure

```
rust-processor/
├── Cargo.toml              # Dependencies and metadata
├── Cargo.lock              # Dependency lock file
├── Dockerfile              # Container build instructions
├── src/
│   ├── main.rs            # Entry point and HTTP server
│   ├── models.rs          # Data structures
│   ├── parser.rs          # CSV/JSON parsing
│   ├── database.rs        # PostgreSQL operations
│   └── processor.rs       # Processing orchestration
```

## Error Handling

The service provides detailed error information:

- **Validation Errors**: Invalid data format or missing required fields
- **Database Errors**: Connection failures or query errors
- **Parsing Errors**: Malformed CSV/JSON files
- **File System Errors**: Missing files or permission issues

## Logging

Logs are written to stdout with configurable levels:

```bash
export RUST_LOG=debug    # Verbose logging
export RUST_LOG=info     # Standard logging (default)
export RUST_LOG=warn     # Only warnings and errors
export RUST_LOG=error    # Only errors
```

## Monitoring

Monitor the service using these metrics:

- HTTP response times
- Records processed per minute
- Error rates
- Database connection pool usage

## Contributing

1. Follow Rust's style guidelines
2. Write tests for new features
3. Update documentation
4. Use `cargo fmt` and `cargo clippy`

## License

MIT License
