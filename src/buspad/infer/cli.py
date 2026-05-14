"""CLI entry point and orchestration for buspad-infer."""

from __future__ import annotations

import argparse
import sys
import time

from buspad.config import add_root_arg, resolve_workspace
from buspad.infer.chips import group_chips_by_tile
from buspad.infer.defs import (
    MODEL_SIZES,
    build_chips_dir,
    build_predictions_dir,
    find_model,
)
from buspad.infer.device import resolve_device
from buspad.infer.formats import ModelFormat, check_runtime, clamp_batch_size
from buspad.infer.io import write_prediction_csv
from buspad.infer.predict import load_model, run_inference_for_tile

FORMAT_CHOICES: dict[str, ModelFormat] = {
    "pt": ModelFormat.PT,
    "onnx": ModelFormat.ONNX,
    "coreml": ModelFormat.COREML,
    "openvino": ModelFormat.OPENVINO,
}

_EPILOG = """\
workflow
-------
  buspad-infer runs YOLO object detection on chipped imagery produced by
  buspad-chip.  Per-tile prediction CSVs are written to the workspace
  output directory for downstream consumption by buspad-georef.

input paths (resolved from workspace)
--------------------------------------
  chips   data/chips/{boro|cd}/{name|number}/{year}/chips/
  model   models/{size}/  (file auto-detected by --format)

output path (created by this command)
--------------------------------------
  predictions   output/detections/{boro|cd}/{name|number}/{year}/predictions/

  Each source tile produces one CSV named {tile_stem}_predictions.csv
  containing chip-level bounding boxes (x1, y1, x2, y2), confidence,
  and class ID.

examples
--------
  # PyTorch nano model, borough-level chips
  buspad-infer nano --year 2024 --boro bronx

  # ONNX small model, community-district chips, explicit device
  buspad-infer small --year 2024 --cd 108 --format onnx --device cpu

  # Custom confidence threshold and batch size
  buspad-infer nano --year 2024 --boro manhattan --batch-size 32 --conf 0.6
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buspad-infer",
        description=(
            "Run YOLO object detection on chipped aerial imagery.  "
            "Reads chips produced by buspad-chip and writes per-tile "
            "prediction CSVs to the workspace output tree."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "model_size",
        choices=MODEL_SIZES,
        metavar="MODEL_SIZE",
        help=(
            "Model size to use for inference.  Resolves to "
            "<workspace>/models/{size}/.  Choices: %(choices)s."
        ),
    )

    parser.add_argument(
        "--year",
        required=True,
        help="Imagery vintage year (e.g. 2024).",
    )

    region = parser.add_mutually_exclusive_group(required=True)
    region.add_argument(
        "--boro",
        help=(
            "Borough name (e.g. bronx, manhattan).  Case-insensitive.  "
            "Chips are read from data/chips/boro/{name}/{year}/chips/."
        ),
    )
    region.add_argument(
        "--cd",
        help=(
            "Community district number (e.g. 108).  "
            "Chips are read from data/chips/cd/{number}/{year}/chips/."
        ),
    )

    parser.add_argument(
        "--format",
        choices=sorted(FORMAT_CHOICES),
        default="pt",
        dest="model_format",
        help=(
            "Model format (default: %(default)s).  The format must match "
            "a model file present in models/{size}/.  Non-PyTorch formats "
            "require the corresponding runtime package to be installed."
        ),
    )
    parser.add_argument(
        "--device",
        default=None,
        help=(
            "Inference device: mps | cuda | cpu.  Default: auto-detected "
            "from available hardware, constrained by format compatibility."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help=(
            "Inference batch size (default: %(default)s).  Automatically "
            "clamped to 1 for non-PyTorch formats."
        ),
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.5,
        help="Confidence threshold for detections (default: %(default)s).",
    )

    add_root_arg(parser)
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    workspace = resolve_workspace(args.root)

    # ---- resolve region ------------------------------------------------
    if args.boro:
        mode, name = "boro", args.boro.lower()
    else:
        mode, name = "cd", args.cd

    # ---- resolve model -------------------------------------------------
    fmt = FORMAT_CHOICES[args.model_format]
    model_path = find_model(workspace, args.model_size, fmt)

    # ---- resolve chip input --------------------------------------------
    chips_dir = build_chips_dir(workspace, mode, name, args.year)
    if not chips_dir.is_dir():
        print(
            f"ERROR: chips directory not found: {chips_dir}\n"
            f"  Run buspad-chip to generate chips before inference.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ---- validate runtime and device -----------------------------------
    check_runtime(fmt)
    device = resolve_device(args.device, fmt)
    batch_size = clamp_batch_size(args.batch_size, fmt)

    # ---- prepare output ------------------------------------------------
    predictions_dir = build_predictions_dir(workspace, mode, name, args.year)
    predictions_dir.mkdir(parents=True, exist_ok=True)

    # ---- banner --------------------------------------------------------
    print(f"Model:       {model_path}")
    print(f"Format:      {fmt.value}")
    print(f"Chips:       {chips_dir}")
    print(f"Output:      {predictions_dir}")
    print(f"Device:      {device}")
    print(f"Batch size:  {batch_size}")
    print(f"Confidence:  {args.conf}\n")

    # ---- inference loop ------------------------------------------------
    model = load_model(model_path)
    t0 = time.perf_counter()

    tile_groups = group_chips_by_tile(chips_dir)
    total_chips = sum(len(v) for v in tile_groups.values())
    print(f"Found {total_chips} chips across {len(tile_groups)} tiles\n")

    total_detections = 0

    for i, (tile_stem, chip_paths) in enumerate(
        sorted(tile_groups.items()), 1,
    ):
        print(
            f"[{i}/{len(tile_groups)}] {tile_stem} "
            f"({len(chip_paths)} chips) ...",
            end=" ",
            flush=True,
        )

        records = run_inference_for_tile(
            model, chip_paths, batch_size, args.conf, device,
        )
        total_detections += len(records)

        if records:
            write_prediction_csv(predictions_dir, tile_stem, records)
            print(f"{len(records)} detections")
        else:
            print("0 detections")

    # ---- summary -------------------------------------------------------
    elapsed = time.perf_counter() - t0
    minutes, seconds = divmod(elapsed, 60)

    print(
        f"\nDone. {total_detections} total detections "
        f"across {len(tile_groups)} tiles."
    )
    print(f"Predictions written to {predictions_dir}")
    print(f"Elapsed time: {int(minutes)}m {seconds:.1f}s")
