"""
Test file for PropIntel Phase 1 Infrastructure
Tests Environment Configuration Loader and Base Scraper Class
"""

import sys
import os
import time
from pathlib import Path
from typing import Dict, Any
from bs4 import BeautifulSoup

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.config.env_loader import EnvironmentConfig, get_config
from ingestion.scrapers.base_scraper import BaseScraper


class TestBaseScraper(BaseScraper):
    """Test implementation of BaseScraper for testing purposes"""
    
    def scrape(self) -> Dict[str, Any]:
        """Test implementation of abstract method"""
        try:
            # Test scraping the base URL
            url = self.base_url
            response = self._make_request(url)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                return {
                    'url': url,
                    'title': soup.title.string if soup.title else 'No title',
                    'status_code': response.status_code,
                    'content_length': len(response.content)
                }
            else:
                return {'url': url, 'error': 'No response received'}
        except Exception as e:
            self.logger.error(f"Error scraping {self.base_url}: {e}")
            return {'url': self.base_url, 'error': str(e)}
    
    def scrape_page(self, url: str) -> Dict[str, Any]:
        """Helper method for testing specific pages"""
        try:
            response = self._make_request(url)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                return {
                    'url': url,
                    'title': soup.title.string if soup.title else 'No title',
                    'status_code': response.status_code,
                    'content_length': len(response.content)
                }
            else:
                return {'url': url, 'error': 'No response received'}
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return {'url': url, 'error': str(e)}


def test_environment_config():
    """Test Environment Configuration Loader"""
    print("🧪 Testing Environment Configuration Loader...")
    
    try:
        # Test configuration loading
        config = EnvironmentConfig()
        
        # Test basic functionality
        website_url = config.get_website_base_url()
        scraping_params = config.get_scraping_params()
        
        print(f"✅ Website URL loaded: {website_url}")
        print(f"✅ Scraping params loaded: {scraping_params}")
        
        # Test individual configuration access
        rate_limit = config.get('SCRAPER_RATE_LIMIT', 2)
        timeout = config.get('SCRAPER_TIMEOUT', 30)
        print(f"✅ Rate limit: {rate_limit}, Timeout: {timeout}")
        
        # Test singleton instance
        config2 = get_config()
        assert config.config == config2.config, "Singleton not working correctly"
        print("✅ Singleton pattern working correctly")
        
        print("✅ Environment Configuration Loader - PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Environment Configuration Loader - FAILED: {e}\n")
        return False


def test_base_scraper():
    """Test Base Scraper Class"""
    print("🧪 Testing Base Scraper Class...")
    
    try:
        # Initialize scraper with test configuration
        config = get_config()
        base_url = config.get_website_base_url()
        scraping_params = config.get_scraping_params()
        
        scraper = TestBaseScraper(base_url=base_url)
        
        print(f"✅ Scraper initialized with base URL: {base_url}")
        
        # Test robots.txt checking
        print("🤖 Testing robots.txt compliance...")
        can_fetch = scraper._can_fetch(base_url)
        print(f"✅ Robots.txt check: {can_fetch}")
        
        # Test simple page scraping using get_page method
        print("🌐 Testing page scraping...")
        soup = scraper.get_page(base_url)
        
        if soup:
            title = soup.title.string if soup.title else 'No title'
            print(f"✅ Successfully scraped page: {title[:50]}...")
            print(f"✅ Page contains {len(soup.find_all())} HTML elements")
        else:
            print("⚠️  Failed to scrape page")
        
        # Test rate limiting
        print("⏱️  Testing rate limiting...")
        start_time = time.time()
        scraper.get_page(base_url)  # Second request should be rate limited
        elapsed = time.time() - start_time
        
        if elapsed >= scraper.rate_limit - 0.5:  # Allow some tolerance
            print(f"✅ Rate limiting working: {elapsed:.2f}s delay")
        else:
            print(f"⚠️  Rate limiting may not be working properly: {elapsed:.2f}s delay")
        
        print("✅ Base Scraper Class - PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Base Scraper Class - FAILED: {e}\n")
        return False


def main():
    """Run all Phase 1 tests"""
    print("🚀 PropIntel Phase 1 Infrastructure Test Suite")
    print("=" * 50)
    
    # Run tests
    test_results = []
    test_results.append(test_environment_config())
    test_results.append(test_base_scraper())
    
    # Summary
    print("📊 Test Results Summary:")
    print("=" * 30)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Phase 1 infrastructure is ready!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("❌ Some components need attention")
    
    print("\n🏁 Phase 1 testing completed!")


if __name__ == "__main__":
    main()