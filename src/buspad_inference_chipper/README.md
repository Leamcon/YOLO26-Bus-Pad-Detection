# buspad-inference-chipper

Chips georeferenced JP2 tiles into 640×640 images for YOLO26 bus pad detection inference.

## Pipeline Context

This package handles Stage 1 of a three-stage detection pipeline:

| Stage | Component | Environment | Description |
|-------|-----------|-------------|-------------|
| **1 — Chipping** | **`buspad-inference-chip`** | **Local** | **Chip, upscale, and export offset/geotransform metadata** |
| 2 — Inference | `inference_colab.py` | Google Colab (T4) | Batched YOLO26n inference on chips |
| 3 — Georeferencing | `buspad-georef` | Local | Map predictions to EPSG:6539 shapefile |

## Dependencies

```
python >= 3.10
rasterio >= 1.3
numpy >= 1.24
Pillow >= 10.0
```

## Installation

```bash
pip install -e src/buspad_inference_chipper
```

## Usage

```bash
# Via installed console script
buspad-inference-chip data/nyc_ortho_2022/boro_staten_island_sp22 \
    --overlap 20 \
    --format jpg

# Via python -m
python -m buspad_inference_chipper data/nyc_ortho_2022/boro_staten_island_sp22 \
    --overlap 20 \
    --format jpg
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_dir` | Yes | — | Path to directory containing `.jp2` tiles. |
| `--overlap` | No | `20` | Overlap percentage. Must yield a stride that divides 4800 evenly. Valid examples: 0, 20, 25, 50. |
| `--format` | No | `jpg` | Output image format (`jpg` or `png`). |
| `--output-dir` | No | Derived | Override the auto-derived output path. |

### Output Path Derivation

The input path is parsed for year and boro from the expected convention `nyc_ortho_{YYYY}/boro_{name}_sp{YY}`. For example, `data/nyc_ortho_2022/boro_staten_island_sp22` produces:

```
output/chips/inference_2022/staten_island_2022/
```

If the path does not match the convention, `--output-dir` is required.

### Overlap and Stride

Tiles are 5000×5000 px. Chips are 200×200 px. The stride must divide 4800 (5000 − 200) evenly.

| Overlap | Stride | Chips/axis | Chips/tile |
|---------|--------|------------|------------|
| 0% | 200 | 25 | 625 |
| 20% | 160 | 31 | 961 |
| 25% | 150 | 33 | 1,089 |
| 50% | 100 | 49 | 2,401 |

## Outputs

```
output/chips/inference_2022/staten_island_2022/
├── chips/              # 640×640 upscaled chip images
│   ├── tile_001_r000_c000.jpg
│   ├── tile_001_r000_c001.jpg
│   └── ...
├── offsets/            # Per-tile offset CSVs
│   ├── tile_001_offsets.csv
│   └── ...
└── geotransforms.json  # Affine coefficients per tile (labeled a–f)
```

**chips/** — 200×200 patches upscaled to 640×640 via Lanczos resampling. Named `{tile_stem}_r{row}_c{col}.{ext}`.

**offsets/** — One CSV per tile mapping each chip filename to its pixel offset within the source tile:

```
chip_filename,x_offset,y_offset
tile_001_r000_c000.jpg,0,0
tile_001_r000_c001.jpg,160,0
```

**geotransforms.json** — Affine transform coefficients per tile, stored with explicit labels to avoid GDAL/Affine ordering ambiguity:

```json
{
  "tile_001.jp2": {
    "transform": {"a": 0.5, "b": 0.0, "c": 980000.0, "d": 0.0, "e": -0.5, "f": 200000.0},
    "crs": "EPSG:6539"
  }
}
```

## Technical Notes

- JP2 tiles are 4-band. The 4th band is dropped; only RGB (bands 1–3) is chipped.
- Each tile is read fully into memory (~75 MB for 5000×5000×3). Tiles are processed sequentially.
- Existing output files are overwritten silently on re-run.

## Downstream

Upload the entire output directory to Google Drive for Stage 2 inference. Stage 2 reads from `chips/` and writes predictions to `predictions/` within the same directory structure.