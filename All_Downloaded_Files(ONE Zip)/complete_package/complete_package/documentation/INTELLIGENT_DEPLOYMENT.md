# Najaf Cemetery Intelligent System - Deployment Guide

## 🎯 System Overview

You now have a **complete AI-powered cemetery management system** with:

- 🧠 **Rules Engine**: Fuzzy logic for uncertain graves & duplicate names
- 🗺️ **Routing Engine**: Valhalla navigation from entrance to grave
- 🔍 **Search Engine**: Elasticsearch multi-language search
- 🎤 **Voice Assistant**: RAG + NLP with multi-language support (Arabic, English, Urdu, Persian)

## 📦 What's Included

### Core Data Pipeline:
- `ftp_monitor.py` - Downloads ZIP files from government FTP
- `rust-processor/` - High-performance Rust data processor
- `najaf_cemetery_sync.py` - Updates map 3x daily
- `init_db.sql` - Complete database schema

### Intelligent Engines:
- `rules_engine.py` - Fuzzy logic for locations & names
- `valhalla_routing.py` - Navigation & routing
- `search_engine.py` - Elasticsearch integration
- `voice_assistant.py` - Voice interface with RAG

### API & Orchestration:
- `api_gateway.py` - Unified FastAPI gateway
- `docker-compose-intelligent.yml` - Complete stack deployment
- `requirements_intelligent.txt` - All Python dependencies

### Documentation:
- `INTELLIGENT_ARCHITECTURE.md` - Complete system architecture
- `QUICK_START.md` - Fast deployment guide
- `MASTER_README.md` - Comprehensive documentation

## 🚀 Quick Deployment

### Prerequisites

- **Docker & Docker Compose** (recommended)
- OR manually: Python 3.11+, Rust 1.75+, PostgreSQL 15+, Elasticsearch 8+, Valhalla

### Option 1: Docker Deployment (Recommended) ⭐

#### Step 1: Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required settings in `.env`:**
```bash
# Database
DB_PASSWORD=your_secure_database_password

# FTP/SFTP Server (from government)
FTP_HOST=ftp.government-establishment.iq
FTP_PORT=22
FTP_USERNAME=najaf_cemetery
FTP_PASSWORD=your_ftp_password
FTP_REMOTE_PATH=/deceased_records

# GeoJSON Map API
GEOJSON_URL=https://api.geojson.io/features/your-map-id

# OpenAI (Optional - for advanced voice features)
OPENAI_API_KEY=sk-your-key-here

# Monitoring
MONITOR_INTERVAL=30
```

#### Step 2: Launch Complete System
```bash
# Start all services
docker-compose -f docker-compose-intelligent.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api_gateway
```

#### Step 3: Verify Services
```bash
# API Gateway
curl http://localhost:8000/health

# Search Engine
curl http://localhost:9200/_cluster/health

# Routing Engine
curl http://localhost:8002/status

# Rust Processor
curl http://localhost:8080/health

# PostgreSQL
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery -c "SELECT COUNT(*) FROM deceased_records;"
```

## 🎯 Services & Ports

| Service | Port | Purpose | URL |
|---------|------|---------|-----|
| API Gateway | 8000 | Main API | http://localhost:8000 |
| Rust Processor | 8080 | Data processing | http://localhost:8080 |
| PostgreSQL | 5432 | Database | postgresql://localhost:5432 |
| Elasticsearch | 9200 | Search | http://localhost:9200 |
| Valhalla | 8002 | Routing | http://localhost:8002 |
| Redis | 6379 | Cache | redis://localhost:6379 |
| Nginx | 80/443 | Proxy | http://localhost |

## 📚 API Documentation

Once deployed, visit: **http://localhost:8000/docs** for interactive API documentation (Swagger UI).

### Key Endpoints:

#### 🔍 **Search Engine**
```bash
# Search by name (fuzzy)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "محمد علي",
    "language": "ar",
    "fuzzy": true,
    "max_results": 10
  }'

# Search by company
curl http://localhost:8000/api/search/company/النجف

# Geospatial search
curl "http://localhost:8000/api/search/location?latitude=32.0175&longitude=44.3142&radius_meters=100"

# Autocomplete
curl "http://localhost:8000/api/search/autocomplete?prefix=محمد"
```

#### 🗺️ **Routing Engine**
```bash
# Get route to grave
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "2024001",
    "entrance": "main",
    "language": "ar"
  }'

# Multi-grave optimized route
curl -X POST http://localhost:8000/api/route/multi-grave \
  -H "Content-Type: application/json" \
  -d '{
    "record_ids": ["2024001", "2024002", "2024003"],
    "entrance": "main"
  }'
```

#### 🧠 **Rules Engine**
```bash
# Estimate uncertain grave location
curl -X POST http://localhost:8000/api/rules/uncertain-grave \
  -H "Content-Type: application/json" \
  -d '{
    "name": "محمد علي حسن",
    "section": "A",
    "approximate_row": 12,
    "burial_date": "1985-05-15"
  }'

# Check for duplicate names
curl -X POST http://localhost:8000/api/rules/check-duplicates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "محمد علي حسن",
    "similarity_threshold": 85.0
  }'
```

#### 🎤 **Voice Assistant**
```bash
# Text-based query (testing)
curl -X POST http://localhost:8000/api/voice/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "أين قبر محمد علي؟",
    "language": "arabic"
  }'

# Audio query
curl -X POST http://localhost:8000/api/voice/audio \
  -F "audio=@voice_query.mp3" \
  -F "language=arabic"
```

## 🧪 Testing the System

### Test Search Engine:
```bash
# Index sample data first
docker-compose exec api_gateway python -c "
from search_engine import ElasticsearchIndexer
indexer = ElasticsearchIndexer('elasticsearch')
indexer.create_index()
"

# Then search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "language": "en"}'
```

### Test Voice Assistant:
```bash
# Test with text
curl -X POST http://localhost:8000/api/voice/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Where is the grave of John Doe?",
    "language": "english"
  }'
```

### Test Rules Engine:
```bash
# Test fuzzy location
curl -X POST http://localhost:8000/api/rules/uncertain-grave \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Person",
    "section": "A",
    "approximate_row": 1
  }'
```

## 📊 Monitoring

### Check Logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api_gateway
docker-compose logs -f search_engine
docker-compose logs -f valhalla
```

### Monitor Resources:
```bash
# Resource usage
docker stats

# Elasticsearch cluster health
curl http://localhost:9200/_cluster/health?pretty

# PostgreSQL connections
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery \
  -c "SELECT count(*) FROM pg_stat_activity;"
```

### View Statistics:
```bash
# Daily stats
curl http://localhost:8000/api/stats/daily

# Section occupancy
curl http://localhost:8000/api/stats/sections
```

## 🔧 Configuration

### Valhalla Routing:

**Important**: Valhalla needs Iraq OSM map data. The default docker-compose will download it automatically, but for production:

```bash
# Custom map data
mkdir -p valhalla_tiles
cd valhalla_tiles
wget https://download.geofabrik.de/asia/iraq-latest.osm.pbf

# Configure in docker-compose:
environment:
  - tile_urls=https://download.geofabrik.de/asia/iraq-latest.osm.pbf
```

### Elasticsearch Settings:

For production, increase memory:
```yaml
# In docker-compose-intelligent.yml
elasticsearch:
  environment:
    - "ES_JAVA_OPTS=-Xms2g -Xmx2g"  # Increase from 512m
```

### Voice Assistant:

**With OpenAI (Recommended):**
- Set `OPENAI_API_KEY` in `.env`
- Gets natural, context-aware responses

**Without OpenAI:**
- Uses template-based responses
- Still fully functional
- No API costs

## 🛠️ Troubleshooting

### Elasticsearch won't start:
```bash
# Increase vm.max_map_count on host
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

### Valhalla routing fails:
```bash
# Check if OSM data is downloaded
docker-compose exec valhalla ls -lh /custom_files/

# Rebuild if needed
docker-compose stop valhalla
docker-compose rm valhalla
docker-compose up -d valhalla
```

### Voice recognition not working:
```bash
# Check if audio libraries are installed
docker-compose exec api_gateway python -c "import speech_recognition; print('OK')"

# Test with text-based query first
curl -X POST http://localhost:8000/api/voice/query \
  -H "Content-Type: application/json" \
  -d '{"text": "test", "language": "english"}'
```

### Database connection issues:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U cemetery_user -d najaf_cemetery -c "SELECT 1;"

# Check logs
docker-compose logs postgres
```

## 📈 Performance Tuning

### For High Load (5000+ records/day):

1. **Scale API Gateway:**
```yaml
api_gateway:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

2. **Elasticsearch Cluster:**
```yaml
elasticsearch:
  deploy:
    replicas: 3
  environment:
    - cluster.name=najaf-cluster
    - discovery.seed_hosts=es01,es02,es03
```

3. **PostgreSQL Read Replicas:**
```yaml
postgres_replica:
  image: postgis/postgis:15-3.4
  environment:
    POSTGRES_REPLICATION_MODE: slave
```

4. **Add Caching:**
```yaml
redis:
  deploy:
    resources:
      limits:
        memory: 1G
```

## 🔐 Security Checklist

- [ ] Changed default database password
- [ ] Using SFTP instead of FTP
- [ ] OpenAI API key secured (if used)
- [ ] Firewall configured (only expose necessary ports)
- [ ] HTTPS enabled (Nginx with SSL certificates)
- [ ] API rate limiting enabled
- [ ] Regular database backups scheduled
- [ ] Log files secured and rotated
- [ ] `.env` file not committed to git

## 🔄 Maintenance

### Daily:
- Monitor logs for errors
- Check service health endpoints
- Verify FTP file processing

### Weekly:
- Review Elasticsearch index health
- Check database size and performance
- Audit search query logs

### Monthly:
- Database VACUUM and ANALYZE
- Update Docker images
- Review and rotate logs
- Update SSL certificates (if manual)
- Backup database and configurations

## 📱 Client Integration

### Web Application:
```javascript
// Search graves
const response = await fetch('http://api.cemetery.com/api/search', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: 'محمد علي',
    language: 'ar',
    fuzzy: true
  })
});

// Get navigation
const route = await fetch('http://api.cemetery.com/api/route', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    record_id: '2024001',
    entrance: 'main',
    language: 'ar'
  })
});
```

### Mobile Application:
```swift
// iOS example
let url = URL(string: "http://api.cemetery.com/api/voice/audio")!
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("multipart/form-data", forHTTPHeaderField: "Content-Type")

// Upload audio for voice query
let task = URLSession.shared.uploadTask(with: request, from: audioData)
task.resume()
```

## 🎓 Next Steps

1. **Customize**: Adapt to your cemetery's specific layout
2. **Train**: Add more cemetery-specific data
3. **Extend**: Add features like QR codes, AR navigation
4. **Monitor**: Set up Prometheus + Grafana
5. **Scale**: Implement horizontal scaling as needed

## 📞 Support Resources

- **API Docs**: http://localhost:8000/docs
- **Architecture**: See `INTELLIGENT_ARCHITECTURE.md`
- **Issues**: Check logs first, then database
- **Performance**: Review `INTELLIGENT_ARCHITECTURE.md` benchmarks

---

## 🎉 Success Indicators

Your system is working correctly if:

✅ All services show "Up" in `docker-compose ps`  
✅ API health endpoint returns healthy: http://localhost:8000/health  
✅ Search returns results  
✅ Routes are calculated successfully  
✅ Voice queries get responses  
✅ FTP files are being processed  
✅ No ERROR logs in `docker-compose logs`  

**Congratulations!** You now have a state-of-the-art AI-powered cemetery management system! 🎊
