"""
Unit tests for search-related Pydantic models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models.search import SearchRequest, SearchMetadata, JobSearchResponse
from app.models.job import WebJobPost
from jobspy.model import Location, Compensation, CompensationInterval


class TestSearchRequest:
    """Test cases for SearchRequest model."""

    def test_valid_search_request(self):
        """Test creating a valid SearchRequest."""
        request = SearchRequest(
            search_term="software engineer",
            location="San Francisco, CA",
            job_type="fulltime",
            site_names=["indeed", "linkedin"],
            results_wanted=25,
            distance=50,
            is_remote=False,
            hours_old=168
        )
        
        assert request.search_term == "software engineer"
        assert request.location == "San Francisco, CA"
        assert request.job_type == "fulltime"
        assert request.site_names == ["indeed", "linkedin"]
        assert request.results_wanted == 25
        assert request.distance == 50
        assert request.is_remote is False
        assert request.hours_old == 168

    def test_default_values(self):
        """Test SearchRequest with default values."""
        request = SearchRequest()
        
        assert request.search_term is None
        assert request.location is None
        assert request.job_type is None
        assert request.site_names == ["indeed", "linkedin", "glassdoor"]
        assert request.results_wanted == 20
        assert request.distance == 50
        assert request.is_remote is False
        assert request.hours_old is None

    def test_results_wanted_validation(self):
        """Test validation of results_wanted field."""
        # Valid range
        request = SearchRequest(results_wanted=50)
        assert request.results_wanted == 50
        
        # Too low
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(results_wanted=0)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Too high
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(results_wanted=101)
        assert "less than or equal to 100" in str(exc_info.value)

    def test_distance_validation(self):
        """Test validation of distance field."""
        # Valid range
        request = SearchRequest(distance=100)
        assert request.distance == 100
        
        # Negative value
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(distance=-1)
        assert "greater than or equal to 0" in str(exc_info.value)
        
        # Too high
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(distance=201)
        assert "less than or equal to 200" in str(exc_info.value)

    def test_hours_old_validation(self):
        """Test validation of hours_old field."""
        # Valid range
        request = SearchRequest(hours_old=24)
        assert request.hours_old == 24
        
        # Too low
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(hours_old=0)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Too high (more than 1 year)
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(hours_old=8761)
        assert "less than or equal to 8760" in str(exc_info.value)

    def test_site_names_validation(self):
        """Test validation of site_names field."""
        # Valid sites
        request = SearchRequest(site_names=["indeed", "linkedin"])
        assert request.site_names == ["indeed", "linkedin"]
        
        # Invalid site
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(site_names=["invalid_site"])
        assert "Unsupported job boards" in str(exc_info.value)
        
        # Mixed valid and invalid
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(site_names=["indeed", "invalid_site"])
        assert "Unsupported job boards" in str(exc_info.value)
        
        # Empty list
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(site_names=[])
        assert "at least 1 item" in str(exc_info.value)

    def test_job_type_validation(self):
        """Test validation of job_type field."""
        # Valid job types
        valid_types = ["fulltime", "parttime", "contract", "temporary", "internship"]
        for job_type in valid_types:
            request = SearchRequest(job_type=job_type)
            assert request.job_type == job_type
        
        # Invalid job type
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(job_type="invalid_type")
        assert "Invalid job type" in str(exc_info.value)

    def test_string_length_validation(self):
        """Test string length validation for search_term and location."""
        # Valid lengths
        request = SearchRequest(
            search_term="a" * 200,  # Max length
            location="a" * 100      # Max length
        )
        assert len(request.search_term) == 200
        assert len(request.location) == 100
        
        # Too long search_term
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(search_term="a" * 201)
        assert "at most 200 characters" in str(exc_info.value)
        
        # Too long location
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(location="a" * 101)
        assert "at most 100 characters" in str(exc_info.value)
        
        # Empty strings (should be treated as None)
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(search_term="")
        assert "at least 1 character" in str(exc_info.value)


class TestSearchMetadata:
    """Test cases for SearchMetadata model."""

    def test_valid_search_metadata(self):
        """Test creating valid SearchMetadata."""
        timestamp = datetime.now()
        metadata = SearchMetadata(
            search_id="search_123",
            timestamp=timestamp,
            total_sites_searched=3,
            successful_sites=["indeed", "linkedin"],
            failed_sites=["glassdoor"],
            search_duration=12.5,
            total_results_found=45
        )
        
        assert metadata.search_id == "search_123"
        assert metadata.timestamp == timestamp
        assert metadata.total_sites_searched == 3
        assert metadata.successful_sites == ["indeed", "linkedin"]
        assert metadata.failed_sites == ["glassdoor"]
        assert metadata.search_duration == 12.5
        assert metadata.total_results_found == 45

    def test_negative_values_validation(self):
        """Test validation of non-negative numeric fields."""
        timestamp = datetime.now()
        
        # Negative total_sites_searched
        with pytest.raises(ValidationError) as exc_info:
            SearchMetadata(
                search_id="test",
                timestamp=timestamp,
                total_sites_searched=-1,
                successful_sites=[],
                failed_sites=[],
                search_duration=0.0,
                total_results_found=0
            )
        assert "greater than or equal to 0" in str(exc_info.value)
        
        # Negative search_duration
        with pytest.raises(ValidationError) as exc_info:
            SearchMetadata(
                search_id="test",
                timestamp=timestamp,
                total_sites_searched=0,
                successful_sites=[],
                failed_sites=[],
                search_duration=-1.0,
                total_results_found=0
            )
        assert "greater than or equal to 0" in str(exc_info.value)
        
        # Negative total_results_found
        with pytest.raises(ValidationError) as exc_info:
            SearchMetadata(
                search_id="test",
                timestamp=timestamp,
                total_sites_searched=0,
                successful_sites=[],
                failed_sites=[],
                search_duration=0.0,
                total_results_found=-1
            )
        assert "greater than or equal to 0" in str(exc_info.value)


class TestJobSearchResponse:
    """Test cases for JobSearchResponse model."""

    def create_sample_job(self, job_id: str = "job_1") -> WebJobPost:
        """Helper method to create a sample WebJobPost."""
        return WebJobPost(
            id=job_id,
            title="Software Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job/1",
            location=Location(city="San Francisco", state="CA"),
            search_id="search_123",
            site="indeed"
        )

    def create_sample_metadata(self) -> SearchMetadata:
        """Helper method to create sample SearchMetadata."""
        return SearchMetadata(
            search_id="search_123",
            timestamp=datetime.now(),
            total_sites_searched=2,
            successful_sites=["indeed", "linkedin"],
            failed_sites=[],
            search_duration=10.0,
            total_results_found=2
        )

    def test_valid_job_search_response(self):
        """Test creating a valid JobSearchResponse."""
        jobs = [self.create_sample_job("job_1"), self.create_sample_job("job_2")]
        metadata = self.create_sample_metadata()
        
        response = JobSearchResponse(
            jobs=jobs,
            total_results=2,
            search_metadata=metadata,
            errors=["Some error"],
            warnings=["Some warning"]
        )
        
        assert len(response.jobs) == 2
        assert response.total_results == 2
        assert response.search_metadata == metadata
        assert response.errors == ["Some error"]
        assert response.warnings == ["Some warning"]

    def test_default_values(self):
        """Test JobSearchResponse with default values."""
        metadata = self.create_sample_metadata()
        
        response = JobSearchResponse(
            jobs=[],
            total_results=0,
            search_metadata=metadata
        )
        
        assert response.jobs == []
        assert response.total_results == 0
        assert response.errors == []
        assert response.warnings == []

    def test_total_results_validation(self):
        """Test validation that total_results matches job count."""
        jobs = [self.create_sample_job()]
        metadata = self.create_sample_metadata()
        
        # Matching count - should work
        response = JobSearchResponse(
            jobs=jobs,
            total_results=1,
            search_metadata=metadata
        )
        assert response.total_results == 1
        
        # Mismatched count - should fail
        with pytest.raises(ValidationError) as exc_info:
            JobSearchResponse(
                jobs=jobs,
                total_results=2,  # Wrong count
                search_metadata=metadata
            )
        assert "total_results must match the number of jobs" in str(exc_info.value)

    def test_negative_total_results(self):
        """Test validation of negative total_results."""
        metadata = self.create_sample_metadata()
        
        with pytest.raises(ValidationError) as exc_info:
            JobSearchResponse(
                jobs=[],
                total_results=-1,
                search_metadata=metadata
            )
        assert "greater than or equal to 0" in str(exc_info.value)