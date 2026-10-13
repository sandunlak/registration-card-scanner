"""Explicit local download and verification of optional OCR model weights."""

from __future__ import annotations

import json
import importlib.metadata
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import shutil

from app.core.config import settings
from app.services.ocr_service import (
    PADDLE_DETECTION_ID,
    PADDLE_RECOGNITION_ID,
    TROCR_MODEL_ID,
    TROCR_REVISION,
    model_root,
)

logger = logging.getLogger(__name__)


def setup_models() -> dict[str, str]:
    """Download/verify local PaddleOCR and TrOCR checkpoints; never called at app startup."""
    root = model_root()
    paddle_dir = root / "paddle"
    detection_dir = paddle_dir / PADDLE_DETECTION_ID
    recognition_dir = paddle_dir / PADDLE_RECOGNITION_ID
    trocr_dir = root / "trocr"
    for directory in (detection_dir, recognition_dir, trocr_dir):
        directory.mkdir(parents=True, exist_ok=True)

    try:
        if importlib.metadata.version("paddleocr") != "3.7.0":
            raise RuntimeError("This setup requires the pinned PaddleOCR 3.7.0 package.")
        if importlib.metadata.version("transformers") != "5.19.0":
            raise RuntimeError("This setup requires the pinned Transformers 5.19.0 package.")
        if not importlib.metadata.version("torch").startswith("2.14.1"):
            raise RuntimeError("This setup requires the verified PyTorch 2.14.1 CPU runtime.")
        from paddleocr import TextDetection, TextRecognition
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        from huggingface_hub import snapshot_download
        import torch

        # Ensure paddle official models are downloaded and cached locally
        for model_id, target_dir in [
            (PADDLE_DETECTION_ID, detection_dir),
            (PADDLE_RECOGNITION_ID, recognition_dir),
        ]:
            if not any(target_dir.glob("*.safetensors")):
                if model_id == PADDLE_DETECTION_ID:
                    _ = TextDetection(model_name=model_id, engine="transformers", device="cpu")
                else:
                    _ = TextRecognition(model_name=model_id, engine="transformers", device="cpu")
                src_dir = Path.home() / ".paddlex" / "official_models" / f"{model_id}_safetensors"
                if src_dir.is_dir():
                    for item in src_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, target_dir / item.name)

        detector = TextDetection(
            model_name=PADDLE_DETECTION_ID,
            model_dir=str(detection_dir),
            engine="transformers",
            device="cpu",
        )
        recognizer = TextRecognition(
            model_name=PADDLE_RECOGNITION_ID,
            model_dir=str(recognition_dir),
            engine="transformers",
            device="cpu",
        )
        with tempfile.TemporaryDirectory(prefix="card-scanner-ocr-setup-") as temp_dir:
            blank = np.full((96, 384, 3), 255, dtype=np.uint8)
            sample_path = Path(temp_dir) / "blank.png"
            if not cv2.imwrite(str(sample_path), blank):
                raise RuntimeError("Could not create local OCR setup probe image.")
            detector.predict(input=str(sample_path), batch_size=1)
            recognizer.predict(input=[blank], batch_size=1)
            if not any(detection_dir.glob("*.safetensors")) or not any(
                recognition_dir.glob("*.safetensors")
            ):
                raise RuntimeError("PaddleOCR did not prepare both local model weight files.")

        snapshot_download(
            repo_id=TROCR_MODEL_ID,
            revision=TROCR_REVISION,
            local_dir=str(trocr_dir),
            cache_dir=str(root / "hf-cache"),
            allow_patterns=[
                "config.json",
                "generation_config.json",
                "merges.txt",
                "model.safetensors",
                "preprocessor_config.json",
                "special_tokens_map.json",
                "tokenizer_config.json",
                "vocab.json",
            ],
        )
        processor = TrOCRProcessor.from_pretrained(trocr_dir, local_files_only=True)
        model = VisionEncoderDecoderModel.from_pretrained(trocr_dir, local_files_only=True)
        model.to("cpu")
        model.eval()
        with torch.inference_mode():
            inputs = processor(images=Image.new("RGB", (160, 48), "white"), return_tensors="pt")
            model.generate(inputs.pixel_values, max_new_tokens=4, num_beams=1)
    except Exception as exc:
        (root / "models-ready.json").unlink(missing_ok=True)
        logger.error("OCR setup failed (%s)", type(exc).__name__)
        raise RuntimeError(
            "OCR model setup failed. Check the optional OCR requirements and local disk space."
        ) from exc

    manifest = {
        "paddle_detection_model": PADDLE_DETECTION_ID,
        "paddle_recognition_model": PADDLE_RECOGNITION_ID,
        "paddleocr_version": "3.7.0",
        "transformers_version": "5.19.0",
        "trocr_model": TROCR_MODEL_ID,
        "trocr_revision": TROCR_REVISION,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = root / "models-ready.json"
    temp_path = root / "models-ready.json.tmp"
    temp_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temp_path.replace(manifest_path)
    print(f"Local OCR models are ready under: {root}")
    print("No registration-card images were used by this setup command.")
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level)
    setup_models()