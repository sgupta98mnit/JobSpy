"""
Job-related Pydantic models extending JobSpy's JobPost model.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from jobspy.model import JobPost


class WebJobPost(JobPost):
    """
    Extended JobPost model for web application use.
    Adds web-specific fields for tracking and relevance.
    """
    search_id: str = Field(
        description="ID of the search that found this job"
    )
    relevance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score for sorting (0.0 to 1.0)"
    )
    site: str = Field(
        description="Job board where this job was found"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "job_123456",
                "title": "Senior Software Engineer",
                "company_name": "Tech Corp",
                "job_url": "https://example.com/job/123456",
                "location": {
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "USA"
                },
                "description": "We are looking for a senior software engineer...",
                "compensation": {
                    "min_amount": 120000,
                    "max_amount": 150000,
                    "interval": "yearly",
                    "currency": "USD"
                },
                "date_posted": "2024-01-15",
                "job_type": ["fulltime"],
                "is_remote": False,
                "search_id": "search_123456789",
                "relevance_score": 0.85,
                "site": "indeed"
            }
        }
    )