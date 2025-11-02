"""
Grave Boundary Detection from Aerial Imagery
Using Deep Learning (Mask R-CNN, SAM) and Traditional CV
For detecting individual graves in satellite/drone images
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
import logging
from dataclasses import dataclass
from pathlib import Path
import json

# Deep Learning imports (install as needed)
try:
    import torch
    from torchvision.models.detection import maskrcnn_resnet50_fpn
    from torchvision.transforms import functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available, deep learning features disabled")

try:
    from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
    SAM_AVAILABLE = True
except ImportError:
    SAM_AVAILABLE = False
    logging.warning("SAM (Segment Anything) not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GraveBoundary:
    """Represents a detected grave boundary"""
    polygon: np.ndarray  # Array of (x, y) coordinates
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    center: Tuple[float, float]  # Center point
    area: float  # Area in square pixels
    confidence: float  # Detection confidence (0-1)
    grave_id: Optional[str] = None
    

class TraditionalGraveDetector:
    """
    Traditional computer vision approach for grave detection
    Good for: Regular grids, clear boundaries, no training needed
    """
    
    def __init__(self):
        pass
    
    def detect_by_watershed(
        self,
        image: np.ndarray,
        min_grave_area: int = 100,
        max_grave_area: int = 10000
    ) -> List[GraveBoundary]:
        """
        Detect graves using watershed segmentation
        Works well for regular grid patterns with clear separation
        
        Args:
            image: Input RGB or grayscale image
            min_grave_area: Minimum grave area in pixels
            max_grave_area: Maximum grave area in pixels
            
        Returns:
            List of detected grave boundaries
        """
        logger.info("Starting watershed segmentation")
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Denoise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Sure background area
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # Finding sure foreground area
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.5 * dist_transform.max(), 255, 0)
        
        # Finding unknown region
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # Marker labelling
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        
        # Apply watershed
        if len(image.shape) == 2:
            image_color = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            image_color = image.copy()
        
        markers = cv2.watershed(image_color, markers)
        
        # Extract boundaries
        boundaries = []
        for label in range(2, markers.max() + 1):
            mask = np.zeros(gray.shape, dtype=np.uint8)
            mask[markers == label] = 255
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filter by area
                if min_grave_area <= area <= max_grave_area:
                    # Get bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Get center
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = x + w // 2, y + h // 2
                    
                    # Simplify polygon
                    epsilon = 0.01 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    boundaries.append(GraveBoundary(
                        polygon=approx.reshape(-1, 2),
                        bbox=(x, y, w, h),
                        center=(cx, cy),
                        area=area,
                        confidence=0.8  # Fixed confidence for traditional methods
                    ))
        
        logger.info(f"Detected {len(boundaries)} graves using watershed")
        return boundaries
    
    def detect_by_grid(
        self,
        image: np.ndarray,
        grid_rows: int,
        grid_cols: int
    ) -> List[GraveBoundary]:
        """
        Detect graves by dividing image into regular grid
        Good for: Perfectly aligned cemetery sections
        
        Args:
            image: Input image
            grid_rows: Number of rows in grid
            grid_cols: Number of columns in grid
            
        Returns:
            List of grave boundaries (rectangular)
        """
        height, width = image.shape[:2]
        cell_height = height // grid_rows
        cell_width = width // grid_cols
        
        boundaries = []
        
        for row in range(grid_rows):
            for col in range(grid_cols):
                x = col * cell_width
                y = row * cell_height
                w = cell_width
                h = cell_height
                
                # Create rectangular polygon
                polygon = np.array([
                    [x, y],
                    [x + w, y],
                    [x + w, y + h],
                    [x, y + h]
                ])
                
                boundaries.append(GraveBoundary(
                    polygon=polygon,
                    bbox=(x, y, w, h),
                    center=(x + w/2, y + h/2),
                    area=w * h,
                    confidence=1.0,
                    grave_id=f"R{row+1}C{col+1}"
                ))
        
        logger.info(f"Created {len(boundaries)} grave cells in {grid_rows}x{grid_cols} grid")
        return boundaries


class DeepLearningGraveDetector:
    """
    Deep learning approach using Mask R-CNN or SAM
    Best for: Irregular patterns, high accuracy, handles variations
    """
    
    def __init__(
        self,
        model_type: str = "maskrcnn",  # "maskrcnn" or "sam"
        model_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.model_type = model_type
        self.device = device
        self.model = None
        
        if model_type == "maskrcnn" and TORCH_AVAILABLE:
            self._load_maskrcnn(model_path)
        elif model_type == "sam" and SAM_AVAILABLE:
            self._load_sam(model_path)
        else:
            logger.error(f"Model type {model_type} not available")
    
    def _load_maskrcnn(self, model_path: Optional[str] = None):
        """Load Mask R-CNN model"""
        logger.info("Loading Mask R-CNN model")
        
        if model_path:
            # Load custom trained model
            self.model = maskrcnn_resnet50_fpn(pretrained=False, num_classes=2)
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
        else:
            # Load pretrained COCO model (for demonstration)
            self.model = maskrcnn_resnet50_fpn(pretrained=True)
        
        self.model.to(self.device)
        self.model.eval()
    
    def _load_sam(self, model_path: Optional[str] = None):
        """Load Segment Anything Model (SAM)"""
        logger.info("Loading SAM model")
        
        model_type = "vit_h"  # or "vit_l", "vit_b"
        
        if not model_path:
            model_path = "sam_vit_h_4b8939.pth"  # Download from Meta
        
        sam = sam_model_registry[model_type](checkpoint=model_path)
        sam.to(device=self.device)
        
        self.mask_generator = SamAutomaticMaskGenerator(sam)
    
    def detect_with_maskrcnn(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5,
        min_grave_area: int = 100
    ) -> List[GraveBoundary]:
        """
        Detect graves using Mask R-CNN
        
        Args:
            image: Input RGB image
            confidence_threshold: Minimum confidence score
            min_grave_area: Minimum grave area in pixels
            
        Returns:
            List of detected graves with boundaries
        """
        if self.model is None or self.model_type != "maskrcnn":
            logger.error("Mask R-CNN model not loaded")
            return []
        
        logger.info("Running Mask R-CNN inference")
        
        # Prepare image
        image_tensor = F.to_tensor(image).unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            predictions = self.model(image_tensor)[0]
        
        # Extract results
        boundaries = []
        
        boxes = predictions['boxes'].cpu().numpy()
        masks = predictions['masks'].cpu().numpy()
        scores = predictions['scores'].cpu().numpy()
        
        for i, (box, mask, score) in enumerate(zip(boxes, masks, scores)):
            if score < confidence_threshold:
                continue
            
            # Convert mask to binary
            mask = mask[0] > 0.5
            
            # Calculate area
            area = mask.sum()
            
            if area < min_grave_area:
                continue
            
            # Find contour from mask
            mask_uint8 = (mask * 255).astype(np.uint8)
            contours, _ = cv2.findContours(
                mask_uint8,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if len(contours) == 0:
                continue
            
            contour = max(contours, key=cv2.contourArea)
            
            # Simplify polygon
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Get center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
            
            boundaries.append(GraveBoundary(
                polygon=approx.reshape(-1, 2),
                bbox=(x, y, w, h),
                center=(cx, cy),
                area=float(area),
                confidence=float(score),
                grave_id=f"GRAVE_{i+1:04d}"
            ))
        
        logger.info(f"Detected {len(boundaries)} graves with Mask R-CNN")
        return boundaries
    
    def detect_with_sam(
        self,
        image: np.ndarray,
        min_grave_area: int = 100,
        max_grave_area: int = 10000
    ) -> List[GraveBoundary]:
        """
        Detect graves using Segment Anything Model (SAM)
        No training needed - zero-shot segmentation!
        
        Args:
            image: Input RGB image
            min_grave_area: Minimum grave area
            max_grave_area: Maximum grave area
            
        Returns:
            List of detected graves
        """
        if self.mask_generator is None:
            logger.error("SAM model not loaded")
            return []
        
        logger.info("Running SAM inference (this may take a while)")
        
        # Generate masks
        masks = self.mask_generator.generate(image)
        
        boundaries = []
        
        for i, mask_data in enumerate(masks):
            segmentation = mask_data['segmentation']
            area = mask_data['area']
            bbox = mask_data['bbox']  # x, y, w, h
            predicted_iou = mask_data['predicted_iou']
            
            # Filter by area
            if not (min_grave_area <= area <= max_grave_area):
                continue
            
            # Find contour
            mask_uint8 = (segmentation * 255).astype(np.uint8)
            contours, _ = cv2.findContours(
                mask_uint8,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if len(contours) == 0:
                continue
            
            contour = max(contours, key=cv2.contourArea)
            
            # Simplify polygon
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Calculate center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2
            
            boundaries.append(GraveBoundary(
                polygon=approx.reshape(-1, 2),
                bbox=tuple(bbox),
                center=(cx, cy),
                area=float(area),
                confidence=float(predicted_iou),
                grave_id=f"GRAVE_{i+1:04d}"
            ))
        
        logger.info(f"Detected {len(boundaries)} graves with SAM")
        return boundaries


class GraveDetectionPipeline:
    """
    Complete pipeline for grave detection from aerial imagery
    """
    
    def __init__(self, method: str = "sam"):
        """
        Initialize detection pipeline
        
        Args:
            method: "traditional", "maskrcnn", or "sam"
        """
        self.method = method
        
        if method == "traditional":
            self.detector = TraditionalGraveDetector()
        elif method in ["maskrcnn", "sam"]:
            self.detector = DeepLearningGraveDetector(model_type=method)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def process_image(
        self,
        image_path: str,
        output_dir: Optional[str] = None
    ) -> Tuple[List[GraveBoundary], np.ndarray]:
        """
        Process a single aerial image
        
        Args:
            image_path: Path to input image
            output_dir: Optional directory to save results
            
        Returns:
            Tuple of (boundaries list, annotated image)
        """
        logger.info(f"Processing image: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert BGR to RGB for deep learning models
        if self.method in ["maskrcnn", "sam"]:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # Detect graves
        if self.method == "traditional":
            boundaries = self.detector.detect_by_watershed(image_rgb)
        elif self.method == "maskrcnn":
            boundaries = self.detector.detect_with_maskrcnn(image_rgb)
        elif self.method == "sam":
            boundaries = self.detector.detect_with_sam(image_rgb)
        
        # Draw results
        annotated = self.visualize_results(image.copy(), boundaries)
        
        # Save if output directory specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save annotated image
            cv2.imwrite(
                str(output_path / f"{Path(image_path).stem}_annotated.jpg"),
                annotated
            )
            
            # Save boundaries as JSON
            self.save_boundaries_json(
                boundaries,
                str(output_path / f"{Path(image_path).stem}_boundaries.json")
            )
        
        return boundaries, annotated
    
    def visualize_results(
        self,
        image: np.ndarray,
        boundaries: List[GraveBoundary],
        draw_polygons: bool = True,
        draw_boxes: bool = False,
        draw_centers: bool = True
    ) -> np.ndarray:
        """Draw detected boundaries on image"""
        
        for i, boundary in enumerate(boundaries):
            # Random color for each grave
            color = tuple(np.random.randint(0, 255, 3).tolist())
            
            # Draw polygon
            if draw_polygons:
                cv2.polylines(
                    image,
                    [boundary.polygon],
                    True,
                    color,
                    2
                )
            
            # Draw bounding box
            if draw_boxes:
                x, y, w, h = boundary.bbox
                cv2.rectangle(image, (x, y), (x+w, y+h), color, 2)
            
            # Draw center point
            if draw_centers:
                cx, cy = int(boundary.center[0]), int(boundary.center[1])
                cv2.circle(image, (cx, cy), 3, (0, 0, 255), -1)
            
            # Draw grave ID
            if boundary.grave_id:
                cv2.putText(
                    image,
                    boundary.grave_id,
                    (int(boundary.center[0]), int(boundary.center[1])),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )
        
        # Add statistics
        cv2.putText(
            image,
            f"Detected: {len(boundaries)} graves",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        
        return image
    
    def save_boundaries_json(
        self,
        boundaries: List[GraveBoundary],
        output_path: str
    ):
        """Save boundaries to JSON file"""
        
        data = {
            "total_graves": len(boundaries),
            "method": self.method,
            "graves": []
        }
        
        for boundary in boundaries:
            data["graves"].append({
                "grave_id": boundary.grave_id,
                "polygon": boundary.polygon.tolist(),
                "bbox": boundary.bbox,
                "center": boundary.center,
                "area_pixels": boundary.area,
                "confidence": boundary.confidence
            })
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved boundaries to {output_path}")
    
    def convert_to_geojson(
        self,
        boundaries: List[GraveBoundary],
        image_bounds: Tuple[float, float, float, float],
        output_path: str
    ):
        """
        Convert pixel coordinates to geographic coordinates (GeoJSON)
        
        Args:
            boundaries: List of grave boundaries
            image_bounds: (min_lon, min_lat, max_lon, max_lat) of image
            output_path: Output GeoJSON file path
        """
        # Would need to convert pixel coords to lat/lon
        # Using image bounds and image dimensions
        pass


def main():
    """Example usage"""
    
    # Choose method: "traditional", "maskrcnn", or "sam"
    pipeline = GraveDetectionPipeline(method="traditional")
    
    # Process image
    boundaries, annotated = pipeline.process_image(
        image_path="cemetery_aerial.jpg",
        output_dir="./grave_detection_results"
    )
    
    print(f"Detected {len(boundaries)} graves")
    
    # Display result
    cv2.imshow("Grave Detection", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
