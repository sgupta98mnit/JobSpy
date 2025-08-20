"""
Unit tests for error models and exception classes.
"""

import pytest
from app.models.errors import (
    ErrorResponse, ValidationErrorDetail, ValidationErrorResponse,
    JobSearchError, ValidationError, RateLimitError, 
    JobBoardError, NetworkError, SearchTimeoutError
)


class TestErrorResponse:
    """Test cases for ErrorResponse model."""

    def test_valid_error_response(self):
        """Test creating a valid ErrorResponse."""
        error = ErrorResponse(
            error_code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            details={"site": "linkedin"},
            retry_after=300
        )
        
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.message == "Too many requests"
        assert error.details == {"site": "linkedin"}
        assert error.retry_after == 300

    def test_minimal_error_response(self):
        """Test ErrorResponse with minimal required fields."""
        error = ErrorResponse(
            error_code="UNKNOWN_ERROR",
            message="Something went wrong"
        )
        
        assert error.error_code == "UNKNOWN_ERROR"
        assert error.message == "Something went wrong"
        assert error.details is None
        assert error.retry_after is None


class TestValidationErrorDetail:
    """Test cases for ValidationErrorDetail model."""

    def test_valid_validation_error_detail(self):
        """Test creating a valid ValidationErrorDetail."""
        detail = ValidationErrorDetail(
            field="results_wanted",
            message="Value must be between 1 and 100",
            invalid_value=150
        )
        
        assert detail.field == "results_wanted"
        assert detail.message == "Value must be between 1 and 100"
        assert detail.invalid_value == 150


class TestValidationErrorResponse:
    """Test cases for ValidationErrorResponse model."""

    def test_valid_validation_error_response(self):
        """Test creating a valid ValidationErrorResponse."""
        validation_errors = [
            ValidationErrorDetail(
                field="results_wanted",
                message="Value must be between 1 and 100",
                invalid_value=150
            ),
            ValidationErrorDetail(
                field="site_names",
                message="Invalid site name",
                invalid_value="invalid_site"
            )
        ]
        
        error = ValidationErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            validation_errors=validation_errors
        )
        
        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Request validation failed"
        assert len(error.validation_errors) == 2
        assert error.validation_errors[0].field == "results_wanted"
        assert error.validation_errors[1].field == "site_names"


class TestJobSearchError:
    """Test cases for JobSearchError exception class."""

    def test_basic_job_search_error(self):
        """Test creating a basic JobSearchError."""
        error = JobSearchError("Something went wrong")
        
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.error_code == "UNKNOWN_ERROR"
        assert error.details == {}

    def test_job_search_error_with_details(self):
        """Test JobSearchError with custom error code and details."""
        details = {"site": "linkedin", "status_code": 500}
        error = JobSearchError(
            "API request failed",
            error_code="API_ERROR",
            details=details
        )
        
        assert error.message == "API request failed"
        assert error.error_code == "API_ERROR"
        assert error.details == details

    def test_to_error_response(self):
        """Test converting JobSearchError to ErrorResponse."""
        error = JobSearchError(
            "Test error",
            error_code="TEST_ERROR",
            details={"key": "value"}
        )
        
        response = error.to_error_response()
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == "TEST_ERROR"
        assert response.message == "Test error"
        assert response.details == {"key": "value"}


class TestValidationError:
    """Test cases for ValidationError exception class."""

    def test_validation_error_basic(self):
        """Test creating a basic ValidationError."""
        error = ValidationError("Validation failed")
        
        assert error.message == "Validation failed"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field_errors == []

    def test_validation_error_with_field_errors(self):
        """Test ValidationError with field-specific errors."""
        field_errors = [
            ValidationErrorDetail(
                field="test_field",
                message="Invalid value",
                invalid_value="bad_value"
            )
        ]
        
        error = ValidationError("Validation failed", field_errors=field_errors)
        
        assert error.field_errors == field_errors

    def test_to_validation_error_response(self):
        """Test converting ValidationError to ValidationErrorResponse."""
        field_errors = [
            ValidationErrorDetail(
                field="test_field",
                message="Invalid value",
                invalid_value="bad_value"
            )
        ]
        
        error = ValidationError("Validation failed", field_errors=field_errors)
        response = error.to_validation_error_response()
        
        assert isinstance(response, ValidationErrorResponse)
        assert response.error_code == "VALIDATION_ERROR"
        assert response.message == "Validation failed"
        assert response.validation_errors == field_errors


class TestRateLimitError:
    """Test cases for RateLimitError exception class."""

    def test_rate_limit_error_basic(self):
        """Test creating a basic RateLimitError."""
        error = RateLimitError("Rate limit exceeded", site="linkedin")
        
        assert error.message == "Rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.site == "linkedin"
        assert error.retry_after is None
        assert error.details["site"] == "linkedin"

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError(
            "Rate limit exceeded",
            site="indeed",
            retry_after=300
        )
        
        assert error.retry_after == 300
        assert error.details["retry_after"] == 300

    def test_rate_limit_error_to_response(self):
        """Test converting RateLimitError to ErrorResponse with retry_after."""
        error = RateLimitError(
            "Rate limit exceeded",
            site="glassdoor",
            retry_after=600
        )
        
        response = error.to_error_response()
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == "RATE_LIMIT_EXCEEDED"
        assert response.retry_after == 600
        assert response.details["site"] == "glassdoor"


class TestJobBoardError:
    """Test cases for JobBoardError exception class."""

    def test_job_board_error_basic(self):
        """Test creating a basic JobBoardError."""
        error = JobBoardError("Job board unavailable", site="indeed")
        
        assert error.message == "Job board unavailable"
        assert error.error_code == "JOB_BOARD_ERROR"
        assert error.site == "indeed"
        assert error.original_error is None
        assert error.details["site"] == "indeed"

    def test_job_board_error_with_original_error(self):
        """Test JobBoardError with original exception."""
        original = Exception("Connection timeout")
        error = JobBoardError(
            "Job board unavailable",
            site="linkedin",
            original_error=original
        )
        
        assert error.original_error == original
        assert error.details["original_error"] == "Connection timeout"


class TestNetworkError:
    """Test cases for NetworkError exception class."""

    def test_network_error_basic(self):
        """Test creating a basic NetworkError."""
        error = NetworkError("Network connection failed")
        
        assert error.message == "Network connection failed"
        assert error.error_code == "NETWORK_ERROR"
        assert error.url is None
        assert error.timeout is None

    def test_network_error_with_details(self):
        """Test NetworkError with URL and timeout."""
        error = NetworkError(
            "Request timeout",
            url="https://api.example.com",
            timeout=30
        )
        
        assert error.url == "https://api.example.com"
        assert error.timeout == 30
        assert error.details["url"] == "https://api.example.com"
        assert error.details["timeout"] == 30


class TestSearchTimeoutError:
    """Test cases for SearchTimeoutError exception class."""

    def test_search_timeout_error(self):
        """Test creating a SearchTimeoutError."""
        error = SearchTimeoutError("Search timed out", timeout_seconds=60)
        
        assert error.message == "Search timed out"
        assert error.error_code == "SEARCH_TIMEOUT"
        assert error.timeout_seconds == 60
        assert error.details["timeout_seconds"] == 60