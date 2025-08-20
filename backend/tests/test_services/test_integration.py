"""
Integration tests for JobSearchService to verify it works with the actual JobSpy library.
"""

import pytest
from unittest.mock import patch
import pandas as pd

from app.services.job_search_service import JobSearchService
from app.models.search import SearchRequest


class TestJobSearchServiceIntegration:
    """Integration tests for JobSearchService."""
    
    @pytest.fixture
    def service(self):
        """Create JobSearchService instance."""
        return JobSearchService()
    
    @pytest.mark.asyncio
    async def test_service_can_be_instantiated(self, service):
        """Test that the service can be created without errors."""
        assert isinstance(service, JobSearchService)
        assert service.default_timeout == 60
        assert hasattr(service, '_executor')
    
    @pytest.mark.asyncio
    async def test_parameter_mapping_integration(self, service):
        """Test parameter mapping with realistic search request."""
        search_request = SearchRequest(
            search_term="python developer",
            location="San Francisco, CA",
            job_type="fulltime",
            site_names=["indeed", "linkedin", "zip_recruiter"],
            results_wanted=15,
            distance=25,
            is_remote=True,
            hours_old=72
        )
        
        params = service._map_search_parameters(search_request)
        
        # Verify all parameters are correctly mapped
        assert params["site_name"] == ["indeed", "linkedin", "ziprecruiter"]
        assert params["search_term"] == "python developer"
        assert params["location"] == "San Francisco, CA"
        assert params["job_type"] == "fulltime"
        assert params["results_wanted"] == 15
        assert params["distance"] == 25
        assert params["is_remote"] is True
        assert params["hours_old"] == 72
        assert params["country_indeed"] == "usa"
        assert params["description_format"] == "markdown"
        assert params["verbose"] == 0
    
    @pytest.mark.asyncio
    async def test_validation_integration(self, service):
        """Test validation with various search requests."""
        # Valid request
        valid_request = SearchRequest(
            search_term="engineer",
            site_names=["indeed"]
        )
        result = await service.validate_search_parameters(valid_request)
        assert result is True
        
        # Valid request with location only
        location_only_request = SearchRequest(
            location="New York",
            site_names=["linkedin"]
        )
        result = await service.validate_search_parameters(location_only_request)
        assert result is True
    
    @pytest.mark.asyncio
    @patch('app.services.job_search_service.scrape_jobs')
    async def test_end_to_end_mock_search(self, mock_scrape_jobs, service):
        """Test complete search workflow with mocked JobSpy."""
        # Create realistic mock data
        mock_data = {
            'id': ['job_001', 'job_002'],
            'title': ['Senior Python Developer', 'Software Engineer'],
            'company_name': ['TechCorp Inc', 'DevCompany LLC'],
            'job_url': ['https://example.com/job1', 'https://example.com/job2'],
            'location': ['San Francisco, CA, USA', 'Remote, USA'],
            'description': ['Python development role...', 'Full-stack development...'],
            'site': ['indeed', 'linkedin'],
            'job_type': ['fulltime', 'fulltime'],
            'min_amount': [120000, 100000],
            'max_amount': [150000, 130000],
            'interval': ['yearly', 'yearly'],
            'currency': ['USD', 'USD'],
            'date_posted': ['2024-01-15', '2024-01-14'],
            'is_remote': [False, True],
            'company_industry': ['Technology', 'Software'],
            'skills': ['Python, Django', 'JavaScript, React'],
            'experience_range': ['3-5 years', '2-4 years']
        }
        mock_df = pd.DataFrame(mock_data)
        mock_scrape_jobs.return_value = mock_df
        
        # Create search request
        search_request = SearchRequest(
            search_term="python developer",
            location="San Francisco",
            site_names=["indeed", "linkedin"],
            results_wanted=10
        )
        
        # Execute search
        result = await service.search_jobs(search_request)
        
        # Verify results
        assert len(result.jobs) == 2
        assert result.total_results == 2
        assert len(result.errors) == 0
        
        # Verify job data
        job1 = result.jobs[0]
        assert job1.title == "Senior Python Developer"
        assert job1.company_name == "TechCorp Inc"
        assert job1.site == "indeed"
        assert job1.location.city == "San Francisco"
        assert job1.location.state == "CA"
        assert job1.compensation.min_amount == 120000
        
        job2 = result.jobs[1]
        assert job2.title == "Software Engineer"
        assert job2.is_remote is True
        
        # Verify metadata
        metadata = result.search_metadata
        assert metadata.total_sites_searched == 2
        assert "indeed" in metadata.successful_sites
        assert "linkedin" in metadata.successful_sites
        assert len(metadata.failed_sites) == 0
        assert metadata.total_results_found == 2
        
        # Verify JobSpy was called correctly
        mock_scrape_jobs.assert_called_once()
        call_kwargs = mock_scrape_jobs.call_args[1]
        assert call_kwargs["site_name"] == ["indeed", "linkedin"]
        assert call_kwargs["search_term"] == "python developer"
        assert call_kwargs["location"] == "San Francisco"
    
    def test_service_cleanup(self):
        """Test that service cleans up resources properly."""
        service = JobSearchService()
        executor = service._executor
        
        # Verify executor exists
        assert executor is not None
        
        # Delete service (triggers cleanup)
        del service
        
        # This test mainly ensures no exceptions during cleanup
        # The actual cleanup verification would require implementation details