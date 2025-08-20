"""
Tests for the export API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, date
from unittest.mock import AsyncMock, patch
import io

from app.main import app
from app.models.job import WebJobPost
from app.services.cache_service import CacheEntry
from app.models.export import ExportFormat
from jobspy.model import JobType, CompensationInterval, Location, Compensation


client = TestClient(app)


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
            is_remote=False
        ),
        WebJobPost(
            id="job_2",
            title="Data Scientist",
            company_name="Data Inc",
            job_url="https://example.com/job2",
            location=Location(city="New York", state="NY", country="USA"),
            site="linkedin",
            search_id="search_123",
            is_remote=True
        )
    ]


@pytest.fixture
def sample_cache_entry(sample_jobs):
    """Create a sample cache entry for testing."""
    return CacheEntry(
        jobs=sample_jobs,
        timestamp=datetime.utcnow(),
        search_metadata={
            "search_id": "search_123",
            "total_sites_searched": 2,
            "successful_sites": ["indeed", "linkedin"],
            "failed_sites": [],
            "search_duration": 5.2
        }
    )


class TestExportEndpoint:
    """Test cases for export endpoints."""
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_search_results_csv_success(self, mock_get_results, sample_cache_entry):
        """Test successful CSV export."""
        mock_get_results.return_value = sample_cache_entry
        
        response = client.get("/api/v1/export/search_123?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]
        
        # Check CSV content
        csv_content = response.content.decode('utf-8')
        assert "Software Engineer" in csv_content
        assert "Data Scientist" in csv_content
        assert "Tech Corp" in csv_content
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_search_results_not_found(self, mock_get_results):
        """Test export when search results not found."""
        mock_get_results.return_value = None
        
        response = client.get("/api/v1/export/nonexistent_search")
        
        assert response.status_code == 404
        assert "Search results not found" in response.json()["detail"]
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_search_results_with_custom_filename(self, mock_get_results, sample_cache_entry):
        """Test export with custom filename."""
        mock_get_results.return_value = sample_cache_entry
        
        response = client.get("/api/v1/export/search_123?filename=my_jobs")
        
        assert response.status_code == 200
        assert "my_jobs.csv" in response.headers["content-disposition"]
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_search_results_exclude_description(self, mock_get_results, sample_cache_entry):
        """Test export excluding descriptions."""
        mock_get_results.return_value = sample_cache_entry
        
        response = client.get("/api/v1/export/search_123?include_description=false")
        
        assert response.status_code == 200
        
        # Parse CSV to check columns
        csv_content = response.content.decode('utf-8')
        lines = csv_content.split('\n')
        headers = lines[0].split(',')
        assert 'description' not in headers
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_search_results_exclude_company_details(self, mock_get_results, sample_cache_entry):
        """Test export excluding company details."""
        mock_get_results.return_value = sample_cache_entry
        
        response = client.get("/api/v1/export/search_123?include_company_details=false")
        
        assert response.status_code == 200
        
        # Parse CSV to check columns
        csv_content = response.content.decode('utf-8')
        lines = csv_content.split('\n')
        headers = lines[0].split(',')
        company_detail_columns = ['company_url', 'company_industry', 'company_num_employees']
        for col in company_detail_columns:
            assert col not in headers
    
    def test_export_search_results_unsupported_format(self):
        """Test export with unsupported format."""
        response = client.get("/api/v1/export/search_123?format=xml")
        
        assert response.status_code == 422  # Validation error for invalid enum
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_info_success(self, mock_get_results, sample_cache_entry):
        """Test getting export info successfully."""
        mock_get_results.return_value = sample_cache_entry
        
        response = client.get("/api/v1/export/search_123/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["search_id"] == "search_123"
        assert data["total_jobs"] == 2
        assert "search_timestamp" in data
        assert "search_metadata" in data
        assert "supported_formats" in data
        assert "csv" in data["supported_formats"]
        assert "estimated_csv_size_kb" in data
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_info_not_found(self, mock_get_results):
        """Test getting export info when search not found."""
        mock_get_results.return_value = None
        
        response = client.get("/api/v1/export/nonexistent_search/info")
        
        assert response.status_code == 404
        assert "Search results not found" in response.json()["detail"]
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    @patch('app.services.export_service.ExportService.export_jobs_to_csv')
    def test_export_service_error_handling(self, mock_export, mock_get_results, sample_cache_entry):
        """Test handling of export service errors."""
        from app.models.errors import ExportError
        
        mock_get_results.return_value = sample_cache_entry
        mock_export.side_effect = ExportError("Export failed", export_format="csv")
        
        response = client.get("/api/v1/export/search_123")
        
        assert response.status_code == 500
        assert "Export failed" in response.json()["detail"]
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_export_empty_job_list(self, mock_get_results):
        """Test export with empty job list."""
        empty_cache_entry = CacheEntry(
            jobs=[],
            timestamp=datetime.utcnow(),
            search_metadata={"search_id": "empty_search"}
        )
        mock_get_results.return_value = empty_cache_entry
        
        response = client.get("/api/v1/export/empty_search")
        
        assert response.status_code == 500
        assert "Export failed" in response.json()["detail"]


class TestExportIntegration:
    """Integration tests for export functionality."""
    
    @patch('app.services.cache_service.search_results_cache.get_search_results')
    def test_full_export_workflow(self, mock_get_results, sample_cache_entry):
        """Test complete export workflow from API to file download."""
        mock_get_results.return_value = sample_cache_entry
        
        # First, get export info
        info_response = client.get("/api/v1/export/search_123/info")
        assert info_response.status_code == 200
        info_data = info_response.json()
        
        # Then, export the data
        export_response = client.get("/api/v1/export/search_123")
        assert export_response.status_code == 200
        
        # Verify the exported data matches the info
        csv_content = export_response.content.decode('utf-8')
        lines = [line for line in csv_content.split('\n') if line.strip()]
        data_rows = len(lines) - 1  # Subtract header row
        
        assert data_rows == info_data["total_jobs"]
        
        # Verify CSV structure
        headers = lines[0].split(',')
        expected_headers = ['job_id', 'title', 'company_name', 'job_url', 'site']
        for header in expected_headers:
            assert header in headers