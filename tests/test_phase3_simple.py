"""
Simple test runner for Phase 3 Data Cleaning Pipeline
Tests individual components without external dependencies
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_content_filter():
    """Test content filtering functionality"""
    print("🧪 Testing Content Filter...")
    
    try:
        from ingestion.cleaners.content_filter import ContentFilter
        
        filter = ContentFilter()
        
        # Test CSS removal
        css_text = "body{color:red}.header{font-size:12px} This is actual content"
        cleaned = filter.remove_css_javascript(css_text)
        print(f"✅ CSS Removal: '{css_text[:50]}...' -> '{cleaned[:50]}...'")
        
        # Test navigation removal
        nav_text = "Home About Contact Us This is real content Services"
        business_content = filter.extract_business_content(nav_text)
        print(f"✅ Navigation Filtering: Found business content: {bool(business_content)}")
        
        print("✅ Content Filter - PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Content Filter - FAILED: {e}\n")
        return False


def test_text_normalizer():
    """Test text normalization functionality"""
    print("🧪 Testing Text Normalizer...")
    
    try:
        from ingestion.cleaners.text_normalizer import TextNormalizer
        
        normalizer = TextNormalizer()
        
        # Test phone normalization
        phones = ["9434745115", "0341-7963322", "033-26310154"]
        normalized_phones = [normalizer.normalize_phone_number(phone) for phone in phones]
        print(f"✅ Phone Normalization: {phones} -> {normalized_phones}")
        
        # Test email normalization
        emails = ["ASTHAINFRAREALTY@GMAIL.COM", "  moumitadas@asthainfrarealty.com  "]
        normalized_emails = [normalizer.normalize_email(email) for email in emails]
        print(f"✅ Email Normalization: {emails} -> {normalized_emails}")
        
        # Test address standardization
        address = "prakash apartment1st floor,g.t. road, gopalpur asansol - 713304"
        normalized_address = normalizer.standardize_address(address)
        print(f"✅ Address Standardization: '{address}' -> '{normalized_address}'")
        
        print("✅ Text Normalizer - PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Text Normalizer - FAILED: {e}\n")
        return False


def test_quality_scorer():
    """Test quality scoring functionality"""
    print("🧪 Testing Quality Scorer...")
    
    try:
        from ingestion.cleaners.quality_scorer import QualityScorer
        
        scorer = QualityScorer()
        
        # Test content quality scoring
        good_content = "Aastha Infra Realty is a leading real estate developer with 30 years of experience"
        bad_content = "body{color:red}.x-navbar{font-size:12px}window.jQuery"
        
        good_score = scorer.score_content_quality(good_content)
        bad_score = scorer.score_content_quality(bad_content)
        
        print(f"✅ Content Quality Scoring: Good content score: {good_score}, Bad content score: {bad_score}")
        
        # Test contact completeness
        contact_data = {
            'phones': ['+91-9434745115', '+91-341-7963322'],
            'emails': ['asthainfrarealty@gmail.com'],
            'addresses': ['Complete address with PIN 713304']
        }
        
        completeness_score = scorer.score_contact_completeness(contact_data)
        print(f"✅ Contact Completeness: Score: {completeness_score}")
        
        # Test overall quality
        sample_data = {
            'company_info': {'name': 'Astha Infra Realty Ltd.', 'welcome_message': good_content},
            'contact_details': contact_data
        }
        
        overall_score = scorer.calculate_overall_quality(sample_data)
        print(f"✅ Overall Quality: Score: {overall_score}")
        
        print("✅ Quality Scorer - PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Quality Scorer - FAILED: {e}\n")
        return False


def test_data_cleaning_pipeline():
    """Test the complete data cleaning pipeline"""
    print("🧪 Testing Complete Data Cleaning Pipeline...")
    
    try:
        from ingestion.cleaners.data_cleaning_pipeline import DataCleaningPipeline
        
        # Load the raw data
        raw_data_path = project_root / 'data' / 'raw' / 'astha_company_info.json'
        
        if not raw_data_path.exists():
            print("⚠️ Raw data file not found, creating sample data...")
            sample_data = {
                "company_info": {
                    "name": "Astha Infra Realty Ltd.",
                    "welcome_message": "body{color:red} Aastha Infra Realty is a leading developer",
                    "tagline": "It Takes Hand To Build A House, But Only Hearts Can Build A Home"
                },
                "contact_details": {
                    "phones": ["9434745115", "0341-7963322"],
                    "emails": ["ASTHAINFRAREALTY@GMAIL.COM", "moumitadas@asthainfrarealty.com"],
                    "addresses": [{"address": "prakash apartment,g.t. road asansol-713304"}]
                }
            }
        else:
            with open(raw_data_path, 'r') as f:
                sample_data = json.load(f)
        
        # Initialize pipeline
        pipeline = DataCleaningPipeline()
        
        # Process data
        print("🔄 Processing data through cleaning pipeline...")
        cleaned_data = pipeline.process(sample_data)
        
        # Validate results
        if cleaned_data and 'data_quality' in cleaned_data:
            quality_score = cleaned_data['data_quality']['overall_quality_score']
            print(f"✅ Pipeline Processing: Quality score: {quality_score}")
            
            # Check if cleaned data is better structured
            if 'company_info' in cleaned_data and 'contact_details' in cleaned_data:
                print("✅ Data Structure: All sections present")
            
            print("✅ Data Cleaning Pipeline - PASSED\n")
            return True
        else:
            print("❌ Pipeline returned invalid data structure")
            return False
        
    except Exception as e:
        print(f"❌ Data Cleaning Pipeline - FAILED: {e}\n")
        return False


def run_actual_cleaning():
    """Run the actual cleaning on our scraped data"""
    print("🚀 Running Actual Data Cleaning on Scraped Data...")
    print("=" * 50)
    
    try:
        from ingestion.cleaners.data_cleaning_pipeline import DataCleaningPipeline
        
        # Load raw data
        raw_data_path = project_root / 'data' / 'raw' / 'astha_company_info.json'
        
        if not raw_data_path.exists():
            print("❌ Raw data file not found. Please run Phase 2 scraping first.")
            return False
        
        with open(raw_data_path, 'r') as f:
            raw_data = json.load(f)
        
        print(f"📁 Loaded raw data from: {raw_data_path}")
        
        # Initialize pipeline
        pipeline = DataCleaningPipeline()
        
        # Process data
        print("🔄 Cleaning data...")
        cleaned_data = pipeline.process(raw_data)
        
        # Save cleaned data
        processed_path = project_root / 'data' / 'processed'
        processed_path.mkdir(exist_ok=True)
        
        cleaned_file_path = processed_path / 'astha_company_info_clean.json'
        
        with open(cleaned_file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Cleaned data saved to: {cleaned_file_path}")
        
        # Generate quality report
        if 'data_quality' in cleaned_data:
            quality = cleaned_data['data_quality']
            print(f"\n📊 Data Quality Report:")
            print(f"   • Overall Quality Score: {quality.get('overall_quality_score', 'N/A')}")
            print(f"   • Content Quality: {quality.get('content_quality_score', 'N/A')}")
            print(f"   • Contact Completeness: {quality.get('contact_completeness_score', 'N/A')}")
            print(f"   • Issues Resolved: {quality.get('issues_resolved', 'N/A')}")
            print(f"   • Validation Passed: {quality.get('validation_passed', 'N/A')}")
        
        print("✅ Actual Data Cleaning - COMPLETED!\n")
        return True
        
    except Exception as e:
        print(f"❌ Actual Data Cleaning - FAILED: {e}\n")
        return False


def main():
    """Run all Phase 3 tests"""
    print("🚀 PropIntel Phase 3 Data Cleaning Pipeline Test Suite")
    print("=" * 60)
    
    # Run component tests
    test_results = []
    test_results.append(test_content_filter())
    test_results.append(test_text_normalizer())
    test_results.append(test_quality_scorer())
    test_results.append(test_data_cleaning_pipeline())
    
    # Run actual cleaning
    actual_cleaning_result = run_actual_cleaning()
    test_results.append(actual_cleaning_result)
    
    # Summary
    print("📊 Test Results Summary:")
    print("=" * 30)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Phase 3 Data Cleaning Pipeline is ready!")
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        print("❌ Some components need attention")
    
    print("\n🏁 Phase 3 testing completed!")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)