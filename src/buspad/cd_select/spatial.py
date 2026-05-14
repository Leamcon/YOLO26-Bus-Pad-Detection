"""Spatial operations: load shapefiles, reproject, intersect."""

import logging
from pathlib import Path

import geopandas as gpd

from . import defs

logger = logging.getLogger(__name__)


def load_boundary(boundary_path: Path) -> gpd.GeoDataFrame:
    """Load boundary shapefile, cast boro_cd to int, reproject if needed."""
    gdf = gpd.read_file(boundary_path)

    if defs.BOUNDARY_CD_FIELD not in gdf.columns:
        raise KeyError(
            f"Field '{defs.BOUNDARY_CD_FIELD}' not found in boundary shapefile."
        )

    gdf[defs.BOUNDARY_CD_FIELD] = (
        gdf[defs.BOUNDARY_CD_FIELD].astype(float).astype(int)
    )

    if gdf.crs is None:
        raise ValueError("Boundary shapefile has no CRS defined.")
    if gdf.crs.to_epsg() != defs.TARGET_CRS:
        logger.info(
            "Reprojecting boundary from EPSG:%s to EPSG:%s",
            gdf.crs.to_epsg(), defs.TARGET_CRS,
        )
        gdf = gdf.to_crs(epsg=defs.TARGET_CRS)

    return gdf


def load_mosaic(path: Path) -> gpd.GeoDataFrame:
    """Load mosaic shapefile, reproject if needed."""
    gdf = gpd.read_file(path)

    if defs.MOSAIC_IMAGE_FIELD not in gdf.columns:
        raise KeyError(
            f"Field '{defs.MOSAIC_IMAGE_FIELD}' not found in mosaic shapefile: {path}"
        )

    gdf[defs.MOSAIC_IMAGE_FIELD] = gdf[defs.MOSAIC_IMAGE_FIELD].astype(str)

    if gdf.crs is None:
        raise ValueError(f"Mosaic shapefile has no CRS defined: {path}")
    if gdf.crs.to_epsg() != defs.TARGET_CRS:
        logger.info(
            "Reprojecting mosaic %s from EPSG:%s to EPSG:%s",
            path.name, gdf.crs.to_epsg(), defs.TARGET_CRS,
        )
        gdf = gdf.to_crs(epsg=defs.TARGET_CRS)

    return gdf


def find_intersecting_tiles(
    boundary_gdf: gpd.GeoDataFrame,
    mosaic_gdf: gpd.GeoDataFrame,
    cd: int,
) -> list[str]:
    """Return Image field values for mosaic tiles intersecting a CD.

    Parameters
    ----------
    boundary_gdf : GeoDataFrame
        Full boundary dataset (boro_cd already cast to int).
    mosaic_gdf : GeoDataFrame
        Mosaic tile index for the relevant borough.
    cd : int
        Community district number (e.g. 101).

    Returns
    -------
    list[str]
        Image field values of intersecting tiles.
    """
    district = boundary_gdf[boundary_gdf[defs.BOUNDARY_CD_FIELD] == cd]

    if district.empty:
        raise ValueError(
            f"Community district {cd} not found in boundary shapefile."
        )

    joined = gpd.sjoin(
        mosaic_gdf,
        district,
        how="inner",
        predicate="intersects",
    )

    image_values = joined[defs.MOSAIC_IMAGE_FIELD].unique().tolist()
    logger.info("CD %d: %d intersecting tiles found.", cd, len(image_values))

    return image_values