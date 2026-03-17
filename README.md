# YOLO26-Bus-Pad-Detection
Implementing YOLO26 toolbox for the detection of bus pads in orthoimagery of New York City


# Bus Pad Detection — YOLO26
NYC DOT Bus Pad Detection Model using YOLO26 and aerial orthoimagery.


## Full Pipeline

### STEP 1 — Prepare Your Data (Local or Colab)

Download the following and place in a folder (e.g. `jp2_207/`):
- JP2 aerial tiles for your target Community District
- Cyclomedia `Point_3D` shapefile files (`.shp`, `.dbf`, `.prj`, `.shx`)

To find which JP2 tiles cover your CD, use the tile index shapefile from NYS GIS.

---

### STEP 2 — Chip Images (Google Colab)

Open a new Colab notebook at [colab.research.google.com](https://colab.research.google.com)

**Cell 1 — Mount Google Drive**
```python
from google.colab import drive
drive.mount('/content/drive')
```

**Cell 2 — Check files are in place**
```python
import os
os.listdir('/content/drive/MyDrive/buspad/jp2_207 (1)/')
```

**Cell 3 — Install libraries**
```python
!pip install rasterio Pillow
```

**Cell 4 — Fix paths in chip_images.py**
** edit base on own drive **

```python
script = open('/content/drive/MyDrive/buspad/chip_images.py').read()
script = script.replace(
    '/Users/wendy/Desktop/buspad/jp2_207',
    '/content/drive/MyDrive/buspad/jp2_207 (1)'
)
script = script.replace(
    '/Users/wendy/Desktop/buspad/chips',
    '/content/drive/MyDrive/buspad/chips'
)
open('/content/drive/MyDrive/buspad/chip_images.py', 'w').write(script)
print('Paths updated!')
```

**Cell 5 — Find any missing tiles**
```python
needed = []
folder = '/content/drive/MyDrive/buspad/jp2_207 (1)/'
existing = [f for f in os.listdir(folder) if f.endswith('.jp2')]
import struct

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

points = read_shp_points(
    '/content/drive/MyDrive/buspad/jp2_207 (1)/Point_3D.shp'
)

for x, y in points:
    tx = (int(x) // 2500) * 2500
    ty = (int(y) // 2500) * 2500
    tx_name = (tx - 1000000) // 1000
    ty_name = ty // 1000
    tile_name = f'{int(tx_name):03d}{int(ty_name):03d}.jp2'
    if tile_name not in existing:
        needed.append(tile_name)

needed = sorted(set(needed))
print(f'Still need {len(needed)} tiles:')
for t in needed:
    print(f'  {t}')
```

**Cell 6 — Run chipping script**
```python
!python /content/drive/MyDrive/buspad/chip_images.py
```

**Output:**
```
chips/
├── has_pad/   ← images WITH bus pads → upload to Roboflow
└── no_pad/    ← images WITHOUT bus pads
```

---

### STEP 3 — Label Images (Roboflow)

// https://app.roboflow.com/join/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3b3Jrc3BhY2VJZCI6Ilh5M2VsWWlyZVlYQ25pVGIzWHJUVkttQ21XQzMiLCJyb2xlIjoib3duZXIiLCJpbnZpdGVyIjoid2VuZHl6aGVuZzk1MEBnbWFpbC5jb20iLCJpYXQiOjE3NzMyNTQ5OTV9.v9xaw2IVPN42nkdInImmwEgjVIAs8kw4D00T7FCgo2A

//put all data^, chipping script may not be totally accurate can check if no_pad has buspad then also upload it to Roboflow


1. Go to [roboflow.com](https://roboflow.com) → sign up free
2. `New Project` → name: `buspad-detection` → type: `Object Detection`
3. Upload all images from `chips/has_pad/`
4. For each image draw a box around the bus pad → label it `bus_pad`
5. Click `Generate Dataset` → export as `YOLOv8` format
6. Copy the export code snippet (looks like below)

```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("your-workspace").project("buspad-detection")
version = project.version(1)
dataset = version.download("yolov8")
```

---

### STEP 4 — Train YOLO26 (Google Colab)

Open a new Colab notebook. First set GPU:
```
Runtime → Change Runtime Type → T4 GPU → Save
```

**Cell 1 — Install libraries**
```python
!pip install roboflow ultralytics
```

**Cell 2 — Download labeled dataset from Roboflow**
```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("your-workspace").project("buspad-detection")
version = project.version(1)
dataset = version.download("yolov8")
```

**Cell 3 — Train YOLO26**
```python
from ultralytics import YOLO

model = YOLO('yolo26n.pt')
model.train(
    data=dataset.location + "/data.yaml",
    epochs=50,
    imgsz=640,
    batch=8,
    name='buspad_yolo26'
)
print('Training complete!')
```

**Cell 4 — Save model to Drive**
```python
from google.colab import drive
drive.mount('/content/drive')

import shutil
shutil.copytree(
    '/content/runs/detect/buspad_yolo26',
    '/content/drive/MyDrive/buspad/model'
)
print('Model saved to Drive!')
```

---


## Current Model Performance (Initial Run)

| Metric | Value | Notes |
|---|---|---|
| mAP50 | 11.9% | Low — small dataset |
| mAP50-95 | 3.5% | Needs more training data |
| Recall | 66.7% | Finds 2 out of 3 bus pads |
| Training images | ~15 labeled | Need 100-200 for good accuracy |
| Epochs | 50 | |
| Hardware | CPU | Use T4 GPU for better results |
