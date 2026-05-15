# buspad

Detect bus pads from NYC ortho-rectified aerial imagery using YOLO26 object detection toolkit.

## Overview

`buspad` is a pip-installable Python package that runs a five-stage inference pipeline over tiled orthoimagery of New York City. Raw aerial tiles are selected by borough or cd level scope, chipped into fixed-size windows, passed through a trained YOLO26 model, and georeferenced back to map coordinates — producing a spatial feature class (Shapefile or GeoPackage) of detected bus pads.

The pipeline is built around [Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26). Nano and small model weights trained on NYC orthoimagery ship with the package. Each of the five commands exposes detailed usage information via `--help`.

## Requirements

- Python ≥ 3.11
- macOS, Linux, or Windows 11 (WSL)
- GPU optional: CUDA or MPS for accelerated inference; CPU fallback is automatic

Optional extras for non-PyTorch model formats:

```
pip install buspad[onnx]       # ONNX Runtime *WIP*
pip install buspad[coreml]     # Core ML (macOS)
pip install buspad[openvino]   # OpenVINO *WIP*
```

## Installation

Download the wheel from the latest GitHub Release and install with pip:

```
pip install https://github.com/Leamcon/YOLO26-Bus-Pad-Detection/releases/download/v1.0.0/buspad-1.0.0-py3-none-any.whl
```

## Data

The models were trained on NYC orthoimagery available from the New York State GIS Clearinghouse:

https://gis.ny.gov/new-york-city-orthoimagery-downloads

Download the tiled imagery for the boroughs you need. After initializing a workspace (see below), place the tile directories under `data/imagery/nyc_ortho_{YYYY}/` following the source's naming convention (`boro_{name}_sp{YY}`). For example:

```
data/imagery/nyc_ortho_2024/
├── boro_bronx_sp24/
├── boro_brooklyn_sp24/
├── boro_manhattan_sp24/
├── boro_queens_sp24/
└── boro_staten_island_sp24/
```

Everything else in the workspace — boundaries, model weights, output directories — is managed by the pipeline.

## Pipeline

The five commands run in sequence. Each reads the output of the previous stage.

```
raw tiles ─→ selected tiles ─→ chips ─→ predictions ─→ georeferenced features
  init        cd_select          chip      infer          georef
```

### 1. Initialize the workspace

```
buspad-init /path/to/workspace
```

Scaffolds the directory structure, copies bundled model weights and community district boundary shapefiles into the workspace, and writes a config file (`~/.buspad/config.toml`) so subsequent commands can locate the workspace automatically.

### 2. Select tiles by community district

```
buspad-cd-select --year 2024 --cd 108
```

Identifies which tiles intersect the specified community district and copies them into `data/imagery/cd/<YEAR>/<CD>/`. Skip this step if you intend to run inference on an entire borough.

### 3. Chip tiles

```
buspad-chip --year 2024 --boro bronx
```

Slices each tile into 200×200 pixel chips (upscaled to 640×640 for inference) and writes chip images, per-tile offset CSVs, and a geotransform reference file into `data/chips/`. Accepts `--boro` or `--cd` to match the scope of the previous step.

### 4. Run inference

```
buspad-infer nano --year 2024 --boro bronx
```

Runs YOLO26 detection on the chipped imagery. The positional argument selects the model size (`nano` or `small`). Use `--format` to specify a non-default model format (`onnx`, `coreml`, `openvino`). Per-tile prediction CSVs are written to `output/detections/`.

### 5. Georeference detections

```
buspad-georef --year 2024 --boro bronx
```

Maps each detection from chip pixel coordinates back to EPSG:6539 map coordinates using the chip offsets and tile geotransforms produced by the chipping step. Writes a georeferenced Shapefile by default; use `--format gpkg` for GeoPackage output.

## Model export

The package ships PyTorch (`.pt`) weights for the nano and small models. To run inference with ONNX, Core ML, or OpenVINO, export the weights using the Ultralytics export API and place the exported files in the corresponding `models/{size}/` directory in your workspace. See the [Ultralytics export documentation](https://docs.ultralytics.com/modes/export) for instructions.

## License

See [LICENSE](LICENSE).