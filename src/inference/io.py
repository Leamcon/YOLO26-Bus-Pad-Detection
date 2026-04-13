"""Prediction output writers."""

import csv
from pathlib import Path

PREDICTION_FIELDNAMES = [
    "chip_filename",
    "x1",
    "y1",
    "x2",
    "y2",
    "confidence",
    "class_id",
]


def write_prediction_csv(
    output_dir: Path, tile_stem: str, records: list[dict],
) -> Path:
    """Write per-tile prediction CSV.  Returns the written path."""
    csv_path = output_dir / f"{tile_stem}_predictions.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PREDICTION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)
    return csv_path