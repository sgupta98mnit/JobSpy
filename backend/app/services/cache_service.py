"""
In-memory cache service for storing search results temporarily.
Used for export functionality to retrieve search results by search_id.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..models.job import WebJobPost


@dataclass
class CacheEntry:
    """Cache entry containing search results and metadata."""
    jobs: List[WebJobPost]
    timestamp: datetime
    search_metadata: Dict
    
    def is_expired(self, ttl_minutes: int = 30) -> bool:
        """Check if cache entry has expired."""
        expiry_time = self.timestamp + timedelta(minutes=ttl_minutes)
        return datetime.utcnow() > expiry_time


class SearchResultsCache:
    """
    In-memory cache for storing search results temporarily.
    
    This cache stores search results for a limited time to enable
    export functionality without requiring persistent storage.
    """
    
    def __init__(self, default_ttl_minutes: int = 30, cleanup_interval_minutes: int = 10):
        """
        Initialize the cache.
        
        Args:
            default_ttl_minutes: Default time-to-live for cache entries in minutes
            cleanup_interval_minutes: How often to run cleanup in minutes
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl_minutes
        self._cleanup_interval = cleanup_interval_minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def store_search_results(
        self, 
        search_id: str, 
        jobs: List[WebJobPost], 
        search_metadata: Dict
    ) -> None:
        """
        Store search results in cache.
        
        Args:
            search_id: Unique identifier for the search
            jobs: List of job posts from the search
            search_metadata: Metadata about the search operation
        """
        async with self._lock:
            entry = CacheEntry(
                jobs=jobs,
                timestamp=datetime.utcnow(),
                search_metadata=search_metadata
            )
            self._cache[search_id] = entry
            
            # Start cleanup task if not already running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def get_search_results(self, search_id: str) -> Optional[CacheEntry]:
        """
        Retrieve search results from cache.
        
        Args:
            search_id: Unique identifier for the search
            
        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(search_id)
            
            if entry is None:
                return None
            
            if entry.is_expired(self._default_ttl):
                # Remove expired entry
                del self._cache[search_id]
                return None
            
            return entry
    
    async def remove_search_results(self, search_id: str) -> bool:
        """
        Remove search results from cache.
        
        Args:
            search_id: Unique identifier for the search
            
        Returns:
            True if entry was removed, False if not found
        """
        async with self._lock:
            if search_id in self._cache:
                del self._cache[search_id]
                return True
            return False
    
    async def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values() 
                if entry.is_expired(self._default_ttl)
            )
            
            return {
                "total_entries": total_entries,
                "active_entries": total_entries - expired_entries,
                "expired_entries": expired_entries,
                "cache_size_mb": self._estimate_cache_size()
            }
    
    def _estimate_cache_size(self) -> float:
        """
        Estimate cache size in MB (rough approximation).
        
        Returns:
            Estimated size in megabytes
        """
        # Rough estimation: assume each job post is ~2KB on average
        total_jobs = sum(len(entry.jobs) for entry in self._cache.values())
        estimated_bytes = total_jobs * 2048  # 2KB per job
        return round(estimated_bytes / (1024 * 1024), 2)
    
    async def _periodic_cleanup(self) -> None:
        """
        Periodically clean up expired cache entries.
        """
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval * 60)  # Convert to seconds
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue cleanup loop
                print(f"Error during cache cleanup: {e}")
    
    async def _cleanup_expired_entries(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                search_id for search_id, entry in self._cache.items()
                if entry.is_expired(self._default_ttl)
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    async def clear_cache(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    def __del__(self):
        """Cleanup when cache is destroyed."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Global cache instance
search_results_cache = SearchResultsCache()