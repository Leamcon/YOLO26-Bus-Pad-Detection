"""Shared constants and data structures for the georeferencing pipeline."""

from __future__ import annotations

from dataclasses import dataclass

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
