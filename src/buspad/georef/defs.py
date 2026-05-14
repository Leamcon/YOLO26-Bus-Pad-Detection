"""Shared constants, data structures, and path builders for the georef pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import Point

CHIP_SIZE: int = 200
UPSCALE_SIZE: int = 640
SCALE_FACTOR: float = CHIP_SIZE / UPSCALE_SIZE  # 0.3125

PREDICTION_REQUIRED_FIELDS: set[str] = {
    "chip_filename",
    "x1",
    "y1",
    "x2",
    "y2",
    "confidence",
    "class_id",
}


@dataclass(frozen=True, slots=True)
class ChipOffset:
    """Pixel offset of a chip within its parent tile."""

    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Detection:
    """A single georeferenced detection."""

    geometry: Point
    confidence: float
    class_id: int
    source_tile: str


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _mode_name(boro: str | None, cd: int | None) -> tuple[str, str]:
    """Return ``(mode, name)`` from the mutually exclusive CLI args."""
    if boro is not None:
        return "boro", boro.lower()
    if cd is not None:
        return "cd", str(cd)
    raise ValueError("Either --boro or --cd is required.")


def build_chips_dir(
    workspace: Path,
    year: int,
    boro: str | None = None,
    cd: int | None = None,
) -> Path:
    """``<workspace>/data/chips/{mode}/{name}/{year}/``"""
    mode, name = _mode_name(boro, cd)
    return workspace / "data" / "chips" / mode / name / str(year)


def build_predictions_dir(
    workspace: Path,
    year: int,
    boro: str | None = None,
    cd: int | None = None,
) -> Path:
    """``<workspace>/output/detections/{mode}/{name}/{year}/predictions/``"""
    mode, name = _mode_name(boro, cd)
    return workspace / "output" / "detections" / mode / name / str(year) / "predictions"


def build_georef_dir(
    workspace: Path,
    year: int,
    boro: str | None = None,
    cd: int | None = None,
) -> Path:
    """``<workspace>/output/detections/{mode}/{name}/{year}/georef/``"""
    mode, name = _mode_name(boro, cd)
    return workspace / "output" / "detections" / mode / name / str(year) / "georef"


def build_output_stem(
    year: int,
    boro: str | None = None,
    cd: int | None = None,
) -> str:
    """Output filename stem, e.g. ``boro_bronx_2024`` or ``cd_108_2024``."""
    mode, name = _mode_name(boro, cd)
    return f"{mode}_{name}_{year}"