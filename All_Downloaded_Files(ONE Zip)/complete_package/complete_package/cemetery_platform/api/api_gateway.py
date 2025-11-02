"""
Najaf Cemetery API Gateway
Unified API integrating all services:
- Rules Engine (Fuzzy Logic)
- Routing Engine (Valhalla)
- Search Engine (Elasticsearch + PostgreSQL)
- Voice Assistant (RAG + NLP)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date, datetime
import logging
import io
import json

# Import our engines
from rules_engine import RulesEngine, FuzzyLocationEngine, FuzzyNameMatcher
from valhalla_routing import ValhallaRoutingEngine, NavigationRoute
from search_engine import CemeterySearchEngine, SearchQuery, SearchResult
from voice_assistant import VoiceAssistant, VoiceResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Najaf Cemetery API",
    description="Intelligent Cemetery Management System with AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class SearchRequest(BaseModel):
    query: str
    language: str = "ar"
    search_type: str = "name"  # name, company, location
    fuzzy: bool = True
    max_results: int = 50
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    section: Optional[str] = None


class RouteRequest(BaseModel):
    record_id: str
    entrance: str = "main"  # main, north, south
    language: str = "en"


class MultiGraveRouteRequest(BaseModel):
    record_ids: List[str]
    entrance: str = "main"


class UncertainGraveRequest(BaseModel):
    name: str
    section: Optional[str] = None
    approximate_row: Optional[int] = None
    approximate_plot: Optional[int] = None
    burial_date: Optional[date] = None


class DuplicateCheckRequest(BaseModel):
    name: str
    similarity_threshold: float = 85.0


class VoiceQueryRequest(BaseModel):
    text: Optional[str] = None
    language: str = "arabic"


class SearchResultResponse(BaseModel):
    record_id: str
    deceased_name: str
    deceased_name_arabic: Optional[str]
    burial_date: date
    burial_location: str
    section: Optional[str]
    row_number: Optional[int]
    plot_number: Optional[int]
    coordinates: Optional[tuple]
    relevance_score: float


# ============== Global Engines Initialization ==============

DB_CONFIG = {
    'host': 'postgres',  # Docker service name
    'database': 'najaf_cemetery',
    'user': 'cemetery_user',
    'password': 'secure_password',
    'port': 5432
}

# Initialize all engines
rules_engine = RulesEngine(DB_CONFIG)
valhalla_engine = ValhallaRoutingEngine("http://valhalla:8002", DB_CONFIG)
search_engine = CemeterySearchEngine("elasticsearch", DB_CONFIG)

# Initialize voice assistant (optional - requires OpenAI API key)
try:
    voice_assistant = VoiceAssistant(
        search_engine=search_engine,
        routing_engine=valhalla_engine,
        rules_engine=rules_engine,
        openai_api_key=None  # Set via environment variable
    )
except Exception as e:
    logger.warning(f"Voice assistant initialization failed: {e}")
    voice_assistant = None


# ============== Health & Status Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Najaf Cemetery API Gateway",
        "version": "1.0.0",
        "status": "operational",
        "engines": {
            "rules_engine": "active",
            "routing_engine": "active",
            "search_engine": "active",
            "voice_assistant": "active" if voice_assistant else "inactive"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "elasticsearch": "connected",
            "valhalla": "connected"
        }
    }


# ============== Search Engine Endpoints ==============

@app.post("/api/search")
async def search_deceased(request: SearchRequest):
    """
    Search for deceased persons
    Supports fuzzy matching and Arabic text
    """
    try:
        logger.info(f"Search request: {request.query} ({request.language})")
        
        search_query = SearchQuery(
            query=request.query,
            language=request.language,
            search_type=request.search_type,
            fuzzy=request.fuzzy,
            max_results=request.max_results,
            date_from=request.date_from,
            date_to=request.date_to,
            section=request.section
        )
        
        results = search_engine.search_by_name(search_query)
        
        return {
            "success": True,
            "count": len(results),
            "results": [
                {
                    "record_id": r.record_id,
                    "deceased_name": r.deceased_name,
                    "deceased_name_arabic": r.deceased_name_arabic,
                    "burial_date": r.burial_date.isoformat(),
                    "burial_location": r.burial_location,
                    "section": r.section,
                    "row_number": r.row_number,
                    "plot_number": r.plot_number,
                    "coordinates": r.coordinates,
                    "relevance_score": r.relevance_score,
                    "match_type": r.match_type
                }
                for r in results
            ]
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/company/{company_name}")
async def search_by_company(
    company_name: str,
    max_results: int = Query(100, ge=1, le=500)
):
    """Search all burials by a specific company"""
    try:
        results = search_engine.search_by_company(company_name, max_results)
        
        return {
            "success": True,
            "company": company_name,
            "count": len(results),
            "results": [
                {
                    "record_id": r.record_id,
                    "deceased_name": r.deceased_name,
                    "burial_date": r.burial_date.isoformat(),
                    "section": r.section
                }
                for r in results
            ]
        }
    
    except Exception as e:
        logger.error(f"Company search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/location")
async def search_by_location(
    latitude: float,
    longitude: float,
    radius_meters: float = Query(100, ge=10, le=1000)
):
    """Search for graves near a specific location"""
    try:
        results = search_engine.search_by_location(
            latitude, longitude, radius_meters
        )
        
        return {
            "success": True,
            "location": {"lat": latitude, "lon": longitude},
            "radius_meters": radius_meters,
            "count": len(results),
            "results": [
                {
                    "record_id": r.record_id,
                    "deceased_name": r.deceased_name,
                    "distance_meters": "calculated_by_es",
                    "coordinates": r.coordinates
                }
                for r in results
            ]
        }
    
    except Exception as e:
        logger.error(f"Location search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/autocomplete")
async def autocomplete(
    prefix: str,
    max_results: int = Query(10, ge=1, le=50)
):
    """Autocomplete suggestions for names"""
    try:
        suggestions = search_engine.autocomplete(prefix, max_results)
        return {
            "success": True,
            "suggestions": suggestions
        }
    
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Routing Engine Endpoints ==============

@app.post("/api/route")
async def get_route(request: RouteRequest):
    """Get navigation route from entrance to grave"""
    try:
        route = valhalla_engine.get_route_to_grave(
            request.record_id,
            request.entrance,
            request.language
        )
        
        if not route:
            raise HTTPException(
                status_code=404,
                detail="Could not calculate route"
            )
        
        return {
            "success": True,
            "route": {
                "total_distance_meters": route.total_distance_meters,
                "total_duration_seconds": route.total_duration_seconds,
                "summary": route.summary,
                "summary_arabic": route.summary_arabic,
                "polyline": route.polyline,
                "steps": [
                    {
                        "instruction": step.instruction,
                        "instruction_arabic": step.instruction_arabic,
                        "distance_meters": step.distance_meters,
                        "duration_seconds": step.duration_seconds
                    }
                    for step in route.steps
                ],
                "entrance": {
                    "lat": route.entrance_point[0],
                    "lon": route.entrance_point[1]
                },
                "destination": {
                    "lat": route.destination_point[0],
                    "lon": route.destination_point[1]
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Routing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/route/multi-grave")
async def get_multi_grave_route(request: MultiGraveRouteRequest):
    """Get optimized route to visit multiple graves"""
    try:
        route = valhalla_engine.optimize_multi_grave_visit(
            request.record_ids,
            request.entrance
        )
        
        if not route:
            raise HTTPException(
                status_code=404,
                detail="Could not calculate multi-grave route"
            )
        
        return {
            "success": True,
            "graves_count": len(request.record_ids),
            "route": {
                "total_distance_meters": route.total_distance_meters,
                "total_duration_seconds": route.total_duration_seconds,
                "summary": route.summary
            }
        }
    
    except Exception as e:
        logger.error(f"Multi-grave routing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Rules Engine Endpoints ==============

@app.post("/api/rules/uncertain-grave")
async def estimate_grave_location(request: UncertainGraveRequest):
    """Estimate location of destroyed or uncertain grave using fuzzy logic"""
    try:
        result = rules_engine.process_uncertain_grave(
            name=request.name,
            section=request.section,
            approximate_row=request.approximate_row,
            approximate_plot=request.approximate_plot,
            burial_date=request.burial_date
        )
        
        return {
            "success": True,
            "name": result['name'],
            "estimated_location": result['estimated_location'],
            "potential_duplicates": result['potential_duplicates'],
            "duplicate_count": result['duplicate_count'],
            "confidence": result['confidence']
        }
    
    except Exception as e:
        logger.error(f"Uncertain grave error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/check-duplicates")
async def check_duplicate_names(request: DuplicateCheckRequest):
    """Check for duplicate/similar names in database"""
    try:
        matches = rules_engine.name_matcher.find_duplicate_names(
            request.name,
            request.similarity_threshold
        )
        
        return {
            "success": True,
            "query_name": request.name,
            "matches_found": len(matches),
            "matches": [
                {
                    "record_id": m.record_id,
                    "full_name": m.full_name,
                    "similarity_score": m.similarity_score,
                    "is_duplicate": m.is_duplicate
                }
                for m in matches
            ]
        }
    
    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Voice Assistant Endpoints ==============

@app.post("/api/voice/query")
async def voice_query_text(request: VoiceQueryRequest):
    """Process text voice query (for testing without audio)"""
    if not voice_assistant:
        raise HTTPException(
            status_code=503,
            detail="Voice assistant not available"
        )
    
    try:
        response = voice_assistant.process_voice_query(
            text_query=request.text,
            language=request.language
        )
        
        return {
            "success": response.success,
            "text": response.text,
            "language": response.language,
            "context": response.context,
            "audio_available": len(response.audio_data) > 0
        }
    
    except Exception as e:
        logger.error(f"Voice query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/audio")
async def voice_query_audio(
    audio: UploadFile = File(...),
    language: str = Query("arabic")
):
    """Process audio voice query"""
    if not voice_assistant:
        raise HTTPException(
            status_code=503,
            detail="Voice assistant not available"
        )
    
    try:
        # Save uploaded audio temporarily
        audio_path = f"/tmp/{audio.filename}"
        with open(audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        # Process voice query
        response = voice_assistant.process_voice_query(
            audio_file_path=audio_path,
            language=language
        )
        
        # Return audio response as streaming
        if response.audio_data:
            return StreamingResponse(
                io.BytesIO(response.audio_data),
                media_type="audio/mpeg",
                headers={
                    "X-Response-Text": response.text,
                    "X-Language": response.language,
                    "X-Success": str(response.success)
                }
            )
        else:
            return {
                "success": response.success,
                "text": response.text,
                "error": "No audio generated"
            }
    
    except Exception as e:
        logger.error(f"Audio voice query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Statistics & Analytics Endpoints ==============

@app.get("/api/stats/daily")
async def get_daily_stats():
    """Get daily burial statistics"""
    # Would query from database
    return {
        "success": True,
        "date": datetime.now().date().isoformat(),
        "total_burials_today": 0,
        "total_burials_all_time": 0
    }


@app.get("/api/stats/sections")
async def get_section_occupancy():
    """Get cemetery section occupancy statistics"""
    # Would query from database
    return {
        "success": True,
        "sections": []
    }


# Run with: uvicorn api_gateway:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
