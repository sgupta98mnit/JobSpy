"""
Search-related Pydantic models for the job search web application.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .job import WebJobPost


class SearchRequest(BaseModel):
    """
    Model for job search request parameters.
    Validates and structures search parameters from the web interface.
    """
    search_term: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=200,
        description="Job title, keywords, or company name to search for"
    )
    location: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="City, state, or country for job location"
    )
    job_type: Optional[str] = Field(
        None,
        description="Type of employment (fulltime, parttime, contract, etc.)"
    )
    site_names: List[str] = Field(
        default=["indeed", "linkedin", "glassdoor"],
        min_length=1,
        max_length=10,
        description="List of job boards to search"
    )
    results_wanted: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of job results to return (1-100)"
    )
    distance: Optional[int] = Field(
        default=50,
        ge=0,
        le=200,
        description="Search radius in miles/kilometers"
    )
    is_remote: bool = Field(
        default=False,
        description="Filter for remote work opportunities"
    )
    hours_old: Optional[int] = Field(
        None,
        ge=1,
        le=8760,  # 1 year in hours
        description="Maximum age of job postings in hours"
    )

    @field_validator('site_names')
    @classmethod
    def validate_site_names(cls, v):
        """Validate that site names are supported job boards."""
        valid_sites = {
            "indeed", "linkedin", "glassdoor", "google", 
            "zip_recruiter", "bayt", "naukri", "bdjobs"
        }
        invalid_sites = [site for site in v if site not in valid_sites]
        if invalid_sites:
            raise ValueError(f"Unsupported job boards: {invalid_sites}. Valid options: {valid_sites}")
        return v

    @field_validator('job_type')
    @classmethod
    def validate_job_type(cls, v):
        """Validate job type against supported values."""
        if v is None:
            return v
        valid_types = {
            "fulltime", "parttime", "contract", "temporary", 
            "internship", "perdiem", "nights", "other", "summer", "volunteer"
        }
        if v not in valid_types:
            raise ValueError(f"Invalid job type: {v}. Valid options: {valid_types}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search_term": "software engineer",
                "location": "San Francisco, CA",
                "job_type": "fulltime",
                "site_names": ["indeed", "linkedin"],
                "results_wanted": 25,
                "distance": 50,
                "is_remote": False,
                "hours_old": 168
            }
        }
    )


class SearchMetadata(BaseModel):
    """
    Metadata about a job search operation.
    Tracks search performance and results.
    """
    search_id: str = Field(
        description="Unique identifier for this search"
    )
    timestamp: datetime = Field(
        description="When the search was initiated"
    )
    total_sites_searched: int = Field(
        ge=0,
        description="Total number of job boards queried"
    )
    successful_sites: List[str] = Field(
        description="Job boards that returned results successfully"
    )
    failed_sites: List[str] = Field(
        description="Job boards that failed or returned errors"
    )
    search_duration: float = Field(
        ge=0.0,
        description="Total search time in seconds"
    )
    total_results_found: int = Field(
        ge=0,
        description="Total number of jobs found across all sites"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search_id": "search_123456789",
                "timestamp": "2024-01-15T10:30:00Z",
                "total_sites_searched": 3,
                "successful_sites": ["indeed", "linkedin"],
                "failed_sites": ["glassdoor"],
                "search_duration": 12.5,
                "total_results_found": 45
            }
        }
    )


class JobSearchResponse(BaseModel):
    """
    Response model for job search results.
    Contains jobs, metadata, and any errors encountered.
    """
    jobs: List[WebJobPost] = Field(
        description="List of job postings found"
    )
    total_results: int = Field(
        ge=0,
        description="Total number of jobs returned"
    )
    search_metadata: SearchMetadata = Field(
        description="Metadata about the search operation"
    )
    errors: List[str] = Field(
        default=[],
        description="List of error messages encountered during search"
    )
    warnings: List[str] = Field(
        default=[],
        description="List of warning messages (e.g., rate limits, partial failures)"
    )

    @field_validator('total_results')
    @classmethod
    def validate_total_results(cls, v, info):
        """Ensure total_results matches the actual number of jobs."""
        if info.data and 'jobs' in info.data and len(info.data['jobs']) != v:
            raise ValueError("total_results must match the number of jobs in the list")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobs": [],
                "total_results": 25,
                "search_metadata": {
                    "search_id": "search_123456789",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "total_sites_searched": 3,
                    "successful_sites": ["indeed", "linkedin"],
                    "failed_sites": ["glassdoor"],
                    "search_duration": 12.5,
                    "total_results_found": 45
                },
                "errors": ["Glassdoor rate limit exceeded"],
                "warnings": ["LinkedIn returned partial results"]
            }
        }
    )