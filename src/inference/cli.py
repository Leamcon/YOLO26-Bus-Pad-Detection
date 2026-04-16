"""CLI argument parsing and input validation."""

import argparse
import sys
from pathlib import Path

from inference.formats import is_valid_model_path

EXPECTED_CHIPS_DIRNAME = "chips"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="inference",
        description="Stage 2: YOLO inference on chipped imagery.",
    )
    parser.add_argument(
        "model_path",
        type=Path,
        help="Path to model file or directory (.pt, .onnx, .mlpackage, .mlmodel, or OpenVINO dir).",
    )
    parser.add_argument(
        "chips_dir",
        type=Path,
        help="Path to directory containing chip images.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Inference device: mps | cuda | cpu (default: auto per format).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Inference batch size (default: 64).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold (default: 0.25).",
    )

    args = parser.parse_args()

    args.model_path = args.model_path.resolve()
    args.chips_dir = args.chips_dir.resolve()

    if not is_valid_model_path(args.model_path):
        parser.error(
            f"Model path not found or unrecognised format: {args.model_path}\n"
            f"  Supported: .pt, .onnx, .mlpackage, .mlmodel, or OpenVINO "
            f"directory containing .xml + .bin"
        )
    if not args.chips_dir.is_dir():
        parser.error(f"Chips directory not found: {args.chips_dir}")

    _validate_chips_dir(args.chips_dir)

    return args


def _validate_chips_dir(chips_dir: Path) -> None:
    """Guard against the parent directory being passed instead of chips/.

    Stage 3 expects predictions/ to be a sibling of chips/ under a common
    parent that also contains geotransform and offset sidecar files.  If the
    caller passes the parent directory by mistake, predictions/ lands one
    level too high and breaks downstream reconstruction.
    """
    if chips_dir.name != EXPECTED_CHIPS_DIRNAME:
        print(
            f"ERROR: chips_dir should point to a directory named "
            f"'{EXPECTED_CHIPS_DIRNAME}', got '{chips_dir.name}'.\n"
            f"  Received path: {chips_dir}\n"
            f"  predictions/ will be written to chips_dir's parent, which "
            f"must also contain geotransform and offset sidecar data.\n"
            f"  If you passed the parent directory by mistake, re-run with "
            f"the chips/ subdirectory instead.",
            file=sys.stderr,
        )
        sys.exit(1)