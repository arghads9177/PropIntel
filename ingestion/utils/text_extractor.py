"""
Text Extraction Utilities for PropIntel Company Information Scraper

This module provides utilities for extracting and cleaning specific
types of information from web pages like addresses, phone numbers,
emails, and business descriptions.
"""

import re
import logging
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup, Tag


class TextExtractor:
    """Utility class for extracting structured information from web content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Regex patterns for various data types
        self.patterns = {
            'phone': [
                r'\b\d{4}-\d{7}\b',  # 0341-7963322 format
                r'\b\d{10}\b',       # 9434745115 format
                r'\b\d{3}-\d{8}\b',  # 033-26310154 format
                r'\(\w\)\s\d{3}-\d{8}',  # (L) 033-26310154 format
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'address_indicators': [
                r'apartment', r'road', r'hooghly', r'asansol', r'bandel',
                r'floor', r'plot', r'housing', r'college', r'sarani'
            ],
            'pin_code': [
                r'\b\d{6}\b'  # 6-digit pin codes
            ]
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s\-.,@()\/:&]', '', text)
        
        return text.strip()
    
    def extract_welcome_message(self, soup: BeautifulSoup) -> str:
        """Extract welcome message or about us content from home page"""
        welcome_candidates = []
        
        # Look for welcome/about sections
        welcome_elements = soup.find_all(text=re.compile(r'welcome|about|aastha|infra', re.IGNORECASE))
        
        for element in welcome_elements:
            parent = element.parent
            if parent:
                # Get the parent container text
                container_text = parent.get_text(strip=True)
                if len(container_text) > 50:  # Only meaningful content
                    welcome_candidates.append(container_text)
        
        # Also look for paragraphs that contain company description
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ['aastha', 'infra', 'realty', 'developer', 'decades']):
                if len(text) > 100:
                    welcome_candidates.append(text)
        
        # Return the longest meaningful text
        if welcome_candidates:
            return max(welcome_candidates, key=len)
        
        return ""
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phones = []
        
        for pattern in self.patterns['phone']:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Clean and deduplicate
        cleaned_phones = []
        for phone in phones:
            cleaned = re.sub(r'[^\d-]', '', phone)
            if cleaned and cleaned not in cleaned_phones:
                cleaned_phones.append(cleaned)
        
        return cleaned_phones
    
    def extract_email_addresses(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        emails = []
        
        for pattern in self.patterns['email']:
            matches = re.findall(pattern, text)
            emails.extend(matches)
        
        # Deduplicate and clean
        return list(set([email.lower() for email in emails]))
    
    def extract_addresses(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract address information from page"""
        addresses = []
        
        # Look for address sections
        address_sections = soup.find_all(text=re.compile(r'address|office|branch', re.IGNORECASE))
        
        for section in address_sections:
            parent = section.parent
            if parent:
                # Get surrounding text
                for sibling in parent.find_next_siblings():
                    if sibling.name:
                        text = sibling.get_text(strip=True)
                        if self._looks_like_address(text):
                            address_info = self._parse_address(text)
                            if address_info:
                                addresses.append(address_info)
        
        # Also check divs and spans that might contain address info
        for element in soup.find_all(['div', 'span', 'p']):
            text = element.get_text(strip=True)
            if self._looks_like_address(text) and len(text) > 20:
                address_info = self._parse_address(text)
                if address_info and address_info not in addresses:
                    addresses.append(address_info)
        
        return addresses
    
    def _looks_like_address(self, text: str) -> bool:
        """Check if text looks like an address"""
        if not text or len(text) < 10:
            return False
        
        text_lower = text.lower()
        
        # Check for address indicators
        indicators = ['apartment', 'road', 'floor', 'plot', 'hooghly', 'asansol', 'bandel']
        has_indicator = any(indicator in text_lower for indicator in indicators)
        
        # Check for pin code
        has_pin = bool(re.search(r'\b\d{6}\b', text))
        
        return has_indicator or has_pin
    
    def _parse_address(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse address text into structured format"""
        if not text:
            return None
        
        # Extract components
        phones = self.extract_phone_numbers(text)
        emails = self.extract_email_addresses(text)
        pin_codes = re.findall(r'\b\d{6}\b', text)
        
        # Clean the address text (remove phones and emails)
        clean_address = text
        for phone in phones:
            clean_address = clean_address.replace(phone, '')
        for email in emails:
            clean_address = clean_address.replace(email, '')
        
        clean_address = self.clean_text(clean_address)
        
        # Skip if too short after cleaning
        if len(clean_address) < 10:
            return None
        
        return {
            'address': clean_address,
            'phones': phones,
            'emails': emails,
            'pin_codes': pin_codes
        }
    
    def extract_office_timing(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract office timing information"""
        timing_info = {}
        
        # Look for timing-related text
        timing_text = soup.find_all(text=re.compile(r'monday|office|timing|am|pm', re.IGNORECASE))
        
        for text in timing_text:
            parent = text.parent
            if parent:
                content = parent.get_text(strip=True)
                
                # Look for day ranges
                day_match = re.search(r'(monday\s+to\s+\w+)', content, re.IGNORECASE)
                if day_match:
                    timing_info['days'] = day_match.group(1)
                
                # Look for time ranges
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[ap]m.*?\d{1,2}:\d{2}\s*[ap]m)', content, re.IGNORECASE)
                if time_match:
                    timing_info['hours'] = time_match.group(1)
        
        return timing_info
    
    def extract_social_media_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links"""
        social_links = {}
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            
            if 'facebook.com' in href:
                social_links['facebook'] = href
            elif 'youtube.com' in href:
                social_links['youtube'] = href
            elif 'instagram.com' in href:
                social_links['instagram'] = href
            elif 'twitter.com' in href or 'x.com' in href:
                social_links['twitter'] = href
        
        return social_links
    
    def extract_company_tagline(self, soup: BeautifulSoup) -> str:
        """Extract company tagline or motto"""
        # Look for tagline patterns
        tagline_patterns = [
            r'it takes.*?home',
            r'number one.*?company',
            r'leading.*?developer'
        ]
        
        page_text = soup.get_text()
        
        for pattern in tagline_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
            if match:
                tagline = match.group(0)
                # Clean and return if reasonable length
                if 10 < len(tagline) < 200:
                    return self.clean_text(tagline)
        
        return ""


if __name__ == "__main__":
    # Test the text extractor
    extractor = TextExtractor()
    
    # Test phone extraction
    test_text = "Contact us at 0341-7963322 or 9434745115"
    phones = extractor.extract_phone_numbers(test_text)
    print(f"Extracted phones: {phones}")
    
    # Test email extraction
    test_text = "Email us at asthainfrarealty@gmail.com or moumitadas@asthainfrarealty.com"
    emails = extractor.extract_email_addresses(test_text)
    print(f"Extracted emails: {emails}")