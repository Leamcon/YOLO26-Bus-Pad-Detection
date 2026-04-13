# Bus Pad Detection Pipeline

Detects bus pads from aerial orthoimagery using a YOLO26n model. The pipeline chips georeferenced JP2 tiles, runs GPU inference via Google Colab, and produces a georeferenced point shapefile of detections in EPSG:6539.

## Pipeline Overview

| Stage | Script | Environment | Input | Output |
|-------|--------|-------------|-------|--------|
| 1 — Chipping | `buspad-inference-chip` | Local | JP2 tile directory | 640×640 chips, offset CSVs, geotransform JSON, `chips.zip` |
| 2 — Inference | `inference_colab.py` | Google Colab (T4) | `chips.zip` (uploaded) | Per-tile prediction CSVs, `predictions.zip` (downloaded) |
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
├── .project-root                       # Anchor file for output path resolution
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
                ├── chips.zip           # Zipped chips/ for Colab upload
                ├── offsets/            # Per-tile offset CSVs
                ├── geotransforms.json  # Affine coefficients (labeled)
                ├── predictions/        # Per-tile prediction CSVs (from Stage 2)
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
| `--no-zip` | No | `False` | Skip `chips.zip` creation. |

**Output path derivation:**
The input path is parsed for year and boro. `data/nyc_ortho_2022/boro_staten_island_sp22` produces `{project_root}/output/chips/inference_2022/staten_island_2022/`. The project root is located by walking up from the script's location until a `.project-root` marker file is found. If the input path does not match the expected `nyc_ortho_{YYYY}/boro_{name}_sp{YY}` convention, `--output-dir` is required.

**Outputs:**
- `chips/` — 640×640 upscaled chip images, named `{tile_stem}_r{row}_c{col}.{ext}`.
- `chips.zip` — Zipped `chips/` directory for Colab upload. Contains `chips/` as a top-level folder. Omitted if `--no-zip` is set.
- `offsets/` — One CSV per tile (`{tile_stem}_offsets.csv`) mapping each chip filename to its pixel offset (`x_offset`, `y_offset`) within the source tile.
- `geotransforms.json` — Affine transform coefficients per tile, stored with labeled keys (`a`, `b`, `c`, `d`, `e`, `f`).

**Error handling:**
If a tile fails to chip or its offset CSV fails to write (permissions, disk full), the error is logged to stderr and the pipeline continues to the next tile. Partial chip output from failed tiles is not cleaned up — it will be overwritten on re-run.

### Stage 2 — Inference (Google Colab)

1. Upload `chips.zip` from the Stage 1 output directory to the Colab runtime.
2. Upload `inference_colab.py` and your trained `.pt` weights.
3. Unzip chips and install dependencies:

```python
!pip install ultralytics -q
!unzip -q /content/chips.zip -d /content/
```

4. Set `COLAB_MODE = True` in the configuration cell:

```python
COLAB_MODE = True
COLAB_CONFIG = {
    "input_dir": "/content",
    "model_path": "/content/models/best.pt",
    "batch_size": 64,
    "conf": 0.25,
    "output_dir": None,  # Defaults to /content/predictions/
}
```

5. Run all cells. On completion, `predictions.zip` is automatically downloaded via the browser. The zip contains a `predictions/` top-level folder.

Alternatively, run as a CLI script on any machine with a GPU:

```bash
python inference_colab.py /path/to/stage1_output /path/to/model.pt \
    --batch-size 64 \
    --conf 0.25
```

In CLI mode, predictions are written to `input_dir/predictions/` (or `--output-dir`) without zipping.

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
- `predictions.zip` — (Colab mode only) Zipped `predictions/` directory, auto-downloaded via browser.

### Stage 3 — Georeferencing (Local)

Unzip `predictions.zip` into the Stage 1 output directory so that `predictions/` sits alongside `offsets/` and `geotransforms.json`:

```bash
unzip -q predictions.zip -d output/chips/inference_2022/staten_island_2022/
```

Then run georeferencing:

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
# Stage 1: chip tiles (produces chips/, offsets/, geotransforms.json, chips.zip)
buspad-inference-chip data/nyc_ortho_2022/boro_staten_island_sp22 --overlap 20

# Stage 2: upload chips.zip to Colab, run inference, download predictions.zip

# Stage 3: unzip predictions into Stage 1 output, then georeference
unzip -q predictions.zip -d output/chips/inference_2022/staten_island_2022/
buspad-georef output/chips/inference_2022/staten_island_2022
```

Final output: `output/chips/inference_2022/staten_island_2022/detections.shp`

## Technical Notes

- **Output path resolution:** Stage 1 anchors its default output to the project root, found by walking up the directory tree to the nearest `.project-root` marker file. This avoids cwd-dependent output paths. If the marker is missing, the script raises `FileNotFoundError`. Stages 2 and 3 derive output paths from their input arguments and are unaffected.
- **Tile dimensions:** 5000×5000 px. Chip size is 200×200 px. With 0% overlap this yields 25×25 = 625 chips per tile. With 20% overlap (stride 160), 31×31 = 961 chips per tile.
- **4th band:** JP2 tiles are 4-band. The 4th band is dropped; only RGB (bands 1–3) is chipped. Band identity is unknown (likely mask or alpha).
- **Affine storage:** Coefficients are stored with explicit labels (`a`–`f`) in JSON to avoid GDAL/Affine ordering ambiguity. Stage 3 reconstructs the `Affine` object directly.
- **Duplicate detections:** Overlapping chips will produce duplicate detections for the same bus pad. No deduplication is applied in this pipeline. Post-process in GIS (e.g., spatial clustering or distance-based merging) as needed.
- **Scale:** Designed for ~300 tiles per collection. Stage 1 processes tiles sequentially. At 961 chips/tile, expect ~288,000 chips per run.
- **Error handling (Stage 1):** Individual tile failures (disk full, permissions) are logged and skipped. The rest of the run completes. Partial output from failed tiles is not cleaned up and will be overwritten on re-run.
- **Colab transfer:** Chip images are transferred to Colab via `chips.zip` (manual upload). Predictions are returned via `predictions.zip` (auto-downloaded). Both zips preserve their containing directory (`chips/`, `predictions/`) so unzipping places files in the expected locations without path adjustment.