"""
Base Web Scraper Class for PropIntel

This module provides the base scraper functionality with session management,
rate limiting, error handling, and retry logic.
"""

import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from ..config.env_loader import get_config


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers with common functionality.
    
    Provides:
    - HTTP session management with connection pooling
    - Rate limiting and retry logic
    - User-agent rotation
    - Robots.txt compliance checking
    - Error handling and logging
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize base scraper.
        
        Args:
            base_url: Base URL for scraping. If None, uses config.
        """
        self.config = get_config()
        self.logger = self.config.get_logger()
        
        self.base_url = base_url or self.config.get_website_base_url()
        self.scraping_params = self.config.get_scraping_params()
        
        # Initialize session with proper configuration
        self.session = self._create_session()
        
        # Rate limiting
        self.rate_limit = self.scraping_params['rate_limit']
        self.last_request_time = 0
        
        # Robots.txt parser
        self.robots_parser = self._load_robots_txt()
        
        # User agents for rotation
        self.user_agents = self._get_user_agents()
        self.current_user_agent_index = 0
        
        self.logger.info(f"BaseScraper initialized for: {self.base_url}")
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy and proper headers."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.scraping_params['max_retries'],
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Updated from method_whitelist
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        return session
    
    def _get_user_agents(self) -> List[str]:
        """Get list of user agents for rotation."""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
    
    def _rotate_user_agent(self) -> None:
        """Rotate to next user agent."""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        user_agent = self.user_agents[self.current_user_agent_index]
        self.session.headers.update({'User-Agent': user_agent})
    
    def _load_robots_txt(self) -> Optional[RobotFileParser]:
        """Load and parse robots.txt file."""
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            self.logger.info(f"Robots.txt loaded from: {robots_url}")
            return rp
        except Exception as e:
            self.logger.warning(f"Could not load robots.txt: {e}")
            return None
    
    def _can_fetch(self, url: str, user_agent: str = '*') -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.robots_parser:
            return True
        
        try:
            return self.robots_parser.can_fetch(user_agent, url)
        except Exception as e:
            self.logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            # Add small random jitter to avoid synchronized requests
            sleep_time += random.uniform(0, 0.5)
            
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with error handling and rate limiting.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object or None if failed
        """
        # Check robots.txt compliance
        if not self._can_fetch(url):
            self.logger.warning(f"Robots.txt disallows fetching: {url}")
            return None
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Rotate user agent occasionally
        if random.random() < 0.2:  # 20% chance
            self._rotate_user_agent()
        
        try:
            # Set timeout from config
            kwargs.setdefault('timeout', self.scraping_params['timeout'])
            
            self.logger.debug(f"Making request to: {url}")
            response = self.session.get(url, **kwargs)
            
            # Check response status
            response.raise_for_status()
            
            self.logger.debug(f"Successfully fetched: {url} (Status: {response.status_code})")
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error for {url}: {e}")
            return None
    
    def get_page(self, url: str, **kwargs) -> Optional[BeautifulSoup]:
        """
        Get page content and return BeautifulSoup object.
        
        Args:
            url: URL to scrape
            **kwargs: Additional arguments for request
            
        Returns:
            BeautifulSoup object or None if failed
        """
        response = self._make_request(url, **kwargs)
        
        if not response:
            return None
        
        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            self.logger.debug(f"Successfully parsed HTML for: {url}")
            return soup
            
        except Exception as e:
            self.logger.error(f"Failed to parse HTML for {url}: {e}")
            return None
    
    def get_absolute_url(self, relative_url: str) -> str:
        """Convert relative URL to absolute URL."""
        return urljoin(self.base_url, relative_url)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the target domain."""
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.base_url)
            
            return (
                parsed.scheme in ('http', 'https') and
                parsed.netloc == base_parsed.netloc
            )
        except Exception:
            return False
    
    def close(self) -> None:
        """Close session and cleanup resources."""
        if self.session:
            self.session.close()
            self.logger.info("Scraper session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    @abstractmethod
    def scrape(self) -> Dict[str, Any]:
        """
        Abstract method for scraping implementation.
        Must be implemented by subclasses.
        
        Returns:
            Dictionary containing scraped data
        """
        pass


class ScrapingError(Exception):
    """Custom exception for scraping errors."""
    pass


if __name__ == "__main__":
    # Test base scraper functionality
    class TestScraper(BaseScraper):
        def scrape(self):
            return {"test": "data"}
    
    scraper = TestScraper()
    print(f"Base URL: {scraper.base_url}")
    print(f"Rate limit: {scraper.rate_limit}")
    print(f"User agents count: {len(scraper.user_agents)}")
    scraper.close()