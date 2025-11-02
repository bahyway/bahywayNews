"""
Search Engine for Najaf Cemetery
Supports searching by:
- Deceased person name (Arabic, English, fuzzy matching)
- Burial company
- Date range
- Location (section, coordinates)
- Multiple languages
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result"""
    record_id: str
    deceased_name: str
    deceased_name_arabic: Optional[str]
    father_name: Optional[str]
    burial_date: date
    burial_location: str
    section: Optional[str]
    row_number: Optional[int]
    plot_number: Optional[int]
    coordinates: Optional[Tuple[float, float]]
    burial_company: Optional[str]
    relevance_score: float
    match_type: str  # 'exact', 'fuzzy', 'partial', 'phonetic'


@dataclass
class SearchQuery:
    """Search query parameters"""
    query: str
    language: str = "ar"  # ar, en, ur, fa
    search_type: str = "name"  # name, company, location
    fuzzy: bool = True
    max_results: int = 50
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    section: Optional[str] = None


class ElasticsearchIndexer:
    """
    Manages Elasticsearch index for cemetery records
    """
    
    def __init__(self, es_host: str = "localhost", es_port: int = 9200):
        self.es = Elasticsearch([f"http://{es_host}:{es_port}"])
        self.index_name = "najaf_cemetery"
        
    def create_index(self):
        """Create Elasticsearch index with proper mappings for Arabic text"""
        
        index_settings = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "arabic_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "arabic_normalization",
                                "arabic_stem"
                            ]
                        },
                        "name_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding"
                            ]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "record_id": {"type": "keyword"},
                    "deceased_name": {
                        "type": "text",
                        "analyzer": "name_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_analyzer"
                            }
                        }
                    },
                    "deceased_name_arabic": {
                        "type": "text",
                        "analyzer": "arabic_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "father_name": {
                        "type": "text",
                        "analyzer": "arabic_analyzer"
                    },
                    "grandfather_name": {
                        "type": "text",
                        "analyzer": "arabic_analyzer"
                    },
                    "burial_date": {"type": "date"},
                    "burial_location": {
                        "type": "text",
                        "analyzer": "arabic_analyzer"
                    },
                    "burial_company": {
                        "type": "text",
                        "analyzer": "arabic_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "section": {"type": "keyword"},
                    "row_number": {"type": "integer"},
                    "plot_number": {"type": "integer"},
                    "coordinates": {"type": "geo_point"},
                    "full_name_search": {
                        "type": "text",
                        "analyzer": "arabic_analyzer"
                    }
                }
            }
        }
        
        # Create index if it doesn't exist
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=index_settings)
            logger.info(f"Created Elasticsearch index: {self.index_name}")
        else:
            logger.info(f"Index {self.index_name} already exists")
    
    def index_record(self, record: Dict):
        """Index a single cemetery record"""
        
        # Prepare document
        doc = {
            "record_id": record.get("record_id"),
            "deceased_name": record.get("deceased_name"),
            "deceased_name_arabic": record.get("deceased_name_arabic"),
            "father_name": record.get("father_name"),
            "grandfather_name": record.get("grandfather_name"),
            "burial_date": record.get("burial_date"),
            "burial_location": record.get("burial_location"),
            "burial_company": record.get("burial_company"),
            "section": record.get("section"),
            "row_number": record.get("row_number"),
            "plot_number": record.get("plot_number"),
        }
        
        # Add coordinates if available
        if record.get("latitude") and record.get("longitude"):
            doc["coordinates"] = {
                "lat": record["latitude"],
                "lon": record["longitude"]
            }
        
        # Create full searchable name
        name_parts = [
            record.get("deceased_name", ""),
            record.get("deceased_name_arabic", ""),
            record.get("father_name", ""),
            record.get("grandfather_name", "")
        ]
        doc["full_name_search"] = " ".join(filter(None, name_parts))
        
        # Index document
        self.es.index(
            index=self.index_name,
            id=record["record_id"],
            body=doc
        )
    
    def bulk_index_from_postgres(self, db_config: Dict):
        """Bulk index all records from PostgreSQL"""
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            record_id,
            deceased_name,
            deceased_name_arabic,
            father_name,
            grandfather_name,
            burial_date,
            burial_location,
            section,
            row_number,
            plot_number,
            ST_Y(coordinates) as latitude,
            ST_X(coordinates) as longitude,
            additional_data->>'burial_company' as burial_company
        FROM deceased_records
        WHERE processing_status = 'completed'
        """
        
        cursor.execute(query)
        
        # Prepare bulk actions
        actions = []
        for record in cursor:
            doc = {
                "_index": self.index_name,
                "_id": record["record_id"],
                "_source": dict(record)
            }
            
            # Add coordinates
            if record.get("latitude") and record.get("longitude"):
                doc["_source"]["coordinates"] = {
                    "lat": record["latitude"],
                    "lon": record["longitude"]
                }
            
            # Full name search
            name_parts = [
                record.get("deceased_name", ""),
                record.get("deceased_name_arabic", ""),
                record.get("father_name", ""),
                record.get("grandfather_name", "")
            ]
            doc["_source"]["full_name_search"] = " ".join(filter(None, name_parts))
            
            actions.append(doc)
        
        # Bulk index
        if actions:
            success, failed = bulk(self.es, actions)
            logger.info(f"Indexed {success} documents, {failed} failed")
        
        cursor.close()
        conn.close()


class CemeterySearchEngine:
    """
    Main search engine combining Elasticsearch and PostgreSQL
    """
    
    def __init__(self, es_host: str, db_config: Dict):
        self.es = Elasticsearch([f"http://{es_host}:9200"])
        self.db_config = db_config
        self.index_name = "najaf_cemetery"
    
    def search_by_name(
        self,
        query: SearchQuery
    ) -> List[SearchResult]:
        """
        Search for deceased person by name
        Supports fuzzy matching and Arabic text
        """
        
        # Build Elasticsearch query
        should_clauses = []
        
        # Exact match (highest priority)
        should_clauses.append({
            "multi_match": {
                "query": query.query,
                "fields": [
                    "deceased_name^3",
                    "deceased_name_arabic^3",
                    "full_name_search^2"
                ],
                "type": "phrase",
                "boost": 5
            }
        })
        
        # Fuzzy match
        if query.fuzzy:
            should_clauses.append({
                "multi_match": {
                    "query": query.query,
                    "fields": [
                        "deceased_name^2",
                        "deceased_name_arabic^2",
                        "father_name",
                        "grandfather_name"
                    ],
                    "fuzziness": "AUTO",
                    "boost": 2
                }
            })
        
        # Partial match
        should_clauses.append({
            "multi_match": {
                "query": query.query,
                "fields": [
                    "full_name_search"
                ],
                "type": "best_fields",
                "boost": 1
            }
        })
        
        # Build filters
        must_filters = []
        
        if query.date_from or query.date_to:
            date_range = {}
            if query.date_from:
                date_range["gte"] = query.date_from.isoformat()
            if query.date_to:
                date_range["lte"] = query.date_to.isoformat()
            
            must_filters.append({
                "range": {
                    "burial_date": date_range
                }
            })
        
        if query.section:
            must_filters.append({
                "term": {"section": query.section}
            })
        
        # Complete Elasticsearch query
        es_query = {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
                "filter": must_filters
            }
        }
        
        # Execute search
        response = self.es.search(
            index=self.index_name,
            body={
                "query": es_query,
                "size": query.max_results,
                "_source": True
            }
        )
        
        # Parse results
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            # Get coordinates
            coords = None
            if 'coordinates' in source:
                coords = (
                    source['coordinates']['lat'],
                    source['coordinates']['lon']
                )
            
            result = SearchResult(
                record_id=source['record_id'],
                deceased_name=source.get('deceased_name', ''),
                deceased_name_arabic=source.get('deceased_name_arabic'),
                father_name=source.get('father_name'),
                burial_date=datetime.fromisoformat(source['burial_date']).date(),
                burial_location=source.get('burial_location', ''),
                section=source.get('section'),
                row_number=source.get('row_number'),
                plot_number=source.get('plot_number'),
                coordinates=coords,
                burial_company=source.get('burial_company'),
                relevance_score=hit['_score'],
                match_type=self._determine_match_type(hit)
            )
            results.append(result)
        
        logger.info(f"Found {len(results)} results for query: {query.query}")
        return results
    
    def search_by_company(
        self,
        company_name: str,
        max_results: int = 100
    ) -> List[SearchResult]:
        """Search for all burials by a specific company"""
        
        es_query = {
            "bool": {
                "should": [
                    {
                        "match": {
                            "burial_company": {
                                "query": company_name,
                                "fuzziness": "AUTO"
                            }
                        }
                    },
                    {
                        "term": {
                            "burial_company.keyword": company_name
                        }
                    }
                ]
            }
        }
        
        response = self.es.search(
            index=self.index_name,
            body={
                "query": es_query,
                "size": max_results
            }
        )
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            coords = None
            if 'coordinates' in source:
                coords = (source['coordinates']['lat'], source['coordinates']['lon'])
            
            result = SearchResult(
                record_id=source['record_id'],
                deceased_name=source.get('deceased_name', ''),
                deceased_name_arabic=source.get('deceased_name_arabic'),
                father_name=source.get('father_name'),
                burial_date=datetime.fromisoformat(source['burial_date']).date(),
                burial_location=source.get('burial_location', ''),
                section=source.get('section'),
                row_number=source.get('row_number'),
                plot_number=source.get('plot_number'),
                coordinates=coords,
                burial_company=source.get('burial_company'),
                relevance_score=hit['_score'],
                match_type='company'
            )
            results.append(result)
        
        return results
    
    def search_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 100
    ) -> List[SearchResult]:
        """Search for graves near a location (geospatial search)"""
        
        es_query = {
            "bool": {
                "filter": {
                    "geo_distance": {
                        "distance": f"{radius_meters}m",
                        "coordinates": {
                            "lat": latitude,
                            "lon": longitude
                        }
                    }
                }
            }
        }
        
        response = self.es.search(
            index=self.index_name,
            body={
                "query": es_query,
                "sort": [
                    {
                        "_geo_distance": {
                            "coordinates": {
                                "lat": latitude,
                                "lon": longitude
                            },
                            "order": "asc",
                            "unit": "m"
                        }
                    }
                ],
                "size": 50
            }
        )
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            coords = None
            if 'coordinates' in source:
                coords = (source['coordinates']['lat'], source['coordinates']['lon'])
            
            result = SearchResult(
                record_id=source['record_id'],
                deceased_name=source.get('deceased_name', ''),
                deceased_name_arabic=source.get('deceased_name_arabic'),
                father_name=source.get('father_name'),
                burial_date=datetime.fromisoformat(source['burial_date']).date(),
                burial_location=source.get('burial_location', ''),
                section=source.get('section'),
                row_number=source.get('row_number'),
                plot_number=source.get('plot_number'),
                coordinates=coords,
                burial_company=source.get('burial_company'),
                relevance_score=hit['_score'],
                match_type='location'
            )
            results.append(result)
        
        return results
    
    def _determine_match_type(self, hit: Dict) -> str:
        """Determine the type of match based on score and query"""
        score = hit['_score']
        
        if score > 10:
            return 'exact'
        elif score > 5:
            return 'fuzzy'
        elif score > 2:
            return 'partial'
        else:
            return 'phonetic'
    
    def autocomplete(self, prefix: str, max_results: int = 10) -> List[str]:
        """Autocomplete suggestions for names"""
        
        es_query = {
            "bool": {
                "should": [
                    {
                        "prefix": {
                            "deceased_name": prefix
                        }
                    },
                    {
                        "prefix": {
                            "deceased_name_arabic": prefix
                        }
                    }
                ]
            }
        }
        
        response = self.es.search(
            index=self.index_name,
            body={
                "query": es_query,
                "size": max_results,
                "_source": ["deceased_name", "deceased_name_arabic"]
            }
        )
        
        suggestions = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            name = source.get('deceased_name_arabic') or source.get('deceased_name')
            if name and name not in suggestions:
                suggestions.append(name)
        
        return suggestions


def main():
    """Test the search engine"""
    
    # Configuration
    ES_HOST = "localhost"
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'najaf_cemetery',
        'user': 'cemetery_user',
        'password': 'your_password',
        'port': 5432
    }
    
    # Initialize indexer
    indexer = ElasticsearchIndexer(ES_HOST)
    indexer.create_index()
    
    # Bulk index from PostgreSQL
    # indexer.bulk_index_from_postgres(DB_CONFIG)
    
    # Initialize search engine
    search_engine = CemeterySearchEngine(ES_HOST, DB_CONFIG)
    
    # Test search
    query = SearchQuery(
        query="محمد علي",
        language="ar",
        fuzzy=True,
        max_results=10
    )
    
    results = search_engine.search_by_name(query)
    
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"- {result.deceased_name} ({result.record_id})")
        print(f"  Score: {result.relevance_score:.2f}, Type: {result.match_type}")
        print(f"  Location: {result.section}-{result.row_number}-{result.plot_number}")
        print()


if __name__ == "__main__":
    main()
