"""CLI entry point for the chip subpackage.

Usage examples:
    buspad-chip --year 2024 --boro bronx
    buspad-chip --year 2024 --cd 108 --overlap 10 --format png
    python -m buspad.chip --year 2024 --boro staten_island --root /tmp/workspace
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from buspad.config import add_root_arg, resolve_workspace
from buspad.chip.defs import TRAVERSAL, resolve_input_dir, resolve_output_dir
from buspad.chip.chip_tiles import chip_tile, validate_overlap

DESCRIPTION = """\
Chip georeferenced JP2 tiles into 200×200 patches upscaled to 640×640 for
YOLO inference.

Reads tiles from one of two source directories depending on mode:

  Borough mode (--boro):
    data/imagery/nyc_ortho_{YYYY}/boro_{NAME}_sp{YY}/

  Community district mode (--cd):
    data/imagery/cd/{YYYY}/{CD}/

Writes chips, per-tile offset CSVs, and a geotransforms.json reference to:

  Borough mode:    data/chips/boro/{NAME}/{YYYY}/
  Community district mode:  data/chips/cd/{CD}/{YYYY}/

All paths are relative to the workspace set by buspad-init (or overridden
with --root).
"""


def _write_tile_csv(output_dir: Path, tile_stem: str, records: list[dict]) -> None:
    """Write per-tile chip offset CSV."""
    csv_path = output_dir / "offsets" / f"{tile_stem}_offsets.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["chip_filename", "x_offset", "y_offset"]
        )
        writer.writeheader()
        writer.writerows(records)


def _write_geotransforms(output_dir: Path, geotransforms: dict) -> Path:
    """Write the combined geotransform reference file. Returns the path."""
    gt_path = output_dir / "geotransforms.json"
    with gt_path.open("w") as f:
        json.dump(geotransforms, f, indent=2)
    return gt_path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="buspad-chip",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Four-digit imagery vintage year (e.g. 2024). Used to locate "
        "the source tile directory and to organize output.",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--boro",
        type=str,
        help="Borough name (case-insensitive). Reads tiles from "
        "data/imagery/nyc_ortho_{YYYY}/boro_{NAME}_sp{YY}/ and writes "
        "chips to data/chips/boro/{NAME}/{YYYY}/.",
    )
    source.add_argument(
        "--cd",
        type=int,
        help="Community district number. Reads tiles from "
        "data/imagery/cd/{YYYY}/{CD}/ and writes chips to "
        "data/chips/cd/{CD}/{YYYY}/.",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=20,
        help="Chip overlap percentage (default: 20). Must yield a stride "
        f"in pixels that evenly divides {TRAVERSAL}.",
    )
    parser.add_argument(
        "--format",
        choices=["jpg", "png"],
        default="jpg",
        dest="img_format",
        help="Output image format for chips (default: jpg).",
    )

    add_root_arg(parser)
    args = parser.parse_args()

    # ── Normalize and resolve ─────────────────────────────────────────
    workspace = resolve_workspace(args.root)

    boro = args.boro.lower().strip() if args.boro else None
    cd = args.cd

    input_dir = resolve_input_dir(workspace, args.year, boro=boro, cd=cd)
    output_dir = resolve_output_dir(workspace, args.year, boro=boro, cd=cd)

    if not input_dir.is_dir():
        print(f"ERROR: input directory does not exist: {input_dir}", file=sys.stderr)
        raise SystemExit(1)

    stride = validate_overlap(args.overlap)

    # ── Create output subdirectories ──────────────────────────────────
    (output_dir / "chips").mkdir(parents=True, exist_ok=True)
    (output_dir / "offsets").mkdir(parents=True, exist_ok=True)

    # ── Discover tiles ────────────────────────────────────────────────
    tiles = sorted(input_dir.glob("*.jp2"))
    if not tiles:
        print(f"ERROR: no .jp2 files found in {input_dir}", file=sys.stderr)
        raise SystemExit(1)

    chips_per_axis = (TRAVERSAL // stride) + 1
    total_per_tile = chips_per_axis**2
    print(
        f"Config: stride={stride}px, overlap={args.overlap}%, "
        f"{chips_per_axis}×{chips_per_axis}={total_per_tile} chips/tile, "
        f"{len(tiles)} tile(s), format={args.img_format}"
    )
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")

    # ── Process tiles ─────────────────────────────────────────────────
    geotransforms: dict = {}

    for i, tile_path in enumerate(tiles, 1):
        print(f"[{i}/{len(tiles)}] {tile_path.name} ...", end=" ", flush=True)

        try:
            records, gt_entry = chip_tile(
                tile_path, output_dir, stride, args.img_format
            )
        except OSError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            continue

        if not records:
            print("SKIPPED")
            continue

        try:
            _write_tile_csv(output_dir, tile_path.stem, records)
        except OSError as e:
            print(f"ERROR writing offsets: {e}", file=sys.stderr)
            continue

        geotransforms[tile_path.name] = gt_entry
        print(f"{len(records)} chips")

    # ── Write geotransform reference ──────────────────────────────────
    gt_path = _write_geotransforms(output_dir, geotransforms)
    print(f"\n{len(geotransforms)} tile(s) processed → {gt_path}")
    print("Done.")