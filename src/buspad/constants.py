"""
buspad/constants.py
===================
Shared constants for the buspad chipping module.
"""

# ── Chip geometry ─────────────────────────────────────────────────────────────
CHIP_SIZE_PX = 200      # native pixels (100 ft at 0.5 ft/px)
OUTPUT_SIZE_PX = 640    # upscaled for labeling

# ── Borough ↔ CD first-digit mapping ─────────────────────────────────────────
BOROUGH_CD_PREFIX = {
    "manhattan":     "1",
    "bronx":         "2",
    "brooklyn":      "3",
    "queens":        "4",
    "staten_island": "5",
}

VALID_BOROUGHS = tuple(BOROUGH_CD_PREFIX.keys())

# ── Path templates (relative to project working directory) ────────────────────
# Imagery: data/nyc_ortho_YYYY/boro_<borough>_spYY/
# Points:  data/points/cd_###_bus_pads/
# Output:  output/chips/YYYY/<borough>/cd_###/has_pad/  and  .../no_pad/

ORTHO_DIR_TEMPLATE = "data/nyc_ortho_{yyyy}/boro_{borough}_sp{yy}"
POINTS_ROOT = "data/points"
CD_DIR_PATTERN = "cd_{cd}_bus_pads"          # {cd} = zero-padded 3-digit code
OUTPUT_DIR_TEMPLATE = "output/chips/{yyyy}/{borough}/cd_{cd}"

TILE_INDEX_FILENAME = ".tile_index.json"

# ── CRS configuration ────────────────────────────────────────────────────────
# Both 2263 and 6539 are NAD83 NY Long Island (ft); 2263 is the original
# datum, 6539 is the 2011 realization.  Sub-pixel offset at 0.5 ft/px —
# safe to treat as equivalent for chipping.
ACCEPTED_TILE_EPSG = {2263, 6539}

# Canonical target CRS for all point data.  Points in other CRS (e.g.,
# WGS84 / 4326) are reprojected to this on load.
TARGET_EPSG = 2263

# ── DBF field expectations ────────────────────────────────────────────────────
STOP_ID_FIELD_INDEX = 10
BUS_PAD_FIELD_INDEX = 11
BUS_PAD_YES_VALUES = {"y", "yes"}