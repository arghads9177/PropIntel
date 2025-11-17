"""
Test file for PropIntel Phase 2 - Company Information Extractor
Tests the complete company information extraction pipeline
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.utils.text_extractor import TextExtractor
from ingestion.scrapers.company_info_scraper import AsthaCompanyInfoScraper
from ingestion.config.env_loader import get_config


def test_text_extractor():
    """Test text extraction utilities"""
    print("🧪 Testing Text Extractor...")
    
    try:
        extractor = TextExtractor()
        
        # Test phone number extraction
        test_text = "Contact us at 0341-7963322 or call 9434745115 for enquiries"
        phones = extractor.extract_phone_numbers(test_text)
        print(f"✅ Phone extraction: Found {len(phones)} numbers - {phones}")
        
        # Test email extraction
        test_text = "Email us at asthainfrarealty@gmail.com or moumitadas@asthainfrarealty.com"
        emails = extractor.extract_email_addresses(test_text)
        print(f"✅ Email extraction: Found {len(emails)} addresses - {emails}")
        
        # Test text cleaning
        dirty_text = "  Extra   spaces  and\t\ttabs\n\nand newlines  "
        clean_text = extractor.clean_text(dirty_text)
        print(f"✅ Text cleaning: '{dirty_text}' -> '{clean_text}'")
        
        print("✅ Text Extractor - PASSED\\n")
        return True
        
    except Exception as e:
        print(f"❌ Text Extractor - FAILED: {e}\\n")
        return False


def test_company_info_scraper():
    """Test company information scraper"""
    print("🧪 Testing Company Info Scraper...")
    
    try:
        # Initialize scraper
        scraper = AsthaCompanyInfoScraper()
        print("✅ Scraper initialized successfully")
        
        # Test home page scraping
        print("🏠 Testing home page extraction...")
        home_data = scraper.scrape_home_page()
        
        if home_data and home_data.get('company_info'):
            company_info = home_data['company_info']
            print(f"✅ Company name: {company_info.get('name', 'Not found')}")
            
            welcome_msg = company_info.get('welcome_message', '')
            if welcome_msg:
                print(f"✅ Welcome message: {welcome_msg[:100]}...")
            else:
                print("⚠️ Welcome message not found")
            
            tagline = company_info.get('tagline', '')
            if tagline:
                print(f"✅ Company tagline: {tagline}")
            else:
                print("⚠️ Company tagline not found")
        else:
            print("⚠️ Home page data extraction incomplete")
        
        # Test contact page scraping
        print("📞 Testing contact page extraction...")
        contact_data = scraper.scrape_contact_page()
        
        if contact_data and contact_data.get('contact_details'):
            contact_info = contact_data['contact_details']
            
            office_timing = contact_info.get('office_timing', {})
            if office_timing:
                print(f"✅ Office timing: {office_timing}")
            else:
                print("⚠️ Office timing not found")
            
            phones = contact_info.get('phones', [])
            emails = contact_info.get('emails', [])
            print(f"✅ Contact info: {len(phones)} phones, {len(emails)} emails")
            
            head_office = contact_info.get('head_office', {})
            branches = contact_info.get('branches', [])
            print(f"✅ Addresses: Head office: {bool(head_office)}, Branches: {len(branches)}")
        else:
            print("⚠️ Contact page data extraction incomplete")
        
        scraper.close()
        print("✅ Company Info Scraper - PASSED\\n")
        return True
        
    except Exception as e:
        print(f"❌ Company Info Scraper - FAILED: {e}\\n")
        return False


def test_full_extraction():
    """Test complete extraction pipeline"""
    print("🧪 Testing Full Extraction Pipeline...")
    
    try:
        # Initialize scraper
        scraper = AsthaCompanyInfoScraper()
        
        # Run complete extraction
        print("🚀 Running complete company information extraction...")
        company_data = scraper.scrape()
        
        if not company_data:
            print("❌ No data extracted")
            return False
        
        # Validate data structure
        required_sections = ['company_info', 'contact_details', 'social_media', 'metadata']
        for section in required_sections:
            if section not in company_data:
                print(f"❌ Missing section: {section}")
                return False
        
        print("✅ Data structure validation passed")
        
        # Check metadata
        metadata = company_data.get('metadata', {})
        pages_scraped = metadata.get('pages_scraped', [])
        completeness = metadata.get('data_completeness', 0)
        
        print(f"✅ Pages scraped: {pages_scraped}")
        print(f"✅ Data completeness: {completeness}%")
        
        # Test file saving
        print("💾 Testing file save functionality...")
        test_filename = 'test_company_info.json'
        file_path = scraper.save_to_json(company_data, test_filename)
        
        # Verify file was created
        if Path(file_path).exists():
            print(f"✅ File saved successfully: {file_path}")
            
            # Clean up test file
            Path(file_path).unlink()
            print("✅ Test file cleaned up")
        else:
            print(f"❌ File not created: {file_path}")
            return False
        
        # Test summary report generation
        print("📋 Testing summary report generation...")
        summary = scraper.generate_summary_report(company_data)
        
        if summary and len(summary) > 100:
            print("✅ Summary report generated successfully")
            print("📄 Sample report preview:")
            print(summary[:200] + "...")
        else:
            print("⚠️ Summary report may be incomplete")
        
        scraper.close()
        print("✅ Full Extraction Pipeline - PASSED\\n")
        return True
        
    except Exception as e:
        print(f"❌ Full Extraction Pipeline - FAILED: {e}\\n")
        return False


def main():
    """Run all Phase 2 tests"""
    print("🚀 PropIntel Phase 2 Company Information Extractor Test Suite")
    print("=" * 60)
    
    # Run tests
    test_results = []
    test_results.append(test_text_extractor())
    test_results.append(test_company_info_scraper())
    test_results.append(test_full_extraction())
    
    # Summary
    print("📊 Test Results Summary:")
    print("=" * 30)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Phase 2 Company Information Extractor is ready!")
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        print("❌ Some components need attention")
    
    print("\\n🏁 Phase 2 testing completed!")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)