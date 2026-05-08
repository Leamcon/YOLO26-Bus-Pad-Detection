"""Command-line interface for the georeferencing pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from buspad_georef.loaders import load_geotransforms, load_offsets
from buspad_georef.processing import process_predictions
from buspad_georef.writers import SUPPORTED_FORMATS, write_detections

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for ``python -m buspad_georef``."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        prog="buspad_georef",
        description="Stage 3: Georeference YOLO detections to a spatial feature class.",
    )
    parser.add_argument(
        "stage1_dir",
        help="Stage 1 output directory (contains offsets/ and geotransforms.json).",
    )
    parser.add_argument(
        "predictions_dir",
        nargs="?",
        default=None,
        help="Directory of prediction CSVs (default: stage1_dir/predictions/).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for the feature class bundle (default: stage1_dir/detections/).",
    )
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="shp",
        dest="out_fmt",
        help="Output format (default: shp).",
    )
    args = parser.parse_args()

    stage1_dir = Path(args.stage1_dir)
    pred_dir = (
        Path(args.predictions_dir) if args.predictions_dir else stage1_dir / "predictions"
    )
    output_dir = Path(args.output) if args.output else stage1_dir / "detections"

    # Validate inputs
    gt_path = stage1_dir / "geotransforms.json"
    offsets_dir = stage1_dir / "offsets"

    for p, label in [
        (gt_path, "geotransforms.json"),
        (offsets_dir, "offsets/"),
        (pred_dir, "predictions/"),
    ]:
        if not p.exists():
            logger.error("%s not found at %s", label, p)
            sys.exit(1)

    logger.info("Loading geotransforms: %s", gt_path)
    transforms = load_geotransforms(gt_path)
    logger.info("  %d tiles", len(transforms))

    logger.info("Loading offsets: %s", offsets_dir)
    offsets = load_offsets(offsets_dir)
    logger.info("  %d tiles", len(offsets))

    logger.info("Processing predictions: %s", pred_dir)
    features = process_predictions(pred_dir, offsets, transforms)
    logger.info("  %d detections georeferenced", len(features))

    if not features:
        logger.warning("No detections to write. Exiting.")
        sys.exit(0)

    write_detections(features, output_dir, fmt=args.out_fmt)
