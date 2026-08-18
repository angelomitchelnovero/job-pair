"""Custom exceptions used across the application."""
from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppException):
    status_code = 404
    error_code = "not_found"


class ValidationError(AppException):
    status_code = 422
    error_code = "validation_error"


class ProcessingError(AppException):
    status_code = 500
    error_code = "processing_error"


class ModelNotFoundError(AppException):
    status_code = 503
    error_code = "model_not_loaded"


class FileTooLargeError(AppException):
    status_code = 413
    error_code = "file_too_large"


class InvalidFileTypeError(AppException):
    status_code = 415
    error_code = "invalid_file_type"
