"""
Stage 2 — Local YOLO Inference

Run batched inference on chipped imagery, output per-tile prediction CSVs.
Predictions are written to a `predictions/` directory alongside the input
chips directory.

Supports exported model formats (CoreML, ONNX, OpenVINO) in addition to
native .pt weights.  Model format is auto-detected from the path; device
compatibility is validated against the detected format.

Usage:
    cd dot_buspads_ml/src
    python -m inference path/to/best.onnx path/to/chips
    python -m inference path/to/best.mlpackage path/to/chips --device mps
    python -m inference path/to/best_openvino_model path/to/chips

Arguments:
    model_path      Path to model file or directory.
    chips_dir       Path to directory containing chip images.

Options:
    --device        Inference device: mps | cuda | cpu (default: auto per format).
    --batch-size    Inference batch size (default: 64).
    --conf          Confidence threshold (default: 0.25).
"""

from inference.cli import parse_args
from inference.chips import group_chips_by_tile
from inference.device import resolve_device
from inference.formats import detect_format, check_runtime
from inference.io import write_prediction_csv
from inference.predict import load_model, run_inference_for_tile


def main():
    args = parse_args()
    fmt = detect_format(args.model_path)
    check_runtime(fmt)
    device = resolve_device(args.device, fmt)

    output_dir = args.chips_dir.parent / "predictions"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Model:       {args.model_path}")
    print(f"Format:      {fmt.value}")
    print(f"Chips:       {args.chips_dir}")
    print(f"Output:      {output_dir}")
    print(f"Device:      {device}")
    print(f"Batch size:  {args.batch_size}")
    print(f"Confidence:  {args.conf}\n")

    model = load_model(args.model_path)

    tile_groups = group_chips_by_tile(args.chips_dir)
    total_chips = sum(len(v) for v in tile_groups.values())
    print(f"Found {total_chips} chips across {len(tile_groups)} tiles\n")

    total_detections = 0

    for i, (tile_stem, chip_paths) in enumerate(sorted(tile_groups.items()), 1):
        print(
            f"[{i}/{len(tile_groups)}] {tile_stem} ({len(chip_paths)} chips) ...",
            end=" ",
            flush=True,
        )

        records = run_inference_for_tile(
            model, chip_paths, args.batch_size, args.conf, device,
        )
        total_detections += len(records)

        if records:
            write_prediction_csv(output_dir, tile_stem, records)
            print(f"{len(records)} detections")
        else:
            print("0 detections")

    print(f"\nDone. {total_detections} total detections across {len(tile_groups)} tiles.")
    print(f"Predictions written to {output_dir}")


if __name__ == "__main__":
    main()