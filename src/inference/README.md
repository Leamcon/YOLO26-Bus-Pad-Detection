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
├── formats.py      Format detection, device compat, runtime checks
├── device.py       Device resolution & validation
├── chips.py        Chip file discovery & tile grouping
├── predict.py      YOLO model loading & batched inference
└── io.py           Prediction output writers
```

## Dependencies

Requires Python ≥ 3.10. Core dependencies:

- `ultralytics` 8.4.x (YOLO26)
- `torch`

Per-format runtime dependencies (install only what you need):

| Format   | Package         |
|----------|-----------------|
| CoreML   | `coremltools`   |
| ONNX     | `onnxruntime`   |
| OpenVINO | `openvino`      |

Native `.pt` weights require only `torch` (already a core dependency).

## Usage

Run from the project `src/` directory:

```bash
cd dot_buspads_ml/src
python -m inference path/to/best.onnx path/to/chips
```

Model format is auto-detected from the path. Device compatibility is
validated against the detected format and auto-selected if not specified.

**Supported model formats**

| Format   | Extensions / layout              | Valid devices     |
|----------|----------------------------------|-------------------|
| PyTorch  | `.pt`                            | cpu, cuda, mps    |
| ONNX     | `.onnx`                          | cpu, cuda         |
| CoreML   | `.mlpackage` dir, `.mlmodel`     | cpu, mps          |
| OpenVINO | `.xml` file, or dir with `.xml` + `.bin` | cpu       |

**Arguments**

| Argument     | Description                              |
|--------------|------------------------------------------|
| `model_path` | Path to model file or directory.         |
| `chips_dir`  | Path to directory containing chip images.|

**Options**

| Option         | Default             | Description                        |
|----------------|---------------------|------------------------------------|
| `--device`     | auto per format     | `mps` \| `cuda` \| `cpu`          |
| `--batch-size` | `64`                | Inference batch size.              |
| `--conf`       | `0.25`              | Confidence threshold.              |

**Examples**

```bash
# ONNX on CPU (auto-detected)
python -m inference models/best.onnx data/tile_01/chips

# CoreML on MPS
python -m inference models/best.mlpackage data/tile_01/chips --device mps

# OpenVINO (CPU only)
python -m inference models/best_openvino_model data/tile_01/chips

# Native .pt on CUDA
python -m inference models/best.pt data/tile_01/chips --device cuda
```

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