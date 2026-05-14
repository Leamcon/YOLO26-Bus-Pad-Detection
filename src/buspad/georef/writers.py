"""Output writers for georeferenced detections."""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd

from buspad_georef.defs import Detection

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS: dict[str, str] = {
    "shp": "ESRI Shapefile",
    "gpkg": "GPKG",
}


def _detections_to_geodataframe(
    features: list[Detection], crs: str = "EPSG:6539"
) -> gpd.GeoDataFrame:
    """Convert Detection list to a GeoDataFrame."""
    return gpd.GeoDataFrame(
        [
            {
                "geometry": d.geometry,
                "confidence": d.confidence,
                "class_id": d.class_id,
                "src_tile": d.source_tile,
            }
            for d in features
        ],
        crs=crs,
    )


def write_detections(
    features: list[Detection],
    output_dir: Path,
    fmt: str = "shp",
    crs: str = "EPSG:6539",
) -> Path:
    """Write detections to the specified format inside a containing directory.

    Args:
        features: Georeferenced detections.
        output_dir: Directory to create and write into.
        fmt: Output format key (``shp`` or ``gpkg``).
        crs: Coordinate reference system string.

    Returns:
        Path to the written file.
    """
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{fmt}'. Choose from: {list(SUPPORTED_FORMATS)}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{output_dir.name}.{fmt}"

    gdf = _detections_to_geodataframe(features, crs=crs)
    gdf.to_file(out_path, driver=SUPPORTED_FORMATS[fmt])

    logger.info("Wrote %d features -> %s", len(gdf), out_path)
    return out_path
