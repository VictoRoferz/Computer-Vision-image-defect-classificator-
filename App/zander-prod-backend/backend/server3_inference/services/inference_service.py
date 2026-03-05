"""
ML Inference Service using YOLOv8
Handles model loading, image inference, and result formatting for PCB defect detection.

Uses a pre-trained YOLOv8n model. The generic COCO classes are mapped to
PCB-relevant categories for demonstration. Replace the model file with a
fine-tuned checkpoint for production accuracy.
"""
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)

# Mapping from COCO classes to PCB defect categories for demo purposes.
# A fine-tuned model would have its own class names.
COCO_TO_PCB_MAP = {
    "person": "Other Defect",
    "cell phone": "Missing Component",
    "laptop": "Missing Component",
    "mouse": "Missing Component",
    "keyboard": "Missing Component",
    "book": "Good Joint",
    "clock": "Good Joint",
    "scissors": "Bridging",
    "knife": "Bridging",
    "fork": "Cold Joint",
    "spoon": "Insufficient Solder",
    "cup": "Excess Solder",
    "bottle": "Tombstoning",
    "remote": "Lifted Pad",
}


class InferenceService:
    """
    YOLOv8 inference service for PCB defect detection.
    """

    def __init__(self):
        self.model: Optional[YOLO] = None
        self.model_path = settings.model_path
        self.confidence_threshold = settings.confidence_threshold
        self.iou_threshold = settings.iou_threshold
        self.image_size = settings.image_size
        self.model_loaded = False
        self.model_info: Dict[str, Any] = {}

        logger.info(f"InferenceService created: model_path={self.model_path}")

    def load_model(self) -> None:
        """Load the YOLOv8 model. Downloads yolov8n.pt automatically if not present."""
        try:
            logger.info(f"Loading model from {self.model_path}...")
            start = time.time()

            self.model = YOLO(self.model_path)

            elapsed = time.time() - start
            self.model_loaded = True

            # Gather model info
            self.model_info = {
                "model_path": self.model_path,
                "model_type": str(type(self.model).__name__),
                "load_time_seconds": round(elapsed, 2),
                "class_count": len(self.model.names) if self.model.names else 0,
            }

            logger.info(
                f"Model loaded in {elapsed:.2f}s "
                f"({self.model_info['class_count']} classes)"
            )

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise RuntimeError(f"Model loading failed: {e}") from e

    def predict_image(
        self,
        image_path: str,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run inference on a single image.

        Args:
            image_path: Path to image file
            confidence: Override confidence threshold

        Returns:
            Dictionary with detections and metadata
        """
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        conf = confidence or self.confidence_threshold
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info(f"Running inference on {path.name} (conf={conf})")
        start = time.time()

        results = self.model.predict(
            source=str(path),
            conf=conf,
            iou=self.iou_threshold,
            imgsz=self.image_size,
            max_det=settings.max_detections,
            verbose=False,
        )

        elapsed = time.time() - start

        # Parse results
        detections = self._parse_results(results)

        # Read image dimensions
        img = cv2.imread(str(path))
        h, w = img.shape[:2] if img is not None else (0, 0)

        # Determine overall quality
        overall = self._determine_quality(detections)

        return {
            "image_path": str(path),
            "image_name": path.name,
            "image_size": {"width": w, "height": h},
            "inference_time_ms": round(elapsed * 1000, 1),
            "confidence_threshold": conf,
            "detections": detections,
            "detection_count": len(detections),
            "overall_quality": overall,
            "model": self.model_info,
        }

    def predict_bytes(
        self,
        image_bytes: bytes,
        filename: str = "upload.jpg",
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run inference on image bytes (from upload).

        Args:
            image_bytes: Raw image bytes
            filename: Original filename
            confidence: Override confidence threshold

        Returns:
            Dictionary with detections and metadata
        """
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        conf = confidence or self.confidence_threshold

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image bytes")

        h, w = img.shape[:2]

        logger.info(f"Running inference on uploaded image {filename} ({w}x{h}, conf={conf})")
        start = time.time()

        results = self.model.predict(
            source=img,
            conf=conf,
            iou=self.iou_threshold,
            imgsz=self.image_size,
            max_det=settings.max_detections,
            verbose=False,
        )

        elapsed = time.time() - start

        detections = self._parse_results(results)
        overall = self._determine_quality(detections)

        return {
            "image_name": filename,
            "image_size": {"width": w, "height": h},
            "inference_time_ms": round(elapsed * 1000, 1),
            "confidence_threshold": conf,
            "detections": detections,
            "detection_count": len(detections),
            "overall_quality": overall,
            "model": self.model_info,
        }

    def _parse_results(self, results) -> List[Dict[str, Any]]:
        """Parse YOLOv8 results into a list of detection dicts."""
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                box = boxes[i]
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # Get COCO class name
                coco_name = self.model.names.get(cls_id, f"class_{cls_id}")

                # Map to PCB defect category
                pcb_class = COCO_TO_PCB_MAP.get(coco_name, "Other Defect")

                detections.append({
                    "class": pcb_class,
                    "original_class": coco_name,
                    "confidence": round(confidence, 4),
                    "bbox": {
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                    },
                })

        # Sort by confidence descending
        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections

    def _determine_quality(self, detections: List[Dict[str, Any]]) -> str:
        """Determine overall quality based on detections."""
        if not detections:
            return "Pass"

        defect_classes = {
            "Cold Joint", "Insufficient Solder", "Excess Solder",
            "Bridging", "Missing Component", "Tombstoning", "Lifted Pad",
        }

        high_conf_defects = [
            d for d in detections
            if d["class"] in defect_classes and d["confidence"] > 0.5
        ]

        if len(high_conf_defects) >= 2:
            return "Fail"
        elif high_conf_defects:
            return "Needs Review"
        else:
            return "Pass"

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            "model_loaded": self.model_loaded,
            "model_info": self.model_info,
            "confidence_threshold": self.confidence_threshold,
        }


# Global instance
inference_service = InferenceService()
