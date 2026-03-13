"""
Tile selection: boundary feature → mosaic index spatial join → tile file list.
"""

import geopandas as gpd
from pathlib import Path
from scripts.ortho_extract.config import CRS_RASTER, CRS_MOSAIC, CRS_BOUNDARY, BORO_DIR_MAP


def load_boundary_features(boundary_shp: str, boro_cd_list: list[int]) -> gpd.GeoDataFrame:
    """Load boundary shapefile and filter to requested boro_cd values.
    Reprojects from WGS84 (4326) to raster CRS (6539).
    """
    gdf = gpd.read_file(boundary_shp)

    if gdf.crs.to_epsg() != CRS_BOUNDARY:
        print(f"  WARNING: boundary CRS is {gdf.crs}, expected EPSG:{CRS_BOUNDARY}")

    # boro_cd is typed as double in the shapefile
    gdf_filtered = gdf[gdf["boro_cd"].isin([float(b) for b in boro_cd_list])].copy()

    if gdf_filtered.empty:
        raise ValueError(
            f"No features found for boro_cd values: {boro_cd_list}. "
            f"Available values: {sorted(gdf['boro_cd'].unique())}"
        )

    missing = set(boro_cd_list) - set(int(v) for v in gdf_filtered["boro_cd"].unique())
    if missing:
        print(f"  WARNING: boro_cd values not found in boundary shapefile: {missing}")

    # Reproject to raster CRS
    gdf_filtered = gdf_filtered.to_crs(epsg=CRS_RASTER)
    return gdf_filtered


def load_mosaic_index(mosaic_shp: str) -> gpd.GeoDataFrame:
    """Load mosaic shapefile and reproject from 2263 to raster CRS (6539)."""
    gdf = gpd.read_file(mosaic_shp)

    if gdf.crs.to_epsg() != CRS_MOSAIC:
        print(f"  WARNING: mosaic CRS is {gdf.crs}, expected EPSG:{CRS_MOSAIC}")

    gdf = gdf.to_crs(epsg=CRS_RASTER)
    return gdf


def find_intersecting_tiles(
    boundary_feature: gpd.GeoDataFrame,
    mosaic_index: gpd.GeoDataFrame,
    tile_dir: Path,
) -> list[Path]:
    """Spatial join to find tiles intersecting a single boundary feature.
    Returns list of resolved tile file paths.
    """
    joined = gpd.sjoin(
        mosaic_index,
        boundary_feature,
        how="inner",
        predicate="intersects",
    )

    if joined.empty:
        return []

    tile_ids = joined["Image"].unique()
    tile_paths = []

    for tid in tile_ids:
        fname = f"{tid}.jp2" if not tid.endswith(".jp2") else tid
        fpath = tile_dir / fname
        if fpath.exists():
            tile_paths.append(fpath)
        else:
            print(f"  WARNING: tile file not found: {fpath}")

    return tile_paths


def get_boro_dir(boro_cd: int) -> str:
    """Resolve boro_cd to its borough directory name."""
    boro_key = int(str(boro_cd)[0])
    if boro_key not in BORO_DIR_MAP:
        raise ValueError(
            f"Cannot resolve boro_cd {boro_cd}: first digit {boro_key} "
            f"not in mapping {list(BORO_DIR_MAP.keys())}"
        )
    return BORO_DIR_MAP[boro_key]


def select_tiles_for_feature(
    boundary_feature: gpd.GeoDataFrame,
    boro_cd: int,
    data_dir: Path,
) -> list[Path]:
    """Full tile selection pipeline for a single boundary feature.
    Loads the appropriate mosaic index and finds intersecting tiles.
    """
    boro_dirname = get_boro_dir(boro_cd)
    tile_dir = data_dir / boro_dirname

    if not tile_dir.exists():
        raise FileNotFoundError(f"Tile directory not found: {tile_dir}")

    # Locate mosaic shapefile — expect one .shp in the tile directory
    mosaic_shps = list(tile_dir.glob("*.shp"))
    if len(mosaic_shps) == 0:
        raise FileNotFoundError(f"No mosaic shapefile found in {tile_dir}")
    if len(mosaic_shps) > 1:
        print(f"  WARNING: multiple shapefiles in {tile_dir}, using {mosaic_shps[0].name}")

    mosaic_index = load_mosaic_index(str(mosaic_shps[0]))
    tile_paths = find_intersecting_tiles(boundary_feature, mosaic_index, tile_dir)

    print(f"  boro_cd {boro_cd}: {len(tile_paths)} tiles selected from {boro_dirname}")
    return tile_paths