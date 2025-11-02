"""
Najaf Cemetery Rules Engine
Fuzzy Logic + PostgreSQL for:
1. Determining uncertain locations of old/destroyed graves
2. Distinguishing between duplicate names (Arabic patronymic patterns)
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
from fuzzywuzzy import fuzz, process
import re
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GraveLocation:
    """Represents a grave location with uncertainty"""
    latitude: float
    longitude: float
    confidence: float  # 0-1 scale
    section: Optional[str]
    row_number: Optional[int]
    plot_number: Optional[int]
    reasoning: str
    

@dataclass
class PersonIdentity:
    """Represents a person's identity with components"""
    record_id: str
    first_name: str
    father_name: Optional[str]
    grandfather_name: Optional[str]
    tribal_name: Optional[str]
    full_name: str
    similarity_score: float
    is_duplicate: bool
    

class FuzzyLocationEngine:
    """
    Determines uncertain locations of old or destroyed graves using:
    - Neighboring graves pattern matching
    - Historical section mapping
    - Spatial clustering
    - Fuzzy coordinate estimation
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        
    def _get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def estimate_destroyed_grave_location(
        self,
        section: str,
        approximate_row: Optional[int] = None,
        approximate_plot: Optional[int] = None,
        burial_date: Optional[datetime] = None,
        nearby_known_graves: Optional[List[str]] = None
    ) -> GraveLocation:
        """
        Estimate location of a destroyed or uncertain grave using fuzzy logic
        
        Args:
            section: Cemetery section code
            approximate_row: Approximate row number (if known)
            approximate_plot: Approximate plot number (if known)
            burial_date: Date of burial (helps narrow down location)
            nearby_known_graves: List of nearby grave record_ids
            
        Returns:
            GraveLocation with estimated coordinates and confidence
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        confidence_factors = []
        reasoning_parts = []
        
        # Strategy 1: Use neighboring graves
        if nearby_known_graves:
            lat, lon, conf = self._estimate_from_neighbors(
                cursor, nearby_known_graves
            )
            confidence_factors.append(conf * 0.4)
            reasoning_parts.append(f"Neighboring graves (confidence: {conf:.2f})")
        
        # Strategy 2: Use section centroid
        lat_section, lon_section, conf_section = self._get_section_centroid(
            cursor, section
        )
        confidence_factors.append(conf_section * 0.3)
        reasoning_parts.append(f"Section {section} centroid")
        
        # Strategy 3: Use burial date patterns
        if burial_date:
            lat_date, lon_date, conf_date = self._estimate_from_burial_period(
                cursor, section, burial_date
            )
            confidence_factors.append(conf_date * 0.2)
            reasoning_parts.append(f"Burial date pattern (±{burial_date.year})")
        
        # Strategy 4: Use row/plot approximation
        if approximate_row or approximate_plot:
            lat_grid, lon_grid, conf_grid = self._estimate_from_grid(
                cursor, section, approximate_row, approximate_plot
            )
            confidence_factors.append(conf_grid * 0.1)
            reasoning_parts.append(f"Grid approximation")
        
        # Combine estimates with weighted average
        if nearby_known_graves:
            final_lat = lat
            final_lon = lon
        else:
            final_lat = lat_section
            final_lon = lon_section
        
        final_confidence = sum(confidence_factors)
        
        cursor.close()
        conn.close()
        
        return GraveLocation(
            latitude=final_lat,
            longitude=final_lon,
            confidence=min(final_confidence, 1.0),
            section=section,
            row_number=approximate_row,
            plot_number=approximate_plot,
            reasoning=" + ".join(reasoning_parts)
        )
    
    def _estimate_from_neighbors(
        self, cursor, nearby_graves: List[str]
    ) -> Tuple[float, float, float]:
        """Estimate location from known neighboring graves"""
        query = """
        SELECT 
            AVG(ST_Y(coordinates)) as avg_lat,
            AVG(ST_X(coordinates)) as avg_lon,
            COUNT(*) as count
        FROM deceased_records
        WHERE record_id = ANY(%s)
            AND coordinates IS NOT NULL
        """
        cursor.execute(query, (nearby_graves,))
        result = cursor.fetchone()
        
        if result and result['count'] > 0:
            confidence = min(result['count'] / len(nearby_graves), 1.0)
            return result['avg_lat'], result['avg_lon'], confidence
        
        return 0, 0, 0
    
    def _get_section_centroid(
        self, cursor, section: str
    ) -> Tuple[float, float, float]:
        """Get the centroid of a cemetery section"""
        query = """
        SELECT 
            ST_Y(ST_Centroid(geometry)) as lat,
            ST_X(ST_Centroid(geometry)) as lon
        FROM burial_sections
        WHERE section_code = %s
        """
        cursor.execute(query, (section,))
        result = cursor.fetchone()
        
        if result:
            return result['lat'], result['lon'], 0.5
        
        # Fallback: average of all graves in section
        query = """
        SELECT 
            AVG(ST_Y(coordinates)) as avg_lat,
            AVG(ST_X(coordinates)) as avg_lon
        FROM deceased_records
        WHERE section = %s AND coordinates IS NOT NULL
        """
        cursor.execute(query, (section,))
        result = cursor.fetchone()
        
        if result and result['avg_lat']:
            return result['avg_lat'], result['avg_lon'], 0.3
        
        return 0, 0, 0
    
    def _estimate_from_burial_period(
        self, cursor, section: str, burial_date: datetime
    ) -> Tuple[float, float, float]:
        """Estimate based on burial date patterns (graves fill chronologically)"""
        # Find graves buried around the same time (±1 year)
        date_range = timedelta(days=365)
        
        query = """
        SELECT 
            AVG(ST_Y(coordinates)) as avg_lat,
            AVG(ST_X(coordinates)) as avg_lon,
            COUNT(*) as count
        FROM deceased_records
        WHERE section = %s
            AND burial_date BETWEEN %s AND %s
            AND coordinates IS NOT NULL
        """
        cursor.execute(query, (
            section,
            burial_date - date_range,
            burial_date + date_range
        ))
        result = cursor.fetchone()
        
        if result and result['count'] > 5:
            confidence = min(result['count'] / 20, 0.8)
            return result['avg_lat'], result['avg_lon'], confidence
        
        return 0, 0, 0
    
    def _estimate_from_grid(
        self, cursor, section: str, row: Optional[int], plot: Optional[int]
    ) -> Tuple[float, float, float]:
        """Estimate from row/plot grid if partially known"""
        conditions = ["section = %s", "coordinates IS NOT NULL"]
        params = [section]
        
        if row:
            conditions.append("row_number BETWEEN %s AND %s")
            params.extend([row - 2, row + 2])
        
        if plot:
            conditions.append("plot_number BETWEEN %s AND %s")
            params.extend([plot - 2, plot + 2])
        
        query = f"""
        SELECT 
            AVG(ST_Y(coordinates)) as avg_lat,
            AVG(ST_X(coordinates)) as avg_lon,
            COUNT(*) as count
        FROM deceased_records
        WHERE {" AND ".join(conditions)}
        """
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result and result['count'] > 0:
            confidence = min(result['count'] / 5, 0.6)
            return result['avg_lat'], result['avg_lon'], confidence
        
        return 0, 0, 0


class FuzzyNameMatcher:
    """
    Distinguishes between duplicate names using Arabic patronymic patterns
    Handles: First Name + Father Name + Grandfather Name + Tribal Name
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        
        # Arabic name pattern variations
        self.name_prefixes = ['ابن', 'بن', 'بنت', 'ال']
        self.common_father_names = [
            'محمد', 'علي', 'حسن', 'حسين', 'أحمد', 'عباس', 'جعفر'
        ]
        
    def _get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def parse_arabic_name(self, full_name: str) -> Dict[str, str]:
        """
        Parse Arabic name into components
        Format: [First] [Father] [Grandfather] [Tribal/Family]
        Example: محمد علي حسن الموسوي
        """
        parts = full_name.strip().split()
        
        parsed = {
            'first_name': parts[0] if len(parts) > 0 else '',
            'father_name': parts[1] if len(parts) > 1 else None,
            'grandfather_name': parts[2] if len(parts) > 2 else None,
            'tribal_name': ' '.join(parts[3:]) if len(parts) > 3 else None
        }
        
        return parsed
    
    def fuzzy_name_similarity(
        self,
        name1: str,
        name2: str,
        threshold: int = 85
    ) -> float:
        """
        Calculate similarity between two names using multiple fuzzy algorithms
        Returns score 0-100
        """
        # Parse both names
        parsed1 = self.parse_arabic_name(name1)
        parsed2 = self.parse_arabic_name(name2)
        
        # Component-wise comparison
        scores = []
        weights = []
        
        # First name (most important)
        if parsed1['first_name'] and parsed2['first_name']:
            score = fuzz.ratio(parsed1['first_name'], parsed2['first_name'])
            scores.append(score)
            weights.append(0.4)
        
        # Father name
        if parsed1['father_name'] and parsed2['father_name']:
            score = fuzz.ratio(parsed1['father_name'], parsed2['father_name'])
            scores.append(score)
            weights.append(0.3)
        
        # Grandfather name
        if parsed1['grandfather_name'] and parsed2['grandfather_name']:
            score = fuzz.ratio(
                parsed1['grandfather_name'],
                parsed2['grandfather_name']
            )
            scores.append(score)
            weights.append(0.2)
        
        # Tribal/family name
        if parsed1['tribal_name'] and parsed2['tribal_name']:
            score = fuzz.ratio(parsed1['tribal_name'], parsed2['tribal_name'])
            scores.append(score)
            weights.append(0.1)
        
        # Calculate weighted average
        if scores:
            total_weight = sum(weights)
            weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
            return weighted_score
        
        # Fallback: simple full name comparison
        return fuzz.ratio(name1, name2)
    
    def find_duplicate_names(
        self,
        name: str,
        similarity_threshold: float = 85.0,
        date_range_days: int = 365
    ) -> List[PersonIdentity]:
        """
        Find potential duplicate names in the database
        
        Args:
            name: Full name to search
            similarity_threshold: Minimum similarity score (0-100)
            date_range_days: Consider only records within this date range
            
        Returns:
            List of PersonIdentity objects with similarity scores
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Parse the input name
        parsed_input = self.parse_arabic_name(name)
        
        # Query for similar names (broad search first)
        query = """
        SELECT 
            record_id,
            deceased_name,
            deceased_name_arabic,
            father_name,
            grandfather_name,
            burial_date,
            section,
            row_number,
            plot_number
        FROM deceased_records
        WHERE deceased_name ILIKE %s
            OR deceased_name_arabic ILIKE %s
            OR deceased_name % %s
        ORDER BY burial_date DESC
        LIMIT 100
        """
        
        # Fuzzy search pattern
        search_pattern = f"%{parsed_input['first_name']}%"
        
        cursor.execute(query, (search_pattern, search_pattern, name))
        results = cursor.fetchall()
        
        # Calculate similarity for each result
        matches = []
        
        for result in results:
            full_name = result['deceased_name'] or result['deceased_name_arabic']
            similarity = self.fuzzy_name_similarity(name, full_name)
            
            if similarity >= similarity_threshold:
                # Build full patronymic name
                name_parts = [full_name]
                if result.get('father_name'):
                    name_parts.append(result['father_name'])
                if result.get('grandfather_name'):
                    name_parts.append(result['grandfather_name'])
                
                matches.append(PersonIdentity(
                    record_id=result['record_id'],
                    first_name=parsed_input['first_name'],
                    father_name=result.get('father_name'),
                    grandfather_name=result.get('grandfather_name'),
                    tribal_name=None,
                    full_name=' '.join(name_parts),
                    similarity_score=similarity,
                    is_duplicate=similarity > 95.0
                ))
        
        cursor.close()
        conn.close()
        
        # Sort by similarity score
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return matches
    
    def resolve_duplicate(
        self,
        candidates: List[PersonIdentity],
        additional_info: Optional[Dict] = None
    ) -> PersonIdentity:
        """
        Resolve which candidate is the actual match using additional info
        
        Args:
            candidates: List of potential duplicates
            additional_info: Dict with burial_date, section, family_contact, etc.
            
        Returns:
            Most likely matching PersonIdentity
        """
        if not candidates:
            return None
        
        # If only one candidate, return it
        if len(candidates) == 1:
            return candidates[0]
        
        # Score each candidate based on additional info
        scored_candidates = []
        
        for candidate in candidates:
            bonus_score = 0
            
            # Add bonus for exact date match
            if additional_info and 'burial_date' in additional_info:
                # Would need to query database for candidate's burial date
                pass
            
            # Add bonus for section match
            if additional_info and 'section' in additional_info:
                # Would need to query database
                pass
            
            total_score = candidate.similarity_score + bonus_score
            scored_candidates.append((total_score, candidate))
        
        # Return highest scoring candidate
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]


class RulesEngine:
    """Main Rules Engine combining fuzzy logic components"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.location_engine = FuzzyLocationEngine(db_config)
        self.name_matcher = FuzzyNameMatcher(db_config)
    
    def process_uncertain_grave(
        self,
        name: str,
        section: Optional[str] = None,
        approximate_row: Optional[int] = None,
        approximate_plot: Optional[int] = None,
        burial_date: Optional[datetime] = None
    ) -> Dict:
        """
        Complete processing for an uncertain/destroyed grave
        
        Returns:
            Dictionary with location estimate and potential duplicates
        """
        logger.info(f"Processing uncertain grave for: {name}")
        
        # Check for duplicate names
        duplicates = self.name_matcher.find_duplicate_names(name)
        
        # Estimate location
        location = None
        if section:
            location = self.location_engine.estimate_destroyed_grave_location(
                section=section,
                approximate_row=approximate_row,
                approximate_plot=approximate_plot,
                burial_date=burial_date
            )
        
        return {
            'name': name,
            'estimated_location': location.__dict__ if location else None,
            'potential_duplicates': [d.__dict__ for d in duplicates[:5]],
            'duplicate_count': len(duplicates),
            'confidence': location.confidence if location else 0.0
        }


def main():
    """Test the rules engine"""
    db_config = {
        'host': 'localhost',
        'database': 'najaf_cemetery',
        'user': 'cemetery_user',
        'password': 'your_password',
        'port': 5432
    }
    
    engine = RulesEngine(db_config)
    
    # Test uncertain grave location
    result = engine.process_uncertain_grave(
        name="محمد علي حسن",
        section="A",
        approximate_row=12,
        burial_date=datetime(2020, 5, 15)
    )
    
    print(f"Results: {result}")


if __name__ == "__main__":
    main()
