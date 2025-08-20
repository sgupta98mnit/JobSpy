"""
Error models and exception classes for the job search web application.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    """
    Standard error response model for API endpoints.
    """
    error_code: str = Field(
        description="Machine-readable error code"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    retry_after: Optional[int] = Field(
        None,
        description="Seconds to wait before retrying (for rate limits)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "details": {
                    "site": "linkedin",
                    "limit": 100,
                    "window": "1 hour"
                },
                "retry_after": 300
            }
        }
    )


class ValidationErrorDetail(BaseModel):
    """
    Detailed validation error information.
    """
    field: str = Field(
        description="Field name that failed validation"
    )
    message: str = Field(
        description="Validation error message"
    )
    invalid_value: Any = Field(
        description="The invalid value that was provided"
    )


class ValidationErrorResponse(ErrorResponse):
    """
    Validation error response with field-specific details.
    """
    validation_errors: List[ValidationErrorDetail] = Field(
        description="List of field validation errors"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "validation_errors": [
                    {
                        "field": "results_wanted",
                        "message": "Value must be between 1 and 100",
                        "invalid_value": 150
                    }
                ]
            }
        }
    )


# Exception Classes

class JobSearchError(Exception):
    """
    Base exception class for job search related errors.
    """
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_error_response(self) -> ErrorResponse:
        """Convert exception to ErrorResponse model."""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details
        )


class ValidationError(JobSearchError):
    """
    Exception for request validation errors.
    """
    def __init__(self, message: str, field_errors: Optional[List[ValidationErrorDetail]] = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field_errors = field_errors or []

    def to_validation_error_response(self) -> ValidationErrorResponse:
        """Convert exception to ValidationErrorResponse model."""
        return ValidationErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            validation_errors=self.field_errors
        )


class RateLimitError(JobSearchError):
    """
    Exception for rate limiting errors.
    """
    def __init__(self, message: str, site: str, retry_after: Optional[int] = None):
        details = {"site": site}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)
        self.site = site
        self.retry_after = retry_after

    def to_error_response(self) -> ErrorResponse:
        """Convert exception to ErrorResponse model with retry_after."""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            retry_after=self.retry_after
        )


class JobBoardError(JobSearchError):
    """
    Exception for job board specific errors.
    """
    def __init__(self, message: str, site: str, original_error: Optional[Exception] = None):
        details = {"site": site}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, "JOB_BOARD_ERROR", details)
        self.site = site
        self.original_error = original_error


class NetworkError(JobSearchError):
    """
    Exception for network-related errors.
    """
    def __init__(self, message: str, url: Optional[str] = None, timeout: Optional[int] = None):
        details = {}
        if url:
            details["url"] = url
        if timeout:
            details["timeout"] = timeout
        super().__init__(message, "NETWORK_ERROR", details)
        self.url = url
        self.timeout = timeout


class SearchTimeoutError(JobSearchError):
    """
    Exception for search timeout errors.
    """
    def __init__(self, message: str, timeout_seconds: int):
        details = {"timeout_seconds": timeout_seconds}
        super().__init__(message, "SEARCH_TIMEOUT", details)
        self.timeout_seconds = timeout_seconds