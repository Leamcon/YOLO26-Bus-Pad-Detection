"""Constants and workspace path builders for the infer subpackage."""

from __future__ import annotations

import sys
from pathlib import Path

from buspad.infer.formats import ModelFormat

MODEL_SIZES: tuple[str, ...] = ("nano", "small")


# ---------------------------------------------------------------------------
# Workspace path builders
# ---------------------------------------------------------------------------

def build_chips_dir(
    workspace: Path, mode: str, name: str, year: str,
) -> Path:
    """Chips input directory.

    Returns ``<workspace>/data/chips/{mode}/{name}/{year}/chips/``.
    """
    return workspace / "data" / "chips" / mode / name / year / "chips"


def build_predictions_dir(
    workspace: Path, mode: str, name: str, year: str,
) -> Path:
    """Predictions output directory.

    Returns ``<workspace>/output/detections/{mode}/{name}/{year}/predictions/``.
    """
    return (
        workspace / "output" / "detections" / mode / name / year / "predictions"
    )


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------

def find_model(workspace: Path, size: str, fmt: ModelFormat) -> Path:
    """Locate a model of the requested format in ``models/{size}/``.

    Scans the size directory for files or directories matching *fmt*.
    Exits with an error if none are found.  If multiple candidates
    exist, uses the first (lexicographic) and warns.
    """
    models_dir = workspace / "models" / size

    if not models_dir.is_dir():
        print(
            f"ERROR: model directory not found: {models_dir}\n"
            f"  Run buspad-init to scaffold the workspace.",
            file=sys.stderr,
        )
        sys.exit(1)

    candidates = _scan_for_format(models_dir, fmt)

    if not candidates:
        print(
            f"ERROR: no {fmt.value} model found in {models_dir}.\n"
            f"  Place a {fmt.value}-format model in the directory and retry.",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(candidates) > 1:
        print(
            f"WARNING: multiple {fmt.value} models in {models_dir}, "
            f"using {candidates[0].name}.",
            file=sys.stderr,
        )

    return candidates[0]


def _scan_for_format(directory: Path, fmt: ModelFormat) -> list[Path]:
    """Return sorted candidate paths matching *fmt* inside *directory*."""
    if fmt is ModelFormat.PT:
        return sorted(directory.glob("*.pt"))

    if fmt is ModelFormat.ONNX:
        return sorted(directory.glob("*.onnx"))

    if fmt is ModelFormat.COREML:
        return sorted(
            p for p in directory.iterdir()
            if p.suffix.lower() in (".mlpackage", ".mlmodel")
        )

    if fmt is ModelFormat.OPENVINO:
        # Prefer subdirectories containing .xml + .bin (ultralytics export
        # convention), fall back to bare .xml files.
        subdirs = sorted(
            p for p in directory.iterdir()
            if p.is_dir()
            and list(p.glob("*.xml"))
            and list(p.glob("*.bin"))
        )
        return subdirs if subdirs else sorted(directory.glob("*.xml"))

    return []