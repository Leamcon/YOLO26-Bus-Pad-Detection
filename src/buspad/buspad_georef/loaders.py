"""File I/O for geotransforms and chip offsets."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from affine import Affine

from buspad_georef.defs import ChipOffset

logger = logging.getLogger(__name__)


def load_geotransforms(gt_path: Path) -> dict[str, Affine]:
    """Load geotransform JSON and reconstruct Affine objects."""
    with open(gt_path, encoding="utf-8") as f:
        raw = json.load(f)

    transforms: dict[str, Affine] = {}
    for tile_filename, entry in raw.items():
        t = entry["transform"]
        transforms[tile_filename] = Affine(
            t["a"], t["b"], t["c"], t["d"], t["e"], t["f"]
        )

    return transforms


def load_offsets(offsets_dir: Path) -> dict[str, dict[str, ChipOffset]]:
    """Load all per-tile offset CSVs.

    Returns:
        Mapping of ``{tile_stem: {chip_filename: ChipOffset}}``.
    """
    all_offsets: dict[str, dict[str, ChipOffset]] = {}

    for csv_path in sorted(offsets_dir.glob("*_offsets.csv")):
        tile_stem = csv_path.stem.replace("_offsets", "")
        chip_offsets: dict[str, ChipOffset] = {}

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                chip_offsets[row["chip_filename"]] = ChipOffset(
                    x=int(row["x_offset"]),
                    y=int(row["y_offset"]),
                )

        all_offsets[tile_stem] = chip_offsets

    return all_offsets
