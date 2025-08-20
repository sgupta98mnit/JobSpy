#!/usr/bin/env python3
"""
Demonstration script for the job search web application data models.
This script shows how to use the Pydantic models for validation and serialization.
"""

import json
from datetime import datetime
from app.models import (
    SearchRequest, JobSearchResponse, SearchMetadata, WebJobPost,
    ErrorResponse, ValidationError, RateLimitError
)
from jobspy.model import Location, Compensation, CompensationInterval


def demo_search_request():
    """Demonstrate SearchRequest model usage."""
    print("=== SearchRequest Demo ===")
    
    # Valid search request
    request = SearchRequest(
        search_term="python developer",
        location="New York, NY",
        job_type="fulltime",
        site_names=["indeed", "linkedin"],
        results_wanted=50,
        distance=25,
        is_remote=True,
        hours_old=72
    )
    
    print("Valid SearchRequest:")
    print(json.dumps(request.model_dump(), indent=2))
    
    # Try invalid request (should raise validation error)
    try:
        invalid_request = SearchRequest(
            results_wanted=150,  # Too high
            site_names=["invalid_site"]  # Invalid site
        )
    except Exception as e:
        print(f"\nValidation error (expected): {e}")
    
    print()


def demo_job_search_response():
    """Demonstrate JobSearchResponse model usage."""
    print("=== JobSearchResponse Demo ===")
    
    # Create sample jobs
    job1 = WebJobPost(
        id="job_001",
        title="Senior Python Developer",
        company_name="Tech Corp",
        job_url="https://example.com/job/001",
        location=Location(city="New York", state="NY"),
        description="We are looking for a senior Python developer...",
        compensation=Compensation(
            min_amount=120000,
            max_amount=150000,
            interval=CompensationInterval.YEARLY,
            currency="USD"
        ),
        search_id="search_123",
        relevance_score=0.95,
        site="indeed",
        is_remote=True
    )
    
    job2 = WebJobPost(
        id="job_002",
        title="Python Backend Engineer",
        company_name="StartupXYZ",
        job_url="https://example.com/job/002",
        location=Location(city="San Francisco", state="CA"),
        search_id="search_123",
        relevance_score=0.87,
        site="linkedin"
    )
    
    # Create metadata
    metadata = SearchMetadata(
        search_id="search_123",
        timestamp=datetime.now(),
        total_sites_searched=2,
        successful_sites=["indeed", "linkedin"],
        failed_sites=[],
        search_duration=8.5,
        total_results_found=2
    )
    
    # Create response
    response = JobSearchResponse(
        jobs=[job1, job2],
        total_results=2,
        search_metadata=metadata,
        errors=[],
        warnings=["LinkedIn returned partial results"]
    )
    
    print("JobSearchResponse:")
    print(json.dumps(response.model_dump(), indent=2, default=str))
    print()


def demo_error_handling():
    """Demonstrate error models and exception handling."""
    print("=== Error Handling Demo ===")
    
    # Rate limit error
    rate_limit_error = RateLimitError(
        "LinkedIn rate limit exceeded",
        site="linkedin",
        retry_after=300
    )
    
    error_response = rate_limit_error.to_error_response()
    print("Rate Limit Error Response:")
    print(json.dumps(error_response.model_dump(), indent=2))
    
    # Validation error
    validation_error = ValidationError(
        "Request validation failed",
        field_errors=[]
    )
    
    validation_response = validation_error.to_validation_error_response()
    print("\nValidation Error Response:")
    print(json.dumps(validation_response.model_dump(), indent=2))
    print()


def main():
    """Run all demonstrations."""
    print("Job Search Web Application - Data Models Demo")
    print("=" * 50)
    
    demo_search_request()
    demo_job_search_response()
    demo_error_handling()
    
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()