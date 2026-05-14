"""Shared workspace resolution for buspad commands."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path


CONFIG_DIR = Path.home() / ".buspad"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def get_workspace() -> Path:
    """Read the workspace path from ~/.buspad/config.toml.

    Returns the workspace as a resolved absolute Path.
    Raises SystemExit if the config file is missing or the
    recorded workspace directory no longer exists.
    """
    if not CONFIG_FILE.exists():
        raise SystemExit(
            "Workspace not configured.\n"
            "Run 'buspad-init <path>' to create a workspace."
        )

    with CONFIG_FILE.open("rb") as f:
        cfg = tomllib.load(f)

    try:
        raw = cfg["buspad"]["workspace"]
    except KeyError:
        raise SystemExit(
            f"Malformed config at {CONFIG_FILE}.\n"
            "Expected [buspad] table with 'workspace' key.\n"
            "Run 'buspad-init <path>' to regenerate."
        )

    workspace = Path(raw)
    if not workspace.is_dir():
        raise SystemExit(
            f"Configured workspace does not exist: {workspace}\n"
            "Run 'buspad-init <path>' to create a new workspace."
        )

    return workspace


def resolve_workspace(root: Path | None) -> Path:
    """Resolve workspace from an explicit override or the config file.

    Parameters
    ----------
    root : Path or None
        If provided, used directly (resolved to absolute).
        If None, falls back to get_workspace().
    """
    if root is not None:
        resolved = root.resolve()
        if not resolved.is_dir():
            raise SystemExit(f"Supplied --root does not exist: {resolved}")
        return resolved
    return get_workspace()


def add_root_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --root workspace override flag to a parser."""
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Override workspace path (ignores ~/.buspad/config.toml).",
    )