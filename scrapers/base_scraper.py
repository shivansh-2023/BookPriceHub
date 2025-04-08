import requests
from fake_useragent import UserAgent
import time
import random
from abc import ABC, abstractmethod
import os
from urllib.parse import urlparse, urlunparse

class BaseScraper(ABC):
    """Base scraper class that all retailer-specific scrapers will inherit from"""
    
    def __init__(self):
        # Initialize with a list of common user agents as fallback
        self.fallback_user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        
        # Try to initialize UserAgent, fall back to predefined list if it fails
        try:
            self.user_agent = UserAgent()
            self.ua_working = True
        except Exception as e:
            print(f"UserAgent initialization failed: {str(e)}. Using fallback user agents.")
            self.ua_working = False
            
        self.session = requests.Session()
        self.rate_limit_delay = (1, 3)  # Random delay between 1-3 seconds
        
        # Initialize proxy list and index
        self.proxy_list = []
        self.current_proxy_index = 0
        self.timeout = 30  # Reasonable timeout for single attempt
        self.connection_timeout = 10  # Quick connection timeout
    
    def _get_headers(self):
        """Generate random user agent headers to avoid detection"""
        try:
            if self.ua_working:
                user_agent = self.user_agent.random
            else:
                user_agent = random.choice(self.fallback_user_agents)
        except Exception:
            user_agent = random.choice(self.fallback_user_agents)
            
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }
    
    def _normalize_url(self, url):
        """Ensure URL is properly formatted"""
        if not url:
            return url
            
        # Parse URL
        try:
            parsed = urlparse(url)
            
            # If no scheme, assume https
            if not parsed.scheme:
                parsed = parsed._replace(scheme='https')
                
            # Rebuild URL
            result = urlunparse(parsed)
            print(f"Normalized URL: {url} -> {result}")
            return result
        except Exception as e:
            print(f"Error normalizing URL '{url}': {str(e)}")
            return url
    
    def _get_next_proxy(self):
        """Get the next proxy from the rotation list"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy

    def _make_request(self, url, method='get', params=None, data=None):
        """Make HTTP request with single attempt"""
        url = self._normalize_url(url)
        print(f"Making {method.upper()} request to: {url}")
        
        try:
            # Prepare request kwargs
            request_kwargs = {
                "headers": self._get_headers(),
                "timeout": (self.connection_timeout, self.timeout),
                "allow_redirects": True,
                "verify": False
            }
            
            # Add method-specific parameters
            if method.lower() == 'get' and params:
                request_kwargs["params"] = params
            elif method.lower() == 'post' and data:
                request_kwargs["data"] = data
            
            # Make the request
            response = getattr(self.session, method.lower())(url, **request_kwargs)
            
            # Handle response
            if response.status_code == 200:
                print(f"Successful request to {url}")
                return response
            else:
                print(f"Request to {url} failed with status code {response.status_code}")
                return None
        
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    @abstractmethod
    def search(self, book_title):
        """Search for a book by title - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def parse_results(self, response):
        """Parse search results - must be implemented by subclasses"""
        pass
