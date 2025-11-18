"""
Manual Data Cleaning Execution for Phase 3
Runs the complete data cleaning pipeline on our scraped data
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Run manual data cleaning"""
    print("🚀 PropIntel Phase 3 - Manual Data Cleaning")
    print("=" * 50)
    
    try:
        # Import cleaning pipeline
        from ingestion.cleaners.data_cleaning_pipeline import DataCleaningPipeline
        
        # Load raw data
        raw_data_path = project_root / 'data' / 'raw' / 'astha_company_info.json'
        
        print(f"Looking for raw data at: {raw_data_path}")
        print(f"File exists: {raw_data_path.exists()}")
        
        if not raw_data_path.exists():
            print("❌ Raw data file not found. Please run Phase 2 scraping first.")
            return False
        
        print(f"📁 Loading raw data from: {raw_data_path}")
        
        with open(raw_data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        print(f"✅ Raw data loaded: {len(raw_data)} main sections")
        
        # Initialize cleaning pipeline
        print("🔧 Initializing data cleaning pipeline...")
        pipeline = DataCleaningPipeline()
        
        # Process the data
        print("🔄 Cleaning data...")
        cleaned_data = pipeline.clean_single_company_data(
            raw_data=raw_data,
            company_id="astha_infra_realty"
        )
        
        # Ensure processed directory exists
        processed_dir = project_root / 'data' / 'processed'
        processed_dir.mkdir(exist_ok=True)
        
        # Save cleaned data
        cleaned_file_path = processed_dir / 'astha_company_info_clean.json'
        
        print(f"💾 Saving cleaned data to: {cleaned_file_path}")
        
        with open(cleaned_file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        # Display quality report
        print("\n📊 DATA CLEANING REPORT:")
        print("-" * 30)
        
        if 'data_quality' in cleaned_data:
            quality = cleaned_data['data_quality']
            print(f"📈 Overall Quality Score: {quality.get('overall_quality_score', 'N/A')}/10")
            print(f"📝 Content Quality: {quality.get('content_quality_score', 'N/A')}/10")
            print(f"📞 Contact Completeness: {quality.get('contact_completeness_score', 'N/A')}/10")
            print(f"🏠 Address Accuracy: {quality.get('address_accuracy_score', 'N/A')}/10")
            print(f"🔧 Issues Resolved: {quality.get('issues_resolved', 'N/A')}")
            print(f"✅ Validation Status: {quality.get('validation_passed', 'N/A')}")
        
        # Display structure improvements
        print("\n📋 STRUCTURE IMPROVEMENTS:")
        print("-" * 25)
        
        if 'company_info' in cleaned_data:
            company = cleaned_data['company_info']
            print(f"🏢 Company Name: {company.get('name', 'N/A')}")
            
            welcome = company.get('welcome_message', '')
            if welcome and len(welcome) > 50:
                print(f"📝 Welcome Message: {welcome[:100]}...")
            
            print(f"🎯 Tagline: {company.get('tagline', 'N/A')}")
        
        if 'contact_details' in cleaned_data:
            contact = cleaned_data['contact_details']
            
            if 'office_timing' in contact:
                timing = contact['office_timing']
                print(f"⏰ Office Hours: {timing.get('days', '')} {timing.get('hours', '')}")
            
            phones = contact.get('phones', [])
            emails = contact.get('emails', [])
            print(f"📞 Contact Info: {len(phones)} phones, {len(emails)} emails")
            
            if 'head_office' in contact:
                print(f"🏢 Head Office: Available")
            
            branches = contact.get('branches', [])
            print(f"🌍 Branches: {len(branches)} locations")
        
        print(f"\n🎉 Data cleaning completed successfully!")
        print(f"📁 Cleaned data saved to: {cleaned_file_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data cleaning failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)