from cachetools import TTLCache
import time
import json

class CacheManager:
    """Manages caching of search results to improve performance"""
    
    def __init__(self, max_size=100, ttl=3600):
        """
        Initialize the cache manager
        
        Args:
            max_size (int): Maximum number of items to store in cache
            ttl (int): Time to live in seconds (default: 1 hour)
        """
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)
    
    def _generate_key(self, book_title, format_filter):
        """Generate a unique cache key based on search parameters"""
        return f"{book_title.lower()}:{format_filter}"
    
    def cache_results(self, book_title, format_filter, results):
        """
        Cache search results
        
        Args:
            book_title (str): The book title that was searched
            format_filter (str): The format filter that was applied
            results (dict): The search results to cache
        """
        key = self._generate_key(book_title, format_filter)
        
        # Add timestamp to results
        cache_entry = {
            'timestamp': time.time(),
            'results': results
        }
        
        self.cache[key] = cache_entry
    
    def get_results(self, book_title, format_filter):
        """
        Retrieve cached results if available
        
        Args:
            book_title (str): The book title to search for
            format_filter (str): The format filter to apply
            
        Returns:
            dict or None: Cached results if available, None otherwise
        """
        key = self._generate_key(book_title, format_filter)
        
        if key in self.cache:
            return self.cache[key]['results']
        
        return None
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
    
    def get_cache_stats(self):
        """Get statistics about the cache"""
        return {
            'size': len(self.cache),
            'max_size': self.cache.maxsize,
            'ttl': self.cache.ttl
        }
