"""File operations: resolve image filenames, validate, copy."""

import logging
import shutil
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


def image_value_to_filename(image_value: str, cfg: Config) -> str:
    """Convert a mosaic Image field value to a zero-padded jp2 filename.

    The Image field is already a string. We strip whitespace, zero-pad
    to 6 characters if purely numeric, and append the file extension.
    """
    value = image_value.strip()

    if value.endswith(cfg.image_extension):
        return value

    if value.isdigit():
        value = value.zfill(6)

    return f"{value}{cfg.image_extension}"


def resolve_and_validate(
    image_values: list[str],
    image_dir: Path,
    cfg: Config,
) -> tuple[list[Path], list[str]]:
    """Resolve Image values to file paths. Return (found, missing) lists."""
    found: list[Path] = []
    missing: list[str] = []

    for val in image_values:
        filename = image_value_to_filename(val, cfg)
        filepath = image_dir / filename

        if filepath.is_file():
            found.append(filepath)
        else:
            missing.append(filename)
            logger.warning("Expected image file not found: %s", filepath)

    return found, missing


def copy_tiles(
    files: list[Path],
    output_dir: Path,
    dry_run: bool = False,
) -> int:
    """Copy tile images to output directory. Returns count of files copied."""
    output_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for src in files:
        dest = output_dir / src.name
        if dry_run:
            logger.info("[DRY RUN] Would copy: %s -> %s", src, dest)
        else:
            shutil.copy2(src, dest)
            logger.debug("Copied: %s -> %s", src, dest)
        copied += 1

    return copied