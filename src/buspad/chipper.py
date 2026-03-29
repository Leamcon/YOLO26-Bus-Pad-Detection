"""
buspad/chipper.py
=================
Chip extraction from JP2 tiles.
"""

import numpy as np
import rasterio
from rasterio.windows import Window
from PIL import Image
from pathlib import Path

from .constants import CHIP_SIZE_PX, OUTPUT_SIZE_PX


def chip_image(
    jp2_path: str | Path,
    px: float,
    py: float,
    out_path: str | Path,
    chip_size: int = CHIP_SIZE_PX,
    output_size: int = OUTPUT_SIZE_PX,
) -> bool:
    """Extract a chip centered on (px, py) and save as PNG.

    If the centered window would exceed tile bounds, shifts inward to
    preserve full chip dimensions.  Rejects tiles smaller than chip_size.

    Returns True on success, False on failure (logged to stderr).
    """
    try:
        with rasterio.open(jp2_path) as src:
            if src.width < chip_size or src.height < chip_size:
                return False

            res_x, res_y = src.res
            col = int((px - src.bounds.left) / res_x)
            row = int((src.bounds.top - py) / res_y)

            half = chip_size // 2
            col_start = col - half
            row_start = row - half

            # clamp to tile bounds
            col_start = max(0, min(col_start, src.width - chip_size))
            row_start = max(0, min(row_start, src.height - chip_size))

            window = Window(col_start, row_start, chip_size, chip_size)
            data = src.read(window=window)  # (bands, H, W)

            # normalize to uint8
            if data.dtype != np.uint8:
                dmax = data.max()
                if dmax == 0:
                    return False
                data = (data / dmax * 255).astype(np.uint8)

            # build RGB array
            if data.shape[0] >= 3:
                rgb = np.stack([data[0], data[1], data[2]], axis=-1)
            else:
                rgb = np.stack([data[0]] * 3, axis=-1)

            img = Image.fromarray(rgb)
            img = img.resize((output_size, output_size), Image.LANCZOS)

            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(out_path)
            return True

    except Exception as e:
        print(f"    Error chipping {jp2_path}: {e}")
        return False