"""
Tests for the cache service functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.cache_service import SearchResultsCache, CacheEntry
from app.models.job import WebJobPost
from jobspy.model import Location


@pytest.fixture
def cache_service():
    """Create a cache service instance for testing."""
    return SearchResultsCache(default_ttl_minutes=1, cleanup_interval_minutes=1)


@pytest.fixture
def sample_jobs():
    """Create sample job posts for testing."""
    from jobspy.model import Location
    
    return [
        WebJobPost(
            id="job_1",
            title="Software Engineer",
            company_name="Tech Corp",
            job_url="https://example.com/job1",
            location=Location(city="San Francisco", state="CA", country="USA"),
            site="indeed",
            search_id="search_123"
        ),
        WebJobPost(
            id="job_2", 
            title="Data Scientist",
            company_name="Data Inc",
            job_url="https://example.com/job2",
            location=Location(city="New York", state="NY", country="USA"),
            site="linkedin",
            search_id="search_123"
        )
    ]


@pytest.fixture
def sample_metadata():
    """Create sample search metadata for testing."""
    return {
        "search_id": "search_123",
        "timestamp": datetime.utcnow().isoformat(),
        "total_sites_searched": 2,
        "successful_sites": ["indeed", "linkedin"],
        "failed_sites": [],
        "search_duration": 5.2,
        "total_results_found": 2
    }


class TestSearchResultsCache:
    """Test cases for SearchResultsCache."""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_search_results(self, cache_service, sample_jobs, sample_metadata):
        """Test storing and retrieving search results."""
        search_id = "test_search_123"
        
        # Store results
        await cache_service.store_search_results(search_id, sample_jobs, sample_metadata)
        
        # Retrieve results
        entry = await cache_service.get_search_results(search_id)
        
        assert entry is not None
        assert len(entry.jobs) == 2
        assert entry.jobs[0].id == "job_1"
        assert entry.jobs[1].id == "job_2"
        assert entry.search_metadata == sample_metadata
    
    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_search_results(self, cache_service):
        """Test retrieving non-existent search results."""
        entry = await cache_service.get_search_results("nonexistent_id")
        assert entry is None
    
    @pytest.mark.asyncio
    async def test_remove_search_results(self, cache_service, sample_jobs, sample_metadata):
        """Test removing search results from cache."""
        search_id = "test_search_456"
        
        # Store results
        await cache_service.store_search_results(search_id, sample_jobs, sample_metadata)
        
        # Verify stored
        entry = await cache_service.get_search_results(search_id)
        assert entry is not None
        
        # Remove results
        removed = await cache_service.remove_search_results(search_id)
        assert removed is True
        
        # Verify removed
        entry = await cache_service.get_search_results(search_id)
        assert entry is None
        
        # Try to remove again
        removed = await cache_service.remove_search_results(search_id)
        assert removed is False
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, sample_jobs, sample_metadata):
        """Test that cache entries expire correctly."""
        # Create cache with very short TTL
        cache_service = SearchResultsCache(default_ttl_minutes=0.01)  # ~0.6 seconds
        search_id = "test_search_expire"
        
        # Store results
        await cache_service.store_search_results(search_id, sample_jobs, sample_metadata)
        
        # Should be available immediately
        entry = await cache_service.get_search_results(search_id)
        assert entry is not None
        
        # Wait for expiration
        await asyncio.sleep(1)
        
        # Should be expired and removed
        entry = await cache_service.get_search_results(search_id)
        assert entry is None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service, sample_jobs, sample_metadata):
        """Test cache statistics functionality."""
        # Initially empty
        stats = await cache_service.get_cache_stats()
        assert stats["total_entries"] == 0
        assert stats["active_entries"] == 0
        
        # Add some entries
        await cache_service.store_search_results("search_1", sample_jobs, sample_metadata)
        await cache_service.store_search_results("search_2", sample_jobs[:1], sample_metadata)
        
        stats = await cache_service.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["cache_size_mb"] > 0
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, cache_service, sample_jobs, sample_metadata):
        """Test clearing all cache entries."""
        # Add entries
        await cache_service.store_search_results("search_1", sample_jobs, sample_metadata)
        await cache_service.store_search_results("search_2", sample_jobs, sample_metadata)
        
        # Verify entries exist
        stats = await cache_service.get_cache_stats()
        assert stats["total_entries"] == 2
        
        # Clear cache
        await cache_service.clear_cache()
        
        # Verify cache is empty
        stats = await cache_service.get_cache_stats()
        assert stats["total_entries"] == 0
        
        # Verify entries are gone
        entry1 = await cache_service.get_search_results("search_1")
        entry2 = await cache_service.get_search_results("search_2")
        assert entry1 is None
        assert entry2 is None


class TestCacheEntry:
    """Test cases for CacheEntry."""
    
    def test_cache_entry_creation(self, sample_jobs, sample_metadata):
        """Test creating a cache entry."""
        timestamp = datetime.utcnow()
        entry = CacheEntry(
            jobs=sample_jobs,
            timestamp=timestamp,
            search_metadata=sample_metadata
        )
        
        assert len(entry.jobs) == 2
        assert entry.timestamp == timestamp
        assert entry.search_metadata == sample_metadata
    
    def test_cache_entry_expiration_check(self, sample_jobs, sample_metadata):
        """Test cache entry expiration logic."""
        # Fresh entry
        fresh_entry = CacheEntry(
            jobs=sample_jobs,
            timestamp=datetime.utcnow(),
            search_metadata=sample_metadata
        )
        assert not fresh_entry.is_expired(ttl_minutes=30)
        
        # Expired entry
        old_timestamp = datetime.utcnow() - timedelta(minutes=60)
        expired_entry = CacheEntry(
            jobs=sample_jobs,
            timestamp=old_timestamp,
            search_metadata=sample_metadata
        )
        assert expired_entry.is_expired(ttl_minutes=30)