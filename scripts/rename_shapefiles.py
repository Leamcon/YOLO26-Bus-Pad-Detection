#!/usr/bin/env python3
"""
Unzips shapefiles and renames all component files to match the zip's name.
Handles the case where zip contains generically-named files (e.g., output.shp).

Usage:
    python rename_shapefiles.py /path/to/zips /path/to/output

If output dir is omitted, defaults to ./data
"""

import argparse
import zipfile
import shutil
from pathlib import Path

# Known shapefile-associated extensions
SHP_EXTENSIONS = {
    '.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx',
    '.fbn', '.fbx', '.ain', '.aih', '.ixs', '.mxs', '.atx',
    '.shp.xml', '.qix', '.qpj'
}

def get_shapefile_basename(files: list[Path]) -> str | None:
    """Find the common basename of the shapefile components."""
    for f in files:
        if f.suffix.lower() == '.shp':
            return f.stem
    return None

def rename_shapefile_set(zip_path: Path, output_dir: Path, dry_run: bool = False):
    new_basename = zip_path.stem  # e.g., "land_use_2024" from "land_use_2024.zip"

    # Each zip gets its own subdirectory: output_dir/land_use_2024/
    dest_dir = output_dir / new_basename
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Extract to a temp subdirectory to avoid collisions
        tmp_dir = output_dir / f"_tmp_{new_basename}"
        zf.extractall(tmp_dir)

    extracted = list(tmp_dir.rglob('*'))
    files = [f for f in extracted if f.is_file()]

    old_basename = get_shapefile_basename(files)
    if old_basename is None:
        print(f"  SKIP {zip_path.name}: no .shp found inside")
        shutil.rmtree(tmp_dir)
        return

    renamed = 0
    for f in files:
        # Handle compound extensions like .shp.xml
        if f.name.lower().endswith('.shp.xml'):
            new_name = f"{new_basename}.shp.xml"
        elif f.stem.lower() == old_basename.lower():
            new_name = f"{new_basename}{f.suffix}"
        else:
            # File doesn't match the shapefile basename — copy as-is
            new_name = f.name

        dest = dest_dir / new_name
        if dry_run:
            print(f"  {f.name} -> {new_basename}/{new_name}")
        else:
            shutil.move(str(f), str(dest))
            renamed += 1

    shutil.rmtree(tmp_dir)
    print(f"  {zip_path.name}: {renamed} files -> {dest_dir.relative_to(output_dir)}/ ({old_basename} -> {new_basename})")

def main():
    parser = argparse.ArgumentParser(
        description='Unzip and rename shapefiles to match their zip filename.'
    )
    parser.add_argument('zip_dir', type=Path, help='Directory containing .zip files')
    parser.add_argument('output_dir', type=Path, nargs='?', default=Path('./data'),
                        help='Output directory (default: ./data)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without moving any files')
    args = parser.parse_args()

    if not args.zip_dir.is_dir():
        parser.error(f"{args.zip_dir} is not a directory")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    zips = sorted(args.zip_dir.glob('*.zip'))
    if not zips:
        parser.error(f"No .zip files found in {args.zip_dir}")

    print(f"Processing {len(zips)} zip files -> {args.output_dir}")
    if args.dry_run:
        print("(DRY RUN — no files will be moved)\n")

    for z in zips:
        rename_shapefile_set(z, args.output_dir, dry_run=args.dry_run)

    print("\nDone.")

if __name__ == '__main__':
    main()