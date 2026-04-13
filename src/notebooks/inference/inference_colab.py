"""
Stage 2 — YOLO Inference (Google Colab)
Run batched inference on chipped imagery, output per-tile prediction CSVs.

Usage in Colab:
    1. Upload chips.zip from Stage 1 and unzip to /content/.
    2. Upload trained YOLO26n model weights (.pt).
    3. Run all cells.

Alternatively, run as script:
    python inference_colab.py /path/to/stage1_output /path/to/model.pt \
        --batch-size 64 --conf 0.25
"""

# --- Cell 1: Setup & Imports ---

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# Colab-specific: install ultralytics if needed, unzip chips
# !pip install ultralytics -q
# !unzip -q /content/chips.zip -d /content/

from ultralytics import YOLO


# --- Cell 2: Configuration ---

def parse_args():
    """Parse CLI args. In Colab, set these directly below instead."""
    parser = argparse.ArgumentParser(description="Stage 2: YOLO inference on chips.")
    parser.add_argument("input_dir", help="Stage 1 output directory (contains chips/ and offsets/).")
    parser.add_argument("model_path", help="Path to trained YOLO26n .pt weights.")
    parser.add_argument("--batch-size", type=int, default=64, help="Inference batch size (default: 64).")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25).")
    parser.add_argument("--output-dir", default=None, help="Output directory for prediction CSVs. Defaults to input_dir/predictions.")
    return parser.parse_args()


# For Colab use: set these manually and skip parse_args()
COLAB_MODE = False  # Set True when running in Colab
COLAB_CONFIG = {
    "input_dir": "/content",
    "model_path": "/content/models/best.pt",
    "batch_size": 64,
    "conf": 0.25,
    "output_dir": None,
}


# --- Cell 3: Chip Grouping ---

def group_chips_by_tile(chip_dir: Path) -> dict[str, list[Path]]:
    """Group chip files by parent tile stem.

    Expects filenames like: {tile_stem}_r{row}_c{col}.{ext}
    Groups by everything before the last _rXXX_cXXX segment.
    """
    groups = defaultdict(list)
    for chip_path in sorted(chip_dir.iterdir()):
        if chip_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        # Strip _rXXX_cXXX.ext to get tile stem
        name = chip_path.stem
        # Find last occurrence of _r###_c###
        parts = name.rsplit("_c", 1)
        if len(parts) == 2:
            prefix = parts[0].rsplit("_r", 1)
            if len(prefix) == 2:
                tile_stem = prefix[0]
                groups[tile_stem].append(chip_path)
                continue
        # Fallback: couldn't parse, skip
        print(f"WARNING: could not parse tile stem from {chip_path.name}, skipping.", file=sys.stderr)

    return dict(groups)


# --- Cell 4: Inference ---

def run_inference_for_tile(
    model: YOLO,
    chip_paths: list[Path],
    batch_size: int,
    conf: float,
) -> list[dict]:
    """Run batched inference on chips for a single tile. Returns prediction records."""
    records = []

    for batch_start in range(0, len(chip_paths), batch_size):
        batch = chip_paths[batch_start : batch_start + batch_size]
        batch_strs = [str(p) for p in batch]

        results = model.predict(batch_strs, conf=conf, verbose=False)

        for chip_path, result in zip(batch, results):
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue

            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            class_ids = boxes.cls.cpu().numpy().astype(int)

            for i in range(len(boxes)):
                records.append(
                    {
                        "chip_filename": chip_path.name,
                        "x1": f"{xyxy[i][0]:.2f}",
                        "y1": f"{xyxy[i][1]:.2f}",
                        "x2": f"{xyxy[i][2]:.2f}",
                        "y2": f"{xyxy[i][3]:.2f}",
                        "confidence": f"{confs[i]:.4f}",
                        "class_id": class_ids[i],
                    }
                )

    return records


def write_prediction_csv(output_dir: Path, tile_stem: str, records: list[dict]):
    """Write per-tile prediction CSV."""
    fieldnames = ["chip_filename", "x1", "y1", "x2", "y2", "confidence", "class_id"]
    csv_path = output_dir / f"{tile_stem}_predictions.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


# --- Cell 5: Main ---

def main(config: dict):
    input_dir = Path(config["input_dir"])
    model_path = Path(config["model_path"])
    batch_size = config["batch_size"]
    conf = config["conf"]

    chip_dir = input_dir / "chips"
    if not chip_dir.is_dir():
        print(f"ERROR: chips directory not found at {chip_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(config["output_dir"]) if config["output_dir"] else input_dir / "predictions"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading model: {model_path}")
    model = YOLO(str(model_path))

    tile_groups = group_chips_by_tile(chip_dir)
    print(f"Found {sum(len(v) for v in tile_groups.values())} chips across {len(tile_groups)} tiles")
    print(f"Batch size: {batch_size}, confidence threshold: {conf}")
    print(f"Output: {output_dir}\n")

    total_detections = 0

    for i, (tile_stem, chip_paths) in enumerate(sorted(tile_groups.items()), 1):
        print(f"[{i}/{len(tile_groups)}] {tile_stem} ({len(chip_paths)} chips) ...", end=" ", flush=True)

        records = run_inference_for_tile(model, chip_paths, batch_size, conf)
        total_detections += len(records)

        if records:
            write_prediction_csv(output_dir, tile_stem, records)
            print(f"{len(records)} detections")
        else:
            print("0 detections")

    print(f"\nDone. {total_detections} total detections across {len(tile_groups)} tiles.")

    # Zip predictions and trigger download in Colab
    if COLAB_MODE:
        zip_path = shutil.make_archive(
            "/content/predictions",
            "zip",
            root_dir=str(input_dir),
            base_dir="predictions",
        )
        print(f"Zipped predictions → {zip_path}")

        from google.colab import files
        files.download(zip_path)


if __name__ == "__main__":
    if COLAB_MODE:
        main(COLAB_CONFIG)
    else:
        args = parse_args()
        main(vars(args))