"""
Tests for the export service functionality.
"""

import pytest
import pandas as pd
from datetime import datetime, date
from io import StringIO

from app.services.export_service import ExportService
from app.models.job import WebJobPost
from app.models.export import ExportFormat
from app.models.errors import ExportError, ValidationError
from jobspy.model import JobType, CompensationInterval, Location, Compensation


@pytest.fixture
def export_service():
    """Create an export service instance for testing."""
    return ExportService()


@pytest.fixture
def sample_jobs():
    """Create sample job posts for testing."""
    return [
        WebJobPost(
            id="job_1",
            title="Software Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job1",
            site="indeed",
            search_id="search_123",
            location=Location(city="San Francisco", state="CA", country="USA"),
            compensation=Compensation(
                min_amount=120000,
                max_amount=150000,
                interval=CompensationInterval.YEARLY,
                currency="USD"
            ),
            job_type=[JobType.FULL_TIME],
            date_posted=date(2024, 1, 15),
            is_remote=False,
            description="Great software engineering role",
            company_industry="Technology",
            job_level="Mid-level",
            skills=["Python", "JavaScript", "React"]
        ),
        WebJobPost(
            id="job_2",
            title="Data Scientist",
            company_name="Data Inc",
            job_url="https://example.com/job2",
            site="linkedin",
            search_id="search_123",
            location=Location(city="New York", state="NY", country="USA"),
            compensation=Compensation(
                min_amount=100000,
                max_amount=130000,
                interval=CompensationInterval.YEARLY,
                currency="USD"
            ),
            job_type=[JobType.FULL_TIME],
            date_posted=date(2024, 1, 14),
            is_remote=True,
            description="Exciting data science opportunity",
            company_industry="Finance",
            job_level="Senior",
            skills=["Python", "SQL", "Machine Learning"]
        )
    ]


class TestExportService:
    """Test cases for ExportService."""
    
    @pytest.mark.asyncio
    async def test_export_jobs_to_csv_basic(self, export_service, sample_jobs):
        """Test basic CSV export functionality."""
        search_id = "test_search_123"
        
        csv_bytes, metadata = await export_service.export_jobs_to_csv(
            jobs=sample_jobs,
            search_id=search_id
        )
        
        # Check metadata
        assert metadata.search_id == search_id
        assert metadata.format == ExportFormat.CSV
        assert metadata.total_jobs_exported == 2
        assert metadata.file_size_bytes == len(csv_bytes)
        assert metadata.filename.endswith('.csv')
        
        # Check CSV content
        csv_content = csv_bytes.decode('utf-8')
        assert "Software Engineer" in csv_content
        assert "Data Scientist" in csv_content
        assert "Tech Corp" in csv_content
        assert "Data Inc" in csv_content
        
        # Parse CSV to verify structure
        df = pd.read_csv(StringIO(csv_content))
        assert len(df) == 2
        assert 'job_id' in df.columns
        assert 'title' in df.columns
        assert 'company_name' in df.columns
    
    @pytest.mark.asyncio
    async def test_export_jobs_to_csv_with_custom_filename(self, export_service, sample_jobs):
        """Test CSV export with custom filename."""
        search_id = "test_search_456"
        custom_filename = "my_custom_export"
        
        csv_bytes, metadata = await export_service.export_jobs_to_csv(
            jobs=sample_jobs,
            search_id=search_id,
            filename=custom_filename
        )
        
        assert metadata.filename == "my_custom_export.csv"
    
    @pytest.mark.asyncio
    async def test_export_jobs_to_csv_exclude_description(self, export_service, sample_jobs):
        """Test CSV export without descriptions."""
        search_id = "test_search_789"
        
        csv_bytes, metadata = await export_service.export_jobs_to_csv(
            jobs=sample_jobs,
            search_id=search_id,
            include_description=False
        )
        
        csv_content = csv_bytes.decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))
        
        # Description column should not be present
        assert 'description' not in df.columns
    
    @pytest.mark.asyncio
    async def test_export_jobs_to_csv_exclude_company_details(self, export_service, sample_jobs):
        """Test CSV export without company details."""
        search_id = "test_search_101"
        
        csv_bytes, metadata = await export_service.export_jobs_to_csv(
            jobs=sample_jobs,
            search_id=search_id,
            include_company_details=False
        )
        
        csv_content = csv_bytes.decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))
        
        # Company detail columns should not be present
        company_columns = ['company_url', 'company_industry', 'company_num_employees']
        for col in company_columns:
            assert col not in df.columns
    
    @pytest.mark.asyncio
    async def test_export_empty_job_list(self, export_service):
        """Test exporting empty job list raises error."""
        search_id = "empty_search"
        
        with pytest.raises(ExportError) as exc_info:
            await export_service.export_jobs_to_csv(
                jobs=[],
                search_id=search_id
            )
        
        assert "No jobs to export" in str(exc_info.value)
        assert exc_info.value.export_format == ExportFormat.CSV
    
    def test_jobs_to_dataframe_complete_data(self, export_service, sample_jobs):
        """Test converting jobs to DataFrame with complete data."""
        df = export_service._jobs_to_dataframe(sample_jobs)
        
        assert len(df) == 2
        
        # Check first job
        job1 = df.iloc[0]
        assert job1['job_id'] == 'job_1'
        assert job1['title'] == 'Software Engineer'
        assert job1['company_name'] == 'Tech Corp'
        assert job1['location_city'] == 'San Francisco'
        assert job1['location_state'] == 'CA'
        assert job1['salary_min'] == 120000
        assert job1['salary_max'] == 150000
        assert job1['salary_interval'] == 'yearly'
        assert job1['job_type'] == 'fulltime'
        assert job1['is_remote'] == False
        assert job1['skills'] == 'Python, JavaScript, React'
        
        # Check second job
        job2 = df.iloc[1]
        assert job2['job_id'] == 'job_2'
        assert job2['title'] == 'Data Scientist'
        assert job2['is_remote'] == True
    
    def test_jobs_to_dataframe_minimal_data(self, export_service):
        """Test converting jobs with minimal data to DataFrame."""
        minimal_job = WebJobPost(
            id="minimal_job",
            title="Basic Job",
            company_name="Test Company",
            job_url="https://example.com/minimal",
            location=Location(city="Test City", state="TS", country="USA"),
            site="test",
            search_id="minimal_search"
        )
        
        df = export_service._jobs_to_dataframe([minimal_job])
        
        assert len(df) == 1
        job = df.iloc[0]
        assert job['job_id'] == 'minimal_job'
        assert job['title'] == 'Basic Job'
        assert job['company_name'] == 'Test Company'
        assert job['location_city'] == 'Test City'
        assert pd.isna(job['salary_min'])
    
    def test_get_supported_formats(self, export_service):
        """Test getting supported export formats."""
        formats = export_service.get_supported_formats()
        assert 'csv' in formats
        assert len(formats) >= 1
    
    def test_validate_export_request_valid(self, export_service, sample_jobs):
        """Test validating valid export request."""
        result = export_service.validate_export_request(sample_jobs, ExportFormat.CSV)
        assert result is True
    
    def test_validate_export_request_empty_jobs(self, export_service):
        """Test validating export request with empty job list."""
        with pytest.raises(ValidationError) as exc_info:
            export_service.validate_export_request([], ExportFormat.CSV)
        
        assert "Cannot export empty job list" in str(exc_info.value)
    
    def test_validate_export_request_invalid_format(self, export_service, sample_jobs):
        """Test validating export request with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            export_service.validate_export_request(sample_jobs, "invalid_format")
        
        assert "Unsupported export format" in str(exc_info.value)