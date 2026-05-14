"""buspad.georef — Georeference YOLO detections to EPSG:6539 map coordinates."""

from buspad.georef.defs import CHIP_SIZE, SCALE_FACTOR, UPSCALE_SIZE, ChipOffset, Detection

__all__ = [
    "CHIP_SIZE",
    "UPSCALE_SIZE",
    "SCALE_FACTOR",
    "ChipOffset",
    "Detection",
]