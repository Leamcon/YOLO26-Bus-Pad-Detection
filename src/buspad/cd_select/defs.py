"""Constants and path resolution for cd_select.

Replaces the old config.py + config.toml pair. All path resolution is
relative to the workspace root provided by buspad.config.
"""

from pathlib import Path

# Borough mapping: leading digit of boro_cd → directory name component
BOROUGH_MAPPING: dict[int, str] = {
    1: "manhattan",
    2: "bronx",
    3: "brooklyn",
    4: "queens",
    5: "staten_island",
}

# Spatial reference
TARGET_CRS = 2263  # EPSG:2263 — NY State Plane Long Island (ft)

# Shapefile field names
BOUNDARY_CD_FIELD = "boro_cd"
MOSAIC_IMAGE_FIELD = "Image"

# File patterns
IMAGE_EXTENSION = ".jp2"
ORTHO_DIR_PATTERN = "nyc_ortho_{year}"
BORO_DIR_PATTERN = "boro_{boro_name}_sp{year_short}"

# Mosaic shapefile naming varies by imagery vintage.
# Default applies to all years unless a year-specific override exists.
MOSAIC_SHAPEFILE_DEFAULT = "nyc_sp_4bd_06in_index{year_short}.shp"
MOSAIC_SHAPEFILE_OVERRIDES: dict[int, str] = {
    2024: "{year_short}_b_{boro_name}_l06_4bd.shp",
}

# Boundary shapefile path relative to workspace root
BOUNDARY_SHAPEFILE_REL = Path(
    "data/boundaries/community_districts_20260306"
    "/geo_export_e1c55842-b6cf-48de-89dd-fb84825c0f0d.shp"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def boro_name(boro_cd: int) -> str:
    """Derive borough name from a community district number."""
    leading = boro_cd // 100
    if leading not in BOROUGH_MAPPING:
        raise ValueError(
            f"Invalid leading digit {leading} from CD {boro_cd}. "
            f"Valid: {list(BOROUGH_MAPPING.keys())}"
        )
    return BOROUGH_MAPPING[leading]


def year_short(year: int) -> str:
    """Two-digit year string for path substitution."""
    return str(year % 100).zfill(2)


# ---------------------------------------------------------------------------
# Path resolution — all relative to workspace root
# ---------------------------------------------------------------------------

def boundary_shapefile(workspace: Path) -> Path:
    return workspace / BOUNDARY_SHAPEFILE_REL


def ortho_dir(workspace: Path, year: int) -> Path:
    dirname = ORTHO_DIR_PATTERN.format(year=year)
    return workspace / "data" / "imagery" / dirname


def boro_dir(workspace: Path, boro_cd: int, year: int) -> Path:
    name = boro_name(boro_cd)
    ys = year_short(year)
    dirname = BORO_DIR_PATTERN.format(boro_name=name, year_short=ys)
    return ortho_dir(workspace, year) / dirname


def mosaic_shapefile_pattern(year: int) -> str:
    return MOSAIC_SHAPEFILE_OVERRIDES.get(year, MOSAIC_SHAPEFILE_DEFAULT)


def mosaic_shapefile_path(workspace: Path, boro_cd: int, year: int) -> Path:
    name = boro_name(boro_cd)
    ys = year_short(year)
    pattern = mosaic_shapefile_pattern(year)
    filename = pattern.format(boro_name=name, year_short=ys)
    return boro_dir(workspace, boro_cd, year) / filename


def image_dir(workspace: Path, boro_cd: int, year: int) -> Path:
    """Directory containing tile images for a borough/year."""
    return boro_dir(workspace, boro_cd, year)


def output_dir(workspace: Path, cd: int, year: int) -> Path:
    """Output directory for selected tiles: data/imagery/cd/<year>/<cd>/."""
    return workspace / "data" / "imagery" / "cd" / str(year) / str(cd)