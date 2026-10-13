"""Lazy, local-only adapters for printed OCR and selected handwriting crops."""

from __future__ import annotations

import importlib.metadata
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.exceptions import OCRUnavailableError, ValidationError
from app.schemas.ocr import HandwritingRegion

logger = logging.getLogger(__name__)

PADDLE_DETECTION_ID = "PP-OCRv6_small_det"
PADDLE_RECOGNITION_ID = "PP-OCRv6_small_rec"
TROCR_MODEL_ID = "microsoft/trocr-base-handwritten"
TROCR_REVISION = "eaacaf452b06415df8f10bb6fad3a4c11e609406"


@dataclass(frozen=True)
class RecognizedRegion:
    text: str
    polygon: list[list[float]]
    recognition_type: str
    model_id: str
    model_version: str
    confidence: float | None
    extra_metadata: dict[str, Any]


class OcrPipeline(Protocol):
    def recognize(
        self, image_path: Path, handwriting_regions: list[HandwritingRegion]
    ) -> tuple[list[RecognizedRegion], int, int]: ...


def model_root() -> Path:
    return Path(settings.ocr_models_dir).expanduser().resolve()


def _load_model_manifest() -> dict[str, Any]:
    manifest_path = model_root() / "models-ready.json"
    if not manifest_path.is_file():
        raise OCRUnavailableError(
            "OCR models are not installed. Run `python -m app.services.ocr_setup` from backend/."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OCRUnavailableError("The local OCR model manifest is missing or invalid.") from exc
    if manifest.get("paddle_detection_model") != PADDLE_DETECTION_ID or manifest.get(
        "paddle_recognition_model"
    ) != PADDLE_RECOGNITION_ID:
        raise OCRUnavailableError("Installed OCR models do not match this application version.")
    if manifest.get("trocr_model") != TROCR_MODEL_ID:
        raise OCRUnavailableError("Installed TrOCR model does not match this application version.")
    return manifest


def _result_json(result: Any) -> dict[str, Any]:
    payload = getattr(result, "json", None)
    if callable(payload):
        payload = payload()
    if not isinstance(payload, dict):
        return {}
    nested = payload.get("res")
    return nested if isinstance(nested, dict) else payload


def _polygon(value: Any) -> list[list[float]] | None:
    try:
        points = np.asarray(value, dtype=np.float32).reshape(-1, 2)
    except (TypeError, ValueError):
        return None
    if len(points) < 4 or not np.isfinite(points).all():
        return None
    return [[float(x), float(y)] for x, y in points]


def _rectify_region(image: np.ndarray, polygon: list[list[float]]) -> np.ndarray:
    points = np.asarray(polygon, dtype=np.float32)
    x_min = max(0, int(np.floor(points[:, 0].min())))
    y_min = max(0, int(np.floor(points[:, 1].min())))
    x_max = min(image.shape[1], int(np.ceil(points[:, 0].max())))
    y_max = min(image.shape[0], int(np.ceil(points[:, 1].max())))
    crop = image[y_min:y_max, x_min:x_max]
    if crop.size == 0:
        raise ValidationError("OCR detected a text region outside the processed image.")
    return crop


class PaddlePrintedOcr:
    """PaddleOCR detector/recognizer on its local Transformers CPU engine."""

    def __init__(self, detector: Any, recognizer: Any) -> None:
        self.detector = detector
        self.recognizer = recognizer
        self.version = importlib.metadata.version("paddleocr")

    @classmethod
    def load(cls) -> PaddlePrintedOcr:
        manifest = _load_model_manifest()
        model_dir = model_root() / "paddle"
        detector_dir = model_dir / PADDLE_DETECTION_ID
        recognizer_dir = model_dir / PADDLE_RECOGNITION_ID
        if (
            not detector_dir.is_dir()
            or not recognizer_dir.is_dir()
            or not any(detector_dir.glob("*.safetensors"))
            or not any(recognizer_dir.glob("*.safetensors"))
        ):
            raise OCRUnavailableError("The local PaddleOCR model files are incomplete; rerun OCR setup.")
        try:
            from paddleocr import TextDetection, TextRecognition

            return cls(
                TextDetection(
                    model_name=PADDLE_DETECTION_ID,
                    model_dir=str(detector_dir),
                    engine="transformers",
                    device="cpu",
                ),
                TextRecognition(
                    model_name=PADDLE_RECOGNITION_ID,
                    model_dir=str(recognizer_dir),
                    engine="transformers",
                    device="cpu",
                ),
            )
        except ImportError as exc:
            raise OCRUnavailableError("Optional PaddleOCR/Transformers packages are not installed.") from exc
        except Exception as exc:
            logger.warning("Local PaddleOCR initialization failed (%s)", type(exc).__name__)
            raise OCRUnavailableError("Local PaddleOCR models could not be loaded.") from exc

    def recognize(self, image_path: Path, image: np.ndarray) -> list[RecognizedRegion]:
        try:
            detection_results = self.detector.predict(input=str(image_path), batch_size=1)
            if not detection_results:
                return []
            detection = _result_json(detection_results[0])
            polygons = detection.get("dt_polys") or []
            detection_scores = detection.get("dt_scores") or []
            valid: list[tuple[list[list[float]], float | None, np.ndarray]] = []
            for index, raw_polygon in enumerate(polygons):
                polygon = _polygon(raw_polygon)
                if polygon is None:
                    continue
                score = _score(detection_scores[index]) if index < len(detection_scores) else None
                valid.append((polygon, score, _rectify_region(image, polygon)))
            if not valid:
                return []

            recognition_results = self.recognizer.predict(
                input=[entry[2] for entry in valid], batch_size=min(8, len(valid))
            )
            recognized: list[RecognizedRegion] = []
            for index, detection_entry in enumerate(valid):
                if index >= len(recognition_results):
                    break
                result = _result_json(recognition_results[index])
                text = result.get("rec_text")
                if text is None:
                    texts = result.get("rec_texts") or []
                    text = texts[0] if texts else ""
                confidence = result.get("rec_score")
                if confidence is None:
                    scores = result.get("rec_scores") or []
                    confidence = scores[0] if scores else None
                recognized.append(
                    RecognizedRegion(
                        text=str(text),
                        polygon=detection_entry[0],
                        recognition_type="printed",
                        model_id=f"PaddleOCR/{PADDLE_DETECTION_ID}+{PADDLE_RECOGNITION_ID}",
                        model_version=self.version,
                        confidence=_score(confidence),
                        extra_metadata={"detection_confidence": detection_entry[1]},
                    )
                )
            return recognized
        except (OCRUnavailableError, ValidationError):
            raise
        except Exception as exc:
            logger.warning("PaddleOCR inference failed (%s)", type(exc).__name__)
            raise ValidationError("Printed-text recognition failed for this image.") from exc


class TrOcrHandwriting:
    """Handwritten line reader; instantiated only if a user supplies line crops."""

    def __init__(self, processor: Any, model: Any) -> None:
        self.processor = processor
        self.model = model

    @classmethod
    def load(cls) -> TrOcrHandwriting:
        _load_model_manifest()
        model_dir = model_root() / "trocr"
        if not (model_dir / "model.safetensors").is_file():
            raise OCRUnavailableError("The local TrOCR checkpoint is missing; rerun OCR setup.")
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            processor = TrOCRProcessor.from_pretrained(model_dir, local_files_only=True)
            model = VisionEncoderDecoderModel.from_pretrained(model_dir, local_files_only=True)
            model.to("cpu")
            model.eval()
            return cls(processor, model)
        except ImportError as exc:
            raise OCRUnavailableError("Optional TrOCR/PyTorch packages are not installed.") from exc
        except Exception as exc:
            logger.warning("Local TrOCR initialization failed (%s)", type(exc).__name__)
            raise OCRUnavailableError("The local handwritten-text model could not be loaded.") from exc

    def recognize(self, crop: np.ndarray) -> str:
        try:
            import torch

            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pixels = self.processor(images=Image.fromarray(rgb), return_tensors="pt").pixel_values
            with torch.inference_mode():
                generated = self.model.generate(pixels, max_new_tokens=128, num_beams=1)
            return str(self.processor.batch_decode(generated, skip_special_tokens=True)[0]).strip()
        except Exception as exc:
            logger.warning("TrOCR line inference failed (%s)", type(exc).__name__)
            raise ValidationError("Handwritten-line recognition failed for this image.") from exc


def _score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(score) or not 0 <= score <= 1:
        return None
    return score


def _handwriting_crop(
    image: np.ndarray, selection: HandwritingRegion
) -> tuple[np.ndarray, list[list[float]]]:
    image_height, image_width = image.shape[:2]
    left = max(0, int(round(selection.x * image_width)))
    top = max(0, int(round(selection.y * image_height)))
    right = min(image_width, int(round((selection.x + selection.width) * image_width)))
    bottom = min(image_height, int(round((selection.y + selection.height) * image_height)))
    if right - left < 2 or bottom - top < 2:
        raise ValidationError("Handwriting crop is too small to recognize.")
    polygon = [
        [float(left), float(top)],
        [float(right), float(top)],
        [float(right), float(bottom)],
        [float(left), float(bottom)],
    ]
    return image[top:bottom, left:right], polygon


class LocalOcrPipeline:
    """Combine printed page OCR with optional, explicitly selected handwriting lines."""

    def __init__(self, printed: PaddlePrintedOcr, handwriting_loader=TrOcrHandwriting.load) -> None:
        self.printed = printed
        self._handwriting_loader = handwriting_loader
        self._handwriting: TrOcrHandwriting | None = None
        self._handwriting_lock = threading.Lock()

    def _get_handwriting(self) -> TrOcrHandwriting:
        with self._handwriting_lock:
            if self._handwriting is None:
                self._handwriting = self._handwriting_loader()
            return self._handwriting

    def recognize(
        self, image_path: Path, handwriting_regions: list[HandwritingRegion]
    ) -> tuple[list[RecognizedRegion], int, int]:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValidationError("The processed image is missing or unreadable.")
        results = self.printed.recognize(image_path, image)
        if handwriting_regions:
            handwriting = self._get_handwriting()
            for selection in handwriting_regions:
                crop, polygon = _handwriting_crop(image, selection)
                results.append(
                    RecognizedRegion(
                        text=handwriting.recognize(crop),
                        polygon=polygon,
                        recognition_type="handwritten",
                        model_id=TROCR_MODEL_ID,
                        model_version=TROCR_REVISION,
                        confidence=None,
                        extra_metadata={"confidence_available": False},
                    )
                )
        return results, image.shape[1], image.shape[0]


_pipeline: LocalOcrPipeline | None = None
_pipeline_lock = threading.Lock()


def create_ocr_pipeline() -> LocalOcrPipeline:
    """Return a process-local lazy singleton; no model loads during app startup."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = LocalOcrPipeline(PaddlePrintedOcr.load())
    return _pipeline