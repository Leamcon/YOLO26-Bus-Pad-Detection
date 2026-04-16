"""Coordinate transforms and prediction processing."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from affine import Affine
from shapely.geometry import Point

from buspad_georef.defs import (
    PREDICTION_REQUIRED_FIELDS,
    SCALE_FACTOR,
    ChipOffset,
    Detection,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Coordinate math
# ---------------------------------------------------------------------------

def chip_detection_to_map(
    cx_640: float,
    cy_640: float,
    chip_offset: ChipOffset,
    transform: Affine,
) -> tuple[float, float]:
    """Convert a detection centroid from 640x640 space to map coordinates.

    Pipeline: 640x640 -> chip pixel -> tile pixel -> map (via affine).
    """
    cx_chip = cx_640 * SCALE_FACTOR
    cy_chip = cy_640 * SCALE_FACTOR

    tile_col = chip_offset.x + cx_chip
    tile_row = chip_offset.y + cy_chip

    map_x, map_y = transform * (tile_col, tile_row)
    return map_x, map_y


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_tile_filename(tile_stem: str, gt_keys: list[str]) -> str | None:
    """Match a tile stem to its key in the geotransform dict.

    GT keys are original filenames (e.g. ``tile_001.jp2``).
    Tile stems lack the extension.  Match by stem comparison.
    """
    for key in gt_keys:
        if Path(key).stem == tile_stem:
            return key
    return None


def _validate_prediction_header(reader: csv.DictReader, pred_path: Path) -> None:
    """Raise if the prediction CSV is missing required columns."""
    if reader.fieldnames is None:
        raise ValueError(f"Empty or headerless CSV: {pred_path}")

    missing = PREDICTION_REQUIRED_FIELDS - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Prediction CSV {pred_path} missing columns: {missing}")


def _parse_prediction_row(row: dict[str, str]) -> tuple[str, float, float, float, int]:
    """Extract and validate fields from a single prediction row.

    Returns:
        ``(chip_filename, cx_640, cy_640, confidence, class_id)``
    """
    chip_fname = row["chip_filename"]
    cx_640 = (float(row["x1"]) + float(row["x2"])) / 2
    cy_640 = (float(row["y1"]) + float(row["y2"])) / 2
    confidence = float(row["confidence"])
    class_id = int(row["class_id"])
    return chip_fname, cx_640, cy_640, confidence, class_id


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_predictions(
    pred_dir: Path,
    offsets: dict[str, dict[str, ChipOffset]],
    transforms: dict[str, Affine],
) -> list[Detection]:
    """Process all prediction CSVs into georeferenced point features."""
    features: list[Detection] = []
    gt_keys = list(transforms.keys())

    pred_files = sorted(pred_dir.glob("*_predictions.csv"))
    if not pred_files:
        raise FileNotFoundError(f"No prediction CSVs found in {pred_dir}")

    for pred_path in pred_files:
        tile_stem = pred_path.stem.replace("_predictions", "")

        tile_filename = resolve_tile_filename(tile_stem, gt_keys)
        if tile_filename is None:
            logger.warning("No geotransform for %s, skipping.", tile_stem)
            continue

        if tile_stem not in offsets:
            logger.warning("No offset CSV for %s, skipping.", tile_stem)
            continue

        transform = transforms[tile_filename]
        tile_offsets = offsets[tile_stem]

        with open(pred_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            _validate_prediction_header(reader, pred_path)

            for row in reader:
                chip_fname, cx_640, cy_640, confidence, class_id = (
                    _parse_prediction_row(row)
                )

                if chip_fname not in tile_offsets:
                    logger.warning(
                        "Chip %s not in offsets for %s, skipping.",
                        chip_fname,
                        tile_stem,
                    )
                    continue

                map_x, map_y = chip_detection_to_map(
                    cx_640, cy_640, tile_offsets[chip_fname], transform
                )

                features.append(
                    Detection(
                        geometry=Point(map_x, map_y),
                        confidence=confidence,
                        class_id=class_id,
                        source_tile=tile_filename,
                    )
                )

    return features
