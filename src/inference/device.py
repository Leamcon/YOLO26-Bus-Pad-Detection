"""Inference device resolution and validation."""

import sys

from inference.formats import ModelFormat, FORMAT_DEVICES


def resolve_device(requested: str | None, fmt: ModelFormat) -> str:
    """Return a validated device string for the given format.

    If no device is requested, auto-detects the best available device
    that is compatible with the model format.  If a device is explicitly
    requested, validates it against the format's supported set.
    """
    valid = FORMAT_DEVICES[fmt]

    if requested is not None:
        if requested not in valid:
            print(
                f"ERROR: device '{requested}' is not compatible with "
                f"format '{fmt.value}'.\n"
                f"  Valid devices for {fmt.value}: {', '.join(sorted(valid))}",
                file=sys.stderr,
            )
            sys.exit(1)
        return requested

    return _auto_detect(valid)


def _auto_detect(valid: set[str]) -> str:
    """Pick the best available device from the valid set."""
    import torch

    if "mps" in valid and torch.backends.mps.is_available():
        return "mps"
    if "cuda" in valid and torch.cuda.is_available():
        return "cuda"
    return "cpu"