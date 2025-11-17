"""
Main Company Information Scraper Script for PropIntel

This script orchestrates the complete company information extraction process
from Astha Infra Realty website and saves the results to JSON files.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.scrapers.company_info_scraper import AsthaCompanyInfoScraper
from ingestion.config.env_loader import get_config


def main():
    """Main execution function"""
    print("🏢 PropIntel Company Information Scraper")
    print("=" * 50)
    
    # Initialize configuration
    config = get_config()
    logger = config.get_logger()
    
    logger.info("Starting company information extraction process...")
    
    try:
        # Initialize scraper
        print("🚀 Initializing company information scraper...")
        scraper = AsthaCompanyInfoScraper()
        
        # Extract company information
        print("📊 Extracting company information from website...")
        print(f"   • Target website: {config.get_website_base_url()}")
        print("   • Pages to scrape: Home page, Contact page")
        
        company_data = scraper.scrape()
        
        if not company_data:
            print("❌ Failed to extract company information")
            return False
        
        # Display extraction summary
        pages_scraped = company_data.get('metadata', {}).get('pages_scraped', [])
        completeness = company_data.get('metadata', {}).get('data_completeness', 0)
        
        print(f"✅ Extraction completed!")
        print(f"   • Pages scraped: {', '.join(pages_scraped)}")
        print(f"   • Data completeness: {completeness}%")
        
        # Save to JSON file
        print("💾 Saving extracted data...")
        file_path = scraper.save_to_json(company_data)
        print(f"   • Saved to: {file_path}")
        
        # Generate and display summary report
        print("\\n📋 EXTRACTION SUMMARY REPORT:")
        print("-" * 30)
        summary = scraper.generate_summary_report(company_data)
        print(summary)
        
        # Log completion
        logger.info(f"Company information extraction completed successfully. Data saved to: {file_path}")
        
        print("\\n🎉 Company information extraction completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during company information extraction: {e}")
        print(f"❌ Error occurred: {e}")
        return False
    
    finally:
        # Clean up
        if 'scraper' in locals():
            scraper.close()


def run_quick_test():
    """Run a quick test of the scraper components"""
    print("🧪 Running Quick Component Test...")
    print("-" * 30)
    
    try:
        # Test configuration
        config = get_config()
        website_url = config.get_website_base_url()
        print(f"✅ Configuration loaded - Website: {website_url}")
        
        # Test scraper initialization
        scraper = AsthaCompanyInfoScraper()
        print("✅ Scraper initialized successfully")
        
        # Test home page access
        home_soup = scraper.get_page(website_url)
        if home_soup:
            print(f"✅ Home page accessible - Found {len(home_soup.find_all())} HTML elements")
        else:
            print("❌ Failed to access home page")
            return False
        
        # Test contact page access
        contact_url = website_url + "contact-us/"
        contact_soup = scraper.get_page(contact_url)
        if contact_soup:
            print(f"✅ Contact page accessible - Found {len(contact_soup.find_all())} HTML elements")
        else:
            print("⚠️ Contact page may not be accessible")
        
        scraper.close()
        print("✅ Quick test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run quick test
        success = run_quick_test()
    else:
        # Run full extraction
        success = main()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)