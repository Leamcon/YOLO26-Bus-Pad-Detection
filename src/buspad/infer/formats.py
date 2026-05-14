"""Model format detection, device compatibility, and runtime validation."""

import sys
from enum import Enum
from pathlib import Path


class ModelFormat(Enum):
    PT = "pt"
    ONNX = "onnx"
    COREML = "coreml"
    OPENVINO = "openvino"


# Maps each format to its set of valid device strings.
FORMAT_DEVICES: dict[ModelFormat, set[str]] = {
    ModelFormat.PT: {"cpu", "cuda", "mps"},
    ModelFormat.ONNX: {"cpu", "cuda"},
    ModelFormat.COREML: {"cpu", "mps"},
    ModelFormat.OPENVINO: {"cpu"},
}

# Maps each format to the package import name needed at runtime.
FORMAT_RUNTIME: dict[ModelFormat, str] = {
    ModelFormat.PT: "torch",
    ModelFormat.ONNX: "onnxruntime",
    ModelFormat.COREML: "coremltools",
    ModelFormat.OPENVINO: "openvino",
}

# Maximum batch size per format.  Ultralytics' non-PyTorch backends
# do not reliably handle multi-image batches.
FORMAT_MAX_BATCH: dict[ModelFormat, int | None] = {
    ModelFormat.PT: None,
    ModelFormat.ONNX: 1,
    ModelFormat.COREML: 1,
    ModelFormat.OPENVINO: 1,
}


def clamp_batch_size(requested: int, fmt: ModelFormat) -> int:
    """Return the effective batch size, clamped to the format's maximum.

    Prints a warning if the requested size is reduced.
    """
    cap = FORMAT_MAX_BATCH[fmt]
    if cap is not None and requested > cap:
        print(
            f"WARNING: batch size {requested} not supported for "
            f"'{fmt.value}' backend, clamping to {cap}.",
            file=sys.stderr,
        )
        return cap
    return requested


def is_valid_model_path(model_path: Path) -> bool:
    """Check whether the path exists and matches a known format."""
    if model_path.is_file():
        return model_path.suffix.lower() in {
            ".pt", ".onnx", ".mlmodel", ".xml",
        }
    if model_path.is_dir():
        if model_path.suffix.lower() == ".mlpackage":
            return True
        xmls = list(model_path.glob("*.xml"))
        bins = list(model_path.glob("*.bin"))
        return len(xmls) > 0 and len(bins) > 0
    return False


def detect_format(model_path: Path) -> ModelFormat:
    """Determine model format from the path.

    Raises ``SystemExit`` on unrecognised format.
    """
    suffix = model_path.suffix.lower()

    if suffix == ".pt":
        return ModelFormat.PT
    if suffix == ".onnx":
        return ModelFormat.ONNX
    if suffix in (".mlpackage", ".mlmodel"):
        return ModelFormat.COREML
    if suffix == ".xml":
        return ModelFormat.OPENVINO

    if model_path.is_dir():
        xmls = list(model_path.glob("*.xml"))
        bins = list(model_path.glob("*.bin"))
        if xmls and bins:
            return ModelFormat.OPENVINO

    print(
        f"ERROR: could not determine model format from: {model_path}",
        file=sys.stderr,
    )
    sys.exit(1)


def check_runtime(fmt: ModelFormat) -> None:
    """Verify the required runtime package is importable.

    Raises ``SystemExit`` with an install hint if the import fails.
    """
    import importlib

    package = FORMAT_RUNTIME[fmt]
    try:
        importlib.import_module(package)
    except ImportError:
        print(
            f"ERROR: format '{fmt.value}' requires the '{package}' "
            f"package, which is not installed.\n"
            f"  Install it with:  pip install {package}",
            file=sys.stderr,
        )
        sys.exit(1)