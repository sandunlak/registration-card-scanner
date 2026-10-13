"""Safe image decoding, quality assessment, and reusable preprocessing operations."""

from __future__ import annotations

import io
import math
import warnings
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError, ValidationError

SUPPORTED_FORMATS = {
    ".jpg": ("JPEG", "image/jpeg"),
    ".jpeg": ("JPEG", "image/jpeg"),
    ".png": ("PNG", "image/png"),
    ".webp": ("WEBP", "image/webp"),
}
MAX_IMAGE_PIXELS = 40_000_000


@dataclass
class ImageProcessingResult:
    processed: bytes
    variants: dict[str, bytes]
    metadata: dict[str, Any]


def _encode_jpeg(image: np.ndarray, quality: int = 95) -> bytes:
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        raise ValidationError("Could not encode the processed image.")
    return encoded.tobytes()


def _order_points(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(differences)]
    ordered[3] = points[np.argmax(differences)]
    return ordered


def _card_boundary(image: np.ndarray) -> tuple[np.ndarray | None, bool]:
    height, width = image.shape[:2]
    scale = min(1.0, 1200 / max(height, width))
    sample = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image
    gray = cv2.cvtColor(sample, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue
        if cv2.contourArea(polygon) < sample.shape[0] * sample.shape[1] * 0.2:
            continue
        points = polygon.reshape(4, 2).astype("float32") / scale
        margin_x = width * 0.01
        margin_y = height * 0.01
        touches_edge = any(
            x <= margin_x or x >= width - margin_x or y <= margin_y or y >= height - margin_y
            for x, y in points
        )
        return points, touches_edge
    return None, False


def _perspective_correct(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    top_left, top_right, bottom_right, bottom_left = _order_points(points)
    width = int(max(np.linalg.norm(bottom_right - bottom_left), np.linalg.norm(top_right - top_left)))
    height = int(max(np.linalg.norm(top_right - bottom_right), np.linalg.norm(top_left - bottom_left)))
    if width < 2 or height < 2:
        raise ValidationError("Detected card boundary is too small to correct.")
    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype="float32",
    )
    transform = cv2.getPerspectiveTransform(_order_points(points), destination)
    return cv2.warpPerspective(image, transform, (width, height))


def _quality_warnings(image: np.ndarray, touches_edge: bool) -> list[str]:
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    warnings_list: list[str] = []
    if width * height < 500_000 or min(width, height) < 600:
        warnings_list.append("low_resolution")
    if cv2.Laplacian(gray, cv2.CV_64F).var() < 70:
        warnings_list.append("possible_blur")
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    if brightness < 55 or brightness > 210:
        warnings_list.append("poor_lighting")
    if contrast < 28:
        warnings_list.append("low_contrast")
    if touches_edge:
        warnings_list.append("card_may_be_cut_off")
    return warnings_list


def _apply_adjustments(
    image: np.ndarray,
    rotation: int = 0,
    crop: dict[str, float] | None = None,
) -> np.ndarray:
    if rotation not in (0, 90, 180, 270):
        raise ValidationError("Rotation must be 0, 90, 180, or 270 degrees.")
    if crop:
        x, y, width, height = (crop.get(key, 0.0) for key in ("x", "y", "width", "height"))
        if (
            not all(math.isfinite(value) for value in (x, y, width, height))
            or
            min(x, y, width, height) < 0
            or width <= 0
            or height <= 0
            or x + width > 1
            or y + height > 1
        ):
            raise ValidationError("Crop coordinates must be normalized fractions within the image.")
        image_height, image_width = image.shape[:2]
        left, top = round(x * image_width), round(y * image_height)
        right, bottom = round((x + width) * image_width), round((y + height) * image_height)
        if right - left < 2 or bottom - top < 2:
            raise ValidationError("Crop area is too small.")
        image = image[top:bottom, left:right]
    if rotation:
        rotate_code = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}[rotation]
        image = cv2.rotate(image, rotate_code)
    return image


def process_image(
    content: bytes,
    filename: str,
    content_type: str | None,
    *,
    max_pixels: int = MAX_IMAGE_PIXELS,
    rotation: int = 0,
    crop: dict[str, float] | None = None,
) -> ImageProcessingResult:
    """Validate and preprocess an image without changing its stored original bytes."""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    expected = SUPPORTED_FORMATS.get(extension)
    if not expected:
        raise UnsupportedFileTypeError("Use a JPEG, PNG, or WebP image.")
    expected_format, expected_mime = expected
    if content_type and content_type.lower().split(";")[0].strip() != expected_mime:
        raise UnsupportedFileTypeError("The declared image type does not match its file extension.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                if probe.format != expected_format:
                    raise UnsupportedFileTypeError("Image contents do not match the declared file type.")
                width, height = probe.size
                if width * height > max_pixels:
                    raise FileTooLargeError("Image dimensions exceed the maximum allowed pixel count.")
                probe.verify()
            with Image.open(io.BytesIO(content)) as source:
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                rgb = np.asarray(normalized)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise FileTooLargeError("Image dimensions exceed the maximum allowed pixel count.") from None
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("The uploaded file is not a valid, decodable image.") from exc

    color = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    color = _apply_adjustments(color, rotation, crop)
    points, touches_edge = _card_boundary(color)
    detected = points is not None
    if points is not None:
        try:
            color = _perspective_correct(color, points)
        except ValidationError:
            detected = False

    quality = _quality_warnings(color, touches_edge)
    if not detected:
        quality.append("boundary_not_detected")

    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    minimum_dimension = min(gray.shape)
    block_size = min(31, minimum_dimension if minimum_dimension % 2 else minimum_dimension - 1)
    if block_size < 3:
        thresholded = cv2.threshold(
            denoised, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )[1]
    else:
        thresholded = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 11
        )
    variants = {
        "grayscale": _encode_jpeg(gray),
        "denoised": _encode_jpeg(denoised),
        "contrast": _encode_jpeg(enhanced),
        "adaptive_threshold": cv2.imencode(".png", thresholded)[1].tobytes(),
    }
    return ImageProcessingResult(
        processed=_encode_jpeg(color),
        variants=variants,
        metadata={
            "width": int(color.shape[1]),
            "height": int(color.shape[0]),
            "original_width": width,
            "original_height": height,
            "boundary_detected": detected,
            "quality_warnings": quality,
        },
    )