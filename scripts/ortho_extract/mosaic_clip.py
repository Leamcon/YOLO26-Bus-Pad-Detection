"""
VRT mosaic construction and boundary clipping.
Outputs 4-band RGBA GeoTIFF with alpha-based masking.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from osgeo import gdal
from pathlib import Path
from typing import Optional
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from scripts.ortho_extract.config import CRS_RASTER, GEOTIFF_COMPRESS, GEOTIFF_TILED, GEOTIFF_BLOCKSIZE


def build_vrt(tile_paths: list[Path], vrt_path: Path) -> Path:
    """Build a GDAL VRT from a list of JP2 tile paths.
    No resampling — tiles are stitched by spatial reference only.
    """
    tile_strs = [str(p) for p in tile_paths]

    vrt_options = gdal.BuildVRTOptions(
        resolution="highest",
        separate=False,  # stack spatially, not as separate bands
    )

    vrt_ds = gdal.BuildVRT(str(vrt_path), tile_strs, options=vrt_options)
    if vrt_ds is None:
        raise RuntimeError(f"GDAL BuildVRT failed for {len(tile_strs)} tiles")

    vrt_ds.FlushCache()
    vrt_ds = None  # close

    print(f"  VRT built: {vrt_path.name} ({len(tile_paths)} tiles)")
    return vrt_path


def clip_to_boundary(
    vrt_path: Path,
    geometry: BaseGeometry,
    output_path: Path,
    boro_cd: int,
) -> Path:
    """Clip the VRT mosaic to a boundary polygon.
    Uses band 4 (alpha) for interior/exterior masking.
    Exterior pixels: all bands = 0, alpha = 0.
    Valid pixels: original RGB values, alpha = 255.
    """
    geom_mapping = [mapping(geometry)]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(vrt_path) as src:
        # Verify expectations
        if src.count != 4:
            print(f"  WARNING: expected 4 bands, got {src.count}")
        if src.dtypes[0] != "uint8":
            print(f"  WARNING: expected uint8, got {src.dtypes[0]}")

        # Mask: crop to geometry bounding box, fill exterior with 0
        out_image, out_transform = rio_mask(
            src,
            geom_mapping,
            crop=True,
            filled=True,
            fill_value=0,
            nodata=0,
        )

        out_profile = src.profile.copy()
        out_profile.update(
            driver="GTiff",
            height=out_image.shape[1],
            width=out_image.shape[2],
            transform=out_transform,
            crs=f"EPSG:{CRS_RASTER}",
            compress=GEOTIFF_COMPRESS,
            tiled=GEOTIFF_TILED,
            blockxsize=GEOTIFF_BLOCKSIZE,
            blockysize=GEOTIFF_BLOCKSIZE,
        )

        with rasterio.open(output_path, "w", **out_profile) as dst:
            dst.write(out_image)

    px_h, px_w = out_image.shape[1], out_image.shape[2]
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  GeoTIFF written: {output_path.name} ({px_w}x{px_h}px, {size_mb:.1f}MB)")

    return output_path


def mosaic_and_clip(
    tile_paths: list[Path],
    geometry: BaseGeometry,
    boro_cd: int,
    output_dir: Path,
    vrt_dir: Optional[Path] = None,
) -> Path:
    """Full mosaic + clip pipeline for a single boundary feature."""
    if vrt_dir is None:
        vrt_dir = output_dir / "vrt_temp"
    vrt_dir.mkdir(parents=True, exist_ok=True)

    vrt_path = vrt_dir / f"mosaic_{boro_cd}.vrt"
    output_path = output_dir / f"ortho_{boro_cd}.tif"

    build_vrt(tile_paths, vrt_path)
    clip_to_boundary(vrt_path, geometry, output_path, boro_cd)

    return output_path