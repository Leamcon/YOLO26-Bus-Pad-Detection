"""CLI for buspad-cd-select: select tiles by community district."""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

from buspad.config import add_root_arg, resolve_workspace

from . import defs
from .fileops import copy_tiles, resolve_and_validate
from .spatial import find_intersecting_tiles, load_boundary, load_mosaic

logger = logging.getLogger(__name__)

EPILOG = """\
workflow:
  1. Reads workspace path from ~/.buspad/config.toml (set by buspad-init).
     Use --root to override for a one-off run.
  2. Loads community district boundaries from the workspace:
       <workspace>/data/boundaries/community_districts_20260306/
  3. For each --year and --cd combination, locates tiles in the source
     ortho-imagery directory:
       <workspace>/data/imagery/nyc_ortho_<YEAR>/
  4. Copies matched tiles to:
       <workspace>/data/imagery/cd/<YEAR>/<CD>/

examples:
  buspad-cd-select --cd 108 --year 2024
  buspad-cd-select --cd 101 201 301 --year 2022 2024
  buspad-cd-select --cd 108 --year 2024 --dry-run
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buspad-cd-select",
        description=(
            "Select ortho-imagery tiles that intersect one or more "
            "NYC community districts."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--cd",
        type=int,
        nargs="+",
        required=True,
        help=(
            "Community district number(s). Leading digit is borough: "
            "1=Manhattan, 2=Bronx, 3=Brooklyn, 4=Queens, 5=Staten Island. "
            "e.g. 108 for Manhattan CD 8, 301 for Brooklyn CD 1."
        ),
    )
    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        required=True,
        help=(
            "Imagery year(s) corresponding to nyc_ortho_<YEAR> directories "
            "in the workspace. e.g. 2024, or 2022 2024 for multi-year batch."
        ),
    )
    add_root_arg(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matched tiles without copying files.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


# ---------------------------------------------------------------------------
# Orchestration helpers
# ---------------------------------------------------------------------------

def group_by_borough(cd_list: list[int]) -> dict[int, list[int]]:
    """Group community district numbers by borough leading digit."""
    groups: dict[int, list[int]] = defaultdict(list)
    for cd in cd_list:
        leading = cd // 100
        if leading not in defs.BOROUGH_MAPPING:
            logger.error("Invalid community district number: %d (skipped)", cd)
            continue
        groups[leading].append(cd)
    return dict(groups)


def validate_year(workspace: Path, year: int) -> bool:
    """Check that the ortho directory for a given year exists."""
    ortho = defs.ortho_dir(workspace, year)
    if not ortho.is_dir():
        logger.error(
            "Ortho imagery directory not found for year %d: %s", year, ortho,
        )
        return False
    return True


def process_borough_group(
    workspace: Path,
    boro_digit: int,
    cd_list: list[int],
    year: int,
    boundary_gdf,
    dry_run: bool,
) -> None:
    """Process all CDs belonging to one borough for a given year."""
    mosaic_path = defs.mosaic_shapefile_path(workspace, cd_list[0], year)
    if not mosaic_path.is_file():
        logger.error("Mosaic shapefile not found: %s", mosaic_path)
        return

    logger.info(
        "Loading mosaic for %s (%d): %s",
        defs.BOROUGH_MAPPING[boro_digit], year, mosaic_path.name,
    )
    mosaic_gdf = load_mosaic(mosaic_path)
    img_dir = defs.image_dir(workspace, cd_list[0], year)

    for cd in cd_list:
        logger.info("--- Processing CD %d, year %d ---", cd, year)
        try:
            image_values = find_intersecting_tiles(
                boundary_gdf, mosaic_gdf, cd,
            )
        except ValueError as e:
            logger.error("%s (skipped)", e)
            continue

        if not image_values:
            logger.warning("CD %d (%d): No intersecting tiles found.", cd, year)
            continue

        found, missing = resolve_and_validate(image_values, img_dir)

        if missing:
            logger.warning(
                "CD %d (%d): %d expected files not found on disk.",
                cd, year, len(missing),
            )

        out = defs.output_dir(workspace, cd, year)
        count = copy_tiles(found, out, dry_run=dry_run)
        action = "Would copy" if dry_run else "Copied"
        logger.info(
            "CD %d (%d): %s %d tile(s) to %s", cd, year, action, count, out,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = parse_args(argv)
    workspace = resolve_workspace(args.root)

    single_mode = len(args.cd) == 1 and len(args.year) == 1

    # Validate all requested years upfront
    valid_years = [y for y in args.year if validate_year(workspace, y)]
    if not valid_years:
        logger.error("No valid imagery years found.")
        sys.exit(1)
    if single_mode and len(valid_years) < len(args.year):
        sys.exit(1)

    # Load boundary once
    logger.info("Loading boundary shapefile...")
    boundary_path = defs.boundary_shapefile(workspace)
    try:
        boundary_gdf = load_boundary(boundary_path)
    except (KeyError, ValueError) as e:
        logger.error("Failed to load boundary shapefile: %s", e)
        sys.exit(1)

    groups = group_by_borough(args.cd)

    if not groups:
        logger.error("No valid community district numbers provided.")
        sys.exit(1)

    for year in valid_years:
        logger.info("=== Year %d ===", year)
        for boro_digit, cd_list in groups.items():
            try:
                process_borough_group(
                    workspace, boro_digit, cd_list, year,
                    boundary_gdf, dry_run=args.dry_run,
                )
            except Exception as e:
                if single_mode:
                    logger.error("Fatal: %s", e)
                    sys.exit(1)
                else:
                    logger.error(
                        "Borough %s, year %d failed: %s (skipped)",
                        defs.BOROUGH_MAPPING.get(boro_digit, str(boro_digit)),
                        year, e,
                    )