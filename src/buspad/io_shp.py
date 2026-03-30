"""
buspad/io_shp.py
================
Minimal SHP/DBF readers with schema validation and CRS reprojection.

Reads point geometries and attributes from Cyclomedia bus pad deliveries.
No dependency on fiona/geopandas — just struct-level parsing.  Points are
reprojected to the target CRS (EPSG:2263) on load if the source .prj
indicates a different projection.
"""

import struct
from pathlib import Path

from pyproj import CRS, Transformer

from .constants import (
    STOP_ID_FIELD_INDEX,
    BUS_PAD_FIELD_INDEX,
    BUS_PAD_YES_VALUES,
    TARGET_EPSG,
    ACCEPTED_TILE_EPSG,
)


def read_dbf(filepath: str | Path) -> tuple[list[tuple], list[list[str]]]:
    """Read a DBF file and return (fields, records).

    fields: list of (name, type, length) tuples
    records: list of lists of stripped string values
    """
    filepath = Path(filepath)
    with open(filepath, "rb") as f:
        header = f.read(32)
        num_records = struct.unpack("<I", header[4:8])[0]
        header_size = struct.unpack("<H", header[8:10])[0]

        fields = []
        while True:
            desc = f.read(32)
            if desc[0] == 0x0D:
                break
            name = desc[0:11].replace(b"\x00", b"").decode("ascii", errors="ignore")
            ftype = chr(desc[11])
            flen = desc[16]
            fields.append((name, ftype, flen))

        f.seek(header_size)
        records = []
        for _ in range(num_records):
            f.read(1)  # deletion flag
            row = []
            for _, _, flen in fields:
                val = f.read(flen).decode("ascii", errors="ignore").strip()
                row.append(val)
            records.append(row)

    return fields, records


def read_shp_points(filepath: str | Path) -> list[tuple[float, float]]:
    """Read point geometries from a shapefile.

    Returns list of (x, y) coordinate tuples.
    """
    filepath = Path(filepath)
    points = []
    with open(filepath, "rb") as f:
        f.seek(100)  # skip file header
        while True:
            rec_header = f.read(8)
            if len(rec_header) < 8:
                break
            rec_length = struct.unpack(">i", rec_header[4:8])[0] * 2
            rec_data = f.read(rec_length)
            if len(rec_data) >= 20:
                x = struct.unpack("<d", rec_data[4:12])[0]
                y = struct.unpack("<d", rec_data[12:20])[0]
                points.append((x, y))
    return points


def read_prj(filepath: str | Path) -> CRS | None:
    """Read a .prj file and return a pyproj CRS, or None on failure."""
    filepath = Path(filepath)
    try:
        wkt = filepath.read_text().strip()
        return CRS.from_wkt(wkt)
    except Exception:
        return None


def _get_transformer(source_crs: CRS) -> Transformer | None:
    """Return a Transformer from source to target CRS, or None if
    the source is already in an accepted CRS."""
    source_epsg = source_crs.to_epsg()
    if source_epsg in ACCEPTED_TILE_EPSG:
        return None
    return Transformer.from_crs(source_crs, CRS.from_epsg(TARGET_EPSG),
                                always_xy=True)


def _reproject_points(
    points: list[tuple[float, float]],
    transformer: Transformer,
) -> list[tuple[float, float]]:
    """Reproject a list of (x, y) points using a pyproj Transformer."""
    xs, ys = zip(*points)
    tx, ty = transformer.transform(xs, ys)
    return list(zip(tx, ty))


def validate_schema(fields: list[tuple]) -> None:
    """Check that expected fields exist at the expected indices.

    Raises ValueError with diagnostic info if the schema doesn't match.
    """
    errors = []

    if len(fields) <= BUS_PAD_FIELD_INDEX:
        raise ValueError(
            f"DBF has only {len(fields)} fields; expected at least "
            f"{BUS_PAD_FIELD_INDEX + 1}. Schema may have changed."
        )

    stop_field = fields[STOP_ID_FIELD_INDEX]
    pad_field = fields[BUS_PAD_FIELD_INDEX]

    if stop_field[1] not in ("C", "N"):
        errors.append(
            f"Field {STOP_ID_FIELD_INDEX} ({stop_field[0]!r}) has type "
            f"{stop_field[1]!r}; expected C or N for stop ID."
        )

    if pad_field[1] != "C":
        errors.append(
            f"Field {BUS_PAD_FIELD_INDEX} ({pad_field[0]!r}) has type "
            f"{pad_field[1]!r}; expected C for bus pad flag."
        )

    if errors:
        raise ValueError(
            "DBF schema validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


def load_bus_stops(
    shp_path: str | Path,
    dbf_path: str | Path,
    prj_path: str | Path | None = None,
) -> tuple[list[tuple], list[tuple]]:
    """Load and classify bus stops from a SHP/DBF pair.

    If prj_path is provided and the CRS is not already State Plane,
    coordinates are reprojected to EPSG:2263.

    Returns (has_pad, no_pad) where each is a list of
    (stop_id, x, y) tuples.

    Validates the DBF schema before processing.  Skips records where
    geometry is missing (more records in DBF than SHP).
    """
    fields, records = read_dbf(dbf_path)
    validate_schema(fields)
    points = read_shp_points(shp_path)

    # ── CRS detection and reprojection ────────────────────────────────────
    transformer = None
    if prj_path is not None:
        source_crs = read_prj(prj_path)
        if source_crs is not None:
            transformer = _get_transformer(source_crs)
            if transformer is not None:
                source_epsg = source_crs.to_epsg()
                print(f"    Reprojecting points: EPSG:{source_epsg} → "
                      f"EPSG:{TARGET_EPSG}")
                points = _reproject_points(points, transformer)
    elif prj_path is None:
        # No .prj file — assume coordinates are already in target CRS
        # and log a warning so this doesn't silently produce bad results
        print("    Warning: no .prj file found; assuming points are in "
              f"EPSG:{TARGET_EPSG}")

    # ── Classify stops ────────────────────────────────────────────────────
    has_pad = []
    no_pad = []

    for i, rec in enumerate(records):
        if i >= len(points):
            break
        x, y = points[i]
        stop_id = rec[STOP_ID_FIELD_INDEX]
        pad_flag = rec[BUS_PAD_FIELD_INDEX].strip().lower()

        if pad_flag in BUS_PAD_YES_VALUES:
            has_pad.append((stop_id, x, y))
        else:
            no_pad.append((stop_id, x, y))

    return has_pad, no_pad