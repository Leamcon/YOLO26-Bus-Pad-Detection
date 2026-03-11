"""
chip_images.py
==============
Cuts 640x640 pixel chips from JP2 tiles centered on bus pad locations.
Saves chips to an output folder ready for upload to Roboflow.

Requirements:
    pip install rasterio shapely numpy Pillow

Usage:
    python chip_images.py
"""

import os
import struct
import math
import numpy as np

# ── EDIT THESE PATHS ──────────────────────────────────────────────────────────
JP2_FOLDER      = "/content/drive/MyDrive/buspad/jp2_207 (1)"   # folder with 25 JP2 tiles
SHP_FILE        = "/content/drive/MyDrive/buspad/jp2_207 (1)/Point_3D.shp"  # Cyclomedia SHP
DBF_FILE        = "/content/drive/MyDrive/buspad/jp2_207 (1)/Point_3D.dbf"  # Cyclomedia DBF
OUTPUT_FOLDER   = "/content/drive/MyDrive/buspad/chips"     # where chips get saved
CHIP_SIZE_PX    = 200   # extract 200px (100 feet), resize to 640
# ─────────────────────────────────────────────────────────────────────────────

def read_dbf(filepath):
    with open(filepath, 'rb') as f:
        header = f.read(32)
        num_records = struct.unpack('<I', header[4:8])[0]
        header_size = struct.unpack('<H', header[8:10])[0]
        fields = []
        while True:
            field_desc = f.read(32)
            if field_desc[0] == 0x0D:
                break
            name = field_desc[0:11].replace(b'\x00', b'').decode('ascii', errors='ignore')
            ftype = chr(field_desc[11])
            flen = field_desc[16]
            fields.append((name, ftype, flen))
        f.seek(header_size)
        records = []
        for i in range(num_records):
            f.read(1)
            record = {}
            for name, ftype, flen in fields:
                val = f.read(flen).decode('ascii', errors='ignore').strip()
                record[name] = val
            records.append(record)
    return fields, records

def read_shp_points(filepath):
    points = []
    with open(filepath, 'rb') as f:
        f.seek(100)
        while True:
            rec_header = f.read(8)
            if len(rec_header) < 8:
                break
            rec_length = struct.unpack('>i', rec_header[4:8])[0] * 2
            rec_data = f.read(rec_length)
            if len(rec_data) >= 20:
                x = struct.unpack('<d', rec_data[4:12])[0]
                y = struct.unpack('<d', rec_data[12:20])[0]
                points.append((x, y))
    return points

def find_jp2_for_point(x, y, jp2_folder):
    """Find which JP2 tile contains the given point."""
    for fname in os.listdir(jp2_folder):
        if not fname.endswith('.jp2'):
            continue
        # tile name encodes xmin/ymin e.g. 010230.jp2 = X=1,010,000 Y=230,000
        base = fname.replace('.jp2', '')
        try:
            tx = int(base[:3]) * 1000 + 1000000  # restore full coordinate
            ty = int(base[3:]) * 1000
            # each tile is 2500 x 2500 feet
            if tx <= x < tx + 2500 and ty <= y < ty + 2500:
                return os.path.join(jp2_folder, fname), tx, ty
        except:
            continue
    return None, None, None

def chip_image(jp2_path, px, py, tile_xmin, tile_ymin, chip_size, out_path):
    """Extract a chip centered on the bus pad location."""
    try:
        import rasterio
        from rasterio.windows import Window

        with rasterio.open(jp2_path) as src:
            # figure out resolution (feet per pixel)
            res_x = src.res[0]
            res_y = src.res[1]

            # convert real-world coords to pixel coords within tile
            col = int((px - src.bounds.left) / res_x)
            row = int((src.bounds.top - py) / res_y)

            half = chip_size // 2

            # make sure chip stays within image bounds
            col_start = max(0, col - half)
            row_start = max(0, row - half)
            col_end = min(src.width, col_start + chip_size)
            row_end = min(src.height, row_start + chip_size)

            window = Window(col_start, row_start,
                            col_end - col_start,
                            row_end - row_start)

            data = src.read(window=window)  # shape: (bands, H, W)

            # convert to uint8 RGB
            if data.dtype != np.uint8:
                data = (data / data.max() * 255).astype(np.uint8)

            if data.shape[0] >= 3:
                rgb = np.stack([data[0], data[1], data[2]], axis=-1)
            else:
                rgb = np.stack([data[0], data[0], data[0]], axis=-1)

            from PIL import Image
            img = Image.fromarray(rgb)
            img = img.resize((640, 640), Image.LANCZOS)

            # already resized to 640x640 above

            img.save(out_path)
            return True

    except Exception as e:
        print(f"    ⚠️  Error: {e}")
        return False

def main():
    # create output folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_FOLDER, 'has_pad'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_FOLDER, 'no_pad'), exist_ok=True)

    print("Loading Cyclomedia bus stop data...")
    fields, records = read_dbf(DBF_FILE)
    points = read_shp_points(SHP_FILE)
    print(f"  Found {len(records)} bus stops")

    # separate into has_pad and no_pad
    has_pad = []
    no_pad  = []
    for i, r in enumerate(records):
        if i >= len(points):
            break
        x, y = points[i]
        bus_pad1 = r.get('Bus Pad(', '').lower()
        bus_pad2 = r.get('Bus Pad ', '').lower()
        stop_id  = r.get('Bus Stop', f'stop_{i}')
        if bus_pad1 == 'y' or bus_pad2 == 'y':
            has_pad.append((stop_id, x, y))
        else:
            no_pad.append((stop_id, x, y))

    print(f"  WITH bus pad: {len(has_pad)}")
    print(f"  WITHOUT bus pad: {len(no_pad)}")

    # chip bus pad locations
    print(f"\nChipping {len(has_pad)} bus pad locations...")
    saved = 0
    for stop_id, x, y in has_pad:
        jp2_path, tx, ty = find_jp2_for_point(x, y, JP2_FOLDER)
        if jp2_path is None:
            print(f"  ⏭️  Stop {stop_id}: no tile found (outside download area)")
            continue
        out_path = os.path.join(OUTPUT_FOLDER, 'has_pad', f"pad_{stop_id}.png")
        print(f"  ✂️  Stop {stop_id} → {os.path.basename(jp2_path)}", end='')
        if chip_image(jp2_path, x, y, tx, ty, CHIP_SIZE_PX, out_path):
            print(" ✅")
            saved += 1
        else:
            print(" ❌")

    # chip no-pad locations (for negative training examples)
    print(f"\nChipping {len(no_pad)} no-pad locations (negative examples)...")
    saved_neg = 0
    for stop_id, x, y in no_pad:
        jp2_path, tx, ty = find_jp2_for_point(x, y, JP2_FOLDER)
        if jp2_path is None:
            continue
        out_path = os.path.join(OUTPUT_FOLDER, 'no_pad', f"nopad_{stop_id}.png")
        print(f"  ✂️  Stop {stop_id} → {os.path.basename(jp2_path)}", end='')
        if chip_image(jp2_path, x, y, tx, ty, CHIP_SIZE_PX, out_path):
            print(" ✅")
            saved_neg += 1
        else:
            print(" ❌")

    print(f"\n{'='*50}")
    print(f"Done!")
    print(f"  Bus pad chips saved:    {saved}  → {OUTPUT_FOLDER}/has_pad/")
    print(f"  No-pad chips saved:     {saved_neg} → {OUTPUT_FOLDER}/no_pad/")
    print(f"\nNext step: upload the 'has_pad' folder to Roboflow and label!")

if __name__ == "__main__":
    main()