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