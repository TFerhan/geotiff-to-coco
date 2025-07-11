# GeoTIFF to COCO Converter Documentation

## Overview

This tool converts geospatial imagery (GeoTIFF files) and OpenStreetMap (OSM) building data into the COCO (Common Objects in Context) format, enabling the creation of computer vision datasets for building detection and classification tasks. The converter bridges the gap between geospatial data and machine learning workflows by transforming geographic coordinates into pixel-based annotations.

## Key Features

### Core Functionality
- **Multi-format Image Support**: Processes GeoTIFF, TIFF, JPG, JPEG, and PNG images
- **Coordinate Transformation**: Automatically converts geographic coordinates (latitude/longitude) to pixel coordinates using geospatial transformations
- **Building Classification**: Categorizes buildings based on OSM building types (residential, commercial, industrial, etc.)
- **Polygon Annotation**: Creates precise segmentation masks for each building footprint
- **Bounding Box Generation**: Automatically generates bounding boxes around building polygons
- **Image Format Conversion**: Converts TIFF images to JPG format with configurable quality settings

### Quality Control
- **Spatial Filtering**: Only includes buildings that intersect with image boundaries
- **Area Filtering**: Removes small polygons below a minimum area threshold (default: 10 pixels)
- **Coordinate Clipping**: Ensures all annotations stay within image bounds
- **Data Validation**: Validates COCO structure using pycocotools

### Output Generation
- **COCO JSON Dataset**: Standard COCO format compatible with popular ML frameworks
- **Annotation Mapping**: Detailed mapping file linking annotations to original data sources
- **Metadata Preservation**: Maintains image metadata and geospatial information

## Value Proposition

### For Computer Vision Researchers
- **Ready-to-Use Datasets**: Eliminates the manual annotation process for building detection tasks
- **Scalable Processing**: Handles large datasets with hundreds of images and thousands of building polygons
- **Framework Compatibility**: Works seamlessly with PyTorch, TensorFlow, and other ML frameworks that support COCO format

### For Geospatial Professionals
- **Bridge GIS and ML**: Connects traditional GIS workflows with modern machine learning approaches
- **Automated Workflow**: Reduces manual processing time from days to hours
- **Accuracy Preservation**: Maintains spatial accuracy through proper coordinate transformations

### For Urban Planning and Development
- **Building Analysis**: Enables automated building detection and classification from satellite/aerial imagery
- **Change Detection**: Facilitates temporal analysis of urban development
- **Large-Scale Mapping**: Supports city-wide or regional building inventory projects

## Requirements

```txt
rasterio>=1.3.0
pandas>=1.5.0
numpy>=1.21.0
shapely>=1.8.0
pyproj>=3.4.0
opencv-python>=4.6.0
Pillow>=9.0.0
pycocotools>=2.0.4
osmnx>=1.2.0
geopandas>=0.11.0
```

## Installation

```bash
# Install required packages
pip install -r requirements.txt

# For QGIS integration (optional)
apt-get update
apt-get install qgis python3-qgis
pip install GDAL
```

## Usage

### Command Line Interface

```bash
# Basic usage
python geo_to_coco.py --images /path/to/images --csv buildings.csv --output dataset.json

# With custom quality settings
python geo_to_coco.py --images /path/to/images --csv buildings.csv --output dataset.json --quality 90

# Skip TIFF conversion
python geo_to_coco.py --images /path/to/images --csv buildings.csv --output dataset.json --no-convert
```

### Python Module Usage

```python
from geo_to_coco import GeoTiffToCoco

# Initialize converter
converter = GeoTiffToCoco(
    images_folder_path="/path/to/images",
    csv_path="/path/to/buildings.csv",
    min_area=10  # Minimum polygon area in pixels
)

# Create COCO dataset
coco_dataset = converter.create_coco_dataset(
    output_path="output.json",
    convert_tiff_to_jpg=True,
    jpg_quality=90
)
```

## Input Data Requirements

### Image Data
- **Format**: GeoTIFF, TIFF, JPG, JPEG, or PNG
- **Geospatial Information**: Must contain coordinate reference system (CRS) and transformation matrix
- **Recommended Resolution**: 640x640 pixels for optimal performance
- **Coordinate System**: Any projected coordinate system (automatically handled)

### CSV Building Data
- **Required Columns**:
  - `building`: Building type classification (e.g., "residential", "commercial")
  - `geometry`: WKT (Well-Known Text) polygon geometries
- **Coordinate System**: WGS84 (EPSG:4326) recommended
- **Data Source**: Typically exported from OSM or other GIS databases

## Output Structure

### COCO JSON Dataset
- **Images**: Metadata for each image including dimensions and file paths
- **Annotations**: Building polygons with segmentation masks, bounding boxes, and categories
- **Categories**: Building type classifications with unique IDs
- **Metadata**: Dataset information, creation date, and versioning

### Annotation Mapping File
- **Traceability**: Links each annotation back to original CSV row
- **Quality Metrics**: Area calculations and validation flags
- **Debugging Support**: Facilitates troubleshooting and data quality assessment

## Performance Considerations

### Processing Speed
- **Batch Processing**: Handles multiple images simultaneously
- **Memory Optimization**: Processes images individually to manage memory usage
- **Parallel Processing**: Can be extended for multi-core processing

### Storage Requirements
- **Input**: Varies based on image size and format
- **Output**: JSON files are typically 1-10MB for city-scale datasets
- **Temporary**: Additional space needed for TIFF to JPG conversion

## Applications

### Research Applications
- **Building Detection**: Train models to identify buildings in satellite imagery
- **Urban Morphology**: Analyze building patterns and urban structure
- **Change Detection**: Monitor urban development over time

### Commercial Applications
- **Property Assessment**: Automated building inventory and valuation
- **Insurance**: Risk assessment based on building types and density
- **Urban Planning**: Support development planning and zoning decisions

### Government Applications
- **Census Support**: Building counting and classification for demographic analysis
- **Emergency Planning**: Building inventory for disaster response planning
- **Tax Assessment**: Automated property identification and classification

## Validation and Quality Assurance

The tool includes built-in validation to ensure data quality:
- **Coordinate Validation**: Verifies all coordinates fall within image bounds
- **Polygon Validation**: Checks for valid polygon geometries
- **COCO Compliance**: Validates output against COCO format specifications
- **Orphaned Annotation Detection**: Identifies and reports annotation issues

This comprehensive tool transforms complex geospatial data into machine learning-ready formats, enabling researchers and practitioners to leverage building footprint data for computer vision applications at scale.
