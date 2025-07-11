import rasterio
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.wkt import loads
import pyproj
from pyproj import Transformer
import json
from datetime import datetime
import cv2
from PIL import Image, ImageDraw
import os
import glob
import argparse
import sys

class GeoTiffToCoco:
    def __init__(self, images_folder_path, csv_path, min_area = 10):
        self.images_folder_path = images_folder_path
        self.csv_path = csv_path
        self.min_area = min_area
        self.image_size = 640  # Fixed size for all images
        self.image_info = {}
        self.categories = {}
        self.annotations = []
        self.annotation_mapping = []  # New list to store mapping information
        self.coco_format = {
            "info": {
                "description": "Dataset for buildings type of Morocco",
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "TFERHAN",
                "date_created": datetime.now().isoformat()
            },
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": []
        }

    def load_images(self):
        """Load all images from the folder and get their information"""
        # Get all image files (common formats)
        image_extensions = ['*.tif', '*.tiff', '*.jpg', '*.jpeg', '*.png']
        image_files = []

        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(self.images_folder_path, ext)))
            image_files.extend(glob.glob(os.path.join(self.images_folder_path, ext.upper())))

        self.image_files = sorted(image_files)

        print(f"Found {len(self.image_files)} images in folder")

        # Load each image and get its geospatial information
        self.images_info = []
        for idx, image_path in enumerate(self.image_files):
            try:
                with rasterio.open(image_path) as src:
                    image_info = {
                        'id': idx + 1,
                        'path': image_path,
                        'filename': os.path.basename(image_path),
                        'width': src.width,
                        'height': src.height,
                        'crs': src.crs,
                        'transform': src.transform,
                        'bounds': src.bounds
                    }
                    self.images_info.append(image_info)

                    # Add to COCO format
                    coco_image_info = {
                        "id": idx + 1,
                        "width": src.width,
                        "height": src.height,
                        "file_name": os.path.basename(image_path),
                        "license": 1,
                        "date_captured": datetime.now().isoformat()
                    }
                    self.coco_format["images"].append(coco_image_info)

            except Exception as e:
                print(f"Error loading image {image_path}: {e}")
                continue

        print(f"Successfully loaded {len(self.images_info)} images")

    def load_csv(self):
        """Load the CSV file with building data"""
        self.df = pd.read_csv(self.csv_path)

        if 'building' not in self.df.columns or 'geometry' not in self.df.columns:
            raise ValueError("CSV must contain 'building' and 'geometry' columns")

        # Convert WKT strings to shapely geometries
        self.df['geometry'] = self.df['geometry'].apply(lambda wkt: loads(wkt) if isinstance(wkt, str) else wkt)

        # Filter valid geometries
        valid_mask = self.df['geometry'].apply(lambda geom: geom is not None and hasattr(geom, 'exterior'))
        self.df = self.df[valid_mask].reset_index(drop=True)

        # Create categories
        unique_types = self.df['building'].unique()
        self.categories = {building_type: idx + 1 for idx, building_type in enumerate(unique_types)}

        # Add categories to COCO format
        for cat_name, cat_id in self.categories.items():
            category_info = {
                "id": cat_id,
                "name": cat_name,
                "supercategory": "building"
            }
            self.coco_format["categories"].append(category_info)

        print(f"Found {len(self.df)} polygons with {len(unique_types)} building types")
        print(f"Building types: {list(unique_types)}")

    def setup_coordinate_transformer(self, source_crs):
        """Setup coordinate transformer for a specific CRS"""
        if source_crs.to_epsg() != 4326:
            return Transformer.from_crs("EPSG:4326", source_crs, always_xy=True)
        else:
            return None

    def geographic_to_pixel(self, lon, lat, transform, transformer=None):
        """Convert geographic coordinates to pixel coordinates"""
        if transformer:
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        col = int((x - transform.c) / transform.a)
        row = int((y - transform.f) / transform.e)

        return col, row

    def polygon_to_pixel_coords(self, polygon, transform, transformer=None):
        """Convert polygon coordinates to pixel coordinates"""
        pixel_coords = []

        exterior_coords = list(polygon.exterior.coords)
        for lon, lat in exterior_coords:
            col, row = self.geographic_to_pixel(lon, lat, transform, transformer)
            pixel_coords.append([col, row])

        return pixel_coords

    def get_bbox_from_coords(self, coords):
        """Get bounding box from coordinates"""
        coords_array = np.array(coords)
        x_min, y_min = coords_array.min(axis=0)
        x_max, y_max = coords_array.max(axis=0)

        width = x_max - x_min
        height = y_max - y_min

        return [int(x_min), int(y_min), int(width), int(height)]

    def get_segmentation_from_coords(self, coords):
        """Get segmentation format from coordinates"""
        segmentation = []
        for coord in coords:
            segmentation.extend(coord)

        return [segmentation]

    def calculate_area(self, coords):
        """Calculate area of polygon"""
        coords_array = np.array(coords)
        x = coords_array[:, 0]
        y = coords_array[:, 1]

        area = 0.5 * abs(sum(x[i] * y[i+1] - x[i+1] * y[i] for i in range(-1, len(x)-1)))
        return area

    def polygon_intersects_image(self, polygon, image_bounds):
        """Check if polygon intersects with image bounds"""
        # Create a polygon from image bounds
        image_poly = Polygon([
            (image_bounds.left, image_bounds.bottom),
            (image_bounds.right, image_bounds.bottom),
            (image_bounds.right, image_bounds.top),
            (image_bounds.left, image_bounds.top)
        ])

        return polygon.intersects(image_poly)

    def filter_valid_polygons_for_image(self, image_info):
        """Filter polygons that are valid for a specific image"""
        valid_polygons = []
        transformer = self.setup_coordinate_transformer(image_info['crs'])

        for idx, row in self.df.iterrows():
            polygon = row['geometry']

            # Check if polygon intersects with image bounds
            if not self.polygon_intersects_image(polygon, image_info['bounds']):
                continue

            # Convert to pixel coordinates
            pixel_coords = self.polygon_to_pixel_coords(polygon, image_info['transform'], transformer)

            coords_array = np.array(pixel_coords)

            # Check if polygon is within image bounds
            if (coords_array[:, 0].max() < 0 or coords_array[:, 0].min() > image_info['width'] or
                coords_array[:, 1].max() < 0 or coords_array[:, 1].min() > image_info['height']):
                continue

            # Clip coordinates to image bounds
            coords_array[:, 0] = np.clip(coords_array[:, 0], 0, image_info['width'])
            coords_array[:, 1] = np.clip(coords_array[:, 1], 0, image_info['height'])

            # Calculate area and filter small polygons
            area = self.calculate_area(coords_array)
            if area > self.min_area:
                valid_polygons.append({
                    'building': row['building'],
                    'coords': coords_array.tolist(),
                    'original_idx': idx
                })

        return valid_polygons

    def convert_tiff_to_jpg(self, tiff_path, quality=100):
        """Convert TIFF image to JPG with specified quality"""
        try:
            # Create JPG filename
            jpg_path = tiff_path.rsplit('.', 1)[0] + '.jpg'

            # Open and convert TIFF to JPG
            with Image.open(tiff_path) as img:
                # Convert to RGB if necessary (TIFF might be in different modes)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Save as JPG with specified quality
                img.save(jpg_path, 'JPEG', quality=quality, optimize=True)

            print(f"  Converted: {os.path.basename(tiff_path)} -> {os.path.basename(jpg_path)}")
            return jpg_path

        except Exception as e:
            print(f"  Error converting {tiff_path}: {e}")
            return None

    def convert_all_tiff_to_jpg(self, quality=100):
        """Convert all TIFF images to JPG and update COCO dataset paths"""
        print("\nConverting TIFF images to JPG...")

        conversions = {}  # Track old_path -> new_path mappings

        for i, image_info in enumerate(self.coco_format["images"]):
            file_name = image_info["file_name"]

            # Check if it's a TIFF file
            if file_name.lower().endswith(('.tif', '.tiff')):
                # Get full path
                full_path = None
                for img_info in self.images_info:
                    if img_info['filename'] == file_name:
                        full_path = img_info['path']
                        break

                if full_path:
                    # Convert TIFF to JPG
                    jpg_path = self.convert_tiff_to_jpg(full_path, quality)

                    if jpg_path:
                        # Update filename in COCO format
                        new_filename = os.path.basename(jpg_path)
                        self.coco_format["images"][i]["file_name"] = new_filename
                        conversions[full_path] = jpg_path

                        # Update images_info as well
                        for img_info in self.images_info:
                            if img_info['path'] == full_path:
                                img_info['path'] = jpg_path
                                img_info['filename'] = new_filename
                                break

        if conversions:
            print(f"Successfully converted {len(conversions)} TIFF images to JPG")

            # Optionally delete original TIFF files
            delete_originals = input("Delete original TIFF files? (y/n): ").lower().strip()
            if delete_originals == 'y':
                for tiff_path in conversions.keys():
                    try:
                        os.remove(tiff_path)
                        print(f"  Deleted: {os.path.basename(tiff_path)}")
                    except Exception as e:
                        print(f"  Error deleting {tiff_path}: {e}")
        else:
            print("No TIFF files found to convert")

    def create_coco_dataset(self, output_path, convert_tiff_to_jpg=True, jpg_quality=100):
        """Create the complete COCO dataset"""
        print("Loading images...")
        self.load_images()

        print("Loading CSV data...")
        self.load_csv()

        annotation_id = 1

        # Process each image
        for image_info in self.images_info:
            print(f"Processing image {image_info['id']}: {image_info['filename']}")

            # Filter polygons for this image
            valid_polygons = self.filter_valid_polygons_for_image(image_info)

            print(f"  Found {len(valid_polygons)} valid polygons for this image")

            # Create annotations for this image
            for polygon_data in valid_polygons:
                coords = polygon_data['coords']
                building_type = polygon_data['building']

                bbox = self.get_bbox_from_coords(coords)
                segmentation = self.get_segmentation_from_coords(coords)
                area = self.calculate_area(coords)

                annotation = {
                    "id": annotation_id,
                    "image_id": image_info['id'],
                    "category_id": self.categories[building_type],
                    "segmentation": segmentation,
                    "area": area,
                    "bbox": bbox,
                    "iscrowd": 0
                }

                self.coco_format["annotations"].append(annotation)

                # Save mapping information for later use
                self.annotation_mapping.append({
                    "annotation_id": annotation_id,
                    "image_id": image_info['id'],
                    "image_filename": image_info['filename'],
                    "polygon_csv_idx": polygon_data['original_idx'],
                    "category_name": building_type,
                    "category_id": self.categories[building_type],
                    "bbox": bbox,
                    "area": area
                })

                annotation_id += 1

        # Convert TIFF to JPG if requested
        if convert_tiff_to_jpg:
            self.convert_all_tiff_to_jpg(jpg_quality)

        # Save the COCO dataset
        with open(output_path, 'w') as f:
            json.dump(self.coco_format, f, indent=2)

        # Save mapping information
        mapping_path = output_path.replace('.json', '_mapping.json')
        with open(mapping_path, 'w') as f:
            json.dump(self.annotation_mapping, f, indent=2)

        print(f"\nCOCO dataset created successfully!")
        print(f"Total images: {len(self.coco_format['images'])}")
        print(f"Total annotations: {len(self.coco_format['annotations'])}")
        print(f"Total categories: {len(self.coco_format['categories'])}")
        print(f"Saved to: {output_path}")
        print(f"Mapping saved to: {mapping_path}")

        # Validate COCO structure
        self.validate_coco_structure(output_path)

        return self.coco_format

    def validate_coco_structure(self, coco_path):
        """Validate COCO structure using pycocotools"""
        try:
            from pycocotools.coco import COCO

            # Suppress pycocotools output
            import io
            import contextlib

            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                coco = COCO(coco_path)

            # Basic validation checks
            image_ids = coco.getImgIds()
            ann_ids = coco.getAnnIds()
            cat_ids = coco.getCatIds()

            print(f"\nCOCO Validation Results:")
            print(f"✓ Structure is valid")
            print(f"✓ Images: {len(image_ids)}")
            print(f"✓ Annotations: {len(ann_ids)}")
            print(f"✓ Categories: {len(cat_ids)}")

            # Check for orphaned annotations
            orphaned_count = 0
            for ann_id in ann_ids:
                ann = coco.loadAnns([ann_id])[0]
                if ann['image_id'] not in image_ids:
                    orphaned_count += 1

            if orphaned_count > 0:
                print(f"⚠ Warning: {orphaned_count} orphaned annotations found")
            else:
                print("✓ No orphaned annotations")

        except ImportError:
            print("\n⚠ pycocotools not installed. Cannot validate COCO structure.")
            print("Install with: pip install pycocotools")
        except Exception as e:
            print(f"\n❌ COCO validation failed: {e}")

def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='Convert GeoTIFF images and OSM CSV to COCO format')

    parser.add_argument('--images', '-i', required=True,
                       help='Path to folder containing 640x640 images')
    parser.add_argument('--csv', '-c', required=True,
                       help='Path to CSV file with OSM building data')
    parser.add_argument('--output', '-o', required=True,
                       help='Output path for COCO JSON file')
    parser.add_argument('--quality', '-q', type=int, default=100,
                       help='JPG quality for TIFF conversion (1-100, default: 100)')
    parser.add_argument('--no-convert', action='store_true',
                       help='Skip TIFF to JPG conversion')
    parser.add_argument('--validate', action='store_true',
                       help='Validate COCO structure after creation')

    args = parser.parse_args()

    # Validate arguments
    if not os.path.exists(args.images):
        print(f"Error: Images folder '{args.images}' does not exist")
        sys.exit(1)

    if not os.path.exists(args.csv):
        print(f"Error: CSV file '{args.csv}' does not exist")
        sys.exit(1)

    if not 1 <= args.quality <= 100:
        print("Error: Quality must be between 1 and 100")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize converter
    print(f"Initializing GeoTIFF to COCO converter...")
    print(f"Images folder: {args.images}")
    print(f"CSV file: {args.csv}")
    print(f"Output: {args.output}")
    print(f"JPG quality: {args.quality}")
    print(f"Convert TIFF: {not args.no_convert}")
    print("-" * 50)

    converter = GeoTiffToCoco(
        images_folder_path=args.images,
        csv_path=args.csv
    )

    # Create COCO dataset
    try:
        coco_dataset = converter.create_coco_dataset(
            output_path=args.output,
            convert_tiff_to_jpg=not args.no_convert,
            jpg_quality=args.quality
        )

        print("\n" + "="*50)
        print("✓ COCO dataset creation completed successfully!")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Error creating COCO dataset: {e}")
        sys.exit(1)
