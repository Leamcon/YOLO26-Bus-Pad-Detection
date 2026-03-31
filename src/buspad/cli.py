"""
buspad/cli.py
=============
CLI parsing and orchestration for chip and list commands.
"""

import argparse
import sys

from .constants import VALID_BOROUGHS, BOROUGH_CD_PREFIX
from .paths import (
    resolve_ortho_dir,
    discover_cds,
    discover_ortho_years,
    resolve_cd_files,
    resolve_output_dir,
    validate_cd_borough,
    PROJECT_ROOT,
)
from .tile_index import get_or_build_index, find_tile_for_point
from .io_shp import load_bus_stops
from .chipper import chip_image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buspad",
        description="Bus pad detection — image chipping pipeline.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── chip command ──────────────────────────────────────────────────────
    chip = sub.add_parser("chip", help="Extract chips from aerial imagery.")
    chip.add_argument(
        "borough",
        choices=VALID_BOROUGHS,
        help="Target borough.",
    )
    chip.add_argument(
        "--year",
        type=int,
        required=True,
        help="Imagery year (YYYY).",
    )
    chip.add_argument(
        "--cd",
        type=str,
        default=None,
        help="Single community district code (3-digit). "
             "Omit to process all available CDs for the borough.",
    )
    chip.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without writing files.",
    )
    chip.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing chip files.",
    )
    chip.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force rebuild of the tile spatial index cache.",
    )

    # ── list command ──────────────────────────────────────────────────────
    sub.add_parser(
        "list",
        help="Report available imagery and point data on disk.",
    )

    return parser


def _chip_cd(
    cd: str,
    borough: str,
    year: int,
    tile_index: list[dict],
    dry_run: bool,
    force: bool,
) -> dict:
    """Process a single community district.  Returns a stats dict."""
    stats = {
        "cd": cd,
        "has_pad_total": 0,
        "no_pad_total": 0,
        "has_pad_saved": 0,
        "no_pad_saved": 0,
        "skipped_existing": 0,
        "skipped_no_tile": 0,
        "failed": 0,
    }

    shp_path, dbf_path = resolve_cd_files(cd)
    has_pad, no_pad = load_bus_stops(shp_path, dbf_path)
    stats["has_pad_total"] = len(has_pad)
    stats["no_pad_total"] = len(no_pad)

    out_dir = resolve_output_dir(borough, year, cd)

    if dry_run:
        print(f"  [dry-run] CD {cd}: {len(has_pad)} pad, "
              f"{len(no_pad)} no-pad stops")
        return stats

    groups = [
        (has_pad, "has_pad", "pad"),
        (no_pad, "no_pad", "nopad"),
    ]

    for stops, subfolder, prefix in groups:
        dest = out_dir / subfolder
        dest.mkdir(parents=True, exist_ok=True)

        for stop_id, x, y in stops:
            out_path = dest / f"{prefix}_{stop_id}.png"

            if out_path.exists() and not force:
                stats["skipped_existing"] += 1
                continue

            tile = find_tile_for_point(x, y, tile_index)
            if tile is None:
                stats["skipped_no_tile"] += 1
                continue

            ok = chip_image(tile["path"], x, y, out_path)
            if ok:
                key = "has_pad_saved" if subfolder == "has_pad" else "no_pad_saved"
                stats[key] += 1
            else:
                stats["failed"] += 1

    return stats


def run_chip(args: argparse.Namespace) -> None:
    """Orchestrate the chip command."""
    borough = args.borough
    year = args.year

    # ── Resolve imagery ───────────────────────────────────────────────────
    try:
        ortho_dir = resolve_ortho_dir(borough, year)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Imagery: {ortho_dir}")

    # ── Determine target CDs ─────────────────────────────────────────────
    if args.cd is not None:
        cd = args.cd.zfill(3)
        try:
            validate_cd_borough(cd, borough)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        cd_list = [cd]
    else:
        cd_list = discover_cds(borough)
        if not cd_list:
            print(f"Error: No point data found for {borough}.", file=sys.stderr)
            sys.exit(1)

    print(f"Target CDs: {', '.join(cd_list)}")

    # ── Build / load tile index ──────────────────────────────────────────
    print("Loading tile index...", end=" ", flush=True)
    tile_index = get_or_build_index(ortho_dir, rebuild=args.rebuild_index)
    print(f"{len(tile_index)} tiles.")

    # ── Process each CD ──────────────────────────────────────────────────
    all_stats = []
    for cd in cd_list:
        print(f"\nProcessing CD {cd}...")
        try:
            stats = _chip_cd(
                cd, borough, year, tile_index,
                dry_run=args.dry_run, force=args.force,
            )
            all_stats.append(stats)
        except (FileNotFoundError, ValueError) as e:
            print(f"  Skipping CD {cd}: {e}")
            continue

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"{'CD':<6} {'pad':>5} {'no-pad':>7} {'saved':>6} "
          f"{'exist':>6} {'no-tile':>8} {'fail':>5}")
    print(f"{'-' * 55}")
    for s in all_stats:
        saved = s["has_pad_saved"] + s["no_pad_saved"]
        print(
            f"{s['cd']:<6} {s['has_pad_total']:>5} {s['no_pad_total']:>7} "
            f"{saved:>6} {s['skipped_existing']:>6} "
            f"{s['skipped_no_tile']:>8} {s['failed']:>5}"
        )
    print(f"{'=' * 55}")

    if args.dry_run:
        print("\n[dry-run] No files were written.")


def _count_chips(year: int | None = None) -> dict:
    """Count PNG files in the output chip directories.

    Returns {borough: {cd: {"has_pad": int, "no_pad": int}}}.
    If year is None, scans all years.
    """
    from .paths import _rooted
    from .constants import OUTPUT_DIR_TEMPLATE

    chip_root = _rooted("output/chips")
    if not chip_root.is_dir():
        return {}

    results = {}
    year_dirs = [chip_root / str(year)] if year else sorted(chip_root.iterdir())

    for year_dir in year_dirs:
        if not year_dir.is_dir():
            continue
        for boro_dir in sorted(year_dir.iterdir()):
            if not boro_dir.is_dir():
                continue
            borough = boro_dir.name
            for cd_dir in sorted(boro_dir.iterdir()):
                if not cd_dir.is_dir():
                    continue
                cd = cd_dir.name.replace("cd_", "")
                counts = {"has_pad": 0, "no_pad": 0}
                for sub in ("has_pad", "no_pad"):
                    d = cd_dir / sub
                    if d.is_dir():
                        counts[sub] = len(list(d.glob("*.png")))
                results.setdefault(borough, {})[cd] = counts

    return results


def run_list() -> None:
    """Report available imagery and point data."""
    reverse = {v: k for k, v in BOROUGH_CD_PREFIX.items()}

    print(f"Project root: {PROJECT_ROOT}\n")

    # ── Imagery ──────────────────────────────────────────────────────────
    ortho = discover_ortho_years()
    print("Imagery on disk:")
    if ortho:
        for borough in VALID_BOROUGHS:
            years = ortho.get(borough, [])
            if years:
                print(f"  {borough:<16} {', '.join(str(y) for y in years)}")
    else:
        print("  (none found)")

    # ── Point data ───────────────────────────────────────────────────────
    print("\nPoint data on disk:")
    all_cds = discover_cds()
    if all_cds:
        for borough in VALID_BOROUGHS:
            prefix = BOROUGH_CD_PREFIX[borough]
            boro_cds = [c for c in all_cds if c[0] == prefix]
            if boro_cds:
                print(f"  {borough:<16} {', '.join(boro_cds)}")
    else:
        print("  (none found)")

    # ── Coverage gaps ────────────────────────────────────────────────────
    print("\nCoverage notes:")
    has_imagery = set(ortho.keys())
    has_points = {
        borough for borough in VALID_BOROUGHS
        if any(c[0] == BOROUGH_CD_PREFIX[borough] for c in all_cds)
    }
    imagery_only = has_imagery - has_points
    points_only = has_points - has_imagery

    if imagery_only:
        for b in sorted(imagery_only):
            print(f"  {b}: imagery available but no point data")
    if points_only:
        for b in sorted(points_only):
            print(f"  {b}: point data available but no imagery")
    if not imagery_only and not points_only and has_imagery:
        print("  All boroughs with imagery have matching point data.")

    # ── Chip counts ──────────────────────────────────────────────────────
    chip_counts = _count_chips()
    print("\nChips on disk:")
    if chip_counts:
        for borough in VALID_BOROUGHS:
            if borough not in chip_counts:
                continue
            cds = chip_counts[borough]
            boro_pad = sum(c["has_pad"] for c in cds.values())
            boro_nopad = sum(c["no_pad"] for c in cds.values())
            print(f"  {borough:<16} {boro_pad:>5} pad, {boro_nopad:>5} no-pad "
                  f"({boro_pad + boro_nopad} total)")
    else:
        print("  (none found)")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "chip":
        run_chip(args)
    elif args.command == "list":
        run_list()