# dot-buspads-inference

Stage 2 of the bus pad detection pipeline: batched YOLO inference on
chipped aerial orthoimagery.

This package is part of the
[dot-buspads-ml](../) project, which covers data acquisition, model
fine-tuning, inference, and prediction post-processing.

## Package structure

```
inference/
├── pyproject.toml
├── README.md
├── __main__.py     Entry point
├── cli.py          Argument parsing & input validation
├── chips.py        Chip file discovery & tile grouping
├── device.py       Inference device detection
├── predict.py      YOLO model loading & batched inference
└── io.py           Prediction output writers
```

## Dependencies

Requires Python ≥ 3.10. Core dependencies are declared in
`pyproject.toml`:

- `ultralytics` 8.4.x (YOLO26)
- `torch`

## Usage

Run from the project `src/` directory:

```bash
cd dot_buspads_ml/src
python -m inference path/to/best.pt path/to/chips --device mps
```

The `chips_dir` argument must point to a directory named `chips/`.
Predictions are written to a sibling `predictions/` directory so that
downstream stages can locate geotransform and offset sidecar data in the
shared parent.

**Arguments**

| Argument     | Description                              |
|--------------|------------------------------------------|
| `model_path` | Path to trained YOLO `.pt` weights.      |
| `chips_dir`  | Path to directory containing chip images.|

**Options**

| Option         | Default      | Description                        |
|----------------|--------------|------------------------------------|
| `--device`     | auto-detect  | `mps` \| `cuda` \| `cpu`          |
| `--batch-size` | `64`         | Inference batch size.              |
| `--conf`       | `0.25`       | Confidence threshold.              |

## Expected directory layout

Inference expects the following layout produced by Stage 1 (chipping):

```
tile_output_dir/
├── chips/
│   ├── {tile_stem}_r0_c0.jpg
│   ├── {tile_stem}_r0_c1.jpg
│   └── ...
├── <geotransform / offset sidecar files>
└── predictions/              ← created by this stage
    └── {tile_stem}_predictions.csv
```

Each prediction CSV contains one row per detection:

```
chip_filename, x1, y1, x2, y2, confidence, class_id
```

Bounding box coordinates are in chip pixel space. Stage 3 uses the
sidecar data in the parent directory to georeference detections back to
the source CRS.

## License

Apache-2.0. See the project-level [LICENSE](../LICENSE) file.