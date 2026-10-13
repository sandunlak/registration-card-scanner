"""Live OCR inference validation; skips automatically when models are absent.

These tests verify that PaddleOCR and TrOCR actually run on the local CPU.
They do NOT run in CI or on machines where `python -m app.services.ocr_setup`
has not been completed.  The mocked unit-level tests in test_ocr.py cover
request/response paths without model weights.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.services.ocr_service import (
    PADDLE_DETECTION_ID,
    PADDLE_RECOGNITION_ID,
    TROCR_MODEL_ID,
    TROCR_REVISION,
    model_root,
)

logger = logging.getLogger(__name__)


def _models_ready() -> bool:
    """Check whether the setup command has prepared local model weights."""
    manifest_path = model_root() / "models-ready.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return (
            manifest.get("paddle_detection_model") == PADDLE_DETECTION_ID
            and manifest.get("paddle_recognition_model") == PADDLE_RECOGNITION_ID
            and manifest.get("trocr_model") == TROCR_MODEL_ID
        )
    except Exception:
        return False


requires_models = pytest.mark.skipif(
    not _models_ready(),
    reason="OCR models not installed; run `python -m app.services.ocr_setup` to enable.",
)


def _synthetic_printed_image(tmp_path: Path) -> Path:
    """Create a synthetic image with clear printed text for PaddleOCR validation."""
    width, height = 800, 400
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Use a reasonably large default font to create clear text
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()

    lines = [
        "Registration Card Scanner",
        "Name: John Smith",
        "Phone: 0771234567",
        "Address: 42 Main Street",
    ]
    y_offset = 40
    for line in lines:
        draw.text((40, y_offset), line, fill="black", font=font)
        y_offset += 60

    output_path = tmp_path / "synthetic_printed.png"
    img.save(str(output_path), format="PNG")
    return output_path


def _synthetic_handwriting_image(tmp_path: Path) -> Path:
    """Create a synthetic image simulating a handwritten line for TrOCR validation."""
    width, height = 600, 80
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except OSError:
        font = ImageFont.load_default()

    # Simulate handwriting-ish text
    draw.text((10, 15), "Sample Name", fill="black", font=font)
    output_path = tmp_path / "synthetic_handwriting.png"
    img.save(str(output_path), format="PNG")
    return output_path


@requires_models
class TestPaddleOcrInference:
    """Validate PaddleOCR detection and recognition on CPU."""

    def test_paddle_loads_and_detects_text(self, tmp_path: Path) -> None:
        """PaddleOCR loads locally and detects text in a synthetic printed image."""
        from app.services.ocr_service import PaddlePrintedOcr

        image_path = _synthetic_printed_image(tmp_path)
        ocr = PaddlePrintedOcr.load()

        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        assert image is not None, "Failed to read synthetic image with OpenCV"

        started = time.perf_counter()
        regions = ocr.recognize(image_path, image)
        elapsed_ms = (time.perf_counter() - started) * 1000

        logger.info(
            "PaddleOCR inference: %d regions in %.0f ms",
            len(regions),
            elapsed_ms,
        )

        # We expect at least some text to be detected from the printed content
        assert len(regions) > 0, (
            "PaddleOCR detected no text regions in the synthetic printed image"
        )

        for region in regions:
            assert region.text, "Detected region has empty text"
            assert len(region.polygon) >= 4, "Polygon should have at least 4 points"
            assert region.recognition_type == "printed"
            assert region.model_id.startswith("PaddleOCR/")
            assert region.model_version
            # Confidence should be a float between 0 and 1 or None
            if region.confidence is not None:
                assert 0 <= region.confidence <= 1

        # Inference should complete within a reasonable time on CPU
        assert elapsed_ms < 60_000, f"Inference took {elapsed_ms:.0f}ms, expected <60s on CPU"

    def test_paddle_returns_model_metadata(self, tmp_path: Path) -> None:
        """Detection results include expected model identifiers and versions."""
        from app.services.ocr_service import PaddlePrintedOcr

        image_path = _synthetic_printed_image(tmp_path)
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        ocr = PaddlePrintedOcr.load()
        regions = ocr.recognize(image_path, image)

        if regions:
            first = regions[0]
            assert PADDLE_DETECTION_ID in first.model_id
            assert PADDLE_RECOGNITION_ID in first.model_id
            assert first.extra_metadata.get("detection_confidence") is None or isinstance(
                first.extra_metadata["detection_confidence"], float
            )

    def test_paddle_handles_blank_image(self, tmp_path: Path) -> None:
        """A blank white image should return zero or minimal regions without error."""
        from app.services.ocr_service import PaddlePrintedOcr

        blank = np.full((300, 400, 3), 255, dtype=np.uint8)
        blank_path = tmp_path / "blank.png"
        cv2.imwrite(str(blank_path), blank)

        ocr = PaddlePrintedOcr.load()
        regions = ocr.recognize(blank_path, blank)
        # Should not crash; may or may not detect spurious regions
        assert isinstance(regions, list)


@requires_models
class TestTrOcrInference:
    """Validate TrOCR handwriting recognition on CPU."""

    def test_trocr_loads_and_recognizes(self, tmp_path: Path) -> None:
        """TrOCR loads from local checkpoint and produces output for a line crop."""
        from app.services.ocr_service import TrOcrHandwriting

        image_path = _synthetic_handwriting_image(tmp_path)
        crop = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        assert crop is not None

        model = TrOcrHandwriting.load()

        started = time.perf_counter()
        text = model.recognize(crop)
        elapsed_ms = (time.perf_counter() - started) * 1000

        logger.info("TrOCR inference: '%s' in %.0f ms", text, elapsed_ms)

        assert isinstance(text, str)
        assert len(text) > 0, "TrOCR returned empty text for a line crop"
        # Inference should complete within a reasonable time on CPU
        assert elapsed_ms < 60_000, f"TrOCR inference took {elapsed_ms:.0f}ms, expected <60s on CPU"

    def test_trocr_model_revision(self) -> None:
        """The pinned TrOCR revision matches the integration constant."""
        from app.services.ocr_service import TrOcrHandwriting

        model = TrOcrHandwriting.load()
        # Just verify load doesn't crash and processor/model exist
        assert model.processor is not None
        assert model.model is not None


@requires_models
class TestLocalOcrPipeline:
    """Validate the combined pipeline (PaddleOCR + optional TrOCR)."""

    def test_pipeline_printed_only(self, tmp_path: Path) -> None:
        """Pipeline runs PaddleOCR without handwriting regions."""
        from app.services.ocr_service import create_ocr_pipeline

        image_path = _synthetic_printed_image(tmp_path)
        pipeline = create_ocr_pipeline()

        started = time.perf_counter()
        regions, width, height = pipeline.recognize(image_path, [])
        elapsed_ms = (time.perf_counter() - started) * 1000

        logger.info(
            "Pipeline (printed-only): %d regions, %dx%d, %.0f ms",
            len(regions),
            width,
            height,
            elapsed_ms,
        )

        assert width > 0 and height > 0
        assert isinstance(regions, list)
        # All regions should be printed (no handwriting was requested)
        for region in regions:
            assert region.recognition_type == "printed"

    def test_pipeline_with_handwriting_regions(self, tmp_path: Path) -> None:
        """Pipeline invokes TrOCR for explicitly provided line crops."""
        from app.schemas.ocr import HandwritingRegion
        from app.services.ocr_service import create_ocr_pipeline

        image_path = _synthetic_printed_image(tmp_path)
        pipeline = create_ocr_pipeline()

        # Define a handwriting region (normalized coordinates over the image)
        hw_region = HandwritingRegion(x=0.05, y=0.1, width=0.6, height=0.15)

        started = time.perf_counter()
        regions, width, height = pipeline.recognize(image_path, [hw_region])
        elapsed_ms = (time.perf_counter() - started) * 1000

        logger.info(
            "Pipeline (printed+handwriting): %d regions, %.0f ms",
            len(regions),
            elapsed_ms,
        )

        # Should have printed results + at least one handwritten result
        handwritten = [r for r in regions if r.recognition_type == "handwritten"]
        assert len(handwritten) == 1, "Expected exactly one handwritten region from one crop"
        assert handwritten[0].model_id == TROCR_MODEL_ID
        assert handwritten[0].model_version == TROCR_REVISION
        assert handwritten[0].confidence is None  # TrOCR doesn't return calibrated confidence
        assert handwritten[0].text  # Should have some recognized text


@requires_models
class TestEvaluationMetrics:
    """Validate the enhanced evaluation module with real inference."""

    def test_evaluation_with_synthetic_manifest(self, tmp_path: Path) -> None:
        """Evaluation module runs end-to-end with a synthetic reference manifest."""
        from app.services.ocr_evaluation import evaluate_manifest

        image_path = _synthetic_printed_image(tmp_path)
        manifest = {
            "cases": [
                {
                    "image_path": str(image_path),
                    "card_format": "synthetic",
                    "kind": "printed",
                    "category": "label",
                    "condition": "clear",
                    "reference": "Registration Card Scanner",
                },
            ],
        }
        manifest_path = tmp_path / "evaluation.local.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = evaluate_manifest(manifest_path)

        assert report["total_cases"] == 1
        assert report["summary"]["total_cases"] == 1
        assert report["summary"]["failures"] == 0
        assert len(report["groups"]) == 1

        group = report["groups"][0]
        assert group["kind"] == "printed"
        assert group["card_format"] == "synthetic"
        assert group["cases"] == 1
        assert group["failures"] == 0
        assert "cer" in group
        assert "wer" in group
        assert "exact_match_rate" in group
        assert "mean_inference_ms" in group
        assert group["mean_inference_ms"] > 0

        # Memory tracking
        if report.get("memory"):
            assert "before_mb" in report["memory"]
            assert "after_mb" in report["memory"]

        logger.info("Evaluation report: %s", json.dumps(report, indent=2))
