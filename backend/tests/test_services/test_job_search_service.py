"""
Unit tests for JobSearchService with mocked JobSpy responses.
"""

import pytest
import pandas as pd
from datetime import datetime, date
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.services.job_search_service import JobSearchService, handle_jobspy_exceptions
from app.models.search import SearchRequest, JobSearchResponse, SearchMetadata
from app.models.job import WebJobPost
from app.models.errors import (
    JobSearchError, 
    RateLimitError, 
    JobBoardError, 
    NetworkError, 
    SearchTimeoutError,
    ValidationError
)
from jobspy.model import JobType


class TestJobSearchService:
    """Test cases for JobSearchService class."""
    
    @pytest.fixture
    def service(self):
        """Create JobSearchService instance for testing."""
        return JobSearchService(default_timeout=30)
    
    @pytest.fixture
    def sample_search_request(self):
        """Create sample SearchRequest for testing."""
        return SearchRequest(
            search_term="software engineer",
            location="San Francisco, CA",
            job_type="fulltime",
            site_names=["indeed", "linkedin"],
            results_wanted=10,
            distance=50,
            is_remote=False,
            hours_old=168
        )
    
    @pytest.fixture
    def sample_jobspy_dataframe(self):
        """Create sample JobSpy DataFrame for testing."""
        data = {
            'id': ['job_1', 'job_2'],
            'title': ['Software Engineer', 'Senior Developer'],
            'company_name': ['Tech Corp', 'Dev Company'],
            'job_url': ['https://example.com/job1', 'https://example.com/job2'],
            'job_url_direct': [None, 'https://direct.com/job2'],
            'location': ['San Francisco, CA, USA', 'New York, NY, USA'],
            'description': ['Great job opportunity', 'Senior role available'],
            'company_url': ['https://techcorp.com', None],
            'job_type': ['fulltime', 'fulltime'],
            'min_amount': [120000, 150000],
            'max_amount': [150000, 180000],
            'interval': ['yearly', 'yearly'],
            'currency': ['USD', 'USD'],
            'date_posted': ['2024-01-15', '2024-01-14'],
            'emails': [None, 'hr@devcompany.com'],
            'is_remote': [False, True],
            'site': ['indeed', 'linkedin'],
            'company_industry': ['Technology', 'Software'],
            'skills': ['Python, JavaScript', 'Java, React'],
            'experience_range': ['3-5 years', '5+ years'],
            'company_rating': [4.5, 4.2],
            'company_reviews_count': [100, 250]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def empty_dataframe(self):
        """Create empty DataFrame for testing no results scenario."""
        return pd.DataFrame()
    
    def test_generate_search_id(self, service):
        """Test search ID generation."""
        search_id = service._generate_search_id()
        assert search_id.startswith("search_")
        assert len(search_id) == 19  # "search_" + 12 hex chars
        
        # Ensure uniqueness
        search_id2 = service._generate_search_id()
        assert search_id != search_id2
    
    def test_map_search_parameters(self, service, sample_search_request):
        """Test parameter mapping from SearchRequest to JobSpy format."""
        params = service._map_search_parameters(sample_search_request)
        
        expected_params = {
            "site_name": ["indeed", "linkedin"],
            "search_term": "software engineer",
            "location": "San Francisco, CA",
            "distance": 50,
            "is_remote": False,
            "job_type": "fulltime",
            "results_wanted": 10,
            "hours_old": 168,
            "country_indeed": "usa",
            "description_format": "markdown",
            "verbose": 0
        }
        
        assert params == expected_params
    
    def test_map_search_parameters_zip_recruiter(self, service):
        """Test parameter mapping handles zip_recruiter site name conversion."""
        search_request = SearchRequest(
            search_term="test",
            site_names=["zip_recruiter", "indeed"]
        )
        
        params = service._map_search_parameters(search_request)
        assert params["site_name"] == ["ziprecruiter", "indeed"]
    
    def test_map_search_parameters_none_values(self, service):
        """Test parameter mapping removes None values."""
        search_request = SearchRequest(
            search_term="test",
            location=None,
            hours_old=None
        )
        
        params = service._map_search_parameters(search_request)
        assert "location" not in params
        assert "hours_old" not in params
        assert "search_term" in params
    
    def test_convert_row_to_webjobpost(self, service, sample_jobspy_dataframe):
        """Test conversion of DataFrame row to WebJobPost."""
        row = sample_jobspy_dataframe.iloc[0]
        search_id = "test_search_123"
        
        job = service._convert_row_to_webjobpost(row, search_id)
        
        assert isinstance(job, WebJobPost)
        assert job.id == "job_1"
        assert job.title == "Software Engineer"
        assert job.company_name == "Tech Corp"
        assert job.search_id == search_id
        assert job.site == "indeed"
        assert job.location.city == "San Francisco"
        assert job.location.state == "CA"
        assert job.location.country == "USA"
        assert job.compensation.min_amount == 120000
        assert job.compensation.max_amount == 150000
        assert job.compensation.interval.value == "yearly"
        assert job.compensation.currency == "USD"
        assert job.job_type == [JobType.FULL_TIME]
        assert job.is_remote is False
    
    def test_convert_row_to_webjobpost_with_nulls(self, service):
        """Test conversion handles null/missing values properly."""
        data = {
            'id': 'job_null',
            'title': 'Test Job',
            'company_name': None,
            'job_url': 'https://example.com',
            'location': None,
            'description': None,
            'min_amount': None,
            'max_amount': None,
            'site': 'indeed'
        }
        row = pd.Series(data)
        search_id = "test_search"
        
        job = service._convert_row_to_webjobpost(row, search_id)
        
        assert job.company_name is None
        assert job.location is None
        assert job.description is None
        assert job.compensation is None
    
    def test_process_search_results_success(self, service, sample_jobspy_dataframe):
        """Test processing of successful search results."""
        search_id = "test_search"
        
        jobs, errors, warnings = service._process_search_results(sample_jobspy_dataframe, search_id)
        
        assert len(jobs) == 2
        assert len(errors) == 0
        assert len(warnings) == 0
        assert all(isinstance(job, WebJobPost) for job in jobs)
        assert all(job.search_id == search_id for job in jobs)
    
    def test_process_search_results_empty(self, service, empty_dataframe):
        """Test processing of empty search results."""
        search_id = "test_search"
        
        jobs, errors, warnings = service._process_search_results(empty_dataframe, search_id)
        
        assert len(jobs) == 0
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "No jobs found" in warnings[0]
    
    def test_create_search_metadata(self, service):
        """Test creation of search metadata."""
        search_id = "test_search"
        from datetime import timezone
        start_time = datetime.now(timezone.utc)
        search_duration = 12.5
        site_names = ["indeed", "linkedin", "glassdoor"]
        total_results = 25
        errors = ["Glassdoor rate limit exceeded"]
        
        metadata = service._create_search_metadata(
            search_id, start_time, search_duration, site_names, total_results, errors
        )
        
        assert isinstance(metadata, SearchMetadata)
        assert metadata.search_id == search_id
        assert metadata.timestamp == start_time
        assert metadata.search_duration == search_duration
        assert metadata.total_sites_searched == 3
        assert metadata.total_results_found == total_results
        assert "glassdoor" in metadata.failed_sites
        assert "indeed" in metadata.successful_sites
        assert "linkedin" in metadata.successful_sites
    
    @pytest.mark.asyncio
    async def test_validate_search_parameters_success(self, service, sample_search_request):
        """Test successful parameter validation."""
        result = await service.validate_search_parameters(sample_search_request)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_search_parameters_no_sites(self, service):
        """Test validation fails when no sites are selected (handled by Pydantic)."""
        # This should fail at the Pydantic level before reaching our validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchRequest(
                search_term="test",
                site_names=[]
            )
    
    @pytest.mark.asyncio
    async def test_validate_search_parameters_no_term_or_location(self, service):
        """Test validation fails when neither search term nor location provided."""
        search_request = SearchRequest(
            search_term=None,
            location=None,
            site_names=["indeed"]
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.validate_search_parameters(search_request)
        
        assert "Either search term or location must be provided" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('app.services.job_search_service.scrape_jobs')
    async def test_search_jobs_success(self, mock_scrape_jobs, service, sample_search_request, sample_jobspy_dataframe):
        """Test successful job search execution."""
        mock_scrape_jobs.return_value = sample_jobspy_dataframe
        
        result = await service.search_jobs(sample_search_request)
        
        assert isinstance(result, JobSearchResponse)
        assert len(result.jobs) == 2
        assert result.total_results == 2
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert isinstance(result.search_metadata, SearchMetadata)
        
        # Verify JobSpy was called with correct parameters
        mock_scrape_jobs.assert_called_once()
        call_args = mock_scrape_jobs.call_args[1]
        assert call_args["site_name"] == ["indeed", "linkedin"]
        assert call_args["search_term"] == "software engineer"
    
    @pytest.mark.asyncio
    @patch('app.services.job_search_service.scrape_jobs')
    async def test_search_jobs_empty_results(self, mock_scrape_jobs, service, sample_search_request, empty_dataframe):
        """Test job search with no results."""
        mock_scrape_jobs.return_value = empty_dataframe
        
        result = await service.search_jobs(sample_search_request)
        
        assert isinstance(result, JobSearchResponse)
        assert len(result.jobs) == 0
        assert result.total_results == 0
        assert len(result.warnings) == 1
        assert "No jobs found" in result.warnings[0]
    
    @pytest.mark.asyncio
    @patch('app.services.job_search_service.scrape_jobs')
    async def test_search_jobs_timeout(self, mock_scrape_jobs, service, sample_search_request):
        """Test job search timeout handling."""
        # Mock a slow operation
        def slow_scrape(*args, **kwargs):
            import time
            time.sleep(2)  # Longer than our test timeout
            return pd.DataFrame()
        
        mock_scrape_jobs.side_effect = slow_scrape
        service.default_timeout = 0.1  # Very short timeout for testing
        
        with pytest.raises(SearchTimeoutError) as exc_info:
            await service.search_jobs(sample_search_request)
        
        assert "timed out" in str(exc_info.value)
        assert exc_info.value.timeout_seconds == 0.1
    
    @pytest.mark.asyncio
    @patch('app.services.job_search_service.scrape_jobs')
    async def test_search_jobs_generic_error(self, mock_scrape_jobs, service, sample_search_request):
        """Test job search with generic error."""
        mock_scrape_jobs.side_effect = Exception("Unexpected error")
        
        with pytest.raises(JobSearchError) as exc_info:
            await service.search_jobs(sample_search_request)
        
        assert "Unexpected error during job search" in str(exc_info.value)
        assert exc_info.value.error_code == "SEARCH_ERROR"


class TestErrorHandlingDecorator:
    """Test cases for the error handling decorator."""
    
    def test_handle_rate_limit_error(self):
        """Test rate limit error handling."""
        @handle_jobspy_exceptions
        def mock_function():
            raise Exception("429 Too Many Requests from linkedin")
        
        with pytest.raises(RateLimitError) as exc_info:
            mock_function()
        
        assert exc_info.value.site == "linkedin"
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after == 300
    
    def test_handle_network_error(self):
        """Test network error handling."""
        @handle_jobspy_exceptions
        def mock_function():
            raise Exception("Connection timeout occurred")
        
        with pytest.raises(NetworkError) as exc_info:
            mock_function()
        
        assert "Network error occurred" in str(exc_info.value)
    
    def test_handle_job_board_error(self):
        """Test job board specific error handling."""
        @handle_jobspy_exceptions
        def mock_function():
            raise Exception("indeed returned invalid response")
        
        with pytest.raises(JobBoardError) as exc_info:
            mock_function()
        
        assert exc_info.value.site == "indeed"
        assert "Error from indeed" in str(exc_info.value)
    
    def test_handle_generic_error(self):
        """Test generic error handling."""
        @handle_jobspy_exceptions
        def mock_function():
            raise Exception("Some unknown error")
        
        with pytest.raises(JobSearchError) as exc_info:
            mock_function()
        
        assert "Job search failed" in str(exc_info.value)
        assert exc_info.value.error_code == "JOBSPY_ERROR"
    
    def test_successful_execution(self):
        """Test decorator doesn't interfere with successful execution."""
        @handle_jobspy_exceptions
        def mock_function():
            return "success"
        
        result = mock_function()
        assert result == "success"


class TestJobSearchServiceIntegration:
    """Integration tests for JobSearchService."""
    
    @pytest.fixture
    def service(self):
        return JobSearchService()
    
    @pytest.mark.asyncio
    async def test_full_search_workflow_mock(self, service):
        """Test complete search workflow with mocked JobSpy."""
        search_request = SearchRequest(
            search_term="python developer",
            location="Remote",
            site_names=["indeed"],
            results_wanted=5
        )
        
        # Mock the DataFrame result
        mock_data = {
            'id': ['test_job_1'],
            'title': ['Python Developer'],
            'company_name': ['Test Company'],
            'job_url': ['https://example.com/job'],
            'location': ['Remote, USA'],
            'description': ['Python development role'],
            'site': ['indeed'],
            'job_type': ['fulltime'],
            'date_posted': ['2024-01-15']
        }
        mock_df = pd.DataFrame(mock_data)
        
        with patch('app.services.job_search_service.scrape_jobs', return_value=mock_df):
            result = await service.search_jobs(search_request)
        
        assert isinstance(result, JobSearchResponse)
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Python Developer"
        assert result.jobs[0].company_name == "Test Company"
        assert result.search_metadata.total_sites_searched == 1
        assert "indeed" in result.search_metadata.successful_sites
    
    def test_service_cleanup(self):
        """Test service cleanup on deletion."""
        service = JobSearchService()
        executor = service._executor
        
        # Delete service
        del service
        
        # Executor should be shutdown (we can't easily test this without implementation details)
        # This test mainly ensures no exceptions are raised during cleanup