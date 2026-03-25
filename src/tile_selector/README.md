# tile_selector

Extracts JP2 orthoimagery tiles that intersect a given NYC community district. Part of the bus pad detection pipeline.

## Purpose

Given one or more community district (CD) numbers, this module:

1. Loads the NYC community district boundary shapefile.
2. Resolves the correct borough mosaic tile index from the CD number.
3. Performs a spatial intersection to identify mosaic tiles overlapping the district.
4. Copies matched JP2 tile images to `output/cd/{boro_cd}/`.

## Usage

```bash
# Single district
python -m src.tile_selector --cd 101

# Batch (cross-borough supported)
python -m src.tile_selector --cd 101 102 501

# Preview matched tiles without copying
python -m src.tile_selector --cd 101 --dry-run
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

## Configuration

All paths, field names, and borough mappings are defined in `config.toml`. Edit this file if data locations or naming conventions change. No code modifications should be necessary for path changes.

## Output

```
output/cd/
├── 101/
│   ├── 000123.jp2
│   ├── 000456.jp2
│   └── ...
├── 501/
│   ├── 002789.jp2
│   └── ...
```

Each CD directory contains all mosaic tiles whose footprint intersects the district boundary. In batch mode, a tile shared by adjacent districts is copied into both.

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
- Single-CD invocation fails hard on errors. Batch mode logs warnings and continues.