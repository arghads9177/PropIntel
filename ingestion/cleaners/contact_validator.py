"""
Contact Validator for PropIntel Data Cleaning Pipeline

This module validates contact information including phone numbers, email addresses,
addresses, and calculates quality scores for the data.
"""

import re
import logging
from typing import List, Dict, Optional, Set, Any

# Simple email validation without external dependency
def is_valid_email(email: str) -> bool:
    """Simple email validation using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


class ContactValidator:
    """Validates and scores contact information quality"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Indian phone number validation patterns
        self.mobile_pattern = r'^\+91-[6-9]\d{4}-\d{5}$'
        self.landline_pattern = r'^\+91-\d{2,4}-\d{7,8}$'
        
        # Valid Indian PIN code pattern
        self.pin_code_pattern = r'^\d{6}$'
        
        # Common Indian area codes for landlines
        self.valid_area_codes = {
            '341': 'Asansol',
            '33': 'Kolkata',
            '343': 'Durgapur',
            '3464': 'Burdwan'
        }
        
        # Valid Indian mobile number prefixes
        self.mobile_prefixes = ['6', '7', '8', '9']
    
    def validate_phone_number(self, phone: str) -> Dict[str, Any]:
        """Validate phone number and return detailed validation result"""
        result = {
            'original': phone,
            'is_valid': False,
            'type': '',
            'area_code': '',
            'issues': []
        }
        
        if not phone:
            result['issues'].append('Empty phone number')
            return result
        
        # Check mobile number
        if re.match(self.mobile_pattern, phone):
            result['is_valid'] = True
            result['type'] = 'mobile'
            
            # Extract prefix to verify it's valid
            prefix = phone.split('-')[1][0]
            if prefix not in self.mobile_prefixes:
                result['issues'].append(f'Invalid mobile prefix: {prefix}')
                result['is_valid'] = False
        
        # Check landline number
        elif re.match(self.landline_pattern, phone):
            result['is_valid'] = True
            result['type'] = 'landline'
            
            # Extract area code
            area_code = phone.split('-')[1]
            result['area_code'] = area_code
            
            if area_code not in self.valid_area_codes:
                result['issues'].append(f'Unknown area code: {area_code}')
        else:
            result['issues'].append('Invalid phone number format')
        
        return result
    
    def validate_email_address(self, email: str) -> Dict[str, Any]:
        """Validate email address format and domain"""
        result = {
            'original': email,
            'is_valid': False,
            'domain': '',
            'issues': []
        }
        
        if not email:
            result['issues'].append('Empty email address')
            return result
        
        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            result['issues'].append('Invalid email format')
            return result
        
        # Extract domain
        domain = email.split('@')[1]
        result['domain'] = domain
        
        # Validate domain format
        domain_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(domain_pattern, domain):
            result['issues'].append(f'Invalid domain: {domain}')
            return result
        
        # Check for common business email domains
        business_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'company.com']
        if domain.lower() in business_domains[:3]:  # Personal email domains
            result['issues'].append('Personal email domain (consider business domain)')
        
        result['is_valid'] = True
        return result
    
    def validate_address(self, address: Dict[str, str]) -> Dict[str, Any]:
        """Validate address completeness and accuracy"""
        result = {
            'is_valid': False,
            'completeness_score': 0.0,
            'issues': [],
            'missing_fields': []
        }
        
        if not address:
            result['issues'].append('Empty address')
            return result
        
        # Required fields for a complete address
        required_fields = ['full_address', 'city', 'state', 'pin_code']
        optional_fields = ['building', 'street', 'area', 'district']
        
        # Check required fields
        present_required = 0
        for field in required_fields:
            if address.get(field):
                present_required += 1
            else:
                result['missing_fields'].append(field)
        
        # Check optional fields
        present_optional = sum(1 for field in optional_fields if address.get(field))
        
        # Calculate completeness score
        required_weight = 0.7
        optional_weight = 0.3
        
        required_score = (present_required / len(required_fields)) * required_weight
        optional_score = (present_optional / len(optional_fields)) * optional_weight
        
        result['completeness_score'] = round((required_score + optional_score) * 100, 2)
        
        # Validate PIN code
        pin_code = address.get('pin_code', '')
        if pin_code:
            if not re.match(self.pin_code_pattern, pin_code):
                result['issues'].append(f'Invalid PIN code format: {pin_code}')
            else:
                # Validate PIN code range for West Bengal
                if not self._is_valid_wb_pin_code(pin_code):
                    result['issues'].append(f'PIN code not in West Bengal range: {pin_code}')
        
        # Validate state
        state = address.get('state', '')
        if state and state != 'West Bengal':
            result['issues'].append(f'Unexpected state for this business: {state}')
        
        # Address is valid if completeness score > 70% and no critical issues
        critical_issues = [issue for issue in result['issues'] if 'Invalid PIN code' in issue]
        result['is_valid'] = result['completeness_score'] >= 70.0 and len(critical_issues) == 0
        
        return result
    
    def _is_valid_wb_pin_code(self, pin_code: str) -> bool:
        """Check if PIN code is valid for West Bengal"""
        if not pin_code or len(pin_code) != 6:
            return False
        
        # West Bengal PIN codes typically start with 7
        wb_prefixes = ['700', '701', '702', '703', '704', '705', '706', '707', '708', '709', 
                       '710', '711', '712', '713', '714', '715', '716', '717', '718', '719',
                       '720', '721', '722', '723', '724', '725', '726', '727', '728', '729',
                       '730', '731', '732', '733', '734', '735', '736', '737', '738', '739',
                       '740', '741', '742', '743', '744', '745']
        
        return pin_code[:3] in wb_prefixes
    
    def validate_office_timing(self, timing: Dict[str, str]) -> Dict[str, Any]:
        """Validate office timing format and reasonableness"""
        result = {
            'is_valid': False,
            'issues': []
        }
        
        if not timing:
            result['issues'].append('Empty office timing')
            return result
        
        # Check for required fields
        if not timing.get('days'):
            result['issues'].append('Missing working days')
        
        if not timing.get('hours'):
            result['issues'].append('Missing office hours')
        
        # Validate time format
        hours_24 = timing.get('hours_24', '')
        if hours_24:
            if not re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', hours_24):
                result['issues'].append('Invalid 24-hour time format')
            else:
                # Check if timing is reasonable
                start_time, end_time = hours_24.split('-')
                start_hour = int(start_time.split(':')[0])
                end_hour = int(end_time.split(':')[0])
                
                if start_hour >= end_hour:
                    result['issues'].append('Start time should be before end time')
                
                if start_hour < 6 or start_hour > 12:
                    result['issues'].append('Unusual start time for business hours')
                
                if end_hour < 14 or end_hour > 22:
                    result['issues'].append('Unusual end time for business hours')
        
        result['is_valid'] = len(result['issues']) == 0
        return result
    
    def detect_duplicates(self, items: List[str]) -> Dict[str, Any]:
        """Detect duplicate items in a list"""
        if not items:
            return {'has_duplicates': False, 'duplicates': [], 'unique_count': 0}
        
        seen = set()
        duplicates = set()
        
        for item in items:
            if item in seen:
                duplicates.add(item)
            else:
                seen.add(item)
        
        return {
            'has_duplicates': len(duplicates) > 0,
            'duplicates': list(duplicates),
            'unique_count': len(seen),
            'total_count': len(items),
            'duplicate_count': len(duplicates)
        }
    
    def calculate_contact_completeness(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall contact information completeness score"""
        scores = {
            'phone_score': 0.0,
            'email_score': 0.0,
            'address_score': 0.0,
            'timing_score': 0.0,
            'overall_score': 0.0
        }
        
        weights = {
            'phone': 0.3,
            'email': 0.25,
            'address': 0.35,
            'timing': 0.1
        }
        
        # Score phone numbers
        phones = contact_data.get('phones', [])
        if phones:
            valid_phones = sum(1 for phone in phones if self.validate_phone_number(phone)['is_valid'])
            scores['phone_score'] = (valid_phones / len(phones)) * 100
        
        # Score email addresses
        emails = contact_data.get('emails', [])
        if emails:
            valid_emails = sum(1 for email in emails if self.validate_email_address(email)['is_valid'])
            scores['email_score'] = (valid_emails / len(emails)) * 100
        
        # Score addresses
        head_office = contact_data.get('head_office', {})
        branches = contact_data.get('branches', [])
        
        address_scores = []
        if head_office.get('address'):
            addr_validation = self.validate_address(head_office['address'])
            address_scores.append(addr_validation['completeness_score'])
        
        for branch in branches:
            if branch.get('address'):
                addr_validation = self.validate_address(branch['address'])
                address_scores.append(addr_validation['completeness_score'])
        
        if address_scores:
            scores['address_score'] = sum(address_scores) / len(address_scores)
        
        # Score office timing
        timing = contact_data.get('office_timing', {})
        if timing:
            timing_validation = self.validate_office_timing(timing)
            scores['timing_score'] = 100.0 if timing_validation['is_valid'] else 50.0
        
        # Calculate overall score
        total_score = 0.0
        for category, weight in weights.items():
            score_key = f'{category}_score'
            total_score += scores[score_key] * weight
        
        scores['overall_score'] = round(total_score, 2)
        
        return scores
    
    def generate_validation_report(self, data: Dict[str, Any]) -> str:
        """Generate a detailed validation report"""
        report = []
        report.append("=" * 50)
        report.append("CONTACT INFORMATION VALIDATION REPORT")
        report.append("=" * 50)
        
        # Phone validation
        phones = data.get('contact_details', {}).get('phones', [])
        report.append(f"\n📞 PHONE NUMBERS ({len(phones)} found):")
        for phone in phones:
            validation = self.validate_phone_number(phone)
            status = "✅ VALID" if validation['is_valid'] else "❌ INVALID"
            report.append(f"  • {phone} - {status} ({validation['type']})")
            if validation['issues']:
                for issue in validation['issues']:
                    report.append(f"    - Issue: {issue}")
        
        # Email validation
        emails = data.get('contact_details', {}).get('emails', [])
        report.append(f"\n📧 EMAIL ADDRESSES ({len(emails)} found):")
        for email in emails:
            validation = self.validate_email_address(email)
            status = "✅ VALID" if validation['is_valid'] else "❌ INVALID"
            report.append(f"  • {email} - {status}")
            if validation['issues']:
                for issue in validation['issues']:
                    report.append(f"    - Issue: {issue}")
        
        # Calculate and display scores
        contact_data = data.get('contact_details', {})
        scores = self.calculate_contact_completeness(contact_data)
        
        report.append(f"\n📊 QUALITY SCORES:")
        report.append(f"  • Phone Numbers: {scores['phone_score']:.1f}%")
        report.append(f"  • Email Addresses: {scores['email_score']:.1f}%") 
        report.append(f"  • Addresses: {scores['address_score']:.1f}%")
        report.append(f"  • Office Timing: {scores['timing_score']:.1f}%")
        report.append(f"  • Overall Score: {scores['overall_score']:.1f}%")
        
        report.append("\n" + "=" * 50)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the contact validator
    validator = ContactValidator()
    
    # Test phone validation
    test_phones = ["+91-9434-74511", "+91-341-7963322", "+91-99999-99999"]
    for phone in test_phones:
        result = validator.validate_phone_number(phone)
        print(f"Phone {phone}: Valid={result['is_valid']}, Issues={result['issues']}")
    
    # Test email validation
    test_emails = ["asthainfrarealty@gmail.com", "invalid.email", "test@company.com"]
    for email in test_emails:
        result = validator.validate_email_address(email)
        print(f"Email {email}: Valid={result['is_valid']}, Issues={result['issues']}")
    
    # Test address validation
    test_address = {
        'full_address': 'Test Address, Asansol - 713304',
        'city': 'Asansol',
        'state': 'West Bengal',
        'pin_code': '713304'
    }
    result = validator.validate_address(test_address)
    print(f"Address completeness: {result['completeness_score']}%, Valid={result['is_valid']}")