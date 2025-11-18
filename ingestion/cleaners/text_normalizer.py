"""
Text Normalizer for PropIntel Data Cleaning Pipeline

This module standardizes and normalizes text data including phone numbers,
email addresses, addresses, and other contact information.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class TextNormalizer:
    """Normalizes and standardizes text data for consistency"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Phone number patterns for India
        self.phone_patterns = [
            r'\b0(\d{2,4})-(\d{7,8})\b',  # Landline: 0341-7963322
            r'\b(\d{10})\b',  # Mobile: 9434745115
            r'\b0(\d{2})-(\d{8})\b',  # STD: 033-26310154
            r'\(([LI])\)\s*(\d{2,4})-(\d{7,8})',  # (L) 033-26310154
        ]
        
        # Email patterns
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Indian states and common city names for standardization
        self.state_mappings = {
            'west bengal': 'West Bengal',
            'wb': 'West Bengal',
            'bengal': 'West Bengal',
            'hooghly': 'Hooghly',
            'hugly': 'Hooghly',
            'asansol': 'Asansol',
            'bandel': 'Bandel'
        }
        
        # Common address terms standardization
        self.address_terms = {
            'apartment': 'Apartment',
            'apt': 'Apartment',
            'road': 'Road',
            'rd': 'Road',
            'street': 'Street',
            'st': 'Street',
            'floor': 'Floor',
            'flr': 'Floor', 
            'plot': 'Plot',
            'house': 'House',
            'building': 'Building',
            'complex': 'Complex'
        }
    
    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number to standard Indian format"""
        if not phone:
            return None
        
        # Clean the phone number
        cleaned = re.sub(r'[^\d\-\(\)\s]', '', phone)
        
        # Try different patterns
        for pattern in self.phone_patterns:
            match = re.search(pattern, cleaned)
            if match:
                groups = match.groups()
                
                if len(groups) == 1:  # Mobile number
                    number = groups[0]
                    if len(number) == 10 and number.startswith(('6', '7', '8', '9')):
                        return f"+91-{number[:5]}-{number[5:]}"
                
                elif len(groups) == 2:  # Landline
                    area_code, number = groups
                    return f"+91-{area_code}-{number}"
                
                elif len(groups) == 3:  # With prefix
                    prefix, area_code, number = groups
                    return f"+91-{area_code}-{number}"
        
        # If no pattern matches, try basic cleaning
        digits_only = re.sub(r'[^\d]', '', phone)
        if len(digits_only) == 10 and digits_only.startswith(('6', '7', '8', '9')):
            return f"+91-{digits_only[:5]}-{digits_only[5:]}"
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            area_code = digits_only[1:4]
            number = digits_only[4:]
            return f"+91-{area_code}-{number}"
        
        return None
    
    def normalize_email_address(self, email: str) -> str:
        """Normalize email address format"""
        if not email:
            return ""
        
        # Clean and lowercase
        email = email.strip().lower()
        
        # Remove any extra characters
        email = re.sub(r'[^\w@.-]', '', email)
        
        return email
    
    def normalize_email(self, email: str) -> str:
        """Alias for normalize_email_address for consistency"""
        return self.normalize_email_address(email)
    
    def normalize_address(self, address: str) -> Dict[str, str]:
        """Normalize address to structured format"""
        if not address:
            return {}
        
        # Clean the address
        cleaned_address = self._clean_address_text(address)
        
        # Extract components
        components = {
            'building': '',
            'street': '',
            'area': '',
            'city': '',
            'district': '',
            'state': '',
            'pin_code': '',
            'full_address': cleaned_address
        }
        
        # Extract PIN code
        pin_match = re.search(r'\b(\d{6})\b', cleaned_address)
        if pin_match:
            components['pin_code'] = pin_match.group(1)
        
        # Extract city and state
        components.update(self._extract_location_info(cleaned_address))
        
        # Extract building/landmark
        components['building'] = self._extract_building_info(cleaned_address)
        
        return components
    
    def _clean_address_text(self, address: str) -> str:
        """Clean address text of unwanted characters and formatting"""
        # Remove extra whitespace
        cleaned = ' '.join(address.split())
        
        # Remove contact numbers from address
        cleaned = re.sub(r'contact\s*no[^0-9]*\d+', '', cleaned, flags=re.IGNORECASE)
        
        # Remove phone numbers
        for pattern in self.phone_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Remove email addresses
        cleaned = re.sub(self.email_pattern, '', cleaned)
        
        # Standardize address terms
        for old_term, new_term in self.address_terms.items():
            cleaned = re.sub(r'\b' + old_term + r'\b', new_term, cleaned, flags=re.IGNORECASE)
        
        # Clean punctuation
        cleaned = re.sub(r'[,\s]+', ' ', cleaned)
        cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
        
        return cleaned.strip()
    
    def _extract_location_info(self, address: str) -> Dict[str, str]:
        """Extract city, district, and state information"""
        location_info = {'city': '', 'district': '', 'state': ''}
        
        address_lower = address.lower()
        
        # Check for known cities
        if 'asansol' in address_lower:
            location_info['city'] = 'Asansol'
            location_info['district'] = 'Paschim Bardhaman'
            location_info['state'] = 'West Bengal'
        elif 'bandel' in address_lower:
            location_info['city'] = 'Bandel'
            location_info['district'] = 'Hooghly'
            location_info['state'] = 'West Bengal'
        elif 'hooghly' in address_lower:
            location_info['district'] = 'Hooghly'
            location_info['state'] = 'West Bengal'
        elif 'kulti' in address_lower:
            location_info['city'] = 'Kulti'
            location_info['district'] = 'Paschim Bardhaman'
            location_info['state'] = 'West Bengal'
        
        # Extract state from address
        for state_variant, standard_state in self.state_mappings.items():
            if state_variant in address_lower:
                location_info['state'] = standard_state
                break
        
        return location_info
    
    def _extract_building_info(self, address: str) -> str:
        """Extract building or landmark information"""
        # Look for apartment/building names
        patterns = [
            r'([A-Za-z\s]+Apartment)',
            r'([A-Za-z\s]+Building)',
            r'([A-Za-z\s]+Complex)',
            r'([A-Za-z\s]+Tower)',
            r'([A-Za-z\s]+Enclave)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for floor information
        floor_match = re.search(r'(\d+(?:st|nd|rd|th)\s*Floor)', address, re.IGNORECASE)
        if floor_match:
            return floor_match.group(1)
        
        return ''
    
    def normalize_office_timing(self, timing_text: str) -> Dict[str, str]:
        """Normalize office timing to standard format"""
        if not timing_text:
            return {}
        
        normalized = {
            'days': '',
            'hours': '',
            'hours_24': ''
        }
        
        # Extract days
        day_match = re.search(r'(monday\s+to\s+\w+)', timing_text, re.IGNORECASE)
        if day_match:
            normalized['days'] = day_match.group(1).title()
        
        # Extract hours
        time_match = re.search(r'(\d{1,2}:\d{2}\s*[ap]m.*?\d{1,2}:\d{2}\s*[ap]m)', timing_text, re.IGNORECASE)
        if time_match:
            hours = time_match.group(1)
            normalized['hours'] = hours
            
            # Convert to 24-hour format
            normalized['hours_24'] = self._convert_to_24_hour(hours)
        
        return normalized
    
    def _convert_to_24_hour(self, time_range: str) -> str:
        """Convert 12-hour time range to 24-hour format"""
        try:
            # Extract start and end times
            times = re.findall(r'(\d{1,2}:\d{2})\s*([ap]m)', time_range, re.IGNORECASE)
            if len(times) >= 2:
                start_time, start_period = times[0]
                end_time, end_period = times[-1]
                
                start_24 = self._convert_time_to_24(start_time, start_period)
                end_24 = self._convert_time_to_24(end_time, end_period)
                
                return f"{start_24}-{end_24}"
        except Exception:
            pass
        
        return ""
    
    def _convert_time_to_24(self, time_str: str, period: str) -> str:
        """Convert single time to 24-hour format"""
        hour, minute = map(int, time_str.split(':'))
        
        if period.lower() == 'pm' and hour != 12:
            hour += 12
        elif period.lower() == 'am' and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute:02d}"
    
    def normalize_company_name(self, name: str) -> str:
        """Normalize company name"""
        if not name:
            return ""
        
        # Clean and standardize
        normalized = name.strip()
        
        # Standardize common business terms
        normalized = re.sub(r'\bLtd\.?\b', 'Ltd.', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bPvt\.?\b', 'Pvt.', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bInfra\b', 'Infra', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bRealty\b', 'Realty', normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def remove_duplicates(self, items: List[str]) -> List[str]:
        """Remove duplicate items while preserving order"""
        seen = set()
        result = []
        
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        
        return result
    
    def standardize_text_case(self, text: str, case_type: str = 'title') -> str:
        """Standardize text case (title, upper, lower)"""
        if not text:
            return ""
        
        if case_type == 'title':
            return text.title()
        elif case_type == 'upper':
            return text.upper()
        elif case_type == 'lower':
            return text.lower()
        else:
            return text


if __name__ == "__main__":
    # Test the text normalizer
    normalizer = TextNormalizer()
    
    # Test phone normalization
    test_phones = ["0341-7963322", "9434745115", "(L) 033-26310154"]
    for phone in test_phones:
        normalized = normalizer.normalize_phone_number(phone)
        print(f"Phone: {phone} -> {normalized}")
    
    # Test email normalization
    test_emails = ["ASTHAINFRAREALTY@GMAIL.COM", "  moumitadas@asthainfrarealty.com  "]
    for email in test_emails:
        normalized = normalizer.normalize_email_address(email)
        print(f"Email: {email} -> {normalized}")
    
    # Test address normalization
    test_address = "Prakash Apartment 1st Floor, G.T. Road, Gopalpur, Asansol - 713304"
    normalized_addr = normalizer.normalize_address(test_address)
    print(f"Address components: {normalized_addr}")
    
    # Test office timing
    test_timing = "Monday to Saturday from 10:00 AM – 5:00 PM"
    normalized_timing = normalizer.normalize_office_timing(test_timing)
    print(f"Timing: {normalized_timing}")