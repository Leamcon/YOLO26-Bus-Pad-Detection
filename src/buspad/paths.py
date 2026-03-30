"""
buspad/paths.py
===============
Path resolution and community district discovery.

All paths are anchored to the project root, resolved from this module's
location (src/buspad/ → project root is two levels up).  A sanity check
confirms the data/ directory exists at the resolved root.
"""

import os
import re
import glob
from pathlib import Path

from .constants import (
    BOROUGH_CD_PREFIX,
    ORTHO_DIR_TEMPLATE,
    POINTS_ROOT,
    CD_DIR_PATTERN,
    OUTPUT_DIR_TEMPLATE,
    VALID_BOROUGHS,
)


def _find_project_root() -> Path:
    """Resolve project root from module location.

    Expects: <root>/src/buspad/paths.py → root is two levels up from
    this file's parent.  Validates by checking for <root>/data/.
    """
    module_dir = Path(__file__).resolve().parent   # src/buspad/
    root = module_dir.parent.parent                # project root
    data_dir = root / "data"
    if not data_dir.is_dir():
        raise RuntimeError(
            f"Cannot locate project root. Expected 'data/' at {root}.\n"
            f"Module is at {module_dir}. Is the project structure intact?"
        )
    return root


PROJECT_ROOT = _find_project_root()


def _rooted(rel: str | Path) -> Path:
    """Resolve a project-relative path against PROJECT_ROOT."""
    return PROJECT_ROOT / rel


def resolve_ortho_dir(borough: str, year: int) -> Path:
    """Return the imagery directory for a borough/year pair.

    Raises FileNotFoundError if the directory does not exist.
    """
    yy = str(year)[-2:]
    rel = ORTHO_DIR_TEMPLATE.format(yyyy=year, borough=borough, yy=yy)
    p = _rooted(rel)
    if not p.is_dir():
        raise FileNotFoundError(f"Imagery directory not found: {p}")
    return p


def discover_ortho_years() -> dict[str, list[int]]:
    """Scan data/ for available imagery directories.

    Returns {borough: [year, ...]} for all boroughs with imagery on disk.
    """
    ortho_root = _rooted("data")
    result = {}
    for entry in sorted(ortho_root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("nyc_ortho_"):
            continue
        match = re.match(r"nyc_ortho_(\d{4})$", entry.name)
        if not match:
            continue
        year = int(match.group(1))
        # scan for borough subdirs within this year
        for sub in sorted(entry.iterdir()):
            if not sub.is_dir() or not sub.name.startswith("boro_"):
                continue
            boro_match = re.match(r"boro_(.+)_sp\d{2}$", sub.name)
            if boro_match:
                borough = boro_match.group(1)
                result.setdefault(borough, []).append(year)
    return result


def discover_cds(borough: str | None = None) -> list[str]:
    """Return sorted list of 3-digit CD codes available on disk.

    If borough is given, filter to CDs whose first digit matches.
    """
    pattern = str(_rooted(os.path.join(POINTS_ROOT, "cd_*_bus_pads")))
    matches = glob.glob(pattern)
    codes = []
    for m in matches:
        dirname = os.path.basename(m)
        match = re.match(r"cd_(\d{3})_bus_pads$", dirname)
        if match:
            codes.append(match.group(1))

    if borough is not None:
        prefix = BOROUGH_CD_PREFIX[borough]
        codes = [c for c in codes if c[0] == prefix]

    return sorted(codes)


def resolve_cd_dir(cd: str) -> Path:
    """Return the point data directory for a community district.

    Raises FileNotFoundError if the directory does not exist.
    """
    dirname = CD_DIR_PATTERN.format(cd=cd)
    p = _rooted(POINTS_ROOT) / dirname
    if not p.is_dir():
        raise FileNotFoundError(f"Point directory not found: {p}")
    return p


def resolve_cd_files(cd: str) -> tuple[Path, Path, Path | None]:
    """Return (shp_path, dbf_path, prj_path) for a community district.

    Expects filenames to follow the containing directory name.
    prj_path is None if no .prj file exists (CRS will be assumed).
    Raises FileNotFoundError if .shp or .dbf is missing.
    """
    cd_dir = resolve_cd_dir(cd)
    basename = CD_DIR_PATTERN.format(cd=cd)
    shp = cd_dir / f"{basename}.shp"
    dbf = cd_dir / f"{basename}.dbf"
    prj = cd_dir / f"{basename}.prj"
    for f in (shp, dbf):
        if not f.is_file():
            raise FileNotFoundError(f"Expected file not found: {f}")
    return shp, dbf, prj if prj.is_file() else None


def resolve_output_dir(borough: str, year: int, cd: str) -> Path:
    """Return the output directory for a borough/year/cd combination.

    Does not create the directory — caller decides based on dry-run flag.
    """
    rel = OUTPUT_DIR_TEMPLATE.format(yyyy=year, borough=borough, cd=cd)
    return _rooted(rel)


def validate_cd_borough(cd: str, borough: str) -> None:
    """Raise ValueError if the CD code does not belong to the borough."""
    expected_prefix = BOROUGH_CD_PREFIX[borough]
    actual_prefix = cd[0]
    if actual_prefix != expected_prefix:
        reverse = {v: k for k, v in BOROUGH_CD_PREFIX.items()}
        actual_borough = reverse.get(actual_prefix, "unknown")
        available = discover_cds(borough)
        avail_str = ", ".join(available) if available else "none found"
        raise ValueError(
            f"CD {cd} belongs to {actual_borough} ({actual_prefix}xx), "
            f"not {borough} ({expected_prefix}xx).\n"
            f"Available {borough} CDs on disk: {avail_str}"
        )