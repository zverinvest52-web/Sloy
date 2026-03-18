# Architecture Documentation

## Overview

The Sloy backend CAD conversion system has been refactored into a modular architecture that separates concerns into specialized components. This document describes the new structure, data flow, design decisions, and deployment guide.

## Modular Structure

### Directory Organization

```
backend/cad/
├── models.py              # Data models (Polyline, Circle, Arc, Line, etc.)
├── validators.py          # Input validation
├── exceptions.py          # Custom exceptions
├── logging_config.py       # Logging configuration
├── __init__.py
├── detectors/             # Detection modules
│   ├── __init__.py
│   ├── base_detector.py   # Abstract base class
│   ├── circle_detector.py # Circle detection (contour + Hough)
│   ├── arc_detector.py    # Arc detection (partial circles)
│   ├── line_detector.py   # Line detection (Hough transform)
│   └── polyline_detector.py # Polyline detection (contour extraction)
├── filters/               # Filtering and refinement modules
│   ├── __init__.py
│   ├── beads_filter.py    # Remove small circles near larger ones
│   ├── corner_filter.py   # Remove circles near polyline corners (KD-tree optimized)
│   └── deduplicator.py    # Remove duplicate detections
├── processors/            # Processing and optimization modules
│   ├── __init__.py
│   ├── polyline_cleaner.py # Orthogonal snapping, short segment removal
│   ├── line_merger.py     # Merge collinear line segments
│   └── snap_extender.py   # Snap and extend interior lines
├── exporters/             # Export format modules
│   ├── __init__.py
│   ├── dxf_exporter.py    # DXF R2010 export
│   └── dxf_r12_exporter.py # DXF R12 export (legacy)
└── utils/                 # Utility modules
    ├── __init__.py
    ├── geometry.py        # Geometry utilities (scaling, deduplication)
    └── spatial_index.py   # Spatial indexing (KD-tree, R-tree)
```

### Component Purposes

**Detectors** - Identify CAD elements in binary images:
- `CircleDetector`: Finds circular shapes using contour circularity and Hough transform
- `ArcDetector`: Identifies partial circles/arcs with angular gap analysis
- `LineDetector`: Extracts line segments using Hough Line Transform
- `PolylineDetector`: Extracts closed polylines from contours with edge artifact filtering

**Filters** - Refine detected elements:
- `BeadsFilter`: Removes small circles that are noise on larger circles
- `CornerFilter`: Removes circles near polyline corners/edges (KD-tree optimized)
- `Deduplicator`: Removes duplicate detections within tolerance

**Processors** - Optimize and clean elements:
- `PolylineCleaner`: Snaps near-orthogonal segments, removes short segments, merges collinear segments
- `LineMerger`: Merges collinear line segments to reduce entity count
- `SnapExtender`: Snaps interior lines to polylines and extends them

**Exporters** - Write to output formats:
- `DXFExporter`: Exports to modern DXF R2010 format
- `DXFR12Exporter`: Exports to legacy DXF R12 format with POLYLINE entities

**Utils** - Shared functionality:
- `GeometryUtils`: Point scaling, deduplication, adaptive tolerances
- `SpatialIndex`: KD-tree and R-tree for efficient spatial queries

## Data Flow Through Detection Pipeline

```
Binary Image Input
    ↓
[Preprocessing]
    ├─ Grayscale conversion
    ├─ Inversion (if needed)
    └─ Caching for performance
    ↓
[Parallel Detection]
    ├─ PolylineDetector → Polylines
    ├─ CircleDetector → Circles (contour + Hough)
    ├─ ArcDetector → Arcs
    └─ LineDetector → Lines (Hough)
    ↓
[Filtering Stage]
    ├─ BeadsFilter (remove small circles near large ones)
    ├─ CornerFilter (remove circles near polyline corners)
    └─ Deduplicator (remove duplicates)
    ↓
[Processing Stage]
    ├─ PolylineCleaner (orthogonal snapping, segment merging)
    ├─ LineMerger (merge collinear segments)
    └─ SnapExtender (snap interior lines)
    ↓
[CADElements Container]
    ├─ polylines: List[Polyline]
    ├─ circles: List[Circle]
    ├─ arcs: List[Arc]
    ├─ lines: List[Line]
    └─ rectangles: List[Rectangle]
    ↓
[Export]
    ├─ DXFExporter → DXF R2010
    └─ DXFR12Exporter → DXF R12
    ↓
Output File
```

## Design Decisions and Trade-offs

### 1. Modular Architecture
**Decision**: Split monolithic `cad_converter.py` into focused modules

**Rationale**:
- Single Responsibility Principle: Each module has one reason to change
- Testability: Modules can be tested independently
- Reusability: Components can be used in different pipelines
- Maintainability: Easier to locate and fix bugs

**Trade-off**: Slight overhead from module imports, but negligible compared to image processing

### 2. Detector Hierarchy with BaseDetector
**Decision**: All detectors inherit from `BaseDetector` abstract class

**Rationale**:
- Consistent interface across all detectors
- Easy to add new detector types
- Polymorphic usage in pipelines

**Trade-off**: Requires inheritance overhead, but provides clear contracts

### 3. Adaptive Thresholds Based on Size
**Decision**: Circle detection uses size-dependent circularity and radial fit thresholds

**Rationale**:
- Small circles (r < 10px): Relaxed thresholds (0.70 circularity) - more false positives acceptable
- Medium circles (10-15px): Moderate thresholds (0.75 circularity)
- Large circles (r > 15px): Strict thresholds (0.85 circularity) - fewer false positives

**Trade-off**: More complex logic, but significantly better detection accuracy across size ranges

### 4. KD-tree for Corner Filtering
**Decision**: Use spatial indexing for circle-to-polyline distance queries

**Rationale**:
- O(n log k) complexity instead of O(n³) brute force
- Handles large numbers of circles and polylines efficiently
- Scales well with image complexity

**Trade-off**: Additional dependency (scipy), but massive performance gain

### 5. Two-Pass Polyline Extraction
**Decision**: Extract polylines with and without morphological closing, then choose best

**Rationale**:
- Pass A (no morphology): Preserves concave corners (e.g., "Г" shapes)
- Pass B (morphology): Connects small gaps
- Choose extraction with more vertices (preserves detail)

**Trade-off**: Slower (2x processing), but better handles diverse drawing styles

### 6. Contour-First, Hough-Fallback for Circles
**Decision**: Try contour-based detection first, fall back to Hough transform

**Rationale**:
- Contours produce connected geometry suitable for DXF polylines
- Hough handles thick strokes where contours fail
- Combines strengths of both methods

**Trade-off**: More complex logic, but robust across stroke widths

### 7. Separate Exporter Classes
**Decision**: DXFExporter and DXFR12Exporter as separate classes

**Rationale**:
- Different DXF versions have different capabilities
- R2010 supports modern features (LWPOLYLINE, SPLINE)
- R12 uses legacy POLYLINE for compatibility
- Easy to add new export formats

**Trade-off**: Code duplication, but clear separation of concerns

## Performance Considerations

### Optimization Techniques

1. **Image Caching**: Grayscale conversion cached to avoid recomputation
2. **Spatial Indexing**: KD-tree for O(log n) nearest neighbor queries
3. **Early Filtering**: Small contours filtered before expensive operations
4. **Bounding Box Checks**: Quick rejection before detailed distance calculations
5. **Adaptive Parameters**: Thresholds adjusted based on image size and element size

### Complexity Analysis

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Polyline extraction | O(n log n) | Contour finding + approximation |
| Circle detection | O(n²) | Contour analysis + deduplication |
| Corner filtering | O(n log k) | KD-tree queries (n=circles, k=vertices) |
| Line merging | O(m²) | m = number of lines |
| DXF export | O(n) | Linear in number of elements |

### Memory Usage

- Image caching: ~1-2 MB for typical 1000x1000 images
- KD-tree: O(k) where k = total polyline vertices
- Element storage: Minimal (coordinates + metadata)

## Extensibility Points

### Adding New Detectors

1. Create `detectors/new_detector.py`
2. Inherit from `BaseDetector`
3. Implement `detect(image, **kwargs)` method
4. Add to `detectors/__init__.py`
5. Integrate into main pipeline

### Adding New Filters

1. Create `filters/new_filter.py`
2. Implement `filter(elements, **kwargs)` method
3. Add to `filters/__init__.py`
4. Insert into filtering stage

### Adding New Export Formats

1. Create `exporters/new_exporter.py`
2. Implement `export(elements, output_path)` method
3. Add to `exporters/__init__.py`
4. Use in export stage

## Deployment Guide

### System Requirements

- Python 3.8+
- OpenCV (cv2) 4.5+
- NumPy 1.19+
- SciPy 1.5+ (for spatial indexing)
- ezdxf 0.16+ (for DXF export)

### Installation

```bash
# Install dependencies
pip install opencv-python numpy scipy ezdxf

# Or with requirements.txt
pip install -r requirements.txt
```

### Configuration Options

Key parameters in `CADConverter.__init__()`:

```python
# Scale factor (pixels to mm)
scale_factor = 1.0

# Circle detection
circle_dp = 1.2                    # Hough accumulator resolution
circle_min_dist = 30               # Minimum distance between centers
circle_param1 = 50                 # Canny edge threshold
circle_param2 = 20                 # Accumulator threshold
circle_min_radius = 5              # Minimum radius (pixels)
circle_max_radius = 200            # Maximum radius (pixels)

# Line detection
hough_threshold = 50               # Accumulator threshold
hough_min_line_length = 50         # Minimum line length (pixels)
hough_max_line_gap = 10            # Maximum gap between segments

# Polyline extraction
min_contour_area = 20.0            # Minimum contour area (pixels²)
keep_area_ratio_of_max = 0.005     # Keep contours >= this ratio of max
approx_epsilon_ratio = 0.001       # Douglas-Peucker epsilon ratio
close_kernel_size = 3              # Morphological close kernel
close_iterations = 1               # Morphological close iterations
```

### Running in Production

```python
from cad.cad_converter import CADConverter
import cv2

# Initialize converter
converter = CADConverter(scale_factor=1.0)

# Load binary image
image = cv2.imread('drawing.png', cv2.IMREAD_GRAYSCALE)

# Extract elements
elements = converter.extract_elements(image)

# Export to DXF
success = converter.to_dxf(elements, 'output.dxf')

if success:
    print("DXF exported successfully")
else:
    print("Export failed")
```

### Monitoring and Logging

Configure logging to track processing:

```python
import logging
from cad.logging_config import setup_logging

# Setup logging
setup_logging(level=logging.INFO)

# Logs will show:
# - Detection results (circles, arcs, lines, polylines)
# - Filtering statistics (removed beads, corner artifacts)
# - Export status
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No circles detected | Increase `circle_param2`, adjust `circle_min_radius` |
| Too many false circles | Increase `circle_param1`, decrease `circle_param2` |
| Missing polylines | Decrease `min_contour_area`, adjust `approx_epsilon_ratio` |
| Jagged lines | Increase `hough_min_line_length`, adjust `snap_angle_degrees` |
| Slow processing | Reduce image size, increase `min_contour_area` |

## Future Improvements

1. **Multi-scale Detection**: Detect elements at multiple image scales
2. **Adaptive Thresholds**: Automatically adjust parameters based on image complexity
3. **Machine Learning**: Train classifiers for element type detection
4. **Parallel Processing**: Process multiple images concurrently
5. **Additional Formats**: Support SVG, PDF, STEP export
6. **Interactive Refinement**: GUI for manual correction of detections
