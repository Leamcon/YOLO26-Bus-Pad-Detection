"""Entry point: python -m src.tile_selector"""

import logging
import sys
from collections import defaultdict

from .cli import parse_args
from .config import Config, load_config
from .fileops import copy_tiles, resolve_and_validate
from .spatial import find_intersecting_tiles, load_boundary, load_mosaic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def group_by_borough(cd_list: list[int], cfg: Config) -> dict[int, list[int]]:
    """Group community district numbers by borough leading digit."""
    groups: dict[int, list[int]] = defaultdict(list)
    for cd in cd_list:
        leading = cd // 100
        if leading not in cfg.borough_mapping:
            logger.error("Invalid community district number: %d (skipped)", cd)
            continue
        groups[leading].append(cd)
    return dict(groups)


def validate_year(year: int, cfg: Config) -> bool:
    """Check that the ortho directory for a given year exists."""
    ortho_dir = cfg.ortho_dir(year)
    if not ortho_dir.is_dir():
        logger.error(
            "Ortho imagery directory not found for year %d: %s", year, ortho_dir,
        )
        return False
    return True


def process_borough_group(
    boro_digit: int,
    cd_list: list[int],
    year: int,
    boundary_gdf,
    cfg: Config,
    dry_run: bool,
) -> None:
    """Process all CDs belonging to one borough for a given year."""
    mosaic_path = cfg.mosaic_shapefile_path(cd_list[0], year)
    if not mosaic_path.is_file():
        logger.error("Mosaic shapefile not found: %s", mosaic_path)
        return

    logger.info(
        "Loading mosaic for %s (%d): %s",
        cfg.borough_mapping[boro_digit], year, mosaic_path.name,
    )
    mosaic_gdf = load_mosaic(mosaic_path, cfg)
    image_dir = cfg.image_dir(cd_list[0], year)

    for cd in cd_list:
        logger.info("--- Processing CD %d, year %d ---", cd, year)
        try:
            image_values = find_intersecting_tiles(boundary_gdf, mosaic_gdf, cd, cfg)
        except ValueError as e:
            logger.error("%s (skipped)", e)
            continue

        if not image_values:
            logger.warning("CD %d (%d): No intersecting tiles found.", cd, year)
            continue

        found, missing = resolve_and_validate(image_values, image_dir, cfg)

        if missing:
            logger.warning(
                "CD %d (%d): %d expected files not found on disk.",
                cd, year, len(missing),
            )

        output_dir = cfg.output_dir(cd, year)
        count = copy_tiles(found, output_dir, dry_run=dry_run)
        action = "Would copy" if dry_run else "Copied"
        logger.info(
            "CD %d (%d): %s %d tile(s) to %s", cd, year, action, count, output_dir,
        )


def main() -> None:
    args = parse_args()
    cfg = load_config()

    single_mode = len(args.cd) == 1 and len(args.year) == 1

    # Validate all requested years upfront
    valid_years = [y for y in args.year if validate_year(y, cfg)]
    if not valid_years:
        logger.error("No valid imagery years found.")
        sys.exit(1)
    if single_mode and len(valid_years) < len(args.year):
        sys.exit(1)

    # Load boundary once
    logger.info("Loading boundary shapefile...")
    try:
        boundary_gdf = load_boundary(cfg)
    except (KeyError, ValueError) as e:
        logger.error("Failed to load boundary shapefile: %s", e)
        sys.exit(1)

    groups = group_by_borough(args.cd, cfg)

    if not groups:
        logger.error("No valid community district numbers provided.")
        sys.exit(1)

    for year in valid_years:
        logger.info("=== Year %d ===", year)
        for boro_digit, cd_list in groups.items():
            try:
                process_borough_group(
                    boro_digit, cd_list, year, boundary_gdf, cfg, dry_run=args.dry_run,
                )
            except Exception as e:
                if single_mode:
                    logger.error("Fatal: %s", e)
                    sys.exit(1)
                else:
                    logger.error(
                        "Borough %s, year %d failed: %s (skipped)",
                        cfg.borough_mapping.get(boro_digit, boro_digit), year, e,
                    )


if __name__ == "__main__":
    main()