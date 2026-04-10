"""
Stage 1 — Chipping Pipeline
Chips JP2 tiles into 200x200 patches, upscales to 640x640, writes offset CSVs
and a geotransform reference file.

Usage:
    python chip_tiles.py data/nyc_ortho_2022/boro_staten_island_sp22 \
        --overlap 20 --format jpg
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

CHIP_SIZE = 200
UPSCALE_SIZE = 640
TILE_SIZE = 5000
TRAVERSAL = TILE_SIZE - CHIP_SIZE  # 4800


def parse_input_path(input_path: str) -> dict | None:
    """Extract year and boro from the input directory convention.

    Expected pattern: .../nyc_ortho_{YYYY}/boro_{boro_name}_sp{YY}
    Returns dict with keys 'year' and 'boro', or None if no match.
    """
    p = Path(input_path).resolve()
    leaf = p.name
    parent = p.parent.name

    leaf_match = re.match(r"^boro_(.+)_sp(\d{2})$", leaf)
    parent_match = re.match(r"^nyc_ortho_(\d{4})$", parent)

    if not leaf_match or not parent_match:
        return None

    year_full = parent_match.group(1)
    boro = leaf_match.group(1)
    year_short = leaf_match.group(2)

    if year_full[-2:] != year_short:
        print(
            f"WARNING: year mismatch — directory says {year_full}, "
            f"suffix says sp{year_short}. Using {year_full}.",
            file=sys.stderr,
        )

    return {"year": year_full, "boro": boro}


def build_output_dir(input_path: str, output_override: str | None) -> Path:
    """Derive output directory from input path convention, or use override."""
    if output_override:
        return Path(output_override)

    parsed = parse_input_path(input_path)
    if parsed is None:
        print(
            "ERROR: input path does not match expected convention "
            "(nyc_ortho_YYYY/boro_NAME_spYY). Provide --output-dir explicitly.",
            file=sys.stderr,
        )
        sys.exit(1)

    return Path("output/chips") / f"inference_{parsed['year']}" / f"{parsed['boro']}_{parsed['year']}"


def validate_overlap(overlap_pct: int) -> int:
    """Validate overlap percentage and return stride in pixels."""
    if overlap_pct == 0:
        return CHIP_SIZE

    stride = int(CHIP_SIZE * (1 - overlap_pct / 100))

    if stride <= 0 or stride > CHIP_SIZE:
        print(f"ERROR: overlap {overlap_pct}% yields invalid stride {stride}.", file=sys.stderr)
        sys.exit(1)

    if TRAVERSAL % stride != 0:
        print(
            f"ERROR: overlap {overlap_pct}% → stride {stride}px does not divide "
            f"{TRAVERSAL} evenly. Choose an overlap that yields a factor of {TRAVERSAL}.",
            file=sys.stderr,
        )
        sys.exit(1)

    return stride


def chip_tile(
    tile_path: Path,
    output_dir: Path,
    stride: int,
    img_format: str,
) -> tuple[list[dict], dict]:
    """Chip a single tile. Returns (chip_records, geotransform_dict)."""
    ext = "jpg" if img_format == "jpg" else "png"
    tile_stem = tile_path.stem

    with rasterio.open(tile_path) as src:
        # Read first 3 bands (drop 4th if present)
        band_count = min(src.count, 3)
        data = src.read(list(range(1, band_count + 1)))  # shape: (C, H, W)
        t = src.transform
        gt = {"a": t.a, "b": t.b, "c": t.c, "d": t.d, "e": t.e, "f": t.f}

    # data shape: (C, H, W) → transpose to (H, W, C) for PIL
    img_array = np.transpose(data, (1, 2, 0))
    h, w = img_array.shape[:2]

    if h != TILE_SIZE or w != TILE_SIZE:
        print(
            f"WARNING: {tile_path.name} is {w}x{h}, expected {TILE_SIZE}x{TILE_SIZE}. Skipping.",
            file=sys.stderr,
        )
        return [], {}

    chips_per_axis = (TRAVERSAL // stride) + 1
    records = []

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

    gt_entry = {"transform": gt, "crs": "EPSG:6539"}
    return records, gt_entry


def write_tile_csv(output_dir: Path, tile_stem: str, records: list[dict]):
    """Write per-tile offset CSV."""
    csv_path = output_dir / "offsets" / f"{tile_stem}_offsets.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["chip_filename", "x_offset", "y_offset"])
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description="Stage 1: Chip JP2 tiles for YOLO inference.")
    parser.add_argument("input_dir", help="Path to directory containing .jp2 tiles.")
    parser.add_argument(
        "--overlap",
        type=int,
        default=20,
        help="Overlap percentage (default: 20). Must yield a stride that divides 4800.",
    )
    parser.add_argument(
        "--format",
        choices=["jpg", "png"],
        default="jpg",
        dest="img_format",
        help="Output image format (default: jpg).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Explicit output directory. Overrides convention-based derivation.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"ERROR: {input_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    stride = validate_overlap(args.overlap)
    output_dir = build_output_dir(args.input_dir, args.output_dir)

    # Create output subdirectories
    (output_dir / "chips").mkdir(parents=True, exist_ok=True)
    (output_dir / "offsets").mkdir(parents=True, exist_ok=True)

    tiles = sorted(input_dir.glob("*.jp2"))
    if not tiles:
        print(f"ERROR: no .jp2 files found in {input_dir}.", file=sys.stderr)
        sys.exit(1)

    chips_per_axis = (TRAVERSAL // stride) + 1
    total_chips_per_tile = chips_per_axis ** 2
    print(
        f"Config: stride={stride}px, overlap={args.overlap}%, "
        f"{chips_per_axis}x{chips_per_axis}={total_chips_per_tile} chips/tile, "
        f"{len(tiles)} tiles, format={args.img_format}"
    )
    print(f"Output: {output_dir}")

    geotransforms = {}

    for i, tile_path in enumerate(tiles, 1):
        print(f"[{i}/{len(tiles)}] {tile_path.name} ...", end=" ", flush=True)

        records, gt_entry = chip_tile(tile_path, output_dir, stride, args.img_format)

        if not records:
            print("SKIPPED")
            continue

        write_tile_csv(output_dir, tile_path.stem, records)
        geotransforms[tile_path.name] = gt_entry
        print(f"{len(records)} chips")

    # Write geotransform reference
    gt_path = output_dir / "geotransforms.json"
    with open(gt_path, "w") as f:
        json.dump(geotransforms, f, indent=2)

    print(f"\nDone. {len(geotransforms)} tiles processed → {gt_path}")


if __name__ == "__main__":
    main()