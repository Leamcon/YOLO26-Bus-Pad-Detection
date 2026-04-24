# tile_selector

Extracts JP2 orthoimagery tiles that intersect a given NYC community district for a specified imagery year. Part of the bus pad detection pipeline.

## Purpose

Given one or more community district (CD) numbers and imagery year(s), this module:

1. Loads the NYC community district boundary shapefile.
2. Validates that the requested ortho imagery year directory exists on disk.
3. Resolves the correct borough mosaic tile index from the CD number and year.
4. Performs a spatial intersection to identify mosaic tiles overlapping the district.
5. Copies matched JP2 tile images to `output/cd/{year}/{boro_cd}/`.

## Usage

```bash
# Single district, single year
python -m src.tile_selector --cd 101 --year 2024

# Batch: multiple districts and years (cross-borough supported)
python -m src.tile_selector --cd 101 102 501 --year 2022 2024

# Preview matched tiles without copying
python -m src.tile_selector --cd 101 --year 2024 --dry-run
```

## CD Numbering

NYC community districts use a three-digit code where the leading digit identifies the borough:

| Digit | Borough        |
|-------|----------------|
| 1     | Manhattan      |
| 2     | Bronx          |
| 3     | Brooklyn       |
| 4     | Queens         |
| 5     | Staten Island  |

Example: `301` = Brooklyn CD 1, `412` = Queens CD 12.

## Imagery Years

Ortho imagery is expected at `data/nyc_ortho_{YYYY}/` with borough subdirectories following the `boro_{name}_sp{YY}` convention. The mosaic shapefile naming varies by vintage:

- **2024:** `{YY}_b_{boro_name}_l06_4bd.shp` (unique per borough)
- **All other years:** `nyc_sp_4bd_06in_index{YY}.shp` (same filename per borough directory)

Year-specific overrides are defined in `config.toml` under `[paths.patterns.mosaic_shapefile]`. Add new entries as naming conventions change.

## Configuration

All paths, field names, patterns, and borough mappings are defined in `config.toml`. Edit this file if data locations or naming conventions change. No code modifications should be necessary for path or pattern changes.

## Output

```
output/cd/
├── 2022/
│   ├── 101/
│   │   ├── 000123.jp2
│   │   └── ...
│   └── 301/
│       └── ...
├── 2024/
│   ├── 101/
│   │   ├── 000456.jp2
│   │   └── ...
│   └── 501/
│       └── ...
```

Each CD directory contains all mosaic tiles whose footprint intersects the district boundary. In batch mode, a tile shared by adjacent districts is copied into both. Multi-year runs produce separate year directories.

## Dependencies

- geopandas
- Python >= 3.11 (uses `tomllib`)

## Module Structure

| File         | Role                                      |
|--------------|-------------------------------------------|
| `__main__.py`| Entry point, orchestration                |
| `cli.py`     | Argument parsing                          |
| `config.toml`| Paths, field names, borough mapping       |
| `config.py`  | Loads and validates `config.toml`         |
| `spatial.py` | Shapefile loading, CRS control, sjoin     |
| `fileops.py` | Filename resolution, validation, file copy|

## Notes

- All spatial operations are performed in EPSG:2263 (NY State Plane Long Island, ft). Shapefiles in other CRS are reprojected automatically.
- The mosaic `Image` field values are zero-padded to 6 digits when numeric to match JP2 filenames on disk.
- Ortho year directories are validated before any spatial work begins. Missing directories produce an error and are skipped in batch mode.
- Single-CD, single-year invocation fails hard on errors. Batch mode logs warnings and continues.