# Initial Image Extraction

Extracts high-resolution raster subsets from the NYC orthoimagery tile collection by community district boundary. Outputs spatially referenced GeoTIFFs at full native resolution for downstream machine vision processing.

## Pipeline Summary

1. User specifies one or more `boro_cd` values via CLI.
2. Boundary features are loaded, filtered, and reprojected from WGS84 (EPSG:4326) to the raster-native CRS (EPSG:6539).
3. The mosaic shapefile for the corresponding borough directory is loaded and reprojected from EPSG:2263 to EPSG:6539.
4. A spatial join identifies tiles intersecting each boundary feature.
5. Intersecting tiles are stitched into a GDAL VRT (no resampling).
6. The VRT is clipped to the boundary polygon and written as a 4-band RGBA GeoTIFF. The alpha channel masks exterior pixels.
7. Optionally, a 3-band RGB JP2 without spatial reference is exported for YOLO ingestion.

## Module Structure

| File | Purpose |
|---|---|
| `config.py` | CRS constants, borough directory mapping, default paths, output settings |
| `extract.py` | CLI argument parsing and main orchestration loop |
| `tile_selection.py` | Boundary loading, mosaic index loading, spatial join for tile identification |
| `mosaic_clip.py` | VRT construction and boundary clipping to GeoTIFF |
| `export.py` | Optional 3-band JP2 export for YOLO ingestion |

## Usage

All commands run from the project root.

Extract specific community districts:

```bash
python -m scripts.ortho_extract.extract --boro_cd 104 108 207 226 303 313 317 403
```

Extract with YOLO export:

```bash
python -m scripts.ortho_extract.extract --boro_cd 401 --yolo
```

Override default paths:

```bash
python -m scripts.ortho_extract.extract --boro_cd 101 \
    --data_dir /path/to/tiles \
    --boundary_shp /path/to/boundary.shp \
    --output_dir /path/to/output
```

## Expected Input Data

Each borough directory must contain JP2 tiles and a mosaic shapefile:

```
data/nyc_ortho_2024/boro_queens_sp24/
├── 050205.jp2
├── 050205.jpw
├── 050205.jp2.aux.xml
├── ...
└── mosaic_index.shp  (with 'Image' field containing tile IDs, e.g. '050205')
```

The boundary shapefile must contain a `boro_cd` field (double) with community district codes.

## Output

```
output/ortho_extracts/
├── ortho_104.tif          # 4-band RGBA GeoTIFF, EPSG:6539
├── ortho_108.tif
├── vrt_temp/              # Intermediate VRT files (lightweight, can be deleted)
│   ├── mosaic_104.vrt
│   └── mosaic_108.vrt
└── yolo/                  # Only if --yolo flag is used
    ├── ortho_104.jp2      # 3-band RGB, no spatial reference
    └── ortho_108.jp2
```

## Design Decisions

- **VRT over in-memory merge.** Boundary features span 3+ tiles at 5000x5000 pixels. VRT avoids holding the full mosaic in RAM.
- **No resampling.** Vector data is reprojected; raster pixels are never transformed. All tiles and outputs remain in EPSG:6539.
- **Alpha-based masking.** The source tiles carry a native alpha channel (band 4). Exterior pixels are set to 0 across all bands including alpha. No synthetic nodata values.
- **EPSG:6539 throughout.** The mosaic index (EPSG:2263) and boundary vector (EPSG:4326) are reprojected to match the raster-native CRS. The datum difference between 2263 and 6539 is sub-pixel in the NYC area; reprojecting rasters to reconcile this would introduce resampling.