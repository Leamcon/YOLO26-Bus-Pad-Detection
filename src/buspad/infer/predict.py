"""YOLO model loading and batched inference."""

from pathlib import Path

from ultralytics import YOLO


def load_model(model_path: Path) -> YOLO:
    """Load a YOLO model from any supported format.

    Ultralytics handles dispatch to the appropriate runtime backend
    based on the file extension / directory structure.  Exported formats
    (CoreML, ONNX, OpenVINO) do not embed task metadata, so we
    explicitly set ``task='detect'``.
    """
    return YOLO(str(model_path), task="detect")


def run_inference_for_tile(
    model: YOLO,
    chip_paths: list[Path],
    batch_size: int,
    conf: float,
    device: str,
) -> list[dict]:
    """Run batched inference on chips for a single tile."""
    records: list[dict] = []

    for batch_start in range(0, len(chip_paths), batch_size):
        batch = chip_paths[batch_start : batch_start + batch_size]
        batch_strs = [str(p) for p in batch]

        results = model.predict(
            batch_strs, conf=conf, device=device, verbose=False,
        )

        for chip_path, result in zip(batch, results):
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue

            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            cls = boxes.cls.cpu().numpy().astype(int)

            for j in range(len(boxes)):
                records.append(
                    {
                        "chip_filename": chip_path.name,
                        "x1": f"{xyxy[j][0]:.2f}",
                        "y1": f"{xyxy[j][1]:.2f}",
                        "x2": f"{xyxy[j][2]:.2f}",
                        "y2": f"{xyxy[j][3]:.2f}",
                        "confidence": f"{confs[j]:.4f}",
                        "class_id": cls[j],
                    }
                )

    return records
