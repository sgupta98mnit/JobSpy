"""
JobSpy integration service layer for the job search web application.
Handles job searching, parameter mapping, and error handling.
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from jobspy import scrape_jobs
from jobspy.model import Site, JobResponse, JobPost as JobSpyJobPost, JobType, Location, Compensation, CompensationInterval
from jobspy.exception import (
    LinkedInException, IndeedException, ZipRecruiterException, 
    GlassdoorException, GoogleJobsException, BaytException, 
    NaukriException, BDJobsException
)

from ..models.search import SearchRequest, JobSearchResponse, SearchMetadata
from ..models.job import WebJobPost
from ..models.errors import (
    JobSearchError, 
    RateLimitError, 
    JobBoardError, 
    NetworkError, 
    SearchTimeoutError
)


class JobSearchService:
    """
    Service class for integrating with JobSpy library.
    Provides async interface for job searching with error handling.
    """
    
    def __init__(self, default_timeout: int = 60):
        """
        Initialize the JobSearchService.
        
        Args:
            default_timeout: Default timeout for search operations in seconds
        """
        self.default_timeout = default_timeout
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    async def search_jobs(self, search_request: SearchRequest) -> JobSearchResponse:
        """
        Perform asynchronous job search using JobSpy.
        
        Args:
            search_request: Validated search parameters
            
        Returns:
            JobSearchResponse: Search results with metadata and error information
            
        Raises:
            SearchTimeoutError: If search exceeds timeout
            JobSearchError: For other search-related errors
        """
        search_id = self._generate_search_id()
        from datetime import timezone
        start_time = datetime.now(timezone.utc)
        
        try:
            # Map web API parameters to JobSpy parameters
            jobspy_params = self._map_search_parameters(search_request)
            
            # Execute search in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            df_result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    self._execute_jobspy_search,
                    jobspy_params
                ),
                timeout=self.default_timeout
            )
            
            # Process results
            jobs, errors, warnings = self._process_search_results(df_result, search_id)
            
            # Create metadata
            end_time = datetime.now(timezone.utc)
            search_duration = (end_time - start_time).total_seconds()
            
            metadata = self._create_search_metadata(
                search_id=search_id,
                start_time=start_time,
                search_duration=search_duration,
                site_names=search_request.site_names,
                total_results=len(jobs),
                errors=errors
            )
            
            return JobSearchResponse(
                jobs=jobs,
                total_results=len(jobs),
                search_metadata=metadata,
                errors=errors,
                warnings=warnings
            )
            
        except asyncio.TimeoutError:
            raise SearchTimeoutError(
                f"Search timed out after {self.default_timeout} seconds",
                timeout_seconds=self.default_timeout
            )
        except Exception as e:
            raise JobSearchError(
                f"Unexpected error during job search: {str(e)}",
                error_code="SEARCH_ERROR",
                details={"original_error": str(e)}
            )
    
    def _generate_search_id(self) -> str:
        """Generate unique search ID."""
        return f"search_{uuid.uuid4().hex[:12]}"
    
    def _map_search_parameters(self, search_request: SearchRequest) -> Dict[str, Any]:
        """
        Map SearchRequest parameters to JobSpy scrape_jobs parameters.
        
        Args:
            search_request: Web API search request
            
        Returns:
            Dict containing JobSpy parameters
        """
        # Map site names to JobSpy format
        site_names = []
        for site in search_request.site_names:
            if site == "zip_recruiter":
                site_names.append("ziprecruiter")
            else:
                site_names.append(site)
        
        params = {
            "site_name": site_names,
            "search_term": search_request.search_term,
            "location": search_request.location,
            "distance": search_request.distance,
            "is_remote": search_request.is_remote,
            "job_type": search_request.job_type,
            "results_wanted": search_request.results_wanted,
            "hours_old": search_request.hours_old,
            "country_indeed": "usa",  # Default to USA, could be configurable
            "description_format": "markdown",
            "verbose": 0  # Reduce logging noise
        }
        
        # Remove None values to use JobSpy defaults
        return {k: v for k, v in params.items() if v is not None}
    
    def _execute_jobspy_search(self, params: Dict[str, Any]) -> pd.DataFrame:
        """
        Execute JobSpy search in a synchronous context.
        
        Args:
            params: JobSpy parameters
            
        Returns:
            pandas.DataFrame: Raw search results
            
        Raises:
            Various JobSpy exceptions that will be caught and handled
        """
        try:
            return scrape_jobs(**params)
        except Exception as e:
            # Let the exception bubble up to be handled by the async wrapper
            raise e
    
    def _process_search_results(
        self, 
        df_result: pd.DataFrame, 
        search_id: str
    ) -> tuple[List[WebJobPost], List[str], List[str]]:
        """
        Process JobSpy DataFrame results into WebJobPost objects.
        
        Args:
            df_result: JobSpy results DataFrame
            search_id: Unique search identifier
            
        Returns:
            Tuple of (jobs_list, errors_list, warnings_list)
        """
        jobs = []
        errors = []
        warnings = []
        
        if df_result.empty:
            warnings.append("No jobs found matching the search criteria")
            return jobs, errors, warnings
        
        # Process each row in the DataFrame
        for _, row in df_result.iterrows():
            try:
                job = self._convert_row_to_webjobpost(row, search_id)
                jobs.append(job)
            except Exception as e:
                errors.append(f"Failed to process job: {str(e)}")
                continue
        
        return jobs, errors, warnings
    
    def _convert_row_to_webjobpost(self, row: pd.Series, search_id: str) -> WebJobPost:
        """
        Convert a pandas Series row to WebJobPost object.
        
        Args:
            row: Single row from JobSpy DataFrame
            search_id: Search identifier
            
        Returns:
            WebJobPost: Converted job post
        """
        # Handle location data
        location_data = None
        if pd.notna(row.get('location')):
            # JobSpy returns location as a string, we need to parse it
            location_str = str(row['location'])
            location_parts = location_str.split(', ')
            if len(location_parts) >= 2:
                location_data = Location(
                    city=location_parts[0] if len(location_parts) > 0 else None,
                    state=location_parts[1] if len(location_parts) > 1 else None,
                    country=location_parts[2] if len(location_parts) > 2 else "USA"
                )
        
        # Handle compensation data
        compensation_data = None
        if any(pd.notna(row.get(field)) for field in ['min_amount', 'max_amount', 'interval']):
            # Convert interval string to CompensationInterval enum
            interval_value = None
            if pd.notna(row.get('interval')):
                interval_str = str(row.get('interval'))
                for interval_enum in CompensationInterval:
                    if interval_str == interval_enum.value:
                        interval_value = interval_enum
                        break
            
            compensation_data = Compensation(
                min_amount=float(row.get('min_amount')) if pd.notna(row.get('min_amount')) else None,
                max_amount=float(row.get('max_amount')) if pd.notna(row.get('max_amount')) else None,
                interval=interval_value,
                currency=str(row.get('currency', 'USD')) if pd.notna(row.get('currency')) else 'USD'
            )
        
        # Handle job_type - convert string to JobType enum list
        job_type_list = None
        if pd.notna(row.get('job_type')):
            job_type_str = str(row['job_type'])
            if job_type_str and job_type_str != 'None':
                # Find matching JobType enum
                for job_type_enum in JobType:
                    if job_type_str in job_type_enum.value:
                        job_type_list = [job_type_enum]
                        break
        
        # Handle date_posted
        date_posted = None
        if pd.notna(row.get('date_posted')):
            date_posted = row['date_posted']
            if isinstance(date_posted, str):
                try:
                    from datetime import datetime
                    date_posted = datetime.strptime(date_posted, '%Y-%m-%d').date()
                except ValueError:
                    date_posted = None
        
        # Create WebJobPost
        return WebJobPost(
            id=str(row.get('id', f"job_{uuid.uuid4().hex[:8]}")),
            title=str(row.get('title', 'Unknown Title')),
            company_name=str(row.get('company_name')) if pd.notna(row.get('company_name')) else None,
            job_url=str(row.get('job_url', '')),
            job_url_direct=str(row.get('job_url_direct')) if pd.notna(row.get('job_url_direct')) else None,
            location=location_data,
            description=str(row.get('description')) if pd.notna(row.get('description')) else None,
            company_url=str(row.get('company_url')) if pd.notna(row.get('company_url')) else None,
            company_url_direct=str(row.get('company_url_direct')) if pd.notna(row.get('company_url_direct')) else None,
            job_type=job_type_list,
            compensation=compensation_data,
            date_posted=date_posted,
            emails=str(row.get('emails')).split(', ') if pd.notna(row.get('emails')) and str(row.get('emails')) != 'None' else None,
            is_remote=bool(row.get('is_remote', False)) if pd.notna(row.get('is_remote')) else None,
            listing_type=str(row.get('listing_type')) if pd.notna(row.get('listing_type')) else None,
            job_level=str(row.get('job_level')) if pd.notna(row.get('job_level')) else None,
            company_industry=str(row.get('company_industry')) if pd.notna(row.get('company_industry')) else None,
            company_addresses=str(row.get('company_addresses')) if pd.notna(row.get('company_addresses')) else None,
            company_num_employees=str(row.get('company_num_employees')) if pd.notna(row.get('company_num_employees')) else None,
            company_revenue=str(row.get('company_revenue')) if pd.notna(row.get('company_revenue')) else None,
            company_description=str(row.get('company_description')) if pd.notna(row.get('company_description')) else None,
            company_logo=str(row.get('company_logo')) if pd.notna(row.get('company_logo')) else None,
            banner_photo_url=str(row.get('banner_photo_url')) if pd.notna(row.get('banner_photo_url')) else None,
            job_function=str(row.get('job_function')) if pd.notna(row.get('job_function')) else None,
            skills=str(row.get('skills')).split(', ') if pd.notna(row.get('skills')) and str(row.get('skills')) != 'None' else None,
            experience_range=str(row.get('experience_range')) if pd.notna(row.get('experience_range')) else None,
            company_rating=float(row.get('company_rating')) if pd.notna(row.get('company_rating')) else None,
            company_reviews_count=int(row.get('company_reviews_count')) if pd.notna(row.get('company_reviews_count')) else None,
            vacancy_count=int(row.get('vacancy_count')) if pd.notna(row.get('vacancy_count')) else None,
            work_from_home_type=str(row.get('work_from_home_type')) if pd.notna(row.get('work_from_home_type')) else None,
            search_id=search_id,
            relevance_score=None,  # Could be calculated based on search terms
            site=str(row.get('site', 'unknown'))
        )
    
    def _create_search_metadata(
        self,
        search_id: str,
        start_time: datetime,
        search_duration: float,
        site_names: List[str],
        total_results: int,
        errors: List[str]
    ) -> SearchMetadata:
        """
        Create search metadata object.
        
        Args:
            search_id: Unique search identifier
            start_time: When the search started
            search_duration: How long the search took in seconds
            site_names: List of requested job boards
            total_results: Number of jobs found
            errors: List of error messages
            
        Returns:
            SearchMetadata: Metadata object
        """
        # Determine which sites succeeded vs failed based on errors
        failed_sites = []
        for error in errors:
            for site in site_names:
                if site.lower() in error.lower():
                    failed_sites.append(site)
        
        successful_sites = [site for site in site_names if site not in failed_sites]
        
        return SearchMetadata(
            search_id=search_id,
            timestamp=start_time,
            total_sites_searched=len(site_names),
            successful_sites=successful_sites,
            failed_sites=failed_sites,
            search_duration=search_duration,
            total_results_found=total_results
        )
    
    async def validate_search_parameters(self, search_request: SearchRequest) -> bool:
        """
        Validate search parameters before executing search.
        
        Args:
            search_request: Search parameters to validate
            
        Returns:
            bool: True if parameters are valid
            
        Raises:
            ValidationError: If parameters are invalid
        """
        # Pydantic already handles most validation, but we can add business logic here
        
        # Check if search term or location is provided
        if not search_request.search_term and not search_request.location:
            from ..models.errors import ValidationError, ValidationErrorDetail
            raise ValidationError(
                "Either search term or location must be provided",
                field_errors=[
                    ValidationErrorDetail(
                        field="search_term",
                        message="Either search term or location must be provided",
                        invalid_value=search_request.search_term
                    ),
                    ValidationErrorDetail(
                        field="location",
                        message="Either search term or location must be provided",
                        invalid_value=search_request.location
                    )
                ]
            )
        
        return True
    
    def __del__(self):
        """Cleanup thread pool executor."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


# Error handling wrapper functions

def handle_jobspy_exceptions(func):
    """
    Decorator to handle JobSpy-specific exceptions and convert them to our error types.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limiting
            if "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                site = "unknown"
                # Try to extract site name from error message
                for site_name in ["linkedin", "indeed", "glassdoor", "google", "ziprecruiter"]:
                    if site_name in error_msg:
                        site = site_name
                        break
                
                raise RateLimitError(
                    f"Rate limit exceeded for {site}. Please try again later.",
                    site=site,
                    retry_after=300  # Default 5 minutes
                )
            
            # Check for network errors
            elif any(keyword in error_msg for keyword in ["connection", "timeout", "network", "dns"]):
                raise NetworkError(
                    f"Network error occurred: {str(e)}",
                    url=None  # Could extract from error if available
                )
            
            # Check for job board specific errors
            elif any(site in error_msg for site in ["linkedin", "indeed", "glassdoor", "google", "ziprecruiter"]):
                site = "unknown"
                for site_name in ["linkedin", "indeed", "glassdoor", "google", "ziprecruiter"]:
                    if site_name in error_msg:
                        site = site_name
                        break
                
                raise JobBoardError(
                    f"Error from {site}: {str(e)}",
                    site=site,
                    original_error=e
                )
            
            # Generic job search error
            else:
                raise JobSearchError(
                    f"Job search failed: {str(e)}",
                    error_code="JOBSPY_ERROR",
                    details={"original_error": str(e)}
                )
    
    return wrapper