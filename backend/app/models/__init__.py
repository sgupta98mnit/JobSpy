"""
Data models for the job search web application.
"""

from .search import SearchRequest, JobSearchResponse, SearchMetadata
from .errors import ErrorResponse, JobSearchError, ValidationError, RateLimitError
from .job import WebJobPost

__all__ = [
    "SearchRequest",
    "JobSearchResponse", 
    "SearchMetadata",
    "ErrorResponse",
    "JobSearchError",
    "ValidationError",
    "RateLimitError",
    "WebJobPost",
]