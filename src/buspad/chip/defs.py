"""Constants and path resolution for the chip subpackage."""

from pathlib import Path

# ── Chipping constants ────────────────────────────────────────────────
CHIP_SIZE = 200
UPSCALE_SIZE = 640
TILE_SIZE = 5000
TRAVERSAL = TILE_SIZE - CHIP_SIZE  # 4800

CRS = "EPSG:6539"  # NAD83 / New York Long Island (ftUS)

# ── Workspace-relative path segments ─────────────────────────────────
IMAGERY_DIR = Path("data", "imagery")
CHIPS_DIR = Path("data", "chips")


def resolve_input_dir(
    workspace: Path,
    year: int,
    *,
    boro: str | None = None,
    cd: int | None = None,
) -> Path:
    """Build the input tile directory from CLI args.

    Boro mode:  data/imagery/nyc_ortho_{YYYY}/boro_{name}_sp{YY}/
    CD mode:    data/imagery/cd/{YYYY}/{CD}/
    """
    if boro is not None:
        short_year = str(year)[-2:]
        return (
            workspace
            / IMAGERY_DIR
            / f"nyc_ortho_{year}"
            / f"boro_{boro}_sp{short_year}"
        )
    return workspace / IMAGERY_DIR / "cd" / str(year) / str(cd)


def resolve_output_dir(
    workspace: Path,
    year: int,
    *,
    boro: str | None = None,
    cd: int | None = None,
) -> Path:
    """Build the output chips directory from CLI args.

    Boro mode:  data/chips/boro/{name}/{YYYY}/
    CD mode:    data/chips/cd/{CD}/{YYYY}/
    """
    if boro is not None:
        return workspace / CHIPS_DIR / "boro" / boro / str(year)
    return workspace / CHIPS_DIR / "cd" / str(cd) / str(year)