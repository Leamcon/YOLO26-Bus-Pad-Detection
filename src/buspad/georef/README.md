# buspad_georef

**Stage 3** of the `dot_buspads_ml` pipeline.  Converts YOLO detection
bounding-box predictions from chip-pixel space back to EPSG:6539 (NAD83)
map coordinates and writes the results as a spatial feature class.

## Prerequisites

Upstream stages must have already produced:

| Artifact | Source | Description |
|---|---|---|
| `offsets/*.csv` | Stage 1 | Per-tile CSVs mapping each chip filename to its (x, y) pixel offset within the parent tile. |
| `geotransforms.json` | Stage 1 | Affine transform coefficients keyed by original tile filename. |
| `predictions/*.csv` | Stage 2 | Per-tile YOLO prediction CSVs with columns: `chip_filename`, `x1`, `y1`, `x2`, `y2`, `confidence`, `class_id`. |

## Usage

From `dot_buspads_ml/src/`:

```bash
# Defaults: reads predictions from stage1_dir/predictions/,
#           writes shapefile to stage1_dir/detections/
python -m buspad_georef /path/to/stage1_output

# Explicit predictions directory and GeoPackage output
python -m buspad_georef /path/to/stage1_output /path/to/preds \
     --output /path/to/output_dir --format gpkg
```

## Coordinate Pipeline

```
640x640 YOLO space
   -> scale by (CHIP_SIZE / UPSCALE_SIZE) -> 200x200 chip space
     -> translate by chip offset           -> tile pixel space
       -> affine transform                 -> EPSG:6539 map space
```

## Package Structure

```
buspad_georef/
├── __init__.py      Public API surface
├── __main__.py      python -m entry point
├── cli.py           Argument parsing, orchestration
├── defs.py          Constants and data structures
├── loaders.py       File I/O (geotransforms, offsets)
├── processing.py    Coordinate math, prediction iteration
└── writers.py       Shapefile / GeoPackage output
```

## Output Formats

| Flag | Format | Notes |
|---|---|---|
| `--format shp` | ESRI Shapefile (default) | Bundled in a containing directory. Field names truncated to 10 chars. |
| `--format gpkg` | GeoPackage | Single file, no field name limits. |