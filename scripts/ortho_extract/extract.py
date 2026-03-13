"""
Main extraction script.

Usage (from project root):
    python -m scripts.ortho_extract.extract --boro_cd 401 402 403
    python -m scripts.ortho_extract.extract --boro_cd 101 --yolo
    python -m scripts.ortho_extract.extract --boro_cd 301 302 --data_dir /path/to/data --output_dir /path/to/output
"""

import argparse
import sys
from pathlib import Path

from scripts.ortho_extract.config import DEFAULT_DATA_DIR, DEFAULT_BOUNDARY_SHP, DEFAULT_OUTPUT_DIR
from scripts.ortho_extract.tile_selection import load_boundary_features, select_tiles_for_feature
from scripts.ortho_extract.mosaic_clip import mosaic_and_clip
from scripts.ortho_extract.export import export_for_yolo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract orthoimagery subsets by community district boundary."
    )
    parser.add_argument(
        "--boro_cd",
        type=int,
        nargs="+",
        required=True,
        help="One or more boro_cd values (e.g., 401 402 403).",
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        default=DEFAULT_DATA_DIR,
        help=f"Root directory containing borough tile subdirectories. Default: {DEFAULT_DATA_DIR}",
    )
    parser.add_argument(
        "--boundary_shp",
        type=str,
        default=DEFAULT_BOUNDARY_SHP,
        help=f"Path to boundary shapefile. Default: {DEFAULT_BOUNDARY_SHP}",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for extracted rasters. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Also export 3-band non-spatial JP2 for YOLO ingestion.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading boundary features for boro_cd: {args.boro_cd}")
    boundary_gdf = load_boundary_features(args.boundary_shp, args.boro_cd)

    results = []

    for _, row in boundary_gdf.iterrows():
        boro_cd = int(row["boro_cd"])
        geometry = row.geometry
        print(f"\nProcessing boro_cd {boro_cd}...")

        # Step 1: tile selection
        tile_paths = select_tiles_for_feature(
            boundary_gdf[boundary_gdf["boro_cd"] == float(boro_cd)],
            boro_cd,
            data_dir,
        )

        if not tile_paths:
            print(f"  SKIPPED: no tiles found for boro_cd {boro_cd}")
            continue

        # Step 2: mosaic and clip
        geotiff_path = mosaic_and_clip(
            tile_paths,
            geometry,
            boro_cd,
            output_dir,
        )
        results.append({"boro_cd": boro_cd, "geotiff": geotiff_path})

        # Step 3: optional YOLO export
        if args.yolo:
            yolo_path = export_for_yolo(geotiff_path, output_dir / "yolo")
            results[-1]["yolo_jp2"] = yolo_path

    # Summary
    print(f"\n{'='*60}")
    print(f"Complete. {len(results)}/{len(args.boro_cd)} features processed.")
    for r in results:
        print(f"  boro_cd {r['boro_cd']}: {r['geotiff']}")
        if "yolo_jp2" in r:
            print(f"    YOLO export: {r['yolo_jp2']}")

    if len(results) < len(args.boro_cd):
        failed = set(args.boro_cd) - {r["boro_cd"] for r in results}
        print(f"  FAILED: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()