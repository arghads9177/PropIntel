"""
Company Information Scraper for PropIntel

This module scrapes company information from Astha Infra Realty website
including welcome messages, contact details, office timing, and addresses.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urljoin

from ..scrapers.base_scraper import BaseScraper
from ..utils.text_extractor import TextExtractor
from ..config.env_loader import get_config


class AsthaCompanyInfoScraper(BaseScraper):
    """Scraper for extracting Astha Infra Realty company information"""
    
    def __init__(self, base_url: str = None):
        """Initialize the company info scraper"""
        config = get_config()
        base_url = base_url or config.get_website_base_url()
        
        super().__init__(base_url)
        
        self.text_extractor = TextExtractor()
        self.config = config
        
        # Define target pages
        self.target_pages = {
            'home': '',  # Base URL
            'contact': 'contact-us/'
        }
        
        self.logger.info(f"Company info scraper initialized for: {self.base_url}")
    
    def scrape(self) -> Dict[str, Any]:
        """Main scraping method - extracts all company information"""
        self.logger.info("Starting company information extraction...")
        
        # Initialize result structure
        result = {
            'company_info': {},
            'contact_details': {},
            'social_media': {},
            'metadata': {
                'pages_scraped': [],
                'scraping_date': datetime.now().isoformat(),
                'base_url': self.base_url
            }
        }
        
        try:
            # Scrape home page
            home_data = self.scrape_home_page()
            if home_data:
                result['company_info'].update(home_data['company_info'])
                result['contact_details'].update(home_data['contact_details'])
                result['social_media'].update(home_data['social_media'])
                result['metadata']['pages_scraped'].append('home')
            
            # Scrape contact page
            contact_data = self.scrape_contact_page()
            if contact_data:
                # Merge contact data (contact page has priority for contact details)
                result['contact_details'].update(contact_data['contact_details'])
                result['metadata']['pages_scraped'].append('contact-us')
            
            # Calculate data completeness
            result['metadata']['data_completeness'] = self._calculate_completeness(result)
            
            self.logger.info(f"Company information extraction completed. Pages scraped: {result['metadata']['pages_scraped']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during company information extraction: {e}")
            result['metadata']['error'] = str(e)
            return result
    
    def scrape_home_page(self) -> Dict[str, Any]:
        """Scrape company information from home page"""
        self.logger.info("Scraping home page for company information...")
        
        home_url = self.base_url
        soup = self.get_page(home_url)
        
        if not soup:
            self.logger.error("Failed to load home page")
            return {}
        
        # Extract company information
        company_info = {
            'name': 'Astha Infra Realty Ltd.',
            'welcome_message': self.text_extractor.extract_welcome_message(soup),
            'tagline': self.text_extractor.extract_company_tagline(soup),
        }
        
        # Extract contact details from home page
        addresses = self.text_extractor.extract_addresses(soup)
        page_text = soup.get_text()
        
        contact_details = {
            'addresses': addresses,
            'phones': self.text_extractor.extract_phone_numbers(page_text),
            'emails': self.text_extractor.extract_email_addresses(page_text),
        }
        
        # Extract social media links
        social_media = self.text_extractor.extract_social_media_links(soup)
        
        self.logger.info(f"Home page extraction completed. Found {len(addresses)} addresses, {len(contact_details['phones'])} phones")
        
        return {
            'company_info': company_info,
            'contact_details': contact_details,
            'social_media': social_media
        }
    
    def scrape_contact_page(self) -> Dict[str, Any]:
        """Scrape contact information from contact us page"""
        self.logger.info("Scraping contact page for detailed contact information...")
        
        contact_url = urljoin(self.base_url, self.target_pages['contact'])
        soup = self.get_page(contact_url)
        
        if not soup:
            self.logger.error("Failed to load contact page")
            return {}
        
        page_text = soup.get_text()
        
        # Extract office timing
        office_timing = self.text_extractor.extract_office_timing(soup)
        
        # Extract detailed contact information
        addresses = self.text_extractor.extract_addresses(soup)
        
        # Organize addresses by type (head office, branches)
        organized_addresses = self._organize_addresses(addresses, page_text)
        
        contact_details = {
            'office_timing': office_timing,
            'head_office': organized_addresses.get('head_office', {}),
            'branches': organized_addresses.get('branches', []),
            'phones': self.text_extractor.extract_phone_numbers(page_text),
            'emails': self.text_extractor.extract_email_addresses(page_text),
        }
        
        self.logger.info(f"Contact page extraction completed. Found {len(addresses)} addresses, office timing: {bool(office_timing)}")
        
        return {
            'contact_details': contact_details
        }
    
    def _organize_addresses(self, addresses: List[Dict], page_text: str) -> Dict[str, Any]:
        """Organize addresses into head office and branches"""
        organized = {
            'head_office': {},
            'branches': []
        }
        
        for addr in addresses:
            address_text = addr['address'].lower()
            
            # Identify head office
            if any(keyword in address_text for keyword in ['h.o', 'head office', 'akash apartment', 'gopalpur']):
                organized['head_office'] = {
                    'address': addr['address'],
                    'phones': addr['phones'],
                    'emails': addr['emails'],
                    'pin_codes': addr['pin_codes']
                }
            
            # Identify branches
            elif any(keyword in address_text for keyword in ['branch', 'bandel', 'hooghly', 'sarat sarani']):
                branch_info = {
                    'name': self._identify_branch_name(addr['address']),
                    'address': addr['address'],
                    'phones': addr['phones'],
                    'emails': addr['emails'],
                    'pin_codes': addr['pin_codes']
                }
                organized['branches'].append(branch_info)
            
            # Other offices
            else:
                branch_info = {
                    'name': self._identify_branch_name(addr['address']),
                    'address': addr['address'],
                    'phones': addr['phones'],
                    'emails': addr['emails'],
                    'pin_codes': addr['pin_codes']
                }
                organized['branches'].append(branch_info)
        
        return organized
    
    def _identify_branch_name(self, address: str) -> str:
        """Identify branch name from address"""
        address_lower = address.lower()
        
        if 'bandel' in address_lower or 'hooghly' in address_lower:
            return 'Bandel Branch'
        elif 'asansol' in address_lower:
            return 'Asansol Branch'
        elif 'kulti' in address_lower:
            return 'Kulti Branch'
        else:
            return 'Other Office'
    
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate data completeness score"""
        total_fields = 0
        filled_fields = 0
        
        # Check company info fields
        company_fields = ['name', 'welcome_message', 'tagline']
        for field in company_fields:
            total_fields += 1
            if data['company_info'].get(field):
                filled_fields += 1
        
        # Check contact detail fields
        contact_fields = ['office_timing', 'head_office', 'phones', 'emails']
        for field in contact_fields:
            total_fields += 1
            if data['contact_details'].get(field):
                filled_fields += 1
        
        # Check social media
        total_fields += 1
        if data['social_media']:
            filled_fields += 1
        
        return round((filled_fields / total_fields) * 100, 2) if total_fields > 0 else 0.0
    
    def save_to_json(self, data: Dict[str, Any], filename: str = None) -> str:
        """Save extracted data to JSON file"""
        if not filename:
            filename = 'astha_company_info.json'
        
        # Ensure data/raw directory exists
        config = get_config()
        storage_paths = config.get_storage_paths()
        raw_data_path = Path(storage_paths['raw_data'])
        raw_data_path.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = raw_data_path / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Company information saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Error saving company information: {e}")
            raise
    
    def generate_summary_report(self, data: Dict[str, Any]) -> str:
        """Generate a human-readable summary report"""
        report = []
        report.append("=" * 50)
        report.append("ASTHA INFRA REALTY - COMPANY INFORMATION SUMMARY")
        report.append("=" * 50)
        
        # Company Info
        if data.get('company_info'):
            report.append("\n📋 COMPANY INFORMATION:")
            company = data['company_info']
            if company.get('name'):
                report.append(f"  • Name: {company['name']}")
            if company.get('tagline'):
                report.append(f"  • Tagline: {company['tagline']}")
            if company.get('welcome_message'):
                report.append(f"  • About: {company['welcome_message'][:100]}...")
        
        # Contact Details
        if data.get('contact_details'):
            report.append("\n📞 CONTACT INFORMATION:")
            contact = data['contact_details']
            
            if contact.get('office_timing'):
                timing = contact['office_timing']
                report.append(f"  • Office Hours: {timing.get('days', '')} {timing.get('hours', '')}")
            
            if contact.get('phones'):
                report.append(f"  • Phone Numbers: {', '.join(contact['phones'])}")
            
            if contact.get('emails'):
                report.append(f"  • Email Addresses: {', '.join(contact['emails'])}")
            
            if contact.get('head_office'):
                ho = contact['head_office']
                report.append(f"  • Head Office: {ho.get('address', 'N/A')}")
            
            if contact.get('branches'):
                report.append(f"  • Branches: {len(contact['branches'])} locations")
                for branch in contact['branches']:
                    report.append(f"    - {branch.get('name', 'Unknown')}: {branch.get('address', 'N/A')}")
        
        # Social Media
        if data.get('social_media'):
            report.append("\n🌐 SOCIAL MEDIA:")
            social = data['social_media']
            for platform, url in social.items():
                report.append(f"  • {platform.title()}: {url}")
        
        # Metadata
        if data.get('metadata'):
            meta = data['metadata']
            report.append(f"\n📊 EXTRACTION SUMMARY:")
            report.append(f"  • Pages Scraped: {', '.join(meta.get('pages_scraped', []))}")
            report.append(f"  • Data Completeness: {meta.get('data_completeness', 0)}%")
            report.append(f"  • Scraping Date: {meta.get('scraping_date', 'Unknown')}")
        
        report.append("\n" + "=" * 50)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the company info scraper
    scraper = AsthaCompanyInfoScraper()
    
    # Extract company information
    company_data = scraper.scrape()
    
    # Print summary
    summary = scraper.generate_summary_report(company_data)
    print(summary)
    
    # Save to file
    file_path = scraper.save_to_json(company_data)
    print(f"\nData saved to: {file_path}")