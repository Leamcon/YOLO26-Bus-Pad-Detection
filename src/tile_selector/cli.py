"""CLI argument parsing for tile_selector."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tile_selector",
        description="Extract mosaic tile images intersecting NYC community districts.",
    )
    parser.add_argument(
        "--cd",
        type=int,
        nargs="+",
        required=True,
        help="Community district number(s). e.g. 101 for Manhattan CD 1, 501 for Staten Island CD 1.",
    )
    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        required=True,
        help="Imagery year(s). e.g. 2024, or 2022 2024 for multi-year batch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matched tiles without copying files.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)