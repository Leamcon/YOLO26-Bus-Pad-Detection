# model-export

CLI tool for exporting fine-tuned YOLO26 models to deployment formats.

## Supported Formats

| Format   | Output Artifact                | Notes                        |
|----------|--------------------------------|------------------------------|
| ONNX     | `<stem>.onnx`                  | Single file                  |
| CoreML   | `<stem>.mlpackage/`            | Directory; macOS only        |
| OpenVINO | `<stem>_openvino_model/`       | Directory (`.xml`, `.bin`)   |

## Installation

From the project root:

```bash
pip install -e src/model_export/
```

This places `model_export` on `sys.path`, allowing invocation from any working directory.

## Usage

```bash
python -m model_export <path/to/weights.pt> -f <format>
```

### Examples

```bash
# Export to ONNX
python -m model_export dot_buspads_ml/models/ls01_v1/weights/best.pt -f onnx
# -> dot_buspads_ml/models/ls01_v1/onnx/best.onnx

# Export to CoreML (macOS only)
python -m model_export dot_buspads_ml/models/ls01_v1/weights/best.pt -f coreml
# -> dot_buspads_ml/models/ls01_v1/coreml/best.mlpackage

# Export to OpenVINO
python -m model_export dot_buspads_ml/models/ls01_v1/weights/best.pt -f openvino
# -> dot_buspads_ml/models/ls01_v1/openvino/best_openvino_model/
```

## Output Location

Exported artifacts are placed in a format-named subdirectory alongside the `weights/` directory within the model generation folder:

```
models/ls01_v1/
├── weights/
│   └── best.pt
├── onnx/
│   └── best.onnx
└── openvino/
    └── best_openvino_model/
```

## Export Configuration

All exports are run with `nms=False` and `half=False`. These defaults suit YOLO26 models and ensure compatibility across deployment targets.

## Platform Requirements

CoreML export requires macOS (`coremltools` dependency). The command will exit with an error if invoked with `-f coreml` on a non-macOS system. ONNX and OpenVINO exports are cross-platform.