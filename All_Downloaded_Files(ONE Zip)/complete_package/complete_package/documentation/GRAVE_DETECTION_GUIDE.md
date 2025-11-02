# Grave Boundary Detection from Aerial Imagery - Complete Guide

## 🎯 Problem Statement

Detect individual grave boundaries from satellite/drone images where graves are densely packed side-by-side (similar to houses in slums/favelas).

## 📊 Comparison of Approaches

| Method | Accuracy | Speed | Training Needed | Best For |
|--------|----------|-------|-----------------|----------|
| **Watershed** | 60-75% | Fast | ❌ No | Regular grids, clear boundaries |
| **Grid Division** | 50-60% | Very Fast | ❌ No | Perfectly aligned sections |
| **Mask R-CNN** | 85-95% | Moderate | ✅ Yes | Irregular patterns, high accuracy |
| **SAM (Meta)** | 80-90% | Slow | ❌ No (zero-shot!) | Quick deployment, no training data |
| **YOLOv8-Seg** | 85-92% | Very Fast | ✅ Yes | Real-time applications |
| **U-Net** | 90-95% | Fast | ✅ Yes | Dense, overlapping objects |

## 🏆 Recommended Approach: **SAM (Segment Anything Model)**

**Why SAM is best for your use case:**
1. ✅ **No training data needed** - works out of the box
2. ✅ **Zero-shot learning** - adapts to any image
3. ✅ **State-of-the-art accuracy** (80-90%)
4. ✅ **Handles dense objects** well
5. ⚠️ **Slower** than YOLO (but acceptable for batch processing)

## 🚀 Quick Start with SAM

### Step 1: Install Dependencies
```bash
pip install opencv-python numpy torch torchvision
pip install git+https://github.com/facebookresearch/segment-anything.git
```

### Step 2: Download SAM Model
```bash
# Download pre-trained model (2.4 GB)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
```

### Step 3: Run Detection
```python
from grave_detection_cv import GraveDetectionPipeline

# Initialize with SAM
pipeline = GraveDetectionPipeline(method="sam")

# Process aerial image
boundaries, annotated = pipeline.process_image(
    image_path="cemetery_drone_image.jpg",
    output_dir="./results"
)

print(f"Detected {len(boundaries)} graves")
```

**Output:**
- `cemetery_drone_image_annotated.jpg` - Visual results
- `cemetery_drone_image_boundaries.json` - Boundary coordinates

## 📐 Complete Workflow

### 1. **Capture Aerial Imagery**

**Option A: Drone**
```
Equipment:
- DJI Mavic 3 / Phantom 4 RTK
- Flight altitude: 50-100m
- Resolution: 20MP+
- Overlap: 70-80%

Software:
- DJI Terra / Pix4D / DroneDeploy
- Creates orthomosaic map
```

**Option B: Satellite**
```
Sources:
- Google Earth Pro (free, lower resolution)
- Sentinel-2 (10m resolution, free)
- Planet Labs (3m resolution, paid)
- Maxar/DigitalGlobe (30cm resolution, expensive)

For graves: Need <1m resolution
Recommended: Drone or commercial satellite
```

### 2. **Pre-processing**

```python
import cv2
import numpy as np

def preprocess_image(image_path):
    """Prepare image for detection"""
    
    # Load image
    image = cv2.imread(image_path)
    
    # 1. Increase contrast (helps with faded graves)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    # 2. Denoise
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
    
    # 3. Sharpen
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    
    return sharpened

# Use before detection
preprocessed = preprocess_image("cemetery_raw.jpg")
cv2.imwrite("cemetery_preprocessed.jpg", preprocessed)
```

### 3. **Run Detection**

```python
from grave_detection_cv import GraveDetectionPipeline

# Initialize pipeline
pipeline = GraveDetectionPipeline(method="sam")

# Detect graves
boundaries, annotated = pipeline.process_image(
    image_path="cemetery_preprocessed.jpg",
    output_dir="./grave_results"
)

# Filter by size (remove false positives)
filtered_boundaries = [
    b for b in boundaries 
    if 100 < b.area < 5000  # Adjust based on your grave sizes
]

print(f"Detected {len(filtered_boundaries)} graves after filtering")
```

### 4. **Post-processing**

```python
def refine_boundaries(boundaries, image):
    """
    Refine detected boundaries using morphological operations
    """
    refined = []
    
    for boundary in boundaries:
        # Create mask
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [boundary.polygon], 255)
        
        # Morphological closing (fills small gaps)
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Morphological opening (removes small noise)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find new contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 0:
            contour = max(contours, key=cv2.contourArea)
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            boundary.polygon = approx.reshape(-1, 2)
            refined.append(boundary)
    
    return refined

# Apply refinement
refined_boundaries = refine_boundaries(filtered_boundaries, image)
```

### 5. **Convert to Geographic Coordinates**

```python
def pixel_to_latlon(
    pixel_x: int,
    pixel_y: int,
    image_width: int,
    image_height: int,
    bounds: tuple  # (min_lon, min_lat, max_lon, max_lat)
) -> tuple:
    """Convert pixel coordinates to lat/lon"""
    
    min_lon, min_lat, max_lon, max_lat = bounds
    
    # Calculate lon/lat per pixel
    lon_per_pixel = (max_lon - min_lon) / image_width
    lat_per_pixel = (max_lat - min_lat) / image_height
    
    # Convert (note: y increases downward in images, but lat increases upward)
    lon = min_lon + (pixel_x * lon_per_pixel)
    lat = max_lat - (pixel_y * lat_per_pixel)
    
    return lat, lon


def create_geojson(boundaries, image_dimensions, geographic_bounds, output_path):
    """Create GeoJSON file with grave boundaries"""
    
    width, height = image_dimensions
    
    features = []
    
    for boundary in boundaries:
        # Convert polygon to lat/lon
        coords = []
        for x, y in boundary.polygon:
            lat, lon = pixel_to_latlon(x, y, width, height, geographic_bounds)
            coords.append([lon, lat])  # GeoJSON uses [lon, lat] order
        
        # Close the polygon
        coords.append(coords[0])
        
        feature = {
            "type": "Feature",
            "properties": {
                "grave_id": boundary.grave_id,
                "area_pixels": boundary.area,
                "confidence": boundary.confidence
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_path, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    return geojson


# Usage
import cv2

image = cv2.imread("cemetery.jpg")
height, width = image.shape[:2]

# You need to know these from your drone/satellite metadata
geographic_bounds = (
    44.3120,  # min_lon (west)
    32.0140,  # min_lat (south)
    44.3180,  # max_lon (east)
    32.0200   # max_lat (north)
)

geojson = create_geojson(
    boundaries=refined_boundaries,
    image_dimensions=(width, height),
    geographic_bounds=geographic_bounds,
    output_path="grave_boundaries.geojson"
)
```

### 6. **Import to PostgreSQL**

```python
import psycopg2
import json

def import_graves_to_database(geojson_path, db_config, section_code):
    """Import detected graves to PostgreSQL database"""
    
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Load GeoJSON
    with open(geojson_path, 'r') as f:
        geojson = json.load(f)
    
    for feature in geojson['features']:
        grave_id = feature['properties']['grave_id']
        coords = feature['geometry']['coordinates'][0]
        
        # Get center point (first coordinate of polygon)
        center_lon, center_lat = coords[0]
        
        # Insert into database
        query = """
        INSERT INTO cemetery_grave_locations (
            grave_id,
            section,
            polygon,
            center_point,
            detection_confidence,
            detection_method,
            created_at
        ) VALUES (
            %s, %s,
            ST_GeomFromGeoJSON(%s),
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (grave_id) DO UPDATE SET
            polygon = EXCLUDED.polygon,
            center_point = EXCLUDED.center_point,
            updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(query, (
            grave_id,
            section_code,
            json.dumps(feature['geometry']),
            center_lon,
            center_lat,
            feature['properties']['confidence'],
            'SAM'
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Imported {len(geojson['features'])} graves to database")


# Usage
import_graves_to_database(
    geojson_path="grave_boundaries.geojson",
    db_config={
        'host': 'localhost',
        'database': 'najaf_cemetery',
        'user': 'cemetery_user',
        'password': 'password'
    },
    section_code="A"
)
```

## 🎓 Training Custom Model (Optional)

If you want even better accuracy, train a custom model:

### Dataset Preparation

```python
import cv2
import json
from pathlib import Path

def create_training_dataset():
    """
    Create annotated dataset for training
    
    Structure:
    dataset/
        images/
            img_001.jpg
            img_002.jpg
        annotations/
            img_001.json
            img_002.json
    """
    
    # Use labelme or CVAT for annotation
    # Each annotation JSON contains:
    {
        "version": "1.0",
        "shapes": [
            {
                "label": "grave",
                "points": [[x1, y1], [x2, y2], ...],
                "shape_type": "polygon"
            }
        ],
        "imagePath": "img_001.jpg",
        "imageHeight": 1080,
        "imageWidth": 1920
    }
```

### Training Script (PyTorch)

```python
import torch
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

def get_model(num_classes=2):  # 1 class (grave) + background
    """Load Mask R-CNN model for training"""
    
    # Load pre-trained model
    model = maskrcnn_resnet50_fpn(pretrained=True)
    
    # Replace box predictor
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    # Replace mask predictor
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256
    model.roi_heads.mask_predictor = MaskRCNNPredictor(
        in_features_mask,
        hidden_layer,
        num_classes
    )
    
    return model


# Training loop
def train_model(model, data_loader, num_epochs=50):
    """Train the model"""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    
    # Optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
    
    # Learning rate scheduler
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)
    
    for epoch in range(num_epochs):
        model.train()
        
        for images, targets in data_loader:
            images = list(image.to(device) for image in images)
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            
            optimizer.zero_grad()
            losses.backward()
            optimizer.step()
        
        lr_scheduler.step()
        
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {losses.item():.4f}")
    
    return model
```

## 📊 Accuracy Metrics

```python
def calculate_iou(pred_polygon, gt_polygon):
    """Calculate Intersection over Union (IoU)"""
    
    from shapely.geometry import Polygon
    
    pred_poly = Polygon(pred_polygon)
    gt_poly = Polygon(gt_polygon)
    
    intersection = pred_poly.intersection(gt_poly).area
    union = pred_poly.union(gt_poly).area
    
    iou = intersection / union if union > 0 else 0
    
    return iou


def evaluate_detection(predicted_boundaries, ground_truth_boundaries, iou_threshold=0.5):
    """Evaluate detection accuracy"""
    
    true_positives = 0
    false_positives = 0
    false_negatives = len(ground_truth_boundaries)
    
    matched_gt = set()
    
    for pred in predicted_boundaries:
        best_iou = 0
        best_gt_idx = -1
        
        for gt_idx, gt in enumerate(ground_truth_boundaries):
            if gt_idx in matched_gt:
                continue
            
            iou = calculate_iou(pred.polygon, gt.polygon)
            
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = gt_idx
        
        if best_iou >= iou_threshold:
            true_positives += 1
            false_negatives -= 1
            matched_gt.add(best_gt_idx)
        else:
            false_positives += 1
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives
    }
```

## 🔧 Troubleshooting

### Issue 1: Too Many False Positives
**Solution:**
- Increase `min_grave_area` threshold
- Add confidence threshold filtering
- Use morphological operations to clean up

### Issue 2: Missing Graves
**Solution:**
- Decrease `min_grave_area` threshold
- Improve image contrast in preprocessing
- Try different detection method

### Issue 3: Merged Graves (Not Separated)
**Solution:**
- Use watershed segmentation for post-processing
- Adjust SAM parameters
- Manual annotation for difficult cases

### Issue 4: Slow Processing
**Solution:**
- Process in tiles (split large image)
- Use GPU acceleration
- Switch to YOLOv8 (faster)
- Batch processing overnight

## 💰 Cost Estimate

| Component | One-time | Monthly |
|-----------|----------|---------|
| Drone (DJI Mavic 3) | $2,000 | - |
| Computer (GPU) | $1,500 | - |
| SAM Model | Free | - |
| Satellite Imagery | - | $50-500 |
| Cloud GPU (optional) | - | $100-300 |
| **Total** | **$3,500** | **$150-800** |

## 🎯 Integration with Cemetery System

```python
# Add to api_gateway.py

@app.post("/api/detection/process-aerial-image")
async def process_aerial_image(
    file: UploadFile = File(...),
    section: str = Query(...),
    geographic_bounds: str = Query(...)  # "min_lon,min_lat,max_lon,max_lat"
):
    """
    Process aerial image and detect grave boundaries
    """
    
    # Save uploaded file
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Parse geographic bounds
    bounds = tuple(map(float, geographic_bounds.split(',')))
    
    # Run detection
    pipeline = GraveDetectionPipeline(method="sam")
    boundaries, annotated = pipeline.process_image(temp_path)
    
    # Convert to GeoJSON
    image = cv2.imread(temp_path)
    height, width = image.shape[:2]
    
    geojson = create_geojson(boundaries, (width, height), bounds, "/tmp/graves.geojson")
    
    # Import to database
    import_graves_to_database("/tmp/graves.geojson", DB_CONFIG, section)
    
    return {
        "success": True,
        "graves_detected": len(boundaries),
        "section": section,
        "geojson": geojson
    }
```

## 📚 Resources

### Papers:
- "Segment Anything" (SAM) - Meta AI, 2023
- "Mask R-CNN" - Facebook AI Research, 2017
- "U-Net: Convolutional Networks for Biomedical Image Segmentation" - 2015

### Tools:
- **Annotation**: [Labelme](https://github.com/wkentaro/labelme), [CVAT](https://github.com/openvinotoolkit/cvat)
- **SAM Demo**: https://segment-anything.com/demo
- **Training**: [Detectron2](https://github.com/facebookresearch/detectron2)

### Datasets:
- Create your own by annotating 50-100 cemetery images
- Each image should have 100-500 graves
- Total: 5,000-50,000 annotated graves for good model

## ✅ Recommended Workflow

1. **Start with SAM** (no training needed)
2. **Evaluate results** on your cemetery images
3. **If accuracy < 80%**: Collect training data and train custom Mask R-CNN
4. **For production**: Deploy best model in Docker container
5. **Automate**: Process new drone imagery automatically

---

**Bottom Line:** Use **SAM** for quick deployment with 80-90% accuracy, or train **Mask R-CNN** for 90-95% accuracy if you have annotated data.
