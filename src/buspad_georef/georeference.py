"""
Stage 3 — Georeferencing & Feature Class Generation
Converts YOLO predictions from chip-pixel space to EPSG:6539 map coordinates
and writes a point shapefile.

Usage:
    python georeference.py /path/to/stage1_output /path/to/predictions_dir

    stage1_output must contain:
        - offsets/          (per-tile offset CSVs from Stage 1)
        - geotransforms.json (labeled Affine coefficients from Stage 1)

    predictions_dir contains per-tile prediction CSVs from Stage 2.
    If omitted, defaults to stage1_output/predictions/.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import geopandas as gpd
from affine import Affine
from shapely.geometry import Point

CHIP_SIZE = 200
UPSCALE_SIZE = 640
SCALE_FACTOR = CHIP_SIZE / UPSCALE_SIZE  # 0.3125


def load_geotransforms(gt_path: Path) -> dict[str, Affine]:
    """Load geotransform JSON and reconstruct Affine objects."""
    with open(gt_path) as f:
        raw = json.load(f)

    transforms = {}
    for tile_filename, entry in raw.items():
        t = entry["transform"]
        transforms[tile_filename] = Affine(t["a"], t["b"], t["c"], t["d"], t["e"], t["f"])

    return transforms


def load_offsets(offsets_dir: Path) -> dict[str, dict[str, tuple[int, int]]]:
    """Load all per-tile offset CSVs.

    Returns: {tile_stem: {chip_filename: (x_offset, y_offset)}}
    """
    all_offsets = {}

    for csv_path in sorted(offsets_dir.glob("*_offsets.csv")):
        tile_stem = csv_path.stem.replace("_offsets", "")
        chip_offsets = {}

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                chip_offsets[row["chip_filename"]] = (
                    int(row["x_offset"]),
                    int(row["y_offset"]),
                )

        all_offsets[tile_stem] = chip_offsets

    return all_offsets


def resolve_tile_filename(tile_stem: str, gt_keys: list[str]) -> str | None:
    """Match a tile stem to its key in the geotransform dict.

    GT keys are original filenames (e.g. 'tile_001.jp2').
    Tile stems lack the extension. Match by stem comparison.
    """
    for key in gt_keys:
        if Path(key).stem == tile_stem:
            return key
    return None


def process_predictions(
    pred_dir: Path,
    offsets: dict[str, dict[str, tuple[int, int]]],
    transforms: dict[str, Affine],
) -> list[dict]:
    """Process all prediction CSVs into georeferenced point features."""
    features = []
    gt_keys = list(transforms.keys())

    pred_files = sorted(pred_dir.glob("*_predictions.csv"))
    if not pred_files:
        print("ERROR: no prediction CSVs found.", file=sys.stderr)
        sys.exit(1)

    for pred_path in pred_files:
        tile_stem = pred_path.stem.replace("_predictions", "")

        # Resolve references
        tile_filename = resolve_tile_filename(tile_stem, gt_keys)
        if tile_filename is None:
            print(f"WARNING: no geotransform for {tile_stem}, skipping.", file=sys.stderr)
            continue

        if tile_stem not in offsets:
            print(f"WARNING: no offset CSV for {tile_stem}, skipping.", file=sys.stderr)
            continue

        transform = transforms[tile_filename]
        tile_offsets = offsets[tile_stem]

        with open(pred_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                chip_fname = row["chip_filename"]

                if chip_fname not in tile_offsets:
                    print(
                        f"WARNING: chip {chip_fname} not found in offsets for {tile_stem}, skipping.",
                        file=sys.stderr,
                    )
                    continue

                x_off, y_off = tile_offsets[chip_fname]

                # Bbox centroid in 640x640 space
                cx_640 = (float(row["x1"]) + float(row["x2"])) / 2
                cy_640 = (float(row["y1"]) + float(row["y2"])) / 2

                # Scale to 200x200 chip space
                cx_chip = cx_640 * SCALE_FACTOR
                cy_chip = cy_640 * SCALE_FACTOR

                # Tile pixel coordinates
                tile_col = x_off + cx_chip
                tile_row = y_off + cy_chip

                # Apply affine: (col, row) → (map_x, map_y)
                map_x, map_y = transform * (tile_col, tile_row)

                features.append(
                    {
                        "geometry": Point(map_x, map_y),
                        "confidence": float(row["confidence"]),
                        "class_id": int(row["class_id"]),
                        "source_tile": tile_filename,
                    }
                )

    return features


def main():
    parser = argparse.ArgumentParser(description="Stage 3: Georeference detections to shapefile.")
    parser.add_argument("stage1_dir", help="Stage 1 output directory (contains offsets/ and geotransforms.json).")
    parser.add_argument("predictions_dir", nargs="?", default=None, help="Directory of prediction CSVs. Defaults to stage1_dir/predictions/.")
    parser.add_argument("--output", default=None, help="Output shapefile path. Defaults to stage1_dir/detections.shp.")
    args = parser.parse_args()

    stage1_dir = Path(args.stage1_dir)
    pred_dir = Path(args.predictions_dir) if args.predictions_dir else stage1_dir / "predictions"
    output_path = Path(args.output) if args.output else stage1_dir / "detections.shp"

    # Validate inputs
    gt_path = stage1_dir / "geotransforms.json"
    offsets_dir = stage1_dir / "offsets"

    for p, label in [(gt_path, "geotransforms.json"), (offsets_dir, "offsets/"), (pred_dir, "predictions/")]:
        if not p.exists():
            print(f"ERROR: {label} not found at {p}", file=sys.stderr)
            sys.exit(1)

    print(f"Loading geotransforms: {gt_path}")
    transforms = load_geotransforms(gt_path)
    print(f"  {len(transforms)} tiles")

    print(f"Loading offsets: {offsets_dir}")
    offsets = load_offsets(offsets_dir)
    print(f"  {len(offsets)} tiles")

    print(f"Processing predictions: {pred_dir}")
    features = process_predictions(pred_dir, offsets, transforms)
    print(f"  {len(features)} detections georeferenced")

    if not features:
        print("No detections to write. Exiting.")
        sys.exit(0)

    gdf = gpd.GeoDataFrame(features, crs="EPSG:6539")
    gdf.to_file(output_path)
    print(f"\nWrote {len(gdf)} features → {output_path}")


if __name__ == "__main__":
    main()