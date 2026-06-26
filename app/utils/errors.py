from __future__ import annotations


class AppError(Exception):
    status_code: int = 400
    error_code: str = "app_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidSensorError(AppError):
    status_code = 404
    error_code = "invalid_sensor"


class InvalidADCError(AppError):
    status_code = 422
    error_code = "invalid_adc"


class ConversionError(AppError):
    status_code = 422
    error_code = "conversion_error"


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
