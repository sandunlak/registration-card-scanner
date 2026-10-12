"""Custom exception classes for the Registration Card Scanner API.

All domain exceptions inherit from AppError so that a single exception
handler in main.py can produce consistent JSON error responses.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found."


class ValidationError(AppError):
    status_code = 422
    detail = "Validation failed."


class UnsupportedFileTypeError(AppError):
    status_code = 415
    detail = "Unsupported file type."


class FileTooLargeError(AppError):
    status_code = 413
    detail = "Uploaded file exceeds the maximum allowed size."


class OCRUnavailableError(AppError):
    status_code = 503
    detail = "OCR service is not available."
