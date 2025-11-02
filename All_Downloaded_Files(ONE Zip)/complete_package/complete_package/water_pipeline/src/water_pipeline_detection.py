"""
Water Pipeline Defect Detection System
Using Drone/Satellite Imagery + Knowledge Graph + Fuzzy Logic

For detecting underground water pipeline leaks in war-zone urban areas
Combines: Computer Vision + Apache TinkerPop + Fuzzy Logic
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# Deep Learning
try:
    import torch
    import torchvision
    from torchvision.models.detection import fasterrcnn_resnet50_fpn
except ImportError:
    pass

# Knowledge Graph (Apache TinkerPop via Gremlin-Python)
try:
    from gremlin_python.driver import client, serializer
    from gremlin_python.process.anonymous_traversal import traversal
    from gremlin_python.process.graph_traversal import __
    from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LeakIndicator:
    """Detected leak indicator from imagery"""
    location: Tuple[float, float]  # (lat, lon)
    indicator_type: str  # 'thermal', 'vegetation', 'subsidence', 'ponding'
    confidence: float  # 0-1
    severity: float  # 0-1
    timestamp: datetime
    image_source: str  # 'drone', 'satellite'
    metadata: Dict


@dataclass
class PipelineSegment:
    """Water pipeline segment in graph"""
    segment_id: str
    start_node: str
    end_node: str
    pipe_material: str  # 'steel', 'pvc', 'concrete'
    diameter_mm: float
    age_years: float
    length_meters: float
    coordinates: List[Tuple[float, float]]
    historical_leaks: int


@dataclass
class DefectProbability:
    """Fuzzy logic-based defect probability"""
    segment_id: str
    probability: float  # 0-1
    contributing_factors: Dict[str, float]
    recommended_action: str
    urgency: str  # 'low', 'medium', 'high', 'critical'


# ============================================================
# 1. EXISTING ALGORITHMS FOR LEAK DETECTION
# ============================================================

class ThermalLeakDetector:
    """
    Algorithm: Thermal Anomaly Detection
    Source: NASA, ESA thermal imaging research
    
    Principle: Water leaks cause temperature anomalies
    - Leaking water is cooler than surrounding soil (daytime)
    - Or warmer than surroundings (nighttime)
    """
    
    def __init__(self, threshold_celsius: float = 2.0):
        self.threshold = threshold_celsius
    
    def detect_from_thermal_image(
        self,
        thermal_image: np.ndarray,  # Temperature in Celsius
        reference_temp: float
    ) -> List[LeakIndicator]:
        """
        Detect thermal anomalies indicating leaks
        
        Works with:
        - FLIR thermal cameras on drones
        - Landsat 8 thermal band
        - Sentinel-2 thermal bands
        """
        
        # Calculate temperature difference
        temp_diff = np.abs(thermal_image - reference_temp)
        
        # Find anomalies
        anomaly_mask = temp_diff > self.threshold
        
        # Find connected components (leak locations)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            anomaly_mask.astype(np.uint8), connectivity=8
        )
        
        indicators = []
        for i in range(1, num_labels):  # Skip background
            area = stats[i, cv2.CC_STAT_AREA]
            
            if area > 10:  # Minimum area threshold
                cx, cy = centroids[i]
                
                # Calculate severity based on temperature difference
                roi = thermal_image[labels == i]
                max_diff = np.max(np.abs(roi - reference_temp))
                severity = min(max_diff / 10.0, 1.0)  # Normalize to 0-1
                
                indicators.append(LeakIndicator(
                    location=(cy, cx),  # Will convert to lat/lon later
                    indicator_type='thermal',
                    confidence=0.8,
                    severity=severity,
                    timestamp=datetime.now(),
                    image_source='thermal',
                    metadata={'temp_diff': float(max_diff), 'area': int(area)}
                ))
        
        return indicators


class VegetationLeakDetector:
    """
    Algorithm: Vegetation Index Analysis
    Source: Remote Sensing literature, USGS
    
    Principle: Water leaks cause vegetation to be greener/healthier
    Uses NDVI (Normalized Difference Vegetation Index)
    """
    
    def __init__(self):
        pass
    
    def calculate_ndvi(
        self,
        nir_band: np.ndarray,  # Near-infrared band
        red_band: np.ndarray   # Red band
    ) -> np.ndarray:
        """
        NDVI = (NIR - Red) / (NIR + Red)
        
        Available from:
        - Multispectral drones
        - Sentinel-2 satellite
        - Landsat 8
        """
        
        # Avoid division by zero
        denominator = nir_band + red_band
        denominator[denominator == 0] = 1e-10
        
        ndvi = (nir_band - red_band) / denominator
        
        return ndvi
    
    def detect_from_multispectral(
        self,
        nir_band: np.ndarray,
        red_band: np.ndarray,
        baseline_ndvi: Optional[np.ndarray] = None
    ) -> List[LeakIndicator]:
        """
        Detect vegetation anomalies indicating water leaks
        """
        
        # Calculate NDVI
        ndvi = self.calculate_ndvi(nir_band, red_band)
        
        if baseline_ndvi is None:
            # Use median as baseline
            baseline_ndvi = np.median(ndvi)
        
        # Find areas with unusually high NDVI (greener than normal)
        ndvi_diff = ndvi - baseline_ndvi
        anomaly_mask = ndvi_diff > 0.15  # Threshold
        
        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        anomaly_mask = cv2.morphologyEx(
            anomaly_mask.astype(np.uint8),
            cv2.MORPH_CLOSE,
            kernel
        )
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            anomaly_mask, connectivity=8
        )
        
        indicators = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            
            if area > 20:  # Minimum area
                cx, cy = centroids[i]
                
                # Calculate severity
                roi = ndvi_diff[labels == i]
                max_ndvi_diff = np.max(roi)
                severity = min(max_ndvi_diff / 0.3, 1.0)
                
                indicators.append(LeakIndicator(
                    location=(cy, cx),
                    indicator_type='vegetation',
                    confidence=0.7,
                    severity=severity,
                    timestamp=datetime.now(),
                    image_source='multispectral',
                    metadata={'ndvi_diff': float(max_ndvi_diff), 'area': int(area)}
                ))
        
        return indicators


class SubsidenceDetector:
    """
    Algorithm: Ground Subsidence Detection via Change Detection
    Source: InSAR (Interferometric Synthetic Aperture Radar) research
    
    Principle: Water leaks cause soil erosion → ground subsidence
    Uses: Temporal image comparison
    """
    
    def __init__(self):
        pass
    
    def detect_subsidence(
        self,
        image_before: np.ndarray,
        image_after: np.ndarray,
        threshold: float = 0.1
    ) -> List[LeakIndicator]:
        """
        Detect ground subsidence using change detection
        
        Works with:
        - High-resolution drone imagery (temporal)
        - DEM (Digital Elevation Model) comparison
        - LiDAR data
        """
        
        # Convert to grayscale if needed
        if len(image_before.shape) == 3:
            before_gray = cv2.cvtColor(image_before, cv2.COLOR_BGR2GRAY)
            after_gray = cv2.cvtColor(image_after, cv2.COLOR_BGR2GRAY)
        else:
            before_gray = image_before
            after_gray = image_after
        
        # Calculate difference
        diff = cv2.absdiff(before_gray, after_gray)
        
        # Normalize
        diff_norm = diff / 255.0
        
        # Threshold
        subsidence_mask = diff_norm > threshold
        
        # Morphological operations
        kernel = np.ones((7, 7), np.uint8)
        subsidence_mask = cv2.morphologyEx(
            subsidence_mask.astype(np.uint8),
            cv2.MORPH_CLOSE,
            kernel
        )
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            subsidence_mask, connectivity=8
        )
        
        indicators = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            
            if area > 30:
                cx, cy = centroids[i]
                
                # Calculate severity
                roi = diff_norm[labels == i]
                max_change = np.max(roi)
                severity = min(max_change / 0.5, 1.0)
                
                indicators.append(LeakIndicator(
                    location=(cy, cx),
                    indicator_type='subsidence',
                    confidence=0.75,
                    severity=severity,
                    timestamp=datetime.now(),
                    image_source='drone',
                    metadata={'change': float(max_change), 'area': int(area)}
                ))
        
        return indicators


class WaterPondingDetector:
    """
    Algorithm: Water Ponding Detection using NDWI
    Source: McFeeters (1996), Xu (2006)
    
    Principle: Surface water accumulation from underground leaks
    Uses: NDWI (Normalized Difference Water Index)
    """
    
    def __init__(self):
        pass
    
    def calculate_ndwi(
        self,
        green_band: np.ndarray,
        nir_band: np.ndarray
    ) -> np.ndarray:
        """
        NDWI = (Green - NIR) / (Green + NIR)
        
        Highlights water bodies and wet areas
        """
        
        denominator = green_band + nir_band
        denominator[denominator == 0] = 1e-10
        
        ndwi = (green_band - nir_band) / denominator
        
        return ndwi
    
    def detect_water_accumulation(
        self,
        green_band: np.ndarray,
        nir_band: np.ndarray,
        threshold: float = 0.3
    ) -> List[LeakIndicator]:
        """
        Detect surface water accumulation indicating leaks
        """
        
        # Calculate NDWI
        ndwi = self.calculate_ndwi(green_band, nir_band)
        
        # Threshold for water
        water_mask = ndwi > threshold
        
        # Remove large water bodies (not leaks)
        kernel = np.ones((15, 15), np.uint8)
        water_mask_cleaned = cv2.morphologyEx(
            water_mask.astype(np.uint8),
            cv2.MORPH_OPEN,
            kernel
        )
        
        # Find small ponding areas
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            water_mask_cleaned, connectivity=8
        )
        
        indicators = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            
            # Look for small to medium ponding (not rivers/lakes)
            if 15 < area < 500:
                cx, cy = centroids[i]
                
                # Calculate severity
                roi = ndwi[labels == i]
                max_ndwi = np.max(roi)
                severity = min((max_ndwi - threshold) / 0.5, 1.0)
                
                indicators.append(LeakIndicator(
                    location=(cy, cx),
                    indicator_type='ponding',
                    confidence=0.85,
                    severity=severity,
                    timestamp=datetime.now(),
                    image_source='multispectral',
                    metadata={'ndwi': float(max_ndwi), 'area': int(area)}
                ))
        
        return indicators


# ============================================================
# 2. KNOWLEDGE GRAPH INTEGRATION (Apache TinkerPop)
# ============================================================

class WaterNetworkGraph:
    """
    Knowledge Graph for water pipeline network
    Uses Apache TinkerPop (Gremlin)
    
    Graph Structure:
    - Vertices: Junction points, valves, pumps, leak indicators
    - Edges: Pipeline segments with properties
    """
    
    def __init__(self, gremlin_endpoint: str = "ws://localhost:8182/gremlin"):
        """
        Initialize connection to TinkerPop graph database
        (e.g., JanusGraph, Neo4j, AWS Neptune)
        """
        try:
            self.connection = DriverRemoteConnection(
                gremlin_endpoint,
                'g'
            )
            self.g = traversal().withRemote(self.connection)
            logger.info("Connected to TinkerPop graph database")
        except Exception as e:
            logger.error(f"Could not connect to graph: {e}")
            self.g = None
    
    def create_pipeline_network(
        self,
        junctions: List[Dict],
        pipelines: List[PipelineSegment]
    ):
        """
        Create water network topology in graph
        """
        
        if not self.g:
            return
        
        # Create junction vertices
        for junction in junctions:
            self.g.addV('junction').property(
                'junction_id', junction['id']
            ).property(
                'lat', junction['lat']
            ).property(
                'lon', junction['lon']
            ).property(
                'elevation_m', junction.get('elevation', 0)
            ).iterate()
        
        # Create pipeline edge segments
        for pipe in pipelines:
            self.g.V().has('junction', 'junction_id', pipe.start_node).as_('start')\
                .V().has('junction', 'junction_id', pipe.end_node).as_('end')\
                .addE('pipeline').from_('start').to('end')\
                .property('segment_id', pipe.segment_id)\
                .property('material', pipe.pipe_material)\
                .property('diameter_mm', pipe.diameter_mm)\
                .property('age_years', pipe.age_years)\
                .property('length_m', pipe.length_meters)\
                .property('historical_leaks', pipe.historical_leaks)\
                .iterate()
        
        logger.info(f"Created network with {len(junctions)} junctions and {len(pipelines)} pipelines")
    
    def add_leak_indicator(
        self,
        indicator: LeakIndicator,
        nearby_segment_id: str
    ):
        """
        Add detected leak indicator to graph
        """
        
        if not self.g:
            return
        
        # Create leak indicator vertex
        self.g.addV('leak_indicator').property(
            'indicator_id', f"LEAK_{datetime.now().timestamp()}"
        ).property(
            'lat', indicator.location[0]
        ).property(
            'lon', indicator.location[1]
        ).property(
            'type', indicator.indicator_type
        ).property(
            'confidence', indicator.confidence
        ).property(
            'severity', indicator.severity
        ).property(
            'timestamp', indicator.timestamp.isoformat()
        ).iterate()
        
        # Link to nearest pipeline segment
        self.g.V().has('leak_indicator', 'lat', indicator.location[0]).as_('leak')\
            .V().hasLabel('junction').as_('j1')\
            .outE('pipeline').has('segment_id', nearby_segment_id).as_('pipe')\
            .inV().as_('j2')\
            .addE('indicates_defect').from_('leak').to('pipe')\
            .property('distance_m', 0)  # Calculate actual distance\
            .iterate()
    
    def find_vulnerable_segments(
        self,
        min_age_years: float = 20,
        min_historical_leaks: int = 2
    ) -> List[str]:
        """
        Query graph for vulnerable pipeline segments
        """
        
        if not self.g:
            return []
        
        # Find segments with age > threshold AND historical leaks
        vulnerable = self.g.E().hasLabel('pipeline')\
            .has('age_years', __.gte(min_age_years))\
            .has('historical_leaks', __.gte(min_historical_leaks))\
            .values('segment_id').toList()
        
        return vulnerable
    
    def trace_downstream_impact(
        self,
        leak_segment_id: str,
        max_hops: int = 10
    ) -> List[str]:
        """
        Trace water flow downstream from leak
        to identify affected areas
        """
        
        if not self.g:
            return []
        
        # Find all junctions downstream (following flow direction)
        downstream = self.g.E().has('pipeline', 'segment_id', leak_segment_id)\
            .inV()\
            .repeat(__.out('pipeline').inV())\
            .times(max_hops)\
            .path()\
            .by('junction_id')\
            .toList()
        
        return downstream


# ============================================================
# 3. FUZZY LOGIC FOR DEFECT PROBABILITY
# ============================================================

class FuzzyDefectAnalyzer:
    """
    Fuzzy Logic system for calculating defect probability
    
    Input Variables (Fuzzified):
    - Pipe age
    - Material condition
    - Historical leak frequency
    - Detected indicators (thermal, vegetation, etc.)
    - Soil type
    - Traffic load
    
    Output: Defect probability (0-1) and urgency level
    """
    
    def __init__(self):
        pass
    
    def fuzzify_age(self, age_years: float) -> Dict[str, float]:
        """
        Fuzzify pipe age into linguistic variables
        
        Returns membership values for: 'new', 'moderate', 'old', 'ancient'
        """
        
        memberships = {}
        
        # New (0-10 years): Triangular membership function
        if age_years <= 0:
            memberships['new'] = 1.0
        elif age_years < 10:
            memberships['new'] = 1.0 - (age_years / 10)
        else:
            memberships['new'] = 0.0
        
        # Moderate (5-25 years): Trapezoidal
        if age_years < 5:
            memberships['moderate'] = 0.0
        elif age_years < 10:
            memberships['moderate'] = (age_years - 5) / 5
        elif age_years < 20:
            memberships['moderate'] = 1.0
        elif age_years < 25:
            memberships['moderate'] = (25 - age_years) / 5
        else:
            memberships['moderate'] = 0.0
        
        # Old (20-50 years): Trapezoidal
        if age_years < 20:
            memberships['old'] = 0.0
        elif age_years < 30:
            memberships['old'] = (age_years - 20) / 10
        elif age_years < 40:
            memberships['old'] = 1.0
        elif age_years < 50:
            memberships['old'] = (50 - age_years) / 10
        else:
            memberships['old'] = 0.0
        
        # Ancient (40+ years): Triangular
        if age_years < 40:
            memberships['ancient'] = 0.0
        elif age_years < 60:
            memberships['ancient'] = (age_years - 40) / 20
        else:
            memberships['ancient'] = 1.0
        
        return memberships
    
    def fuzzify_indicator_count(self, count: int) -> Dict[str, float]:
        """
        Fuzzify number of leak indicators detected
        
        Returns: 'few', 'several', 'many'
        """
        
        memberships = {}
        
        # Few (0-2): Triangular
        if count <= 0:
            memberships['few'] = 1.0
        elif count < 2:
            memberships['few'] = 1.0 - (count / 2)
        else:
            memberships['few'] = 0.0
        
        # Several (1-4): Trapezoidal
        if count < 1:
            memberships['several'] = 0.0
        elif count < 2:
            memberships['several'] = count - 1
        elif count < 3:
            memberships['several'] = 1.0
        elif count < 4:
            memberships['several'] = 4 - count
        else:
            memberships['several'] = 0.0
        
        # Many (3+): Triangular
        if count < 3:
            memberships['many'] = 0.0
        elif count < 5:
            memberships['many'] = (count - 3) / 2
        else:
            memberships['many'] = 1.0
        
        return memberships
    
    def fuzzify_material_vulnerability(self, material: str) -> float:
        """
        Material vulnerability score
        """
        
        vulnerability_scores = {
            'pvc': 0.3,
            'steel': 0.5,
            'cast_iron': 0.7,
            'concrete': 0.6,
            'asbestos': 0.9,  # Very old and brittle
            'unknown': 0.5
        }
        
        return vulnerability_scores.get(material.lower(), 0.5)
    
    def apply_fuzzy_rules(
        self,
        age_fuzzy: Dict[str, float],
        indicator_fuzzy: Dict[str, float],
        material_vulnerability: float,
        historical_leaks: int
    ) -> float:
        """
        Apply fuzzy inference rules
        
        Rules (example):
        1. IF age is ancient AND indicators are many THEN probability is very_high
        2. IF age is old AND indicators are several THEN probability is high
        3. IF age is moderate AND indicators are few THEN probability is low
        etc.
        """
        
        rules_fired = []
        
        # Rule 1: Ancient + Many indicators = 0.95
        rules_fired.append(
            min(age_fuzzy.get('ancient', 0), indicator_fuzzy.get('many', 0)) * 0.95
        )
        
        # Rule 2: Ancient + Several indicators = 0.85
        rules_fired.append(
            min(age_fuzzy.get('ancient', 0), indicator_fuzzy.get('several', 0)) * 0.85
        )
        
        # Rule 3: Old + Many indicators = 0.85
        rules_fired.append(
            min(age_fuzzy.get('old', 0), indicator_fuzzy.get('many', 0)) * 0.85
        )
        
        # Rule 4: Old + Several indicators = 0.70
        rules_fired.append(
            min(age_fuzzy.get('old', 0), indicator_fuzzy.get('several', 0)) * 0.70
        )
        
        # Rule 5: Moderate + Many indicators = 0.65
        rules_fired.append(
            min(age_fuzzy.get('moderate', 0), indicator_fuzzy.get('many', 0)) * 0.65
        )
        
        # Rule 6: Moderate + Several indicators = 0.50
        rules_fired.append(
            min(age_fuzzy.get('moderate', 0), indicator_fuzzy.get('several', 0)) * 0.50
        )
        
        # Rule 7: New + Few indicators = 0.20
        rules_fired.append(
            min(age_fuzzy.get('new', 0), indicator_fuzzy.get('few', 0)) * 0.20
        )
        
        # Rule 8: Material vulnerability factor
        material_factor = material_vulnerability
        
        # Rule 9: Historical leaks boost
        leak_boost = min(historical_leaks * 0.1, 0.3)
        
        # Defuzzification: Take maximum of all fired rules
        base_probability = max(rules_fired) if rules_fired else 0.5
        
        # Adjust with material and historical factors
        final_probability = min(
            base_probability * (1 + material_factor) + leak_boost,
            1.0
        )
        
        return final_probability
    
    def calculate_defect_probability(
        self,
        segment: PipelineSegment,
        indicators: List[LeakIndicator]
    ) -> DefectProbability:
        """
        Calculate overall defect probability for a pipeline segment
        """
        
        # Fuzzify inputs
        age_fuzzy = self.fuzzify_age(segment.age_years)
        indicator_fuzzy = self.fuzzify_indicator_count(len(indicators))
        material_vuln = self.fuzzify_material_vulnerability(segment.pipe_material)
        
        # Apply fuzzy rules
        probability = self.apply_fuzzy_rules(
            age_fuzzy,
            indicator_fuzzy,
            material_vuln,
            segment.historical_leaks
        )
        
        # Calculate average severity from indicators
        avg_severity = np.mean([ind.severity for ind in indicators]) if indicators else 0.0
        
        # Determine urgency
        if probability > 0.8 or avg_severity > 0.8:
            urgency = 'critical'
            action = 'Immediate inspection and repair required'
        elif probability > 0.6:
            urgency = 'high'
            action = 'Schedule inspection within 1 week'
        elif probability > 0.4:
            urgency = 'medium'
            action = 'Schedule inspection within 1 month'
        else:
            urgency = 'low'
            action = 'Monitor for changes'
        
        # Contributing factors
        factors = {
            'age': segment.age_years,
            'material': material_vuln,
            'historical_leaks': segment.historical_leaks,
            'indicator_count': len(indicators),
            'avg_severity': avg_severity
        }
        
        return DefectProbability(
            segment_id=segment.segment_id,
            probability=probability,
            contributing_factors=factors,
            recommended_action=action,
            urgency=urgency
        )


# ============================================================
# 4. COMPLETE PIPELINE
# ============================================================

class WaterLeakDetectionPipeline:
    """
    Complete pipeline combining all components
    """
    
    def __init__(
        self,
        gremlin_endpoint: str = "ws://localhost:8182/gremlin"
    ):
        # Initialize detectors
        self.thermal_detector = ThermalLeakDetector()
        self.vegetation_detector = VegetationLeakDetector()
        self.subsidence_detector = SubsidenceDetector()
        self.ponding_detector = WaterPondingDetector()
        
        # Initialize knowledge graph
        self.graph = WaterNetworkGraph(gremlin_endpoint)
        
        # Initialize fuzzy logic
        self.fuzzy_analyzer = FuzzyDefectAnalyzer()
        
        logger.info("Water leak detection pipeline initialized")
    
    def process_drone_imagery(
        self,
        thermal_image: Optional[np.ndarray] = None,
        nir_band: Optional[np.ndarray] = None,
        red_band: Optional[np.ndarray] = None,
        green_band: Optional[np.ndarray] = None,
        previous_image: Optional[np.ndarray] = None,
        current_image: Optional[np.ndarray] = None
    ) -> List[LeakIndicator]:
        """
        Process all available imagery and detect leak indicators
        """
        
        all_indicators = []
        
        # 1. Thermal detection
        if thermal_image is not None:
            thermal_indicators = self.thermal_detector.detect_from_thermal_image(
                thermal_image,
                reference_temp=np.median(thermal_image)
            )
            all_indicators.extend(thermal_indicators)
            logger.info(f"Found {len(thermal_indicators)} thermal indicators")
        
        # 2. Vegetation detection
        if nir_band is not None and red_band is not None:
            veg_indicators = self.vegetation_detector.detect_from_multispectral(
                nir_band, red_band
            )
            all_indicators.extend(veg_indicators)
            logger.info(f"Found {len(veg_indicators)} vegetation indicators")
        
        # 3. Subsidence detection
        if previous_image is not None and current_image is not None:
            subsidence_indicators = self.subsidence_detector.detect_subsidence(
                previous_image, current_image
            )
            all_indicators.extend(subsidence_indicators)
            logger.info(f"Found {len(subsidence_indicators)} subsidence indicators")
        
        # 4. Water ponding detection
        if green_band is not None and nir_band is not None:
            ponding_indicators = self.ponding_detector.detect_water_accumulation(
                green_band, nir_band
            )
            all_indicators.extend(ponding_indicators)
            logger.info(f"Found {len(ponding_indicators)} ponding indicators")
        
        return all_indicators
    
    def analyze_segment(
        self,
        segment: PipelineSegment,
        indicators: List[LeakIndicator]
    ) -> DefectProbability:
        """
        Analyze a pipeline segment with detected indicators
        """
        
        # Use fuzzy logic to calculate defect probability
        defect_prob = self.fuzzy_analyzer.calculate_defect_probability(
            segment, indicators
        )
        
        return defect_prob
    
    def generate_inspection_priority_list(
        self,
        segments: List[PipelineSegment],
        indicators_by_segment: Dict[str, List[LeakIndicator]]
    ) -> List[DefectProbability]:
        """
        Generate prioritized list of segments for inspection
        """
        
        results = []
        
        for segment in segments:
            indicators = indicators_by_segment.get(segment.segment_id, [])
            defect_prob = self.analyze_segment(segment, indicators)
            results.append(defect_prob)
        
        # Sort by probability (descending)
        results.sort(key=lambda x: x.probability, reverse=True)
        
        return results


def main():
    """Example usage"""
    
    # Initialize pipeline
    pipeline = WaterLeakDetectionPipeline()
    
    # Example: Load drone imagery
    thermal_image = cv2.imread('thermal_image.tif', cv2.IMREAD_UNCHANGED)
    
    # Process imagery
    indicators = pipeline.process_drone_imagery(thermal_image=thermal_image)
    
    print(f"Detected {len(indicators)} leak indicators")
    
    # Example pipeline segment
    segment = PipelineSegment(
        segment_id="SEG_001",
        start_node="J001",
        end_node="J002",
        pipe_material="steel",
        diameter_mm=300,
        age_years=35,
        length_meters=250,
        coordinates=[(32.0, 44.0), (32.01, 44.01)],
        historical_leaks=2
    )
    
    # Analyze
    defect_prob = pipeline.analyze_segment(segment, indicators)
    
    print(f"Defect Probability: {defect_prob.probability:.2f}")
    print(f"Urgency: {defect_prob.urgency}")
    print(f"Action: {defect_prob.recommended_action}")


if __name__ == "__main__":
    main()
