# Bus Pad Detection Pipeline

Detects bus pads from aerial orthoimagery using a YOLO26n model. The pipeline chips georeferenced JP2 tiles, runs GPU inference, and produces a georeferenced point shapefile of detections in EPSG:6539.

## Pipeline Overview

| Stage | Script | Environment | Input | Output |
|-------|--------|-------------|-------|--------|
| 1 — Chipping | `buspad-inference-chip` | Local | JP2 tile directory | 640×640 chips, offset CSVs, geotransform JSON |
| 2 — Inference | `inference_colab.py` | Google Colab (T4) | Chip directory | Per-tile prediction CSVs |
| 3 — Georeferencing | `buspad-georef` | Local | Stage 1 + Stage 2 outputs | Point shapefile (EPSG:6539) |

## Requirements

### Local (Stages 1 & 3)

```
python >= 3.10
rasterio
numpy
Pillow
geopandas
shapely
affine
```

### Colab (Stage 2)

```
ultralytics
```

Install in Colab with `!pip install ultralytics -q`.

## Directory Structure

```
project/
├── src/
│   ├── buspad/                         # Core bus pad utilities (separate package)
│   ├── buspad_inference_chipper/       # Stage 1 — chipping
│   │   ├── chip_tiles.py
│   │   └── pyproject.toml
│   ├── buspad_georef/                  # Stage 3 — georeferencing
│   │   ├── georeference.py
│   │   └── pyproject.toml
│   ├── ortho_extract/                  # Orthoimagery extraction (separate package)
│   ├── tile_selector/                  # Tile selection (separate package)
│   └── __init__.py
├── notebooks/
│   └── inference_colab.py              # Stage 2 — upload to Colab
├── data/
│   └── nyc_ortho_2022/
│       └── boro_staten_island_sp22/
│           ├── tile_001.jp2
│           ├── tile_002.jp2
│           └── ...
└── output/
    └── chips/
        └── inference_2022/
            └── staten_island_2022/
                ├── chips/              # 640×640 chip images
                ├── offsets/            # Per-tile offset CSVs
                ├── geotransforms.json  # Affine coefficients (labeled)
                ├── predictions/        # Per-tile prediction CSVs (Stage 2)
                └── detections.shp      # Final output (Stage 3)
```

## Usage

### Stage 1 — Chipping (Local)

```bash
buspad-inference-chip data/nyc_ortho_2022/boro_staten_island_sp22 \
    --overlap 20 \
    --format jpg
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_dir` | Yes | — | Path to directory containing `.jp2` tiles. |
| `--overlap` | No | `20` | Overlap percentage. Must yield a stride that divides 4800 evenly. Valid examples: 0, 20, 25, 50. |
| `--format` | No | `jpg` | Output image format (`jpg` or `png`). |
| `--output-dir` | No | Derived | Override the auto-derived output path. |

**Output path derivation:**
The input path is parsed for year and boro. `data/nyc_ortho_2022/boro_staten_island_sp22` produces `output/chips/inference_2022/staten_island_2022/`. If the path does not match the expected `nyc_ortho_{YYYY}/boro_{name}_sp{YY}` convention, `--output-dir` is required.

**Outputs:**
- `chips/` — 640×640 upscaled chip images, named `{tile_stem}_r{row}_c{col}.{ext}`.
- `offsets/` — One CSV per tile (`{tile_stem}_offsets.csv`) mapping each chip filename to its pixel offset (`x_offset`, `y_offset`) within the source tile.
- `geotransforms.json` — Affine transform coefficients per tile, stored with labeled keys (`a`, `b`, `c`, `d`, `e`, `f`).

### Stage 2 — Inference (Google Colab)

1. Upload the Stage 1 output directory to Google Drive (or directly to the Colab runtime).
2. Upload `inference_colab.py` and your trained `.pt` weights.
3. Edit the `COLAB_CONFIG` block at the top of the script:

```python
COLAB_MODE = True
COLAB_CONFIG = {
    "input_dir": "/content/drive/MyDrive/chips/inference_2022/staten_island_2022",
    "model_path": "/content/drive/MyDrive/models/yolo26n_buspad.pt",
    "batch_size": 64,
    "conf": 0.25,
    "output_dir": None,  # Defaults to input_dir/predictions/
}
```

4. Run all cells.

Alternatively, run as a CLI script on any machine with a GPU:

```bash
python inference_colab.py /path/to/stage1_output /path/to/model.pt \
    --batch-size 64 \
    --conf 0.25
```

**Arguments (CLI mode):**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_dir` | Yes | — | Stage 1 output directory (must contain `chips/`). |
| `model_path` | Yes | — | Path to trained YOLO26n `.pt` weights. |
| `--batch-size` | No | `64` | Inference batch size. T4 can typically handle 128+. |
| `--conf` | No | `0.25` | Confidence threshold for detections. |
| `--output-dir` | No | `input_dir/predictions/` | Output directory for prediction CSVs. |

**Outputs:**
- `predictions/` — One CSV per tile (`{tile_stem}_predictions.csv`). Each row: `chip_filename`, `x1`, `y1`, `x2`, `y2` (in 640×640 space), `confidence`, `class_id`. Tiles with no detections produce no CSV.

### Stage 3 — Georeferencing (Local)

```bash
buspad-georef output/chips/inference_2022/staten_island_2022
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `stage1_dir` | Yes | — | Stage 1 output directory (must contain `offsets/` and `geotransforms.json`). |
| `predictions_dir` | No | `stage1_dir/predictions/` | Directory of Stage 2 prediction CSVs. |
| `--output` | No | `stage1_dir/detections.shp` | Output shapefile path. |

**Coordinate transform chain:**

```
Detection centroid (640×640 space)
  → Scale by 200/640 → centroid in chip space
  → Add chip pixel offset → tile pixel coordinates
  → Apply Affine transform → EPSG:6539 map coordinates
```

**Outputs:**
- `detections.shp` — Point shapefile in EPSG:6539 with attributes: `confidence`, `class_id`, `source_tile`.

## End-to-End Example

```bash
# Stage 1: chip tiles
buspad-inference-chip data/nyc_ortho_2022/boro_staten_island_sp22 --overlap 20

# Stage 2: upload to Colab, run inference, download predictions/ directory
# Place predictions/ inside the Stage 1 output directory.

# Stage 3: georeference
buspad-georef output/chips/inference_2022/staten_island_2022
```

Final output: `output/chips/inference_2022/staten_island_2022/detections.shp`

## Technical Notes

- **Tile dimensions:** 5000×5000 px. Chip size is 200×200 px. With 0% overlap this yields 25×25 = 625 chips per tile. With 20% overlap (stride 160), 31×31 = 961 chips per tile.
- **4th band:** JP2 tiles are 4-band. The 4th band is dropped; only RGB (bands 1–3) is chipped. Band identity is unknown (likely mask or alpha).
- **Affine storage:** Coefficients are stored with explicit labels (`a`–`f`) in JSON to avoid GDAL/Affine ordering ambiguity. Stage 3 reconstructs the `Affine` object directly.
- **Duplicate detections:** Overlapping chips will produce duplicate detections for the same bus pad. No deduplication is applied in this pipeline. Post-process in GIS (e.g., spatial clustering or distance-based merging) as needed.
- **Scale:** Designed for ~300 tiles per collection. Stage 1 processes tiles sequentially. At 961 chips/tile, expect ~288,000 chips per run.