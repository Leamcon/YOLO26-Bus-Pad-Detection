"""Spatial operations: load shapefiles, reproject, intersect."""

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)


def load_boundary(cfg: Config) -> gpd.GeoDataFrame:
    """Load boundary shapefile, cast boro_cd to int, reproject if needed."""
    gdf = gpd.read_file(cfg.boundary_shapefile)

    cd_field = cfg.boundary_cd_field
    if cd_field not in gdf.columns:
        raise KeyError(f"Field '{cd_field}' not found in boundary shapefile.")

    gdf[cd_field] = gdf[cd_field].astype(float).astype(int)

    if gdf.crs is None:
        raise ValueError("Boundary shapefile has no CRS defined.")
    if gdf.crs.to_epsg() != cfg.target_crs:
        logger.info(
            "Reprojecting boundary from EPSG:%s to EPSG:%s",
            gdf.crs.to_epsg(), cfg.target_crs,
        )
        gdf = gdf.to_crs(epsg=cfg.target_crs)

    return gdf


def load_mosaic(path: Path, cfg: Config) -> gpd.GeoDataFrame:
    """Load mosaic shapefile, reproject if needed."""
    gdf = gpd.read_file(path)

    if cfg.mosaic_image_field not in gdf.columns:
        raise KeyError(
            f"Field '{cfg.mosaic_image_field}' not found in mosaic shapefile: {path}"
        )

    # Ensure Image field is string type
    gdf[cfg.mosaic_image_field] = gdf[cfg.mosaic_image_field].astype(str)

    if gdf.crs is None:
        raise ValueError(f"Mosaic shapefile has no CRS defined: {path}")
    if gdf.crs.to_epsg() != cfg.target_crs:
        logger.info(
            "Reprojecting mosaic %s from EPSG:%s to EPSG:%s",
            path.name, gdf.crs.to_epsg(), cfg.target_crs,
        )
        gdf = gdf.to_crs(epsg=cfg.target_crs)

    return gdf


def find_intersecting_tiles(
    boundary_gdf: gpd.GeoDataFrame,
    mosaic_gdf: gpd.GeoDataFrame,
    cd: int,
    cfg: Config,
) -> list[str]:
    """Return list of Image field values for mosaic tiles intersecting a CD.

    Parameters
    ----------
    boundary_gdf : GeoDataFrame
        Full boundary dataset (boro_cd already cast to int).
    mosaic_gdf : GeoDataFrame
        Mosaic tile index for the relevant borough.
    cd : int
        Community district number (e.g. 101).
    cfg : Config
        Application configuration.

    Returns
    -------
    list[str]
        Image field values of intersecting tiles.
    """
    district = boundary_gdf[boundary_gdf[cfg.boundary_cd_field] == cd]

    if district.empty:
        raise ValueError(f"Community district {cd} not found in boundary shapefile.")

    joined = gpd.sjoin(
        mosaic_gdf,
        district,
        how="inner",
        predicate="intersects",
    )

    image_values = joined[cfg.mosaic_image_field].unique().tolist()
    logger.info("CD %d: %d intersecting tiles found.", cd, len(image_values))

    return image_values