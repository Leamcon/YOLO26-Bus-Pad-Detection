"""Command-line interface for the georeferencing pipeline."""

from __future__ import annotations

import argparse
import logging
import sys

from buspad.config import add_root_arg, resolve_workspace
from buspad.georef.defs import (
    build_chips_dir,
    build_georef_dir,
    build_output_stem,
    build_predictions_dir,
)
from buspad.georef.loaders import load_geotransforms, load_offsets
from buspad.georef.processing import process_predictions
from buspad.georef.writers import SUPPORTED_FORMATS, write_detections

logger = logging.getLogger(__name__)

EPILOG = """\
path conventions
────────────────
  All paths are relative to the resolved workspace root.

  chip sidecar data (produced by buspad-chip):
    data/chips/{boro|cd}/{name}/{year}/
    ├── offsets/              per-tile chip offset CSVs
    └── geotransforms.json    affine transforms and CRS per source tile

  prediction CSVs (produced by buspad-infer):
    output/detections/{boro|cd}/{name}/{year}/predictions/
    └── {tile_stem}_predictions.csv

  georef output (produced by this command):
    output/detections/{boro|cd}/{name}/{year}/georef/
    └── {mode}_{name}_{year}.{shp|gpkg}

examples
────────
  buspad-georef --year 2024 --boro bronx
    chips  -> data/chips/boro/bronx/2024/
    preds  -> output/detections/boro/bronx/2024/predictions/
    output -> output/detections/boro/bronx/2024/georef/boro_bronx_2024.shp

  buspad-georef --year 2024 --cd 108 --format gpkg
    chips  -> data/chips/cd/108/2024/
    preds  -> output/detections/cd/108/2024/predictions/
    output -> output/detections/cd/108/2024/georef/cd_108_2024.gpkg

  buspad-georef --year 2024 --boro manhattan --root /tmp/workspace
    Uses /tmp/workspace instead of the configured workspace.
"""


def main() -> None:
    """Entry point for ``buspad-georef``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        prog="buspad-georef",
        description=(
            "Georeference YOLO detections to EPSG:6539 map coordinates. "
            "Reads chip sidecar data (offsets, geotransforms) and prediction "
            "CSVs produced by buspad-chip and buspad-infer, then writes a "
            "georeferenced feature class."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Imagery vintage year (e.g. 2024).",
    )

    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--boro",
        type=str,
        default=None,
        help="Borough name (case-insensitive). Selects borough-mode paths.",
    )
    scope.add_argument(
        "--cd",
        type=int,
        default=None,
        help="Community district number. Selects CD-mode paths.",
    )

    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="shp",
        dest="out_fmt",
        help="Output spatial format (default: shp).",
    )

    add_root_arg(parser)
    args = parser.parse_args()

    # -- workspace and paths ------------------------------------------------
    workspace = resolve_workspace(args.root)

    chips_dir = build_chips_dir(workspace, args.year, boro=args.boro, cd=args.cd)
    pred_dir = build_predictions_dir(workspace, args.year, boro=args.boro, cd=args.cd)
    georef_dir = build_georef_dir(workspace, args.year, boro=args.boro, cd=args.cd)
    out_stem = build_output_stem(args.year, boro=args.boro, cd=args.cd)

    gt_path = chips_dir / "geotransforms.json"
    offsets_dir = chips_dir / "offsets"

    # -- validate inputs ----------------------------------------------------
    for p, label in [
        (gt_path, "geotransforms.json"),
        (offsets_dir, "offsets/"),
        (pred_dir, "predictions/"),
    ]:
        if not p.exists():
            logger.error("%s not found at %s", label, p)
            sys.exit(1)

    # -- load ---------------------------------------------------------------
    logger.info("Loading geotransforms: %s", gt_path)
    transforms = load_geotransforms(gt_path)
    logger.info("  %d tiles", len(transforms))

    logger.info("Loading offsets: %s", offsets_dir)
    offsets = load_offsets(offsets_dir)
    logger.info("  %d tiles", len(offsets))

    # -- process ------------------------------------------------------------
    logger.info("Processing predictions: %s", pred_dir)
    features = process_predictions(pred_dir, offsets, transforms)
    logger.info("  %d detections georeferenced", len(features))

    if not features:
        logger.warning("No detections to write. Exiting.")
        sys.exit(0)

    # -- write --------------------------------------------------------------
    write_detections(features, georef_dir, stem=out_stem, fmt=args.out_fmt)