"""
Unit tests for job-related Pydantic models.
"""

import pytest
from pydantic import ValidationError
from app.models.job import WebJobPost
from jobspy.model import Location, Compensation, CompensationInterval


class TestWebJobPost:
    """Test cases for WebJobPost model."""

    def test_valid_web_job_post(self):
        """Test creating a valid WebJobPost."""
        job = WebJobPost(
            id="job_123",
            title="Senior Software Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job/123",
            location=Location(city="San Francisco", state="CA"),
            search_id="search_456",
            relevance_score=0.85,
            site="indeed"
        )
        
        assert job.id == "job_123"
        assert job.title == "Senior Software Engineer"
        assert job.company_name == "Tech Corp"
        assert job.job_url == "https://example.com/job/123"
        assert job.location.city == "San Francisco"
        assert job.location.state == "CA"
        assert job.search_id == "search_456"
        assert job.relevance_score == 0.85
        assert job.site == "indeed"

    def test_minimal_web_job_post(self):
        """Test creating WebJobPost with minimal required fields."""
        job = WebJobPost(
            title="Software Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job/123",
            location=None,
            search_id="search_456",
            site="indeed"
        )
        
        assert job.title == "Software Engineer"
        assert job.company_name == "Tech Corp"
        assert job.job_url == "https://example.com/job/123"
        assert job.location is None
        assert job.search_id == "search_456"
        assert job.relevance_score is None
        assert job.site == "indeed"

    def test_relevance_score_validation(self):
        """Test validation of relevance_score field."""
        # Valid scores
        valid_scores = [0.0, 0.5, 1.0]
        for score in valid_scores:
            job = WebJobPost(
                title="Test Job",
                company_name="Test Corp",
                job_url="https://example.com/job",
                location=None,
                search_id="search_123",
                site="indeed",
                relevance_score=score
            )
            assert job.relevance_score == score
        
        # Score too low
        with pytest.raises(ValidationError) as exc_info:
            WebJobPost(
                title="Test Job",
                company_name="Test Corp",
                job_url="https://example.com/job",
                location=None,
                search_id="search_123",
                site="indeed",
                relevance_score=-0.1
            )
        assert "greater than or equal to 0" in str(exc_info.value)
        
        # Score too high
        with pytest.raises(ValidationError) as exc_info:
            WebJobPost(
                title="Test Job",
                company_name="Test Corp",
                job_url="https://example.com/job",
                location=None,
                search_id="search_123",
                site="indeed",
                relevance_score=1.1
            )
        assert "less than or equal to 1" in str(exc_info.value)

    def test_with_compensation(self):
        """Test WebJobPost with compensation information."""
        compensation = Compensation(
            min_amount=120000,
            max_amount=150000,
            interval=CompensationInterval.YEARLY,
            currency="USD"
        )
        
        job = WebJobPost(
            title="Senior Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job",
            location=Location(city="New York", state="NY"),
            compensation=compensation,
            search_id="search_123",
            site="linkedin"
        )
        
        assert job.compensation.min_amount == 120000
        assert job.compensation.max_amount == 150000
        assert job.compensation.interval == CompensationInterval.YEARLY
        assert job.compensation.currency == "USD"

    def test_with_description(self):
        """Test WebJobPost with job description."""
        description = "We are looking for a senior software engineer with 5+ years of experience..."
        
        job = WebJobPost(
            title="Senior Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job",
            location=None,
            description=description,
            search_id="search_123",
            site="glassdoor"
        )
        
        assert job.description == description

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Missing title
        with pytest.raises(ValidationError) as exc_info:
            WebJobPost(
                company_name="Tech Corp",
                job_url="https://example.com/job",
                location=None,
                search_id="search_123",
                site="indeed"
            )
        assert "title" in str(exc_info.value)
        
        # Missing job_url
        with pytest.raises(ValidationError) as exc_info:
            WebJobPost(
                title="Software Engineer",
                company_name="Tech Corp",
                location=None,
                search_id="search_123",
                site="indeed"
            )
        assert "job_url" in str(exc_info.value)
        
        # Missing search_id
        with pytest.raises(ValidationError) as exc_info:
            WebJobPost(
                title="Software Engineer",
                company_name="Tech Corp",
                job_url="https://example.com/job",
                location=None,
                site="indeed"
            )
        assert "search_id" in str(exc_info.value)
        
        # Missing site
        with pytest.raises(ValidationError) as exc_info:
            WebJobPost(
                title="Software Engineer",
                company_name="Tech Corp",
                job_url="https://example.com/job",
                location=None,
                search_id="search_123"
            )
        assert "site" in str(exc_info.value)

    def test_inheritance_from_jobpost(self):
        """Test that WebJobPost properly inherits from JobPost."""
        job = WebJobPost(
            title="Software Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job",
            location=Location(city="Austin", state="TX"),
            search_id="search_123",
            site="indeed",
            is_remote=True,
            job_type=None,
            date_posted=None
        )
        
        # Test inherited fields
        assert job.is_remote is True
        assert job.job_type is None
        assert job.date_posted is None
        
        # Test web-specific fields
        assert job.search_id == "search_123"
        assert job.site == "indeed"