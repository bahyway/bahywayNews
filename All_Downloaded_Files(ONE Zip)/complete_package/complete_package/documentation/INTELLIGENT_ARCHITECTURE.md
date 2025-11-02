# Najaf Cemetery Intelligent System - Complete Architecture

## Executive Summary

A **multi-engine AI-powered cemetery management system** that processes 1000+ daily deceased records and provides intelligent services through voice interface in multiple languages (Arabic, English, Urdu, Persian).

## System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACES                              │
│  🌐 Web App  │  📱 Mobile App  │  🎤 Voice Interface (Multi-language) │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                          │
│  - RESTful API endpoints                                              │
│  - Request routing                                                    │
│  - Response aggregation                                               │
└────────────┬────────────┬────────────┬────────────┬───────────────────┘
             │            │            │            │
    ┌────────▼────┐  ┌───▼─────┐  ┌──▼──────┐  ┌──▼─────────────────┐
    │ RULES       │  │ ROUTING │  │ SEARCH  │  │ VOICE ASSISTANT    │
    │ ENGINE      │  │ ENGINE  │  │ ENGINE  │  │ (RAG + NLP)        │
    └─────────────┘  └─────────┘  └─────────┘  └────────────────────┘
```

## Three Intelligent Engine Layers

### 1️⃣ **Rules Engine - Fuzzy Logic + PostgreSQL**

**Purpose:** Handle uncertainty and ambiguity in cemetery data

#### Components:
- **Fuzzy Location Engine**: Estimates locations of destroyed/uncertain graves
- **Fuzzy Name Matcher**: Distinguishes between duplicate Arabic names

#### Use Cases:

**A) Uncertain Grave Location Estimation**
```
Problem: Old grave destroyed, only knows:
- Section: A
- Approximate row: 12
- Burial date: ~1985

Solution (Fuzzy Logic):
1. Find neighboring graves in database
2. Calculate section centroid
3. Analyze burial date patterns (graves filled chronologically)
4. Apply weighted average algorithm
5. Return: Estimated coordinates + confidence score
```

**B) Duplicate Name Detection**
```
Problem: "محمد علي حسن" appears 247 times

Solution (Fuzzy Matching):
1. Parse name: First + Father + Grandfather + Tribal
2. Calculate component-wise similarity scores
3. Weight components (First: 40%, Father: 30%, etc.)
4. Return: Ranked list with similarity scores
5. Resolve using additional data (date, section, family)
```

#### Algorithms:
- **Levenshtein Distance** for string similarity
- **Spatial Clustering** for location estimation
- **Temporal Pattern Matching** for date-based inference
- **Weighted Scoring** for confidence calculation

#### API Endpoints:
```
POST /api/rules/uncertain-grave
POST /api/rules/check-duplicates
```

### 2️⃣ **Routing Engine - Valhalla Integration**

**Purpose:** Navigation from cemetery entrance to grave location

#### Architecture:
```
User Request → API Gateway → Valhalla Engine → Route Calculation
                                ↓
                          PostgreSQL (grave coordinates)
                                ↓
                          Turn-by-turn directions
```

#### Features:
- **Single Grave Navigation**: Entrance → Specific grave
- **Multi-Grave Optimization**: Visit multiple graves (TSP solution)
- **Multiple Entrances**: Main, North, South gates
- **Walking Routes**: Pedestrian-optimized paths
- **Multi-language Directions**: Arabic, English, Urdu, Persian

#### Route Calculation Process:
1. Query grave coordinates from PostgreSQL
2. Determine nearest entrance (or use specified)
3. Call Valhalla API with coordinates
4. Parse polyline and instructions
5. Translate instructions to target language
6. Return: Distance, duration, step-by-step directions

#### API Endpoints:
```
POST /api/route                 # Single grave route
POST /api/route/multi-grave     # Multi-grave optimized route
```

#### Example Response:
```json
{
  "total_distance_meters": 234.5,
  "total_duration_seconds": 180,
  "summary": "235m, 3 minutes",
  "summary_arabic": "٢٣٥ متر، ٣ دقائق",
  "steps": [
    {
      "instruction": "Head north",
      "instruction_arabic": "اتجه شمالًا",
      "distance_meters": 50,
      "duration_seconds": 40
    }
  ]
}
```

### 3️⃣ **Search Engine - Elasticsearch + PostgreSQL**

**Purpose:** Fast, multi-language, fuzzy search for deceased persons and companies

#### Architecture:
```
PostgreSQL (Source of Truth)
     ↓ Bulk Index
Elasticsearch (Search Index)
     ↓ Query
Search Results (Ranked by Relevance)
```

#### Features:
- **Multi-language Search**: Arabic, English, Urdu, Persian
- **Fuzzy Matching**: Handles typos and variations
- **Phonetic Matching**: Similar-sounding names
- **Autocomplete**: Real-time suggestions
- **Geospatial Search**: Find graves near location
- **Company Search**: All burials by specific company
- **Date Range Filtering**: Search by burial date
- **Section Filtering**: Limit to specific cemetery sections

#### Search Types:

**1. Name Search**
```
Input: "محمد علي" (fuzzy=true)
Process:
- Exact match (boost: 5x)
- Fuzzy match with Levenshtein distance
- Partial match on full name
- Arabic text normalization
Result: Ranked list with relevance scores
```

**2. Company Search**
```
Input: "شركة النجف للجنائز"
Process:
- Exact company name match
- Fuzzy company name match
Result: All burials by that company
```

**3. Location Search**
```
Input: lat=32.0175, lon=44.3142, radius=100m
Process:
- Geospatial distance calculation
- Sort by distance
Result: Nearest graves
```

#### Elasticsearch Index Mapping:
```json
{
  "deceased_name": {
    "type": "text",
    "analyzer": "arabic_analyzer",
    "fields": {
      "keyword": {"type": "keyword"},
      "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
    }
  },
  "coordinates": {"type": "geo_point"},
  "burial_date": {"type": "date"}
}
```

#### API Endpoints:
```
POST   /api/search                    # Main search
GET    /api/search/company/{name}     # Company search
GET    /api/search/location           # Geospatial search
GET    /api/search/autocomplete       # Autocomplete
```

## 4️⃣ **RAG + NLP Voice Assistant**

**Purpose:** Natural language voice interface in multiple languages

### Architecture:
```
Voice Input (Audio) → Speech-to-Text → Intent Classification
                           ↓
                    Entity Extraction
                           ↓
              Execute (Search/Route/Rules)
                           ↓
          RAG (Retrieval-Augmented Generation)
                           ↓
                 Natural Language Response
                           ↓
               Text-to-Speech → Voice Output
```

### Components:

#### 1. **Speech Recognition** (Multi-language STT)
- Google Speech API
- Supports: Arabic (ar-SA), English (en-US), Urdu (ur-PK), Persian (fa-IR)
- Handles audio files and real-time microphone input

#### 2. **NLP Intent Classification**
- Classifies user intent into:
  - `search_person`: Looking for a specific grave
  - `get_directions`: Asking for navigation
  - `find_company`: Company information
  - `general_info`: General cemetery questions
  
- Pattern matching + GPT-3.5 fallback
- Confidence scoring

#### 3. **Entity Extraction**
- Person names (with Arabic patronymic parsing)
- Location information
- Date references
- Company names

#### 4. **RAG (Retrieval-Augmented Generation)**
- Retrieves relevant data from:
  - Search Engine results
  - Routing Engine directions
  - Rules Engine estimates
- Generates contextual response using:
  - Template-based (fast, no API)
  - GPT-based (natural, requires OpenAI API)

#### 5. **Text-to-Speech** (Multi-language TTS)
- gTTS (Google Text-to-Speech)
- Outputs MP3 audio
- Natural pronunciation for each language

### Voice Query Examples:

**Arabic:**
```
User: "أين قبر محمد علي حسن؟"
Assistant: 
  1. Recognizes Arabic speech
  2. Classifies intent: search_person
  3. Extracts: "محمد علي حسن"
  4. Searches database
  5. Responds: "وجدت قبر محمد علي حسن في القسم أ، الصف ١٢، المقبرة ٤٥"
  6. Returns Arabic audio
```

**English:**
```
User: "How do I get to grave A-12-45?"
Assistant:
  1. Recognizes English speech
  2. Classifies intent: get_directions
  3. Extracts: section=A, row=12, plot=45
  4. Calculates route
  5. Responds: "Walk 235 meters north for 3 minutes..."
  6. Returns English audio
```

### API Endpoints:
```
POST /api/voice/query          # Text-based query (testing)
POST /api/voice/audio          # Audio-based query
```

## Data Flow - Complete System

### Daily Processing Cycle

```
1. 00:00-08:00  Government generates deceased records
                    ↓
2. 08:00        ZIP file → FTP server
                    ↓
3. 08:30        Python FTP Monitor detects & downloads
                    ↓
4. 08:31        File extracted to staging
                    ↓
5. 08:32        Rust Processor triggered
                    ↓
6. 08:35        1000+ records processed
                    ↓
7. 08:36        PostgreSQL updated
                    ↓
8. 08:37        Elasticsearch reindexed
                    ↓
9. 09:00        GeoJSON export & map update
                    ↓
10. ALL DAY     Voice Assistant serves queries
                Rules Engine handles uncertainties
                Routing Engine provides directions
                Search Engine finds graves
```

### Real-time Query Flow

```
User Voice Query (Arabic): "أين قبر محمد علي؟"
        ↓
1. Speech-to-Text → "أين قبر محمد علي؟"
        ↓
2. Intent Classification → search_person
        ↓
3. Entity Extraction → name: "محمد علي"
        ↓
4. Search Engine Query → Returns 3 matches
        ↓
5. Rules Engine Check → Identifies duplicates
        ↓
6. RAG Generation → Natural response
        ↓
7. Text-to-Speech → Arabic audio
        ↓
Response: "وجدت ٣ نتائج. الأقرب في القسم أ..."
```

## Technology Stack

### Core Languages:
- **Python**: Engines, API Gateway, Voice Assistant
- **Rust**: High-performance data processing
- **SQL**: Database queries and spatial operations

### Frameworks & Libraries:
- **FastAPI**: API Gateway
- **Elasticsearch**: Search engine
- **Valhalla**: Routing engine
- **OpenAI GPT**: NLP and response generation
- **FuzzyWuzzy**: Fuzzy string matching
- **SpeechRecognition**: STT
- **gTTS**: TTS
- **PostGIS**: Spatial database

### Infrastructure:
- **PostgreSQL + PostGIS**: Spatial database
- **Docker + Docker Compose**: Containerization
- **Nginx**: Reverse proxy
- **Redis**: Optional caching

## Database Schema Updates

### New Fields for Intelligent Features:
```sql
ALTER TABLE deceased_records ADD COLUMN
  father_name VARCHAR(255),
  grandfather_name VARCHAR(255),
  tribal_name VARCHAR(255),
  location_confidence FLOAT,
  duplicate_group_id VARCHAR(50);

CREATE INDEX idx_name_components ON deceased_records 
  (deceased_name, father_name, grandfather_name);
```

## Performance Benchmarks

| Operation | Time | Throughput |
|-----------|------|------------|
| Fuzzy name search | 50-100ms | 10-20 queries/sec |
| Route calculation | 200-500ms | 2-5 routes/sec |
| Elasticsearch search | 10-50ms | 20-100 queries/sec |
| Voice query (full) | 2-5 seconds | 0.2-0.5 queries/sec |
| Data processing | 3-5 min | 300-500 records/sec |

## Security Considerations

1. **API Authentication**: JWT tokens for API access
2. **Voice Privacy**: Audio not stored, only transcribed text
3. **Database Encryption**: At-rest encryption for PostgreSQL
4. **Rate Limiting**: Prevent API abuse
5. **Input Validation**: Sanitize all user inputs
6. **HTTPS**: All API endpoints over TLS

## Scalability

### Current Capacity (1000 records/day):
- Single instance of each service
- ~10-50 concurrent users
- ~100-500 queries/minute

### Future Scale (5000+ records/day):
- Horizontal scaling: Multiple API Gateway instances
- Elasticsearch cluster: 3+ nodes
- PostgreSQL read replicas
- Redis caching layer
- Message queue (RabbitMQ/Kafka)
- Load balancer (Nginx/HAProxy)

## Deployment Architecture

```
           Internet
              ↓
        [Load Balancer]
              ↓
      [API Gateway x3]  ← Horizontal scaling
         ↙    ↓    ↘
    [Search] [Route] [Rules] [Voice]
         ↓      ↓      ↓       ↓
      [Elasticsearch] [Valhalla]
              ↓
        [PostgreSQL]
         Master → Read Replica
              ↓
          [Redis Cache]
```

## Monitoring & Observability

### Metrics to Track:
- API response times (p50, p95, p99)
- Search query latency
- Route calculation time
- Voice query success rate
- Database query performance
- Elasticsearch index health
- System resource usage (CPU, memory, disk)

### Logging:
- Structured JSON logging
- Log aggregation (ELK stack)
- Error tracking (Sentry)
- Audit logs for all operations

## Future Enhancements

1. **Computer Vision**: Grave photo recognition
2. **AR Navigation**: Augmented reality wayfinding
3. **Predictive Analytics**: Capacity planning
4. **Family Trees**: Genealogy linking
5. **Memorial Pages**: Digital tributes
6. **QR Codes**: On-grave information
7. **Mobile App**: Native iOS/Android
8. **Offline Mode**: Cached data for areas with no network

## Cost Estimation

### Monthly Running Costs (AWS/Cloud):
- EC2/Compute: $100-200
- RDS PostgreSQL: $50-100
- Elasticsearch: $100-200
- Storage (S3/EBS): $20-50
- OpenAI API: $10-50 (depends on usage)
- **Total**: ~$280-600/month

### On-Premise Alternative:
- Hardware: $2000-5000 one-time
- Electricity: $30-50/month
- No API costs (use local LLMs)

## Conclusion

This intelligent cemetery system combines:
✅ **Fuzzy Logic** for handling uncertainty
✅ **Routing Engine** for navigation
✅ **Search Engine** for fast queries
✅ **Voice Assistant** for natural interaction
✅ **Multi-language Support** for diverse users
✅ **RAG + NLP** for contextual responses

Result: A comprehensive, AI-powered solution that transforms cemetery management from manual record-keeping to intelligent, accessible information system.
