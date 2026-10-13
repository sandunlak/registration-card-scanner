"""Focused tests for safe image decoding and preprocessing."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError, ValidationError
from app.services.image_processing import process_image


def make_png(size: tuple[int, int] = (900, 700)) -> bytes:
    image = Image.new("RGB", size, (240, 235, 220))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_processes_color_fallback_and_generates_independent_variants() -> None:
    result = process_image(make_png(), "card.png", "image/png")

    assert result.processed.startswith(b"\xff\xd8")
    assert set(result.variants) == {"grayscale", "denoised", "contrast", "adaptive_threshold"}
    assert "boundary_not_detected" in result.metadata["quality_warnings"]
    assert result.metadata["boundary_detected"] is False


def test_rejects_wrong_extension_and_content() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        process_image(make_png(), "card.gif", "image/gif")
    with pytest.raises(UnsupportedFileTypeError):
        process_image(make_png(), "card.jpg", "image/jpeg")


def test_rejects_corrupt_content_and_excessive_pixel_count() -> None:
    with pytest.raises(ValidationError, match="valid, decodable"):
        process_image(b"not an image", "card.png", "image/png")
    with pytest.raises(FileTooLargeError, match="pixel count"):
        process_image(make_png(), "card.png", "image/png", max_pixels=100)


def test_exif_orientation_is_normalized_for_processing() -> None:
    image = Image.new("RGB", (800, 1200), (30, 100, 180))
    exif = Image.Exif()
    exif[274] = 6
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)

    result = process_image(output.getvalue(), "card.jpg", "image/jpeg")

    assert result.metadata["original_width"] == 800
    assert result.metadata["original_height"] == 1200
    assert result.metadata["width"] > result.metadata["height"]


def test_very_small_image_gets_quality_warnings_instead_of_threshold_failure() -> None:
    result = process_image(make_png((8, 8)), "tiny.png", "image/png")

    assert "low_resolution" in result.metadata["quality_warnings"]
    assert "boundary_not_detected" in result.metadata["quality_warnings"]
    assert result.variants["adaptive_threshold"].startswith(b"\x89PNG")