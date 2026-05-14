# DOT Bus Pads ML

Detection of bus pads from orthographic aerial imagery of urban environments using machine learning.

## Project Overview

This project develops a machine vision pipeline to identify bus pad infrastructure from high-resolution aerial orthoimagery of New York City. The current focus is on preprocessing and pipeline development, with model training built around the YOLO26 toolkit.

## Data Sources

- **Orthoimagery:** NY Statewide Digital Orthoimagery Program — 4-band RGBA JP2 tiles at native resolution, organized by borough. Approximately 20GB total across five borough directories.
- **Boundary Vector:** NYC Community Districts shapefile via NYC Open Data. Features identified by `boro_cd` (double), where the first digit encodes the borough (1=Manhattan, 2=Bronx, 3=Brooklyn, 4=Queens, 5=Staten Island).

Data is not included in this repository. See individual pipeline READMEs for expected directory structure.

## Project Structure

```
dot_buspads_ml/
├── README.md
├── data/
│   ├── nyc_ortho_2024/
│   │   ├── boro_manhattan_sp24/
│   │   ├── boro_bronx_sp24/
│   │   ├── boro_brooklyn_sp24/
│   │   ├── boro_queens_sp24/
│   │   └── boro_staten_island_sp24/
│   └── boundaries/
│        └── community_districts_20260306/
│            └── geo_export_e1c55842-b6cf-48de-89dd-fb84825c0f0d.shp
├── scripts/
│   ├── __init__.py
│   └── ortho_extract/
└── output/
   └── ortho_extracts/
```

## Environment Setup

This project uses conda for environment management.

```bash
conda create -n geocomp python=3.14
conda activate geocomp
conda install rasterio geopandas gdal shapely
```

Key dependencies: rasterio, geopandas, GDAL (Python bindings), shapely.

## Usage

All scripts are invoked from the project root using Python's `-m` flag:

```bash
python -m scripts.ortho_extract.extract --boro_cd 401 402 403
```

See `scripts/ortho_extract/README.md` for pipeline-specific documentation.

## Version Control

Local Git repository. Not currently hosted on a remote.