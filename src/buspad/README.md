# buspad

Image chipping pipeline for bus pad detection from NYC aerial orthoimagery.

Extracts labeled image chips from georeferenced JP2 tiles at known bus stop locations, classifying them by bus pad presence for downstream object detection training (YOLO via Roboflow).

## Requirements

```
pip install rasterio numpy Pillow
```

Python 3.10+ (uses `X | Y` union type syntax).

## Project structure

The module expects the following layout relative to the project root:

```
project_root/
├── data/
│   ├── nyc_ortho_YYYY/
│   │   ├── boro_manhattan_spYY/
│   │   │   ├── *.jp2
│   │   │   └── .tile_index.json  (auto-generated cache)
│   │   ├── boro_bronx_spYY/
│   │   ├── boro_brooklyn_spYY/
│   │   ├── boro_queens_spYY/
│   │   └── boro_staten_island_spYY/
│   └── points/
│       ├── cd_101_bus_pads/
│       │   ├── cd_101_bus_pads.shp
│       │   └── cd_101_bus_pads.dbf
│       ├── cd_403_bus_pads/
│       └── ...
├── output/
│   └── chips/YYYY/borough/cd_###/has_pad/
│                                 /no_pad/
└── src/
    └── buspad/
```

Imagery is sourced from the NYC orthoimagery program (released biennially). Point data is Cyclomedia bus stop inventories broken down by community district.

### Community district codes

The first digit of each 3-digit CD code identifies the borough:

| Prefix | Borough        |
|--------|----------------|
| 1xx    | Manhattan      |
| 2xx    | Bronx          |
| 3xx    | Brooklyn       |
| 4xx    | Queens         |
| 5xx    | Staten Island  |

## Usage

Run from anywhere within the project — paths are anchored to the project root automatically.

```
python -m buspad <command> [options]
```

### `list` — discover available data

```
python -m buspad list
```

Reports imagery directories, point data, and coverage gaps by borough. No arguments required.

Example output:

```
Project root: /home/user/bus-pad-detect

Imagery on disk:
  manhattan        2024
  brooklyn         2024

Point data on disk:
  manhattan        101, 103, 105, 107, 109, 111
  brooklyn         301, 303, 306

Coverage notes:
  All boroughs with imagery have matching point data.
```

### `chip` — extract image chips

Process all available CDs for a borough:

```
python -m buspad chip brooklyn --year 2024
```

Process a single community district:

```
python -m buspad chip brooklyn --year 2024 --cd 301
```

Dry run (report work without writing files):

```
python -m buspad chip brooklyn --year 2024 --dry-run
```

Force overwrite of existing chips:

```
python -m buspad chip brooklyn --year 2024 --force
```

Rebuild the tile spatial index (normally cached after first run):

```
python -m buspad chip brooklyn --year 2024 --rebuild-index
```

Flags can be combined:

```
python -m buspad chip queens --year 2024 --cd 403 --dry-run
```

### Output

Chips are written to `output/chips/YYYY/borough/cd_###/` with subdirectories `has_pad/` and `no_pad/`. Each chip is a 640×640 PNG upscaled from a 200×200 native-pixel extraction (100 ft extent at 0.5 ft/px resolution).

Files are named `pad_<stop_id>.png` and `nopad_<stop_id>.png`. Existing files are skipped unless `--force` is set.

A summary table is printed after each run:

```
=======================================================
CD     pad   no-pad  saved  exist   no-tile  fail
-------------------------------------------------------
301      12      45     57      0        3     0
303       8      31     39      0        0     0
=======================================================
```

## Tile index caching

On first run for a borough/year, the module reads georeferenced bounds from every JP2 in the imagery directory and caches the result as `.tile_index.json` alongside the tiles. Since imagery is immutable post-download, the cache is trusted on subsequent runs. Use `--rebuild-index` to force a rebuild if needed.

## Coordinate reference systems

Imagery tiles use EPSG:6539 (NAD83(2011) / NY Long Island, ft). Tile mosaics bundled with the imagery use EPSG:2263 (NAD83 / NY Long Island, ft). Both are State Plane Long Island projections; the datum offset between them is sub-pixel at 0.5 ft/px and does not affect chipping. The module asserts that all tiles belong to one of these two CRS families and will reject tiles with unexpected projections.

## Roboflow integration

The output directory structure (`has_pad/` and `no_pad/` per CD) is designed for upload to Roboflow for labeling. Multiple CD directories can be uploaded into the same Roboflow project to build a combined training set. A `collect` command to aggregate chips into a flat staging directory is planned for a future version.

## Module layout

| File             | Purpose                                        |
|------------------|------------------------------------------------|
| `__main__.py`    | Entry point for `python -m buspad`             |
| `cli.py`         | Argument parsing, validation, orchestration    |
| `paths.py`       | Path resolution, CD discovery, root anchoring  |
| `constants.py`   | Chip sizes, path templates, borough/CD mapping |
| `tile_index.py`  | JP2 spatial index with JSON caching            |
| `chipper.py`     | Chip extraction and upscaling                  |
| `io_shp.py`      | SHP/DBF readers with schema validation         |

## Edge cases

- **Chips near tile boundaries**: extraction window is shifted inward to maintain full 200×200 extent. The bus pad may be off-center in these cases.
- **Stops outside imagery coverage**: logged as `no-tile` in the summary and skipped.
- **CD/borough mismatch**: `--cd 301` with borough `manhattan` produces an error with the correct borough and available CDs listed.
- **Missing point data**: the module discovers CDs at runtime from disk contents. Missing directories are reported, not assumed.