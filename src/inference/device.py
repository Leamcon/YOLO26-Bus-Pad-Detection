"""Inference device detection."""


def detect_device(requested: str | None) -> str:
    """Return the best available device, or validate the user's choice."""
    if requested is not None:
        return requested

    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"