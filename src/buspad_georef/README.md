# buspad-georef

Georeferences YOLO bus pad detections from chip-pixel space to EPSG:6539 map coordinates and writes a point shapefile.

## Pipeline Context

This package handles Stage 3 of a three-stage detection pipeline:

| Stage | Component | Environment | Description |
|-------|-----------|-------------|-------------|
| 1 — Chipping | `buspad-inference-chip` | Local | Chip, upscale, and export offset/geotransform metadata |
| 2 — Inference | `inference_colab.py` | Google Colab (T4) | Batched YOLO26n inference on chips |
| **3 — Georeferencing** | **`buspad-georef`** | **Local** | **Map predictions to EPSG:6539 shapefile** |

## Dependencies

```
python >= 3.10
geopandas >= 0.14
shapely >= 2.0
affine >= 2.4
```

## Installation

```bash
pip install -e src/buspad_georef
```

## Inputs

This stage consumes outputs from both Stage 1 and Stage 2. The expected directory structure:

```
inference_2022/staten_island_2022/
├── chips/              # Not used by this stage
├── offsets/            # From Stage 1 (required)
│   ├── tile_001_offsets.csv
│   └── ...
├── geotransforms.json  # From Stage 1 (required)
└── predictions/        # From Stage 2 (required)
    ├── tile_001_predictions.csv
    └── ...
```

## Usage

```bash
# Via installed console script
buspad-georef output/chips/inference_2022/staten_island_2022

# Via python -m
python -m buspad_georef output/chips/inference_2022/staten_island_2022
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `stage1_dir` | Yes | — | Stage 1 output directory (must contain `offsets/` and `geotransforms.json`). |
| `predictions_dir` | No | `stage1_dir/predictions/` | Directory of Stage 2 prediction CSVs. |
| `--output` | No | `stage1_dir/detections.shp` | Output shapefile path. |

## Coordinate Transform Chain

Each detection undergoes four steps to go from model output to map coordinates:

```
1. Bbox centroid in 640×640 space
   cx = (x1 + x2) / 2,  cy = (y1 + y2) / 2

2. Scale to 200×200 chip space
   cx_chip = cx × (200/640),  cy_chip = cy × (200/640)

3. Tile pixel coordinates
   tile_col = x_offset + cx_chip,  tile_row = y_offset + cy_chip

4. Affine transform → EPSG:6539
   map_x, map_y = transform * (tile_col, tile_row)
```

The Affine object is reconstructed from labeled coefficients (`a`–`f`) stored in `geotransforms.json`, using `Affine(a, b, c, d, e, f)` and the `transform * (col, row)` interface directly. This avoids GDAL/Affine coefficient ordering ambiguity.

## Output

```
inference_2022/staten_island_2022/
└── detections.shp      # + .shx, .dbf, .prj sidecars
```

Point shapefile in EPSG:6539 with one feature per detection. Attributes:

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | float | Model confidence score |
| `class_id` | int | Predicted class ID |
| `source_tile` | str | Original JP2 tile filename |

## Technical Notes

- Tiles with no prediction CSV (zero detections in Stage 2) are silently skipped.
- Chips referenced in predictions but missing from the offset CSV trigger a warning and are skipped.
- Duplicate detections from overlapping chips are not deduplicated. The same bus pad detected in adjacent chips will produce multiple points. Post-process in GIS (spatial clustering or distance-based merging) as needed.
- The `affine` package is a transitive dependency of `rasterio` but is listed explicitly here since `rasterio` is not a direct dependency of this package.

## Upstream

Ensure the Stage 2 `predictions/` directory has been downloaded from Colab and placed inside the Stage 1 output directory before running this stage.