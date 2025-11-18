"""
Data Cleaning Pipeline for PropIntel

This module provides comprehensive data cleaning capabilities for scraped real estate data.
It processes raw scraped content through intelligent extraction and cleaning stages to produce 
high-quality, structured data ready for the RAG system.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .intelligent_data_extractor import IntelligentDataExtractor


class DataCleaningPipeline:
    """Orchestrates the complete data cleaning workflow with intelligent extraction"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import traceback
from datetime import datetime

from ingestion.cleaners.content_filter import ContentFilter
from ingestion.cleaners.text_normalizer import TextNormalizer
from ingestion.cleaners.contact_validator import ContactValidator
from ingestion.cleaners.data_quality_scorer import DataQualityScorer
from ingestion.config.env_loader import get_config


class DataCleaningPipeline:
    """Orchestrates the complete data cleaning pipeline"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the data cleaning pipeline"""
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize intelligent data extractor
        self.data_extractor = IntelligentDataExtractor()
        
        # Set output directory
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'data' / 'processed'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Processing metadata
        self.processing_stats = {
            'files_processed': 0,
            'successful_cleanings': 0,
            'failed_cleanings': 0,
            'records_processed': 0
        }
        
        self.logger.info(f"Intelligent data cleaning pipeline initialized with output directory: {self.output_dir}")
    
    def clean_single_company_data(self, raw_data: Dict[str, Any], 
                                  company_id: Optional[str] = None) -> Dict[str, Any]:
        """Clean data for a single company through intelligent extraction"""
        
        if not company_id:
            company_id = raw_data.get('company_info', {}).get('name', 'unknown_company')
            company_id = company_id.lower().replace(' ', '_')

        self.logger.info(f"Starting intelligent data extraction for: {company_id}")

        try:
            # Extract company information
            self.logger.info(f"Extracting company information for {company_id}")
            company_info = self.data_extractor.extract_company_info(raw_data)
            
            # Extract contact details
            self.logger.info(f"Extracting contact details for {company_id}")
            contact_details = self.data_extractor.extract_contact_details(raw_data)
            
            # Extract social media
            self.logger.info(f"Extracting social media information for {company_id}")
            social_media = self.data_extractor.extract_social_media(raw_data)
            
            # Structure the clean data
            cleaned_data = {
                "company_info": company_info,
                "contact_details": contact_details
            }
            
            # Add social media if found
            if social_media:
                cleaned_data["social_media"] = social_media
            
            # Update processing stats
            self.processing_stats['successful_cleanings'] += 1
            self.processing_stats['records_processed'] += 1
            
            self.logger.info(f"Successfully completed intelligent data extraction for: {company_id}")
            
            return cleaned_data

        except Exception as e:
            error_msg = f"Error in data extraction for {company_id}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error("Traceback:", exc_info=True)
            
            self.processing_stats['failed_cleanings'] += 1
            
            # Return minimal structure on error
            return {
                "company_info": {"name": "Astha Infra Realty Ltd."},
                "contact_details": {},
                "error": str(e)
            }
    
    def process_file(self, input_file_path: str, output_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Process a single JSON file through the cleaning pipeline"""
        
        input_path = Path(input_file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file_path}")
        
        # Read raw data
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Clean the data
        cleaned_data = self.clean_single_company_data(raw_data)
        
        # Determine output path
        if output_file_path:
            output_path = Path(output_file_path)
        else:
            output_path = self.output_dir / f"{input_path.stem}_clean.json"
        
        # Save cleaned data
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        self.processing_stats['files_processed'] += 1
        
        return {
            'input_file': str(input_path),
            'output_file': str(output_path),
            'success': True,
            'cleaned_data': cleaned_data
        }
    
    def generate_pipeline_report(self) -> str:
        """Generate a summary report of pipeline processing"""
        
        report = []
        report.append("=" * 50)
        report.append("PROPINTEL DATA CLEANING PIPELINE REPORT")
        report.append("=" * 50)
        report.append(f"Files Processed: {self.processing_stats['files_processed']}")
        report.append(f"Successful Cleanings: {self.processing_stats['successful_cleanings']}") 
        report.append(f"Failed Cleanings: {self.processing_stats['failed_cleanings']}")
        report.append(f"Records Processed: {self.processing_stats['records_processed']}")
        
        if self.processing_stats['files_processed'] > 0:
            success_rate = (self.processing_stats['successful_cleanings'] / self.processing_stats['files_processed']) * 100
            report.append(f"Success Rate: {success_rate:.1f}%")
        
        report.append("=" * 50)
        
        return "\n".join(report)
        """Apply content filtering to remove technical artifacts"""
        filtered_data = data.copy()
        
        # Filter company info content
        if 'company_info' in filtered_data:
            company_info = filtered_data['company_info']
            
            # Filter welcome message
            if 'welcome_message' in company_info:
                original_message = company_info['welcome_message']
                filtered_message = self.content_filter.extract_business_content(original_message)
                company_info['welcome_message'] = filtered_message
                
                self.logger.debug(f"Welcome message filtered: {len(original_message)} -> {len(filtered_message)} chars")
            
            # Filter description
            if 'description' in company_info:
                original_desc = company_info['description']
                filtered_desc = self.content_filter.extract_business_content(original_desc)
                company_info['description'] = filtered_desc
        
        return filtered_data
    
    def _apply_text_normalization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply text normalization to standardize formats"""
        normalized_data = data.copy()
        
        # Normalize contact details
        if 'contact_details' in normalized_data:
            contact_details = normalized_data['contact_details']
            
            # Normalize phone numbers
            if 'phones' in contact_details:
                normalized_phones = []
                for phone in contact_details['phones']:
                    normalized_phone = self.text_normalizer.normalize_phone_number(phone)
                    if normalized_phone:
                        normalized_phones.append(normalized_phone)
                contact_details['phones'] = normalized_phones
            
            # Normalize email addresses
            if 'emails' in contact_details:
                normalized_emails = []
                for email in contact_details['emails']:
                    normalized_email = self.text_normalizer.normalize_email_address(email)
                    if normalized_email:
                        normalized_emails.append(normalized_email)
                contact_details['emails'] = normalized_emails
            
            # Normalize addresses
            if 'head_office' in contact_details and contact_details['head_office'].get('address'):
                head_office = contact_details['head_office']
                if isinstance(head_office['address'], str):
                    # Address is a string, parse it directly
                    original_address = head_office['address']
                    normalized_address = self.text_normalizer.normalize_address(original_address)
                    contact_details['head_office']['address'] = {
                        'full_address': original_address,
                        'parsed': normalized_address
                    }
                elif isinstance(head_office['address'], dict) and 'full_address' in head_office['address']:
                    # Address is a dict with full_address field
                    original_address = head_office['address']['full_address']
                    normalized_address = self.text_normalizer.normalize_address(original_address)
                    contact_details['head_office']['address'] = normalized_address
            
            # Normalize branch addresses
            if 'branches' in contact_details:
                for branch in contact_details['branches']:
                    if branch.get('address'):
                        if isinstance(branch['address'], str):
                            # Address is a string, parse it directly
                            original_address = branch['address']
                            normalized_address = self.text_normalizer.normalize_address(original_address)
                            branch['address'] = {
                                'full_address': original_address,
                                'parsed': normalized_address
                            }
                        elif isinstance(branch['address'], dict) and branch['address'].get('full_address'):
                            # Address is a dict with full_address field
                            original_address = branch['address']['full_address']
                            normalized_address = self.text_normalizer.normalize_address(original_address)
                            branch['address'] = normalized_address
            
            # Normalize office timing
            if 'office_timing' in contact_details:
                timing = contact_details['office_timing']
                if timing.get('hours'):
                    normalized_timing = self.text_normalizer.normalize_office_timing(timing['hours'])
                    contact_details['office_timing'].update(normalized_timing)
        
        return normalized_data
    
    def _validate_contact_information(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all contact information and return validation results"""
        validation_results = {
            'phone_validations': [],
            'email_validations': [],
            'address_validations': [],
            'timing_validation': {},
            'duplicate_detection': {},
            'completeness_score': {}
        }
        
        contact_details = data.get('contact_details', {})
        
        # Validate phone numbers
        phones = contact_details.get('phones', [])
        for phone in phones:
            validation = self.contact_validator.validate_phone_number(phone)
            validation_results['phone_validations'].append(validation)
        
        # Validate email addresses
        emails = contact_details.get('emails', [])
        for email in emails:
            validation = self.contact_validator.validate_email_address(email)
            validation_results['email_validations'].append(validation)
        
        # Validate addresses
        head_office = contact_details.get('head_office')
        if head_office and head_office.get('address'):
            validation = self.contact_validator.validate_address(head_office['address'])
            validation_results['address_validations'].append({
                'type': 'head_office',
                'validation': validation
            })
        
        branches = contact_details.get('branches', [])
        for i, branch in enumerate(branches):
            if branch.get('address'):
                validation = self.contact_validator.validate_address(branch['address'])
                validation_results['address_validations'].append({
                    'type': f'branch_{i+1}',
                    'validation': validation
                })
        
        # Validate office timing
        timing = contact_details.get('office_timing')
        if timing:
            validation = self.contact_validator.validate_office_timing(timing)
            validation_results['timing_validation'] = validation
        
        # Detect duplicates
        validation_results['duplicate_detection']['phones'] = self.contact_validator.detect_duplicates(phones)
        validation_results['duplicate_detection']['emails'] = self.contact_validator.detect_duplicates(emails)
        
        # Calculate completeness score
        validation_results['completeness_score'] = self.contact_validator.calculate_contact_completeness(contact_details)
        
        return validation_results
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall data quality and generate scores"""
        return self.quality_scorer.calculate_overall_quality_score(data)
    
    def _structure_final_data(self, data: Dict[str, Any], 
                             validation_results: Dict[str, Any], 
                             quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Structure the final cleaned data in production format"""
        
        final_data = {
            'company_profile': {
                'basic_info': data.get('company_info', {}),
                'contact_information': data.get('contact_details', {}),
                'online_presence': data.get('online_presence', {}),
                'business_details': data.get('business_details', {})
            },
            'data_quality': {
                'overall_score': quality_assessment.get('overall_score', 0),
                'quality_grade': quality_assessment.get('quality_grade', 'Unknown'),
                'component_scores': quality_assessment.get('component_scores', {}),
                'validation_summary': self._create_validation_summary(validation_results)
            },
            'metadata': {
                'source_url': data.get('source_url', ''),
                'extraction_timestamp': data.get('extraction_timestamp', ''),
                'cleaning_timestamp': datetime.now().isoformat(),
                'data_version': '1.0.0'
            }
        }
        
        return final_data
    
    def _create_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of validation results"""
        summary = {
            'phones': {
                'total': len(validation_results.get('phone_validations', [])),
                'valid': sum(1 for v in validation_results.get('phone_validations', []) if v['is_valid']),
                'invalid': sum(1 for v in validation_results.get('phone_validations', []) if not v['is_valid'])
            },
            'emails': {
                'total': len(validation_results.get('email_validations', [])),
                'valid': sum(1 for v in validation_results.get('email_validations', []) if v['is_valid']),
                'invalid': sum(1 for v in validation_results.get('email_validations', []) if not v['is_valid'])
            },
            'addresses': {
                'total': len(validation_results.get('address_validations', [])),
                'valid': sum(1 for v in validation_results.get('address_validations', []) if v['validation']['is_valid']),
                'invalid': sum(1 for v in validation_results.get('address_validations', []) if not v['validation']['is_valid'])
            },
            'completeness_score': validation_results.get('completeness_score', {}).get('overall_score', 0)
        }
        
        return summary
    
    def _collect_all_issues(self, validation_results: Dict[str, Any], 
                           quality_assessment: Dict[str, Any]) -> List[str]:
        """Collect all issues found during cleaning and validation"""
        issues = []
        
        # Collect validation issues
        for phone_validation in validation_results.get('phone_validations', []):
            issues.extend(phone_validation.get('issues', []))
        
        for email_validation in validation_results.get('email_validations', []):
            issues.extend(email_validation.get('issues', []))
        
        for addr_validation in validation_results.get('address_validations', []):
            issues.extend(addr_validation['validation'].get('issues', []))
        
        # Collect quality assessment issues
        for component_score in quality_assessment.get('component_scores', {}).values():
            issues.extend(component_score.get('issues', []))
        
        return list(set(issues))  # Remove duplicates
    
    def process_file(self, input_file_path: str, output_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Process a single JSON file through the cleaning pipeline"""
        
        input_path = Path(input_file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file_path}")
        
        # Determine output path
        if not output_file_path:
            output_file_path = self.output_dir / f"cleaned_{input_path.name}"
        else:
            output_file_path = Path(output_file_path)
        
        self.logger.info(f"Processing file: {input_file_path}")
        
        # Load raw data
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Process through pipeline
        processing_result = self.clean_single_company_data(raw_data)
        
        # Save cleaned data
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(processing_result, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Cleaned data saved to: {output_file_path}")
        
        # Update statistics
        self.stats['total_processed'] += 1
        if processing_result['success']:
            self.stats['successful_cleanings'] += 1
            quality_score = processing_result['cleaning_metadata']['quality_assessment'].get('overall_score', 0)
            self.stats['average_quality_score'] = (
                (self.stats['average_quality_score'] * (self.stats['successful_cleanings'] - 1) + quality_score)
                / self.stats['successful_cleanings']
            )
        else:
            self.stats['failed_cleanings'] += 1
        
        return processing_result
    
    def process_directory(self, input_dir: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Process all JSON files in a directory"""
        
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats['processing_start_time'] = datetime.now().isoformat()
        
        # Find all JSON files
        json_files = list(input_path.glob("*.json"))
        
        if not json_files:
            self.logger.warning(f"No JSON files found in: {input_dir}")
            return {'processed_files': [], 'stats': self.stats}
        
        self.logger.info(f"Found {len(json_files)} JSON files to process")
        
        processed_files = []
        
        for json_file in json_files:
            try:
                result = self.process_file(str(json_file))
                processed_files.append({
                    'input_file': str(json_file),
                    'output_file': str(self.output_dir / f"cleaned_{json_file.name}"),
                    'success': result['success'],
                    'quality_score': result['cleaning_metadata']['quality_assessment'].get('overall_score', 0)
                })
            except Exception as e:
                self.logger.error(f"Failed to process {json_file}: {str(e)}")
                processed_files.append({
                    'input_file': str(json_file),
                    'success': False,
                    'error': str(e)
                })
                self.stats['failed_cleanings'] += 1
        
        self.stats['processing_end_time'] = datetime.now().isoformat()
        
        return {
            'processed_files': processed_files,
            'stats': self.stats
        }
    
    def generate_pipeline_report(self) -> str:
        """Generate a comprehensive pipeline processing report"""
        report = []
        report.append("=" * 60)
        report.append("DATA CLEANING PIPELINE REPORT")
        report.append("=" * 60)
        
        if self.stats['processing_start_time']:
            report.append(f"Processing Started: {self.stats['processing_start_time']}")
        if self.stats['processing_end_time']:
            report.append(f"Processing Completed: {self.stats['processing_end_time']}")
        
        report.append(f"Total Files Processed: {self.stats['total_processed']}")
        report.append(f"Successful Cleanings: {self.stats['successful_cleanings']}")
        report.append(f"Failed Cleanings: {self.stats['failed_cleanings']}")
        
        if self.stats['successful_cleanings'] > 0:
            report.append(f"Average Quality Score: {self.stats['average_quality_score']:.2f}/100")
            success_rate = (self.stats['successful_cleanings'] / self.stats['total_processed']) * 100
            report.append(f"Success Rate: {success_rate:.1f}%")
        
        report.append("=" * 60)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the pipeline with sample data
    pipeline = DataCleaningPipeline()
    
    # Process the Astha company data
    input_file = "data/raw/astha_company_info.json"
    
    try:
        result = pipeline.process_file(input_file)
        
        print("Pipeline processing completed!")
        print(f"Success: {result['success']}")
        
        if result['success']:
            quality_score = result['cleaning_metadata']['quality_assessment']['overall_score']
            quality_grade = result['cleaning_metadata']['quality_assessment']['quality_grade']
            print(f"Quality Score: {quality_score}/100 ({quality_grade})")
            
            print(f"Issues Found: {len(result['cleaning_metadata']['issues_found'])}")
            print(f"Recommendations: {len(result['cleaning_metadata']['recommendations'])}")
        
        # Generate report
        report = pipeline.generate_pipeline_report()
        print("\n" + report)
        
    except Exception as e:
        print(f"Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()