"""
Configuration for orthoimagery extraction pipeline.
"""

# -- CRS constants --
CRS_RASTER = 6539       # NAD83(2011) / NY Long Island (ftUS) — native tile CRS
CRS_MOSAIC = 2263       # NAD83 / NY Long Island (ftUS) — mosaic shapefile CRS
CRS_BOUNDARY = 4326     # WGS84 — boundary shapefile CRS

# -- Borough directory mapping --
# First digit of boro_cd (as int) maps to tile directory name
BORO_DIR_MAP = {
    1: "boro_manhattan_sp24",
    2: "boro_bronx_sp24",
    3: "boro_brooklyn_sp24",
    4: "boro_queens_sp24",
    5: "boro_staten_island_sp24",
}

# -- Default paths (relative to project root, not script location) --
DEFAULT_DATA_DIR = "data/nyc_ortho_2024"
DEFAULT_BOUNDARY_SHP = "data/boundaries/community_districts_20260306/geo_export_e1c55842-b6cf-48de-89dd-fb84825c0f0d.shp"
DEFAULT_OUTPUT_DIR = "output/ortho_extracts"

# -- Output settings --
GEOTIFF_COMPRESS = "DEFLATE"
GEOTIFF_TILED = True
GEOTIFF_BLOCKSIZE = 512