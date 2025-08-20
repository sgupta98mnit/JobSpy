"""
Job search endpoint.

Provides job search functionality using the JobSpy integration service.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, timezone
import logging

from ....models.search import SearchRequest, JobSearchResponse, SearchMetadata
from ....models.errors import (
    JobSearchError, 
    RateLimitError, 
    JobBoardError, 
    NetworkError, 
    SearchTimeoutError,
    ValidationError
)
from ....services.job_search_service import JobSearchService


# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


def get_job_search_service() -> JobSearchService:
    """
    Dependency to provide JobSearchService instance.
    
    Returns:
        JobSearchService: Service instance for job searching
    """
    return JobSearchService()


@router.post("/", response_model=JobSearchResponse)
async def search_jobs(
    search_request: SearchRequest,
    job_service: JobSearchService = Depends(get_job_search_service)
) -> JobSearchResponse:
    """
    Search for jobs across multiple job boards.
    
    This endpoint accepts search parameters and returns job listings from
    various job boards including Indeed, LinkedIn, Glassdoor, and others.
    
    Args:
        search_request: Job search parameters including search term, location,
                       job type, and other filters
        job_service: Injected JobSearchService dependency
    
    Returns:
        JobSearchResponse: Search results with jobs, metadata, and any errors
    
    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        # Validate search parameters
        await job_service.validate_search_parameters(search_request)
        
        # Log search request (without sensitive data)
        logger.info(
            f"Job search requested: term='{search_request.search_term}', "
            f"location='{search_request.location}', "
            f"sites={search_request.site_names}, "
            f"results_wanted={search_request.results_wanted}"
        )
        
        # Perform the search
        search_response = await job_service.search_jobs(search_request)
        
        # Log search results
        logger.info(
            f"Search completed: search_id={search_response.search_metadata.search_id}, "
            f"results={search_response.total_results}, "
            f"duration={search_response.search_metadata.search_duration:.2f}s, "
            f"errors={len(search_response.errors)}"
        )
        
        return search_response
        
    except ValidationError as e:
        logger.warning(f"Validation error in search request: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation Error",
                "message": e.message,
                "field_errors": [
                    {
                        "field": error.field,
                        "message": error.message,
                        "invalid_value": error.invalid_value
                    }
                    for error in e.field_errors
                ] if e.field_errors else []
            }
        )
        
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate Limit Exceeded",
                "message": e.message,
                "site": e.site,
                "retry_after": e.retry_after
            },
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else None
        )
        
    except SearchTimeoutError as e:
        logger.error(f"Search timeout: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "error": "Search Timeout",
                "message": e.message,
                "timeout_seconds": e.timeout_seconds
            }
        )
        
    except NetworkError as e:
        logger.error(f"Network error during search: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Network Error",
                "message": e.message,
                "url": e.url
            }
        )
        
    except JobBoardError as e:
        logger.warning(f"Job board error: {e.message}")
        # For job board errors, we return 200 but include the error in the response
        # This allows partial results from other job boards
        return JobSearchResponse(
            jobs=[],
            total_results=0,
            search_metadata=SearchMetadata(
                search_id="error_search",
                timestamp=datetime.now(timezone.utc),
                total_sites_searched=1,
                successful_sites=[],
                failed_sites=[e.site] if e.site else ["unknown"],
                search_duration=0.0,
                total_results_found=0
            ),
            errors=[e.message],
            warnings=[]
        )
        
    except JobSearchError as e:
        logger.error(f"Job search error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Job Search Error",
                "message": e.message,
                "error_code": e.error_code,
                "details": e.details
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during job search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred while processing your search request"
            }
        )


@router.get("/validate", status_code=status.HTTP_200_OK)
async def validate_search_parameters(
    search_term: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    site_names: Optional[str] = None,  # Comma-separated string
    results_wanted: Optional[int] = 20,
    distance: Optional[int] = 50,
    is_remote: Optional[bool] = False,
    hours_old: Optional[int] = None,
    job_service: JobSearchService = Depends(get_job_search_service)
):
    """
    Validate search parameters without performing the actual search.
    
    This endpoint can be used to validate search parameters before submitting
    a search request, useful for form validation in the frontend.
    
    Args:
        search_term: Job title, keywords, or company name
        location: City, state, or country for job location
        job_type: Type of employment
        site_names: Comma-separated list of job boards
        results_wanted: Number of results to return
        distance: Search radius
        is_remote: Filter for remote work
        hours_old: Maximum age of job postings
        job_service: Injected JobSearchService dependency
    
    Returns:
        dict: Validation result with success status and any errors
    """
    try:
        # Parse site_names if provided
        parsed_site_names = ["indeed", "linkedin", "glassdoor"]
        if site_names:
            parsed_site_names = [site.strip() for site in site_names.split(",")]
        
        # Create SearchRequest for validation
        search_request = SearchRequest(
            search_term=search_term,
            location=location,
            job_type=job_type,
            site_names=parsed_site_names,
            results_wanted=results_wanted,
            distance=distance,
            is_remote=is_remote,
            hours_old=hours_old
        )
        
        # Validate parameters
        is_valid = await job_service.validate_search_parameters(search_request)
        
        return {
            "valid": is_valid,
            "message": "Search parameters are valid",
            "validated_parameters": search_request.model_dump()
        }
        
    except ValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "valid": False,
                "message": e.message,
                "field_errors": [
                    {
                        "field": error.field,
                        "message": error.message,
                        "invalid_value": error.invalid_value
                    }
                    for error in e.field_errors
                ] if e.field_errors else []
            }
        )
        
    except Exception as e:
        # Handle Pydantic validation errors
        error_msg = str(e)
        if "validation error" in error_msg.lower():
            # Extract field name and error message from Pydantic error
            field_name = "unknown"
            if "job_type" in error_msg:
                field_name = "job_type"
            elif "site_names" in error_msg:
                field_name = "site_names"
            elif "results_wanted" in error_msg:
                field_name = "results_wanted"
            elif "distance" in error_msg:
                field_name = "distance"
            elif "hours_old" in error_msg:
                field_name = "hours_old"
            
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "valid": False,
                    "message": error_msg,
                    "field_errors": [
                        {
                            "field": field_name,
                            "message": error_msg,
                            "invalid_value": None
                        }
                    ]
                }
            )
        
        logger.error(f"Error validating search parameters: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "valid": False,
                "message": "An error occurred while validating parameters"
            }
        )