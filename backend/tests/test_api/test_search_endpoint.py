"""
Integration tests for the job search API endpoint.

Tests the complete search endpoint functionality including request validation,
error handling, and response formatting.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import pandas as pd

from app.main import app
from app.models.search import SearchRequest, JobSearchResponse, SearchMetadata
from app.models.job import WebJobPost
from app.models.errors import (
    RateLimitError, 
    SearchTimeoutError, 
    NetworkError, 
    JobBoardError,
    ValidationError,
    ValidationErrorDetail
)


client = TestClient(app)


class TestSearchEndpoint:
    """Test cases for the job search endpoint."""
    
    def test_search_endpoint_success(self):
        """Test successful job search request."""
        # Mock successful search response
        from jobspy.model import Location
        
        mock_jobs = [
            WebJobPost(
                id="job_1",
                title="Software Engineer",
                company_name="Tech Corp",
                job_url="https://example.com/job1",
                location=Location(city="San Francisco", state="CA", country="USA"),
                search_id="search_123",
                site="indeed"
            ),
            WebJobPost(
                id="job_2", 
                title="Data Scientist",
                company_name="Data Inc",
                job_url="https://example.com/job2",
                location=Location(city="New York", state="NY", country="USA"),
                search_id="search_123",
                site="linkedin"
            )
        ]
        
        mock_metadata = SearchMetadata(
            search_id="search_123",
            timestamp=datetime.now(timezone.utc),
            total_sites_searched=2,
            successful_sites=["indeed", "linkedin"],
            failed_sites=[],
            search_duration=5.2,
            total_results_found=2
        )
        
        mock_response = JobSearchResponse(
            jobs=mock_jobs,
            total_results=2,
            search_metadata=mock_metadata,
            errors=[],
            warnings=[]
        )
        
        with patch('app.services.job_search_service.JobSearchService.search_jobs', 
                  new_callable=AsyncMock) as mock_search:
            with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                      new_callable=AsyncMock) as mock_validate:
                
                mock_validate.return_value = True
                mock_search.return_value = mock_response
                
                response = client.post(
                    "/api/v1/search/",
                    json={
                        "search_term": "software engineer",
                        "location": "San Francisco, CA",
                        "site_names": ["indeed", "linkedin"],
                        "results_wanted": 20
                    }
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_results"] == 2
        assert len(data["jobs"]) == 2
        assert data["jobs"][0]["title"] == "Software Engineer"
        assert data["jobs"][1]["title"] == "Data Scientist"
        assert data["search_metadata"]["search_id"] == "search_123"
        assert data["search_metadata"]["successful_sites"] == ["indeed", "linkedin"]
        assert data["errors"] == []
    
    def test_search_endpoint_validation_error(self):
        """Test search endpoint with validation errors."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            
            mock_validate.side_effect = ValidationError(
                "Either search term or location must be provided",
                field_errors=[
                    ValidationErrorDetail(
                        field="search_term",
                        message="Either search term or location must be provided",
                        invalid_value=None
                    )
                ]
            )
            
            response = client.post(
                "/api/v1/search/",
                json={
                    "site_names": ["indeed"],
                    "results_wanted": 20
                }
            )
        
        assert response.status_code == 422
        data = response.json()
        
        assert data["detail"]["error"] == "Validation Error"
        assert "Either search term or location must be provided" in data["detail"]["message"]
        assert len(data["detail"]["field_errors"]) == 1
        assert data["detail"]["field_errors"][0]["field"] == "search_term"
    
    def test_search_endpoint_rate_limit_error(self):
        """Test search endpoint with rate limit error."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            with patch('app.services.job_search_service.JobSearchService.search_jobs',
                      new_callable=AsyncMock) as mock_search:
                
                mock_validate.return_value = True
                mock_search.side_effect = RateLimitError(
                    "Rate limit exceeded for LinkedIn",
                    site="linkedin",
                    retry_after=300
                )
                
                response = client.post(
                    "/api/v1/search/",
                    json={
                        "search_term": "software engineer",
                        "site_names": ["linkedin"],
                        "results_wanted": 20
                    }
                )
        
        assert response.status_code == 429
        data = response.json()
        
        assert data["detail"]["error"] == "Rate Limit Exceeded"
        assert data["detail"]["site"] == "linkedin"
        assert data["detail"]["retry_after"] == 300
        assert response.headers.get("Retry-After") == "300"
    
    def test_search_endpoint_timeout_error(self):
        """Test search endpoint with timeout error."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            with patch('app.services.job_search_service.JobSearchService.search_jobs',
                      new_callable=AsyncMock) as mock_search:
                
                mock_validate.return_value = True
                mock_search.side_effect = SearchTimeoutError(
                    "Search timed out after 60 seconds",
                    timeout_seconds=60
                )
                
                response = client.post(
                    "/api/v1/search/",
                    json={
                        "search_term": "software engineer",
                        "site_names": ["indeed"],
                        "results_wanted": 20
                    }
                )
        
        assert response.status_code == 408
        data = response.json()
        
        assert data["detail"]["error"] == "Search Timeout"
        assert data["detail"]["timeout_seconds"] == 60
    
    def test_search_endpoint_network_error(self):
        """Test search endpoint with network error."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            with patch('app.services.job_search_service.JobSearchService.search_jobs',
                      new_callable=AsyncMock) as mock_search:
                
                mock_validate.return_value = True
                mock_search.side_effect = NetworkError(
                    "Connection failed to job board",
                    url="https://indeed.com"
                )
                
                response = client.post(
                    "/api/v1/search/",
                    json={
                        "search_term": "software engineer",
                        "site_names": ["indeed"],
                        "results_wanted": 20
                    }
                )
        
        assert response.status_code == 503
        data = response.json()
        
        assert data["detail"]["error"] == "Network Error"
        assert data["detail"]["url"] == "https://indeed.com"
    
    def test_search_endpoint_job_board_error(self):
        """Test search endpoint with job board error returns partial results."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            with patch('app.services.job_search_service.JobSearchService.search_jobs',
                      new_callable=AsyncMock) as mock_search:
                
                mock_validate.return_value = True
                mock_search.side_effect = JobBoardError(
                    "Glassdoor is temporarily unavailable",
                    site="glassdoor",
                    original_error=Exception("Service unavailable")
                )
                
                response = client.post(
                    "/api/v1/search/",
                    json={
                        "search_term": "software engineer",
                        "site_names": ["glassdoor"],
                        "results_wanted": 20
                    }
                )
        
        assert response.status_code == 200  # Job board errors return 200 with error info
        data = response.json()
        
        assert data["total_results"] == 0
        assert len(data["jobs"]) == 0
        assert len(data["errors"]) == 1
        assert "Glassdoor is temporarily unavailable" in data["errors"][0]
        assert data["search_metadata"]["failed_sites"] == ["glassdoor"]
    
    def test_search_endpoint_invalid_json(self):
        """Test search endpoint with invalid JSON payload."""
        response = client.post(
            "/api/v1/search/",
            json={
                "search_term": "software engineer",
                "results_wanted": "invalid_number"  # Should be int
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_search_endpoint_missing_required_fields(self):
        """Test search endpoint with missing required fields."""
        response = client.post(
            "/api/v1/search/",
            json={}  # Empty payload
        )
        
        # Should pass validation since all fields have defaults or are optional
        # But should fail business logic validation
        assert response.status_code in [200, 422]  # Depends on validation logic
    
    def test_search_endpoint_invalid_site_names(self):
        """Test search endpoint with invalid site names."""
        response = client.post(
            "/api/v1/search/",
            json={
                "search_term": "software engineer",
                "site_names": ["invalid_site", "another_invalid"]
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestSearchValidationEndpoint:
    """Test cases for the search validation endpoint."""
    
    def test_validate_endpoint_success(self):
        """Test successful parameter validation."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            
            mock_validate.return_value = True
            
            response = client.get(
                "/api/v1/search/validate",
                params={
                    "search_term": "software engineer",
                    "location": "San Francisco, CA",
                    "site_names": "indeed,linkedin",
                    "results_wanted": 20
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["message"] == "Search parameters are valid"
        assert "validated_parameters" in data
        assert data["validated_parameters"]["search_term"] == "software engineer"
        assert data["validated_parameters"]["site_names"] == ["indeed", "linkedin"]
    
    def test_validate_endpoint_validation_error(self):
        """Test validation endpoint with invalid parameters."""
        # Test with invalid job_type that will fail Pydantic validation
        response = client.get(
            "/api/v1/search/validate",
            params={
                "search_term": "software engineer",
                "job_type": "invalid_type"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        
        assert data["valid"] is False
        assert "Invalid job type" in data["message"]
        assert len(data["field_errors"]) == 1
        assert data["field_errors"][0]["field"] == "job_type"
    
    def test_validate_endpoint_default_parameters(self):
        """Test validation endpoint with default parameters."""
        with patch('app.services.job_search_service.JobSearchService.validate_search_parameters',
                  new_callable=AsyncMock) as mock_validate:
            
            mock_validate.return_value = True
            
            response = client.get("/api/v1/search/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["validated_parameters"]["site_names"] == ["indeed", "linkedin", "glassdoor"]
        assert data["validated_parameters"]["results_wanted"] == 20
        assert data["validated_parameters"]["distance"] == 50
        assert data["validated_parameters"]["is_remote"] is False


class TestSearchEndpointIntegration:
    """Integration tests that test the complete search flow."""
    
    @pytest.mark.asyncio
    async def test_complete_search_flow_with_mocked_jobspy(self):
        """Test complete search flow with mocked JobSpy responses."""
        # Create mock DataFrame that JobSpy would return
        mock_df = pd.DataFrame([
            {
                'id': 'job_1',
                'title': 'Software Engineer',
                'company_name': 'Tech Corp',
                'job_url': 'https://example.com/job1',
                'location': 'San Francisco, CA',
                'description': 'Great software engineering role',
                'site': 'indeed',
                'date_posted': '2024-01-15',
                'job_type': 'fulltime',
                'is_remote': False,
                'min_amount': 120000,
                'max_amount': 150000,
                'interval': 'yearly',
                'currency': 'USD'
            },
            {
                'id': 'job_2',
                'title': 'Senior Developer',
                'company_name': 'Dev Inc',
                'job_url': 'https://example.com/job2',
                'location': 'New York, NY',
                'description': 'Senior development position',
                'site': 'linkedin',
                'date_posted': '2024-01-14',
                'job_type': 'fulltime',
                'is_remote': True,
                'min_amount': 140000,
                'max_amount': 180000,
                'interval': 'yearly',
                'currency': 'USD'
            }
        ])
        
        with patch('app.services.job_search_service.JobSearchService._execute_jobspy_search') as mock_scrape:
            mock_scrape.return_value = mock_df
            
            response = client.post(
                "/api/v1/search/",
                json={
                    "search_term": "software engineer",
                    "location": "San Francisco, CA",
                    "site_names": ["indeed", "linkedin"],
                    "results_wanted": 20,
                    "is_remote": False
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "jobs" in data
        assert "total_results" in data
        assert "search_metadata" in data
        assert "errors" in data
        assert "warnings" in data
        
        # Verify job data
        assert data["total_results"] == 2
        assert len(data["jobs"]) == 2
        
        # Verify first job
        job1 = data["jobs"][0]
        assert job1["title"] == "Software Engineer"
        assert job1["company_name"] == "Tech Corp"
        assert job1["site"] == "indeed"
        
        # Verify metadata
        metadata = data["search_metadata"]
        assert "search_id" in metadata
        assert metadata["total_sites_searched"] == 2
        assert "indeed" in metadata["successful_sites"] or "linkedin" in metadata["successful_sites"]
        assert metadata["total_results_found"] == 2
    
    def test_search_endpoint_with_real_validation(self):
        """Test search endpoint with real Pydantic validation."""
        # Test with invalid results_wanted (too high)
        response = client.post(
            "/api/v1/search/",
            json={
                "search_term": "software engineer",
                "results_wanted": 500  # Exceeds max of 100
            }
        )
        
        assert response.status_code == 422
        
        # Test with invalid distance (negative)
        response = client.post(
            "/api/v1/search/",
            json={
                "search_term": "software engineer",
                "distance": -10
            }
        )
        
        assert response.status_code == 422
        
        # Test with invalid hours_old (too high)
        response = client.post(
            "/api/v1/search/",
            json={
                "search_term": "software engineer",
                "hours_old": 10000  # Exceeds max of 8760
            }
        )
        
        assert response.status_code == 422