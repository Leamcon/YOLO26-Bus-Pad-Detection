"""buspad-init: scaffold a workspace and copy package resources."""

from __future__ import annotations

import argparse
import sys
from importlib.resources import files
from importlib.abc import Traversable
from pathlib import Path


_CONFIG_DIR = Path.home() / ".buspad"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"

# Directories created under the workspace root.
_WORKSPACE_DIRS: list[tuple[str, ...]] = [
    ("data", "boundaries"),
    ("data", "imagery", "nyc_ortho_2024"),
    ("data", "chips", "cd"),
    ("data", "chips", "boro"),
    ("models", "nano"),
    ("models", "small"),
    ("output", "detections"),
]

# Resource copies: (resource subpath parts, workspace dest parts).
# Each entry copies all files from the resource directory into the
# corresponding workspace directory, overwriting on collision.
_RESOURCE_COPIES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (
        ("boundaries", "community_districts_20260306"),
        ("data", "boundaries", "community_districts_20260306"),
    ),
    (
        ("models", "nano"),
        ("models", "nano"),
    ),
    (
        ("models", "small"),
        ("models", "small"),
    ),
]

_EPILOG = """\
directories created under <path>:
  data/boundaries/                community district boundary shapefiles
  data/imagery/nyc_ortho_2024/    ortho-imagery tiles (2024 vintage)
  data/chips/cd/                  chipped tiles by community district
  data/chips/boro/                chipped tiles by borough
  models/nano/                    YOLO26n model weights
  models/small/                   YOLO26s model weights
  output/detections/              inference and georeferenced outputs

The nyc_ortho_2024 directory is created by default as the 2024 vintage is
the latest available at time of publishing. Additional ortho-imagery
directories may be added under data/imagery/ but must follow the
nyc_ortho_{YYYY} naming convention to ensure correct execution of
downstream package commands.

Bundled boundary shapefiles and model weights are copied into the
workspace. The workspace path is written to ~/.buspad/config.toml;
subsequent buspad commands resolve it automatically.
"""


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _copy_tree(src: Traversable, dest: Path) -> None:
    """Copy every file in *src* (non-recursive) into *dest*."""
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            target = dest / item.name
            target.write_bytes(item.read_bytes())
            print(f"  {item.name} -> {target}")


# ------------------------------------------------------------------
# public steps
# ------------------------------------------------------------------

def scaffold_dirs(workspace: Path) -> None:
    """Create the workspace directory tree."""
    print("Scaffolding directories...")
    for parts in _WORKSPACE_DIRS:
        target = workspace / Path(*parts)
        target.mkdir(parents=True, exist_ok=True)
        print(f"  {target}")


def copy_resources(workspace: Path) -> None:
    """Copy package resources into the workspace (always overwrites)."""
    print("Copying resources...")
    pkg = files("buspad.resources")
    for src_parts, dest_parts in _RESOURCE_COPIES:
        src_dir: Traversable = pkg
        for part in src_parts:
            src_dir = src_dir / part
        dest_dir = workspace / Path(*dest_parts)
        _copy_tree(src_dir, dest_dir)


def write_config(workspace: Path) -> None:
    """Write workspace path to ~/.buspad/config.toml."""
    print("Writing config...")
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # TOML literal string (single-quoted) preserves Windows backslashes.
    content = (
        "# buspad workspace configuration\n"
        "[buspad]\n"
        f"workspace = '{workspace}'\n"
    )
    _CONFIG_FILE.write_text(content, encoding="utf-8")
    print(f"  {_CONFIG_FILE}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="buspad-init",
        description="Scaffold a buspad workspace and copy package resources.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Workspace directory (created if it does not exist).",
    )
    args = parser.parse_args()
    workspace: Path = args.path.resolve()

    print(f"Initializing workspace: {workspace}\n")

    scaffold_dirs(workspace)
    print()
    copy_resources(workspace)
    print()
    write_config(workspace)

    print(f"\nDone. All buspad commands will use this workspace.")