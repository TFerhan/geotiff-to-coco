#!/bin/bash

# GDAL Retile Interactive Script
# This script helps tile large GeoTIFF images into smaller tiles for machine learning datasets

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate directory path
validate_directory() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        print_error "Directory '$dir' does not exist!"
        return 1
    fi
    return 0
}

# Function to validate file path
validate_file() {
    local file="$1"
    if [ ! -f "$file" ]; then
        print_error "File '$file' does not exist!"
        return 1
    fi
    return 0
}

# Function to get user input with default value
get_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        echo "${input:-$default}"
    else
        read -p "$prompt: " input
        echo "$input"
    fi
}

# Function to get yes/no input
get_yes_no() {
    local prompt="$1"
    local default="$2"
    local input
    
    while true; do
        if [ -n "$default" ]; then
            read -p "$prompt (y/n) [$default]: " input
            input="${input:-$default}"
        else
            read -p "$prompt (y/n): " input
        fi
        
        case "$input" in
            [Yy]|[Yy]es) return 0 ;;
            [Nn]|[Nn]o) return 1 ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

# Function to display help
show_help() {
    cat << EOF
GDAL Retile Interactive Script
=============================

This script helps you tile large GeoTIFF images into smaller tiles suitable for machine learning datasets.

Usage:
    $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -i, --input FILE    Input GeoTIFF file
    -o, --output DIR    Output directory for tiles
    -s, --size SIZE     Tile size (default: 640)
    -v, --overlap SIZE  Overlap size (default: 64)
    --csv FILE          CSV metadata file (optional)
    --batch             Run in batch mode (non-interactive)

Examples:
    $0                                    # Interactive mode
    $0 -i input.tif -o tiles/             # Specify input and output
    $0 --batch -i input.tif -o tiles/     # Batch mode

Requirements:
    - GDAL tools (gdal_retile.py)
    - Write permissions for output directory

EOF
}

# Default values
DEFAULT_TILE_SIZE=640
DEFAULT_OVERLAP=64
BATCH_MODE=false
INPUT_FILE=""
OUTPUT_DIR=""
CSV_FILE=""
TILE_SIZE=""
OVERLAP=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--input)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--size)
            TILE_SIZE="$2"
            shift 2
            ;;
        -v|--overlap)
            OVERLAP="$2"
            shift 2
            ;;
        --csv)
            CSV_FILE="$2"
            shift 2
            ;;
        --batch)
            BATCH_MODE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if GDAL is installed
if ! command_exists gdal_retile.py; then
    print_error "gdal_retile.py is not installed or not in PATH"
    print_info "Install GDAL tools:"
    print_info "Ubuntu/Debian: sudo apt-get install gdal-bin"
    print_info "CentOS/RHEL: sudo yum install gdal"
    print_info "macOS: brew install gdal"
    exit 1
fi

print_info "GDAL Retile Interactive Script"
print_info "================================"
echo

# Interactive mode
if [ "$BATCH_MODE" = false ]; then
    print_info "This script will help you tile a large GeoTIFF image into smaller tiles."
    echo
    
    # Get input file
    while true; do
        if [ -n "$INPUT_FILE" ]; then
            INPUT_FILE=$(get_input "Enter input GeoTIFF file path" "$INPUT_FILE")
        else
            INPUT_FILE=$(get_input "Enter input GeoTIFF file path")
        fi
        
        if validate_file "$INPUT_FILE"; then
            break
        fi
    done
    
    # Get output directory
    while true; do
        if [ -n "$OUTPUT_DIR" ]; then
            OUTPUT_DIR=$(get_input "Enter output directory for tiles" "$OUTPUT_DIR")
        else
            OUTPUT_DIR=$(get_input "Enter output directory for tiles" "tiles")
        fi
        
        # Create directory if it doesn't exist
        if [ ! -d "$OUTPUT_DIR" ]; then
            if get_yes_no "Directory '$OUTPUT_DIR' doesn't exist. Create it?" "y"; then
                mkdir -p "$OUTPUT_DIR"
                print_success "Created directory: $OUTPUT_DIR"
                break
            fi
        else
            if [ "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]; then
                if get_yes_no "Directory '$OUTPUT_DIR' is not empty. Continue?" "n"; then
                    break
                fi
            else
                break
            fi
        fi
    done
    
    # Get tile size
    TILE_SIZE=$(get_input "Enter tile size (pixels)" "${TILE_SIZE:-$DEFAULT_TILE_SIZE}")
    
    # Get overlap
    OVERLAP=$(get_input "Enter overlap size (pixels)" "${OVERLAP:-$DEFAULT_OVERLAP}")
    
    # Get CSV metadata file (optional)
    if get_yes_no "Generate CSV metadata file?" "y"; then
        CSV_FILE=$(get_input "Enter CSV metadata file name" "metadata.csv")
    fi
    
    # Show summary
    echo
    print_info "Configuration Summary:"
    print_info "Input file: $INPUT_FILE"
    print_info "Output directory: $OUTPUT_DIR"
    print_info "Tile size: ${TILE_SIZE}x${TILE_SIZE}"
    print_info "Overlap: $OVERLAP pixels"
    if [ -n "$CSV_FILE" ]; then
        print_info "CSV metadata: $CSV_FILE"
    fi
    echo
    
    if ! get_yes_no "Proceed with tiling?" "y"; then
        print_info "Operation cancelled."
        exit 0
    fi
    
else
    # Batch mode validation
    if [ -z "$INPUT_FILE" ] || [ -z "$OUTPUT_DIR" ]; then
        print_error "Batch mode requires --input and --output arguments"
        exit 1
    fi
    
    if ! validate_file "$INPUT_FILE"; then
        exit 1
    fi
    
    # Set defaults if not provided
    TILE_SIZE="${TILE_SIZE:-$DEFAULT_TILE_SIZE}"
    OVERLAP="${OVERLAP:-$DEFAULT_OVERLAP}"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
fi

# Validate numeric inputs
if ! [[ "$TILE_SIZE" =~ ^[0-9]+$ ]] || [ "$TILE_SIZE" -lt 1 ]; then
    print_error "Tile size must be a positive integer"
    exit 1
fi

if ! [[ "$OVERLAP" =~ ^[0-9]+$ ]] || [ "$OVERLAP" -lt 0 ]; then
    print_error "Overlap must be a non-negative integer"
    exit 1
fi

# Build gdal_retile command
GDAL_CMD="gdal_retile.py"
GDAL_CMD="$GDAL_CMD -ps $TILE_SIZE $TILE_SIZE"
GDAL_CMD="$GDAL_CMD -overlap $OVERLAP"
GDAL_CMD="$GDAL_CMD -targetDir $OUTPUT_DIR"

if [ -n "$CSV_FILE" ]; then
    GDAL_CMD="$GDAL_CMD -csv $CSV_FILE"
    GDAL_CMD="$GDAL_CMD -csvDelim ,"
fi

GDAL_CMD="$GDAL_CMD $INPUT_FILE"

# Execute the command
print_info "Starting tiling process..."
print_info "Command: $GDAL_CMD"
echo

if eval "$GDAL_CMD"; then
    print_success "Tiling completed successfully!"
    
    # Count generated tiles
    TILE_COUNT=$(find "$OUTPUT_DIR" -name "*.tif" -o -name "*.tiff" | wc -l)
    print_info "Generated $TILE_COUNT tiles in $OUTPUT_DIR"
    
    if [ -n "$CSV_FILE" ] && [ -f "$CSV_FILE" ]; then
        print_info "Metadata saved to: $CSV_FILE"
    fi
    
    # Show next steps
    echo
    print_info "Next steps:"
    print_info "1. Review the generated tiles in: $OUTPUT_DIR"
    print_info "2. Prepare your OSM building data (CSV format)"
    print_info "3. Run the GeoTIFF to COCO converter:"
    print_info "   python geo_to_coco.py --images $OUTPUT_DIR --csv buildings.csv --output dataset.json"
    
else
    print_error "Tiling failed!"
    exit 1
fi
