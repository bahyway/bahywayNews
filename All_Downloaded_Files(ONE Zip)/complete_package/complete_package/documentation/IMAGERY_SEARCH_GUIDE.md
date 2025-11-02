# Finding Test Imagery for Water Pipeline Defects in War Zones
## Complete Search Guide & Data Sources

## 🔍 **GOOGLE SEARCH PROMPTS (Copy & Paste)**

### For General Water Leaks:
```
"water main break" thermal imaging drone
"water pipe leak" infrared detection
"underground water leak" thermal camera
"water leak detection" multispectral imagery
"pipeline leak" satellite detection
"water infrastructure damage" drone survey
```

### For War Zone Specific:
```
"Syria water infrastructure damage" satellite
"Ukraine water system destruction" imagery
"Yemen water pipeline" damage assessment
"Iraq water network" bombing damage
"Gaza water infrastructure" drone footage
"Aleppo water supply" destruction satellite
```

### For Research/Academic Papers:
```
"water leak detection" thermal imagery site:researchgate.net
"pipeline defect detection" remote sensing site:.edu
"water infrastructure monitoring" satellite site:arxiv.org
filetype:pdf "water leak detection" thermal imaging
filetype:pdf "pipeline failure" remote sensing
```

### For Datasets:
```
"water leak detection dataset" download
"thermal imagery water leak" github
"pipeline defect dataset" kaggle
"infrastructure damage dataset" war zone
site:github.com "water leak" thermal dataset
site:kaggle.com pipeline defect detection
```

### For News/Documentation:
```
"water pipeline break" before after images
"water main burst" aerial view
"water shortage" Syria infrastructure damage
"water crisis" Iraq pipeline bombing
site:reuters.com water pipeline damage Syria
site:aljazeera.com water infrastructure Yemen
```

### For Sentinel/Landsat (Satellite):
```
site:earthexplorer.usgs.gov water leak
site:scihub.copernicus.eu pipeline monitoring
"Sentinel-2" water leak detection
"Landsat 8" thermal water infrastructure
```

## 🛰️ **FREE SATELLITE IMAGERY SOURCES**

### 1. **USGS EarthExplorer** (Best Free Source)
```
URL: https://earthexplorer.usgs.gov/

What you get:
- Landsat 8 (30m resolution, thermal band)
- Sentinel-2 (10m resolution, multispectral)
- Historical imagery (1970s-present)
- FREE download

How to search:
1. Go to https://earthexplorer.usgs.gov/
2. Click "Use Map" and zoom to area of interest (e.g., Mosul, Iraq)
3. Select coordinates or draw polygon
4. Choose date range (e.g., 2020-2024 for recent war damage)
5. Select datasets: Landsat 8-9 OLI/TIRS, Sentinel-2
6. Click "Results" and download

Specific searches for war zones:
- Coordinates: Aleppo: 36.2°N, 37.15°E
- Coordinates: Mosul: 36.34°N, 43.12°E
- Coordinates: Damascus: 33.51°N, 36.29°E
- Coordinates: Sana'a: 15.35°N, 44.21°E
```

### 2. **Copernicus Open Access Hub** (Sentinel Satellites)
```
URL: https://scihub.copernicus.eu/

What you get:
- Sentinel-1 (SAR - works through clouds)
- Sentinel-2 (10m multispectral)
- Sentinel-3 (thermal)
- FREE, updated every 5 days

Search example:
footprint:"Intersects(POLYGON((44.4 33.3, 44.5 33.3, 44.5 33.4, 44.4 33.4, 44.4 33.3)))" 
AND producttype:S2MSI2A 
AND cloudcoverpercentage:[0 TO 10]

For Baghdad area (example):
https://scihub.copernicus.eu/dhus/#/home
Search: Baghdad, Iraq
Date: 2020-2024
Product: Sentinel-2 L2A
Cloud cover: <10%
```

### 3. **Google Earth Engine** (Requires Account)
```
URL: https://earthengine.google.com/

What you get:
- Landsat, Sentinel, MODIS
- Historical time series
- Analysis tools
- FREE for research

Code example:
var region = ee.Geometry.Point([44.4, 33.3]); // Baghdad
var sentinel = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(region)
  .filterDate('2020-01-01', '2024-01-01')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10));
```

### 4. **NASA Worldview**
```
URL: https://worldview.earthdata.nasa.gov/

What you get:
- Near real-time satellite imagery
- Multiple satellites (MODIS, VIIRS, Landsat)
- Easy visualization
- FREE download

How to use:
1. Visit https://worldview.earthdata.nasa.gov/
2. Search location: "Aleppo, Syria"
3. Select layers: "Corrected Reflectance (True Color)"
4. Add "Thermal Anomalies" layer
5. Use timeline to see changes
6. Download selected area
```

## 📸 **DRONE/THERMAL IMAGERY SOURCES**

### 1. **YouTube (Surprisingly Useful)**
```
Search terms:
"thermal drone water leak"
"FLIR water pipe inspection"
"thermal imaging water leak detection"
"drone thermal camera pipeline"
"water main break aerial view"

Channels to check:
- DJI Official (thermal drone demos)
- FLIR Systems (thermal imaging)
- Utilities companies
- News channels (war zone footage)

Download:
Use youtube-dl or online downloader
Extract frames: ffmpeg -i video.mp4 -vf fps=1 frame_%04d.png
```

### 2. **Research Papers (Supplementary Materials)**
```
Sites:
- ResearchGate: https://www.researchgate.net/
- IEEE Xplore: https://ieeexplore.ieee.org/
- arXiv: https://arxiv.org/
- MDPI: https://www.mdpi.com/

Search:
"water leak detection thermal imaging" supplementary data
"pipeline defect remote sensing" dataset

Many papers include downloadable imagery in supplementary files
```

### 3. **GitHub Datasets**
```
Search on GitHub:
https://github.com/search?q=water+leak+detection+dataset

Specific repos (check these):
github.com/topics/leak-detection
github.com/topics/thermal-imaging
github.com/topics/pipeline-inspection

Example datasets:
- Thermal water leak images
- Annotated pipeline defects
- Satellite imagery with labels
```

### 4. **Kaggle Datasets**
```
URL: https://www.kaggle.com/datasets

Search:
"infrastructure damage"
"pipeline defect"
"water leak"
"thermal imaging"

Example datasets:
- Building damage assessment (Syria, Ukraine)
- Infrastructure monitoring
- Satellite imagery classification
```

## 🌍 **WAR ZONE SPECIFIC SOURCES**

### 1. **UN OCHA (Humanitarian Data)**
```
URL: https://data.humdata.org/

What you get:
- Infrastructure damage assessments
- Satellite imagery analysis
- Conflict zones data
- Water system status

Search:
https://data.humdata.org/dataset
Keywords: "water infrastructure" "Syria"
          "pipeline damage" "Iraq"
          "water systems" "Yemen"
```

### 2. **UNOSAT (UN Satellite Analysis)**
```
URL: https://unosat.org/

What you get:
- Damage assessment maps
- Before/after satellite imagery
- Infrastructure analysis
- Free for humanitarian use

Areas covered:
- Syria (extensive coverage)
- Iraq
- Yemen
- Gaza
- Ukraine
```

### 3. **REACH Initiative**
```
URL: https://www.reach-initiative.org/

What you get:
- Water infrastructure assessments
- Field surveys with GPS
- Damage maps
- Reports with imagery

Search their resource center:
"water infrastructure assessment Syria"
"WASH facilities damage Iraq"
```

### 4. **Conflict Damage Assessment**
```
Sources:
- Bellingcat (https://www.bellingcat.com/)
- Syrian Archive (https://syrianarchive.org/)
- Airwars (https://airwars.org/)

What you get:
- Verified incident locations
- Satellite imagery analysis
- Infrastructure damage documentation
```

## 🎓 **ACADEMIC/RESEARCH DATASETS**

### 1. **xBD Dataset (Building Damage)**
```
URL: https://xview2.org/

What: 
- 850k+ building annotations
- Before/after disaster imagery
- Includes conflict damage
- FREE download

Use case:
While focused on buildings, methodology applies to pipelines
Includes war zone imagery from Syria, Iraq
```

### 2. **IEEE DataPort**
```
URL: https://ieee-dataport.org/

Search: "infrastructure monitoring"
        "pipeline inspection"
        "thermal imaging"

Many datasets from research papers
```

### 3. **Zenodo (Open Science)**
```
URL: https://zenodo.org/

Search: "water infrastructure"
        "pipeline defect"
        "thermal imaging dataset"

Researchers upload datasets here
Often includes code + data
```

## 📊 **COMMERCIAL (Paid but High Quality)**

### 1. **Planet Labs**
```
URL: https://www.planet.com/

What:
- 3m resolution
- Daily updates
- 150+ satellites
- Good for monitoring changes

Cost: $500-$5000/month
Free: Education/research program available
Request: https://www.planet.com/markets/education-and-research/
```

### 2. **Maxar/DigitalGlobe**
```
URL: https://www.maxar.com/

What:
- 30-50cm resolution
- Highest quality commercial
- Historical archive

Cost: $10-50 per km²
Free: Open Data Program for disasters
Check: https://www.maxar.com/open-data
```

### 3. **Airbus Defence and Space**
```
URL: https://www.intelligence-airbusds.com/

What:
- Pleiades (50cm resolution)
- SPOT satellites
- Near-real-time

Cost: Similar to Maxar
```

## 🔬 **SPECIFIC EXAMPLE SEARCHES**

### Example 1: Aleppo Water Infrastructure
```
Google: "Aleppo water station" damage satellite imagery

USGS EarthExplorer:
- Location: 36.2°N, 37.15°E
- Date: 2015-2017 (heavy conflict period)
- Dataset: Landsat 8
- Path/Row: 174/35

Copernicus:
- Search: "Aleppo"
- Product: Sentinel-2
- Date: 2016-2024 (before/after)
```

### Example 2: Mosul Water Treatment
```
Coordinates: 36.34°N, 43.12°E

Search terms:
"Mosul water treatment plant" destruction
"Mosul water infrastructure" ISIS damage
site:unosat.org Mosul water

Satellite:
- Landsat 8: Path 169/Row 35
- Sentinel-2: Tile 38SMB
```

### Example 3: Damascus Suburbs Pipeline
```
Google: "Damascus Ghouta" water pipeline damage

Sentinel Hub EO Browser:
https://apps.sentinel-hub.com/eo-browser/
- Location: Damascus suburbs
- Time range: 2018-2024
- Visualization: False color (to see vegetation/water)
```

## 💾 **DOWNLOAD & PREPROCESSING SCRIPTS**

### Download Sentinel-2 (Python)
```python
from sentinelsat import SentinelAPI

api = SentinelAPI('username', 'password', 
                  'https://scihub.copernicus.eu/dhus')

# Baghdad area
footprint = "POLYGON((44.3 33.2, 44.5 33.2, 44.5 33.4, 44.3 33.4, 44.3 33.2))"

products = api.query(footprint,
                     date=('20200101', '20240101'),
                     platformname='Sentinel-2',
                     cloudcoverpercentage=(0, 10))

# Download
api.download_all(products)
```

### Download Landsat (Python)
```python
import landsatxplore

# Search
results = landsatxplore.search(
    dataset='landsat_ot_c2_l2',
    latitude=33.3,
    longitude=44.4,
    start_date='2020-01-01',
    end_date='2024-01-01',
    max_cloud_cover=10
)

# Download
for result in results:
    landsatxplore.download(result['entityId'], 
                          output_dir='./imagery/')
```

## 🎯 **WHAT TO LOOK FOR IN IMAGERY**

### Signs of Water Leaks:

#### 1. **Thermal Anomalies**
```
What to see:
- Cool spots (water is cooler than soil)
- Linear patterns (following pipe routes)
- Consistent temperature difference
- Size: 5-50m diameter

Best time: Early morning or late evening
Best band: Landsat 8 Band 10 (thermal)
```

#### 2. **Vegetation Anomalies (NDVI)**
```
What to see:
- Greener patches in urban areas
- Linear green patterns
- Contrast with surrounding vegetation

Formula: NDVI = (NIR - Red) / (NIR + Red)
Bands: Sentinel-2 B8 (NIR) and B4 (Red)
```

#### 3. **Ground Subsidence**
```
What to see:
- Depressions in roads
- Collapsed areas
- Cracks in pavement
- Compare temporal images

Method: Change detection between dates
```

#### 4. **Water Ponding**
```
What to see:
- Standing water in dry areas
- Wet soil appearance
- Dark patches

Formula: NDWI = (Green - NIR) / (Green + NIR)
```

## 📁 **ORGANIZING YOUR TEST DATASET**

### Recommended Structure:
```
test_imagery/
├── thermal/
│   ├── landsat8_thermal_baghdad_2023.tif
│   ├── flir_drone_leak1.jpg
│   └── metadata.json
├── multispectral/
│   ├── sentinel2_baghdad_20230515.tif
│   ├── bands/
│   │   ├── B04_red.tif
│   │   ├── B08_nir.tif
│   │   └── B03_green.tif
│   └── metadata.json
├── temporal/
│   ├── before_war_2011.tif
│   ├── during_conflict_2015.tif
│   ├── after_2020.tif
│   └── metadata.json
├── ground_truth/
│   ├── confirmed_leaks.geojson
│   ├── pipe_network.geojson
│   └── labels.csv
└── documentation/
    ├── sources.md
    ├── preprocessing.md
    └── licenses.txt
```

## ⚖️ **LEGAL CONSIDERATIONS**

### Can You Use This Imagery?

**✅ FREE TO USE:**
- Landsat (US Government - Public Domain)
- Sentinel (ESA - Open Access)
- NASA imagery (Public Domain)
- UN humanitarian data (Open License)

**✅ WITH ATTRIBUTION:**
- Google Earth imagery (with proper credit)
- Academic datasets (cite the paper)
- Creative Commons licensed images

**⚠️ COMMERCIAL RESTRICTIONS:**
- Planet Labs (license required)
- Maxar (license required)
- News agency photos (contact for permission)

**📄 DOCUMENTATION:**
Always include:
```
Image source: [Sentinel-2, Copernicus]
Acquisition date: [2023-05-15]
License: [Open Access]
URL: [https://scihub.copernicus.eu/...]
Processing: [Describe any modifications]
```

## 🔧 **QUICK START COMMANDS**

### Download Sample Imagery:
```bash
# Install tools
pip install sentinelsat landsatxplore rasterio

# Download Sentinel-2 for Baghdad
python download_sentinel.py --lat 33.3 --lon 44.4 \
       --start 2023-01-01 --end 2023-12-31 \
       --clouds 10

# Download Landsat 8
python download_landsat.py --lat 33.3 --lon 44.4 \
       --start 2023-01-01 --end 2023-12-31

# Process for water leak detection
python preprocess_imagery.py --input sentinel2.tif \
       --output processed/ --calc-ndvi --calc-ndwi
```

## 📝 **FOR YOUR DOCUMENTATION**

### Sample Figure Captions:
```
Figure 1: Thermal imagery showing temperature anomaly 
indicating potential water leak. Source: Landsat 8, 
2023-06-15. Location: Baghdad, Iraq (33.3°N, 44.4°E).

Figure 2: NDVI analysis showing vegetation anomaly 
along pipeline route. Data: Sentinel-2 L2A. 
Acquisition: 2023-05-20. Cloud cover: <5%.

Figure 3: Before (2011) and after (2015) comparison 
showing infrastructure damage. Source: USGS EarthExplorer.
Resolution: 30m.
```

## 🎯 **RECOMMENDED APPROACH**

### For Your Documentation:

**Step 1:** Get free Sentinel-2 imagery
```
- Go to https://scihub.copernicus.eu/
- Search: Your target city
- Download: Recent cloudless image
- This is LEGAL and FREE
```

**Step 2:** Get thermal from Landsat 8
```
- Go to https://earthexplorer.usgs.gov/
- Same location
- Download: Band 10 (thermal)
- Also FREE
```

**Step 3:** Look for examples on YouTube
```
- Search: "thermal water leak detection"
- Download educational videos
- Extract frames
- Reference source
```

**Step 4:** Create synthetic examples
```
- If no real data, create annotated examples
- Use image editing to show:
  * What thermal anomaly looks like
  * What NDVI anomaly looks like
  * What ponding looks like
- Clearly label as "Illustrative example"
```

---

## 🎊 **READY-TO-USE SEARCH COMMANDS**

Copy and paste these into Google:

```
1. site:researchgate.net "water leak detection" thermal imaging filetype:pdf

2. "water pipeline damage" Syria satellite before after

3. site:github.com water leak thermal dataset

4. site:kaggle.com infrastructure damage detection

5. "Sentinel-2" NDVI water leak detection

6. thermal drone water leak site:youtube.com

7. "water main break" aerial thermal imagery

8. site:unosat.org water infrastructure damage assessment

9. "Landsat 8" thermal band pipeline monitoring

10. site:data.humdata.org water infrastructure Syria
```

**Start with these and you'll find PLENTY of test imagery!** 🎯

---

**Good luck with your testing!** 🚀
