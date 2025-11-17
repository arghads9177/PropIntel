"""
Test script for Phase 1 implementation - Environment Config and Base Scraper
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from ingestion.config.env_loader import EnvironmentConfig, get_config
from ingestion.scrapers.base_scraper import BaseScraper


class TestScraper(BaseScraper):
    """Simple test scraper implementation."""
    
    def scrape(self):
        """Test scraping method."""
        return {"status": "test_successful", "base_url": self.base_url}


def test_environment_config():
    """Test environment configuration loading."""
    print("=" * 50)
    print("Testing Environment Configuration")
    print("=" * 50)
    
    try:
        # Test configuration loading
        config = EnvironmentConfig()
        
        print(f"✅ Configuration loaded successfully")
        print(f"📍 Website Base URL: {config.get_website_base_url()}")
        print(f"⚙️  Scraping Params: {config.get_scraping_params()}")
        print(f"📁 Storage Paths: {config.get_storage_paths()}")
        
        # Test global config instance
        global_config = get_config()
        print(f"🌐 Global config instance created: {global_config is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_base_scraper():
    """Test base scraper functionality."""
    print("\n" + "=" * 50)
    print("Testing Base Scraper")
    print("=" * 50)
    
    try:
        # Test scraper initialization
        scraper = TestScraper()
        
        print(f"✅ Base scraper initialized successfully")
        print(f"📍 Base URL: {scraper.base_url}")
        print(f"⏱️  Rate Limit: {scraper.rate_limit} seconds")
        print(f"🔄 Max Retries: {scraper.scraping_params['max_retries']}")
        print(f"⏰ Timeout: {scraper.scraping_params['timeout']} seconds")
        print(f"🎭 User Agents Count: {len(scraper.user_agents)}")
        
        # Test robots.txt loading
        robots_status = "✅ Loaded" if scraper.robots_parser else "⚠️  Not available"
        print(f"🤖 Robots.txt: {robots_status}")
        
        # Test session creation
        session_status = "✅ Active" if scraper.session else "❌ Failed"
        print(f"🔗 HTTP Session: {session_status}")
        
        # Test URL validation
        test_url = scraper.get_absolute_url("/test")
        print(f"🔗 URL Conversion Test: {test_url}")
        
        # Test scrape method
        result = scraper.scrape()
        print(f"📊 Scrape Test Result: {result}")
        
        # Clean up
        scraper.close()
        print(f"🧹 Scraper closed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Base scraper test failed: {e}")
        return False


def main():
    """Run all Phase 1 tests."""
    print("🚀 PropIntel Phase 1 Testing")
    print("Testing Environment Configuration and Base Scraper")
    
    # Test results
    config_test = test_environment_config()
    scraper_test = test_base_scraper()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    print(f"Environment Config: {'✅ PASSED' if config_test else '❌ FAILED'}")
    print(f"Base Scraper: {'✅ PASSED' if scraper_test else '❌ FAILED'}")
    
    overall_status = config_test and scraper_test
    print(f"\nOverall Phase 1 Status: {'✅ SUCCESS' if overall_status else '❌ FAILED'}")
    
    if overall_status:
        print("\n🎉 Phase 1 implementation is ready!")
        print("You can now proceed to Phase 2 - Company Info Extractor")
    else:
        print("\n❌ Please fix the issues before proceeding to Phase 2")
    
    return overall_status


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)