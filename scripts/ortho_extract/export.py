"""
Export GeoTIFF to non-spatial JP2 for YOLO ingestion.
Drops alpha channel, strips georeferencing.
"""

import rasterio
from pathlib import Path
from typing import Optional


def export_for_yolo(geotiff_path: Path, output_dir: Optional[Path] = None) -> Path:
    """Read 4-band GeoTIFF, write 3-band RGB JP2 without spatial reference."""
    if output_dir is None:
        output_dir = geotiff_path.parent / "yolo"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / geotiff_path.with_suffix(".jp2").name

    with rasterio.open(geotiff_path) as src:
        profile = {
            "driver": "JP2OpenJPEG",
            "dtype": src.dtypes[0],
            "width": src.width,
            "height": src.height,
            "count": 3,
            "quality": "100",
            "reversible": "YES",
            # No CRS, no transform — intentionally omitted
        }

        with rasterio.open(output_path, "w", **profile) as dst:
            for band_idx in range(1, 4):  # bands 1, 2, 3 only
                dst.write(src.read(band_idx), band_idx)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  YOLO JP2 written: {output_path.name} ({size_mb:.1f}MB)")

    return output_path