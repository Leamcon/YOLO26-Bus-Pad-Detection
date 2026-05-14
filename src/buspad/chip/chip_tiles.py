"""Core chipping logic — stateless functions that operate on single tiles."""

import sys

import numpy as np
import rasterio
from PIL import Image

from buspad.chip.defs import CHIP_SIZE, CRS, TILE_SIZE, TRAVERSAL, UPSCALE_SIZE
from pathlib import Path


def validate_overlap(overlap_pct: int) -> int:
    """Validate overlap percentage and return stride in pixels.

    Raises SystemExit if the overlap yields an invalid or indivisible stride.
    """
    if overlap_pct == 0:
        return CHIP_SIZE

    stride = int(CHIP_SIZE * (1 - overlap_pct / 100))

    if stride <= 0 or stride > CHIP_SIZE:
        print(
            f"ERROR: overlap {overlap_pct}% yields invalid stride {stride}.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if TRAVERSAL % stride != 0:
        print(
            f"ERROR: overlap {overlap_pct}% → stride {stride}px does not divide "
            f"{TRAVERSAL} evenly. Choose an overlap that yields a factor of "
            f"{TRAVERSAL}.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return stride


def chip_tile(
    tile_path: Path,
    output_dir: Path,
    stride: int,
    img_format: str,
) -> tuple[list[dict], dict]:
    """Chip a single tile into patches and upscale for inference.

    Reads a JP2 tile, extracts CHIP_SIZE×CHIP_SIZE patches at the given
    stride, upscales each to UPSCALE_SIZE×UPSCALE_SIZE, and writes them
    to ``output_dir / "chips"``.

    Returns
    -------
    records : list[dict]
        Per-chip metadata (filename, x/y offsets) for the offset CSV.
    gt_entry : dict
        Geotransform and CRS for this tile, keyed for geotransforms.json.
        Empty dict if the tile was skipped.
    """
    ext = "jpg" if img_format == "jpg" else "png"
    tile_stem = tile_path.stem

    with rasterio.open(tile_path) as src:
        band_count = min(src.count, 3)
        data = src.read(list(range(1, band_count + 1)))  # (C, H, W)
        t = src.transform
        gt = {"a": t.a, "b": t.b, "c": t.c, "d": t.d, "e": t.e, "f": t.f}

    img_array = np.transpose(data, (1, 2, 0))  # (H, W, C)
    h, w = img_array.shape[:2]

    if h != TILE_SIZE or w != TILE_SIZE:
        print(
            f"WARNING: {tile_path.name} is {w}×{h}, expected "
            f"{TILE_SIZE}×{TILE_SIZE}. Skipping.",
            file=sys.stderr,
        )
        return [], {}

    chips_per_axis = (TRAVERSAL // stride) + 1
    records: list[dict] = []

    for row_idx in range(chips_per_axis):
        for col_idx in range(chips_per_axis):
            y_off = row_idx * stride
            x_off = col_idx * stride

            chip = img_array[y_off : y_off + CHIP_SIZE, x_off : x_off + CHIP_SIZE]
            chip_img = Image.fromarray(chip)
            chip_upscaled = chip_img.resize(
                (UPSCALE_SIZE, UPSCALE_SIZE), Image.LANCZOS
            )

            chip_fname = f"{tile_stem}_r{row_idx:03d}_c{col_idx:03d}.{ext}"
            chip_upscaled.save(output_dir / "chips" / chip_fname)

            records.append(
                {
                    "chip_filename": chip_fname,
                    "x_offset": x_off,
                    "y_offset": y_off,
                }
            )

    return records, {"transform": gt, "crs": CRS}