# inference_colab

Runs batched YOLO26n inference on chipped imagery and outputs per-tile prediction CSVs.

## Pipeline Context

This notebook handles Stage 2 of a three-stage detection pipeline:

| Stage | Component | Environment | Description |
|-------|-----------|-------------|-------------|
| 1 — Chipping | `buspad-inference-chip` | Local | Chip, upscale, and export offset/geotransform metadata |
| **2 — Inference** | **`inference_colab.py`** | **Google Colab (T4)** | **Batched YOLO26n inference on chips** |
| 3 — Georeferencing | `buspad-georef` | Local | Map predictions to EPSG:6539 shapefile |

## Dependencies

```
ultralytics
```

Install in Colab with `!pip install ultralytics -q`.

## Inputs

This stage consumes the output of Stage 1 (`buspad-inference-chip`). The expected directory structure:

```
inference_2022/staten_island_2022/
├── chips/              # 640×640 chip images (required)
│   ├── tile_001_r000_c000.jpg
│   └── ...
├── offsets/            # Not used by this stage
└── geotransforms.json  # Not used by this stage
```

Only `chips/` is read. Chip filenames must follow the `{tile_stem}_r{row}_c{col}.{ext}` convention — the tile stem is extracted from filenames to group chips by source tile.

## Usage

### Colab

1. Upload the Stage 1 output directory to Google Drive (or directly to the Colab runtime).
2. Upload `inference_colab.py` and your trained `.pt` weights.
3. Edit the config block at the top of the script:

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

### CLI (any machine with GPU)

```bash
python inference_colab.py /path/to/stage1_output /path/to/model.pt \
    --batch-size 64 \
    --conf 0.25
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_dir` | Yes | — | Stage 1 output directory (must contain `chips/`). |
| `model_path` | Yes | — | Path to trained YOLO26n `.pt` weights. |
| `--batch-size` | No | `64` | Inference batch size. T4 can typically handle 128+. |
| `--conf` | No | `0.25` | Confidence threshold for detections. |
| `--output-dir` | No | `input_dir/predictions/` | Output directory for prediction CSVs. |

## Outputs

```
inference_2022/staten_island_2022/
└── predictions/
    ├── tile_001_predictions.csv
    ├── tile_002_predictions.csv
    └── ...
```

One CSV per tile. Each row represents a single detection:

```
chip_filename,x1,y1,x2,y2,confidence,class_id
tile_001_r012_c015.jpg,142.50,298.00,410.75,512.30,0.8723,0
```

Bounding box coordinates (`x1`, `y1`, `x2`, `y2`) are in 640×640 pixel space. Tiles with no detections produce no CSV.

## Technical Notes

- Inference is batched explicitly rather than relying on Ultralytics' internal batching, for predictable memory control.
- Batch size 64 is conservative for a T4 (16 GB VRAM). 640×640 RGB chips through YOLO26n should allow 128+ comfortably.
- Chip-to-tile grouping is reconstructed from filenames at runtime. The Stage 1 offset CSVs are not needed and do not need to be uploaded.
- The annotated/visualized chip images from YOLO are not used. Only the structured prediction data (bbox coordinates, confidence, class) is extracted.

## Downstream

Download the `predictions/` directory and place it inside the Stage 1 output directory. Stage 3 (`buspad-georef`) reads from `predictions/`, `offsets/`, and `geotransforms.json` to produce the final georeferenced shapefile.