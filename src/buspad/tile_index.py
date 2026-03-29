"""
buspad/tile_index.py
====================
Spatial index of JP2 tile bounds with JSON caching.

The index is built once per imagery directory and cached as a JSON sidecar.
Since imagery is immutable post-download, the cache is trusted if it exists.
Use --rebuild-index to force a rebuild.
"""

import json
import os
import tempfile
from pathlib import Path

import rasterio

from .constants import TILE_INDEX_FILENAME, ACCEPTED_EPSG


def _cache_path(ortho_dir: Path) -> Path:
    return ortho_dir / TILE_INDEX_FILENAME


def build_index(ortho_dir: Path) -> list[dict]:
    """Scan all JP2 files in ortho_dir and return a list of tile metadata.

    Each entry: {"path": str, "left": float, "bottom": float,
                 "right": float, "top": float, "width": int, "height": int}

    Asserts that each tile's CRS is in the accepted set.
    """
    index = []
    jp2_files = sorted(f for f in os.listdir(ortho_dir) if f.endswith(".jp2"))

    if not jp2_files:
        raise FileNotFoundError(f"No JP2 files found in {ortho_dir}")

    for fname in jp2_files:
        fpath = ortho_dir / fname
        with rasterio.open(fpath) as src:
            epsg = src.crs.to_epsg() if src.crs else None
            if epsg not in ACCEPTED_EPSG:
                raise ValueError(
                    f"Tile {fname} has EPSG:{epsg}; "
                    f"expected one of {ACCEPTED_EPSG}."
                )
            b = src.bounds
            index.append({
                "path": str(fpath),
                "left": b.left,
                "bottom": b.bottom,
                "right": b.right,
                "top": b.top,
                "width": src.width,
                "height": src.height,
            })

    return index


def save_index(index: list[dict], ortho_dir: Path) -> None:
    """Write tile index to JSON sidecar with atomic rename."""
    cache = _cache_path(ortho_dir)
    fd, tmp = tempfile.mkstemp(dir=ortho_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(index, f, indent=2)
        os.replace(tmp, cache)
    except BaseException:
        os.unlink(tmp)
        raise


def load_index(ortho_dir: Path) -> list[dict] | None:
    """Load cached tile index if it exists.  Returns None if absent."""
    cache = _cache_path(ortho_dir)
    if not cache.is_file():
        return None
    with open(cache) as f:
        return json.load(f)


def get_or_build_index(
    ortho_dir: Path,
    rebuild: bool = False,
) -> list[dict]:
    """Return tile index, building and caching if necessary.

    Args:
        ortho_dir: path to borough imagery directory
        rebuild: if True, ignore existing cache and rebuild
    """
    if not rebuild:
        cached = load_index(ortho_dir)
        if cached is not None:
            return cached

    index = build_index(ortho_dir)
    save_index(index, ortho_dir)
    return index


def find_tile_for_point(x: float, y: float, index: list[dict]) -> dict | None:
    """Return the tile entry containing the point, or None."""
    for tile in index:
        if (tile["left"] <= x < tile["right"]
                and tile["bottom"] <= y < tile["top"]):
            return tile
    return None