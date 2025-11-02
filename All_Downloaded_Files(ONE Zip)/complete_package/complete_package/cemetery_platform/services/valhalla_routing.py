"""
Valhalla Routing Engine Integration
Provides navigation from cemetery entrance to specific grave locations
Supports walking routes within the cemetery
"""

import requests
import json
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RouteStep:
    """Single step in navigation route"""
    instruction: str
    instruction_arabic: str
    distance_meters: float
    duration_seconds: float
    coordinates: List[Tuple[float, float]]
    

@dataclass
class NavigationRoute:
    """Complete navigation route"""
    total_distance_meters: float
    total_duration_seconds: float
    steps: List[RouteStep]
    polyline: str
    summary: str
    summary_arabic: str
    entrance_point: Tuple[float, float]
    destination_point: Tuple[float, float]


class ValhallaRoutingEngine:
    """
    Integration with Valhalla routing engine for cemetery navigation
    """
    
    def __init__(self, valhalla_url: str, db_config: Dict):
        """
        Initialize Valhalla integration
        
        Args:
            valhalla_url: URL of Valhalla routing API
            db_config: PostgreSQL database configuration
        """
        self.valhalla_url = valhalla_url
        self.db_config = db_config
        
        # Najaf Cemetery main entrance coordinates (approximate - adjust as needed)
        self.cemetery_entrance = {
            'main': (32.0160, 44.3120),  # Main entrance
            'north': (32.0200, 44.3130),  # North gate
            'south': (32.0120, 44.3110),  # South gate
        }
    
    def _get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def get_grave_coordinates(self, record_id: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a specific grave"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            ST_Y(coordinates) as latitude,
            ST_X(coordinates) as longitude
        FROM deceased_records
        WHERE record_id = %s AND coordinates IS NOT NULL
        """
        cursor.execute(query, (record_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return (result['latitude'], result['longitude'])
        return None
    
    def find_nearest_entrance(
        self,
        destination: Tuple[float, float]
    ) -> Tuple[str, Tuple[float, float]]:
        """
        Find the nearest cemetery entrance to the destination
        
        Returns:
            Tuple of (entrance_name, coordinates)
        """
        min_distance = float('inf')
        nearest_entrance = 'main'
        nearest_coords = self.cemetery_entrance['main']
        
        for name, coords in self.cemetery_entrance.items():
            # Simple Euclidean distance (good enough for small areas)
            distance = ((destination[0] - coords[0])**2 + 
                       (destination[1] - coords[1])**2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                nearest_entrance = name
                nearest_coords = coords
        
        logger.info(f"Nearest entrance: {nearest_entrance}")
        return nearest_entrance, nearest_coords
    
    def calculate_route_valhalla(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        costing: str = "pedestrian"
    ) -> Optional[Dict]:
        """
        Calculate route using Valhalla routing engine
        
        Args:
            start: (latitude, longitude) starting point
            end: (latitude, longitude) destination
            costing: Routing profile (pedestrian, auto, bicycle)
            
        Returns:
            Valhalla route response or None if failed
        """
        # Valhalla API request format
        request_data = {
            "locations": [
                {"lat": start[0], "lon": start[1]},
                {"lat": end[0], "lon": end[1]}
            ],
            "costing": costing,
            "directions_options": {
                "units": "kilometers",
                "language": "en"
            }
        }
        
        try:
            logger.info(f"Requesting route from Valhalla: {start} -> {end}")
            
            response = requests.post(
                f"{self.valhalla_url}/route",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Valhalla returned status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Valhalla API: {e}")
            return None
    
    def parse_valhalla_response(self, valhalla_response: Dict) -> NavigationRoute:
        """Parse Valhalla response into NavigationRoute object"""
        
        if not valhalla_response or 'trip' not in valhalla_response:
            raise ValueError("Invalid Valhalla response")
        
        trip = valhalla_response['trip']
        legs = trip.get('legs', [])
        
        if not legs:
            raise ValueError("No route legs found")
        
        leg = legs[0]
        
        # Parse route steps
        steps = []
        for maneuver in leg.get('maneuvers', []):
            step = RouteStep(
                instruction=maneuver.get('instruction', ''),
                instruction_arabic=self._translate_instruction(
                    maneuver.get('instruction', '')
                ),
                distance_meters=maneuver.get('length', 0) * 1000,
                duration_seconds=maneuver.get('time', 0),
                coordinates=[]  # Would need to decode from shape
            )
            steps.append(step)
        
        # Get summary
        summary = leg.get('summary', {})
        
        route = NavigationRoute(
            total_distance_meters=summary.get('length', 0) * 1000,
            total_duration_seconds=summary.get('time', 0),
            steps=steps,
            polyline=leg.get('shape', ''),
            summary=f"{summary.get('length', 0):.2f} km, {summary.get('time', 0) / 60:.0f} minutes",
            summary_arabic=f"{summary.get('length', 0):.2f} كم، {summary.get('time', 0) / 60:.0f} دقيقة",
            entrance_point=trip['locations'][0],
            destination_point=trip['locations'][1]
        )
        
        return route
    
    def _translate_instruction(self, instruction_en: str) -> str:
        """
        Translate navigation instruction to Arabic
        Simple translation - in production, use proper translation API
        """
        translations = {
            "Continue": "استمر",
            "Turn right": "انعطف يمينًا",
            "Turn left": "انعطف يسارًا",
            "Arrive at your destination": "وصلت إلى وجهتك",
            "Head": "اتجه",
            "north": "شمالًا",
            "south": "جنوبًا",
            "east": "شرقًا",
            "west": "غربًا",
        }
        
        instruction_ar = instruction_en
        for en, ar in translations.items():
            instruction_ar = instruction_ar.replace(en, ar)
        
        return instruction_ar
    
    def get_route_to_grave(
        self,
        record_id: str,
        entrance: str = "main",
        language: str = "en"
    ) -> Optional[NavigationRoute]:
        """
        Get complete navigation route from entrance to grave
        
        Args:
            record_id: Deceased person's record ID
            entrance: Which entrance to start from (main, north, south)
            language: Response language (en, ar, ur, fa)
            
        Returns:
            NavigationRoute object or None if grave not found
        """
        # Get grave coordinates
        grave_coords = self.get_grave_coordinates(record_id)
        
        if not grave_coords:
            logger.error(f"Grave coordinates not found for record {record_id}")
            return None
        
        # Get entrance coordinates
        if entrance not in self.cemetery_entrance:
            logger.warning(f"Unknown entrance {entrance}, using main")
            entrance = "main"
        
        entrance_coords = self.cemetery_entrance[entrance]
        
        # Or find nearest entrance automatically
        # entrance_name, entrance_coords = self.find_nearest_entrance(grave_coords)
        
        # Calculate route using Valhalla
        valhalla_response = self.calculate_route_valhalla(
            entrance_coords,
            grave_coords,
            costing="pedestrian"
        )
        
        if not valhalla_response:
            logger.error("Failed to calculate route")
            return None
        
        # Parse response
        route = self.parse_valhalla_response(valhalla_response)
        
        logger.info(f"Route calculated: {route.summary}")
        return route
    
    def get_route_with_waypoints(
        self,
        waypoints: List[Tuple[float, float]],
        costing: str = "pedestrian"
    ) -> Optional[NavigationRoute]:
        """
        Get route through multiple waypoints
        Useful for visiting multiple graves in one trip
        
        Args:
            waypoints: List of (lat, lon) coordinates to visit
            costing: Routing profile
            
        Returns:
            NavigationRoute object
        """
        if len(waypoints) < 2:
            raise ValueError("Need at least 2 waypoints")
        
        request_data = {
            "locations": [
                {"lat": lat, "lon": lon} for lat, lon in waypoints
            ],
            "costing": costing,
            "directions_options": {
                "units": "kilometers",
                "language": "en"
            }
        }
        
        try:
            response = requests.post(
                f"{self.valhalla_url}/route",
                json=request_data,
                timeout=15
            )
            
            if response.status_code == 200:
                return self.parse_valhalla_response(response.json())
            else:
                logger.error(f"Valhalla returned status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Valhalla API: {e}")
            return None
    
    def optimize_multi_grave_visit(
        self,
        record_ids: List[str],
        entrance: str = "main"
    ) -> Optional[NavigationRoute]:
        """
        Optimize route to visit multiple graves (Traveling Salesman Problem)
        
        Args:
            record_ids: List of record IDs to visit
            entrance: Starting entrance
            
        Returns:
            Optimized NavigationRoute
        """
        # Get coordinates for all graves
        waypoints = [self.cemetery_entrance[entrance]]
        
        for record_id in record_ids:
            coords = self.get_grave_coordinates(record_id)
            if coords:
                waypoints.append(coords)
        
        # Return to entrance
        waypoints.append(self.cemetery_entrance[entrance])
        
        if len(waypoints) < 3:
            logger.error("Not enough valid waypoints")
            return None
        
        # Use Valhalla's optimized route (if available)
        # Or implement TSP optimization here
        
        return self.get_route_with_waypoints(waypoints)


class RouteVisualization:
    """
    Generate visualization data for displaying routes on maps
    """
    
    @staticmethod
    def decode_polyline(polyline: str, precision: int = 6) -> List[Tuple[float, float]]:
        """
        Decode Google-style encoded polyline
        
        Args:
            polyline: Encoded polyline string
            precision: Encoding precision (5 or 6)
            
        Returns:
            List of (lat, lon) coordinate pairs
        """
        coordinates = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(polyline):
            # Decode latitude
            result = 0
            shift = 0
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlat = ~(result >> 1) if result & 1 else result >> 1
            lat += dlat
            
            # Decode longitude
            result = 0
            shift = 0
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlng = ~(result >> 1) if result & 1 else result >> 1
            lng += dlng
            
            coordinates.append((
                lat / (10 ** precision),
                lng / (10 ** precision)
            ))
        
        return coordinates
    
    @staticmethod
    def to_geojson(route: NavigationRoute) -> Dict:
        """Convert route to GeoJSON format for map display"""
        coordinates = RouteVisualization.decode_polyline(route.polyline)
        
        return {
            "type": "Feature",
            "properties": {
                "distance_meters": route.total_distance_meters,
                "duration_seconds": route.total_duration_seconds,
                "summary": route.summary,
                "summary_arabic": route.summary_arabic
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in coordinates]
            }
        }


def main():
    """Test the routing engine"""
    
    # Configuration
    VALHALLA_URL = "http://localhost:8002"  # Local Valhalla instance
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'najaf_cemetery',
        'user': 'cemetery_user',
        'password': 'your_password',
        'port': 5432
    }
    
    # Initialize routing engine
    router = ValhallaRoutingEngine(VALHALLA_URL, DB_CONFIG)
    
    # Test route to a specific grave
    route = router.get_route_to_grave(
        record_id="2024001",
        entrance="main",
        language="ar"
    )
    
    if route:
        print(f"Route Summary: {route.summary}")
        print(f"Route Summary (Arabic): {route.summary_arabic}")
        print(f"Total Steps: {len(route.steps)}")
        
        # Convert to GeoJSON for display
        geojson = RouteVisualization.to_geojson(route)
        print(f"GeoJSON: {json.dumps(geojson, indent=2)}")
    else:
        print("Could not calculate route")


if __name__ == "__main__":
    main()
