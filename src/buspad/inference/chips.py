"""Chip file discovery and grouping by parent tile."""

import sys
from collections import defaultdict
from pathlib import Path

CHIP_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def group_chips_by_tile(chip_dir: Path) -> dict[str, list[Path]]:
    """Group chip files by parent tile stem.

    Expects filenames like: {tile_stem}_r{row}_c{col}.{ext}
    Groups by everything before the last _rXXX_cXXX segment.
    """
    groups: dict[str, list[Path]] = defaultdict(list)

    for chip_path in sorted(chip_dir.iterdir()):
        if chip_path.suffix.lower() not in CHIP_EXTENSIONS:
            continue

        tile_stem = _parse_tile_stem(chip_path)
        if tile_stem is not None:
            groups[tile_stem].append(chip_path)
        else:
            print(
                f"WARNING: could not parse tile stem from "
                f"{chip_path.name}, skipping.",
                file=sys.stderr,
            )

    return dict(groups)


def _parse_tile_stem(chip_path: Path) -> str | None:
    """Extract the tile stem from a chip filename.

    Filenames follow the pattern {tile_stem}_r{row}_c{col}.{ext}.
    Returns the tile_stem portion or None if the pattern doesn't match.
    """
    name = chip_path.stem
    parts = name.rsplit("_c", 1)
    if len(parts) == 2:
        prefix = parts[0].rsplit("_r", 1)
        if len(prefix) == 2:
            return prefix[0]
    return None