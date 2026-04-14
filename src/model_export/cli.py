"""CLI entry point for YOLO model export."""

import argparse
import platform
import shutil
import sys
from pathlib import Path

FORMAT_CONFIG = {
    "onnx": {
        "suffix": ".onnx",
        "is_dir": False,
        "artifact_name": lambda stem: f"{stem}.onnx",
    },
    "coreml": {
        "suffix": ".mlpackage",
        "is_dir": True,
        "artifact_name": lambda stem: f"{stem}.mlpackage",
    },
    "openvino": {
        "suffix": "_openvino_model",
        "is_dir": True,
        "artifact_name": lambda stem: f"{stem}_openvino_model",
    },
}

SUPPORTED_FORMATS = list(FORMAT_CONFIG.keys())


def _resolve_exported_artifact(weights_dir: Path, stem: str, fmt: str) -> Path:
    """Locate the exported artifact produced by ultralytics in the weights directory."""
    cfg = FORMAT_CONFIG[fmt]
    artifact = weights_dir / cfg["artifact_name"](stem)
    if not artifact.exists():
        raise FileNotFoundError(
            f"Expected export artifact not found at {artifact}. "
            f"Check ultralytics output for format '{fmt}'."
        )
    return artifact


def _move_artifact(artifact: Path, dest_dir: Path) -> Path:
    """Move exported artifact (file or directory) into the target directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / artifact.name
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    shutil.move(str(artifact), str(target))
    return target


def export_model(model_path: Path, fmt: str) -> Path:
    """Load a YOLO model, export it, and relocate the artifact.

    Returns the final path of the exported model.
    """
    if fmt == "coreml" and platform.system() != "Darwin":
        print(
            f"ERROR: CoreML export requires macOS. Current platform: {platform.system()}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not model_path.is_file():
        print(f"ERROR: Model file not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    from ultralytics import YOLO

    model = YOLO(str(model_path))
    model.export(format=fmt, nms=False, half=False)

    weights_dir = model_path.parent
    stem = model_path.stem  # e.g. "best"
    artifact = _resolve_exported_artifact(weights_dir, stem, fmt)

    # Walk back from weights/ into the generation directory, create format subdir.
    generation_dir = weights_dir.parent
    dest_dir = generation_dir / fmt
    final_path = _move_artifact(artifact, dest_dir)

    return final_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m model_export",
        description="Export a fine-tuned YOLO model to a deployment format.",
    )
    parser.add_argument(
        "model_path",
        type=Path,
        help="Path to the .pt weights file (e.g. models/ls01_v1/weights/best.pt).",
    )
    parser.add_argument(
        "-f",
        "--format",
        required=True,
        choices=SUPPORTED_FORMATS,
        dest="fmt",
        help="Target export format.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    final_path = export_model(args.model_path, args.fmt)
    print(f"Export complete: {final_path}")