"""
Data Quality Scorer for PropIntel Data Cleaning Pipeline

This module provides comprehensive quality scoring for scraped real estate data,
evaluating completeness, accuracy, and business value of the extracted information.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
import json
import re


class DataQualityScorer:
    """Comprehensive data quality assessment for real estate company data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define quality thresholds
        self.thresholds = {
            'excellent': 90.0,
            'good': 75.0,
            'fair': 60.0,
            'poor': 40.0
        }
        
        # Define business value weights
        self.business_weights = {
            'company_info': 0.20,
            'contact_details': 0.35,
            'online_presence': 0.15,
            'business_details': 0.20,
            'content_quality': 0.10
        }
    
    def calculate_company_info_score(self, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Score company basic information completeness and quality"""
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'components': {},
            'issues': []
        }
        
        components = {
            'name': 25.0,        # Company name is critical
            'description': 20.0,  # Business description
            'welcome_message': 15.0,  # Welcome/about message
            'logo_url': 10.0,    # Brand presence
            'website_url': 10.0, # Official website
            'founded_year': 10.0, # Business establishment
            'type': 10.0         # Business type/category
        }
        
        total_score = 0.0
        
        for field, max_points in components.items():
            field_score = 0.0
            value = company_info.get(field)
            
            if value:
                if field == 'name':
                    # Company name should be meaningful
                    if len(str(value).strip()) >= 3:
                        field_score = max_points
                    else:
                        score_details['issues'].append(f"Company name too short: {value}")
                
                elif field == 'description':
                    # Description should be substantial
                    desc_length = len(str(value).strip())
                    if desc_length >= 100:
                        field_score = max_points
                    elif desc_length >= 50:
                        field_score = max_points * 0.7
                    elif desc_length >= 20:
                        field_score = max_points * 0.4
                    else:
                        score_details['issues'].append(f"Description too brief: {desc_length} chars")
                
                elif field == 'welcome_message':
                    # Welcome message quality
                    msg_length = len(str(value).strip())
                    if msg_length >= 50 and not self._contains_code_artifacts(value):
                        field_score = max_points
                    elif msg_length >= 20:
                        field_score = max_points * 0.6
                    else:
                        score_details['issues'].append(f"Welcome message quality issues")
                
                elif field == 'logo_url':
                    # Check if logo URL is valid
                    if self._is_valid_url(value):
                        field_score = max_points
                    else:
                        score_details['issues'].append(f"Invalid logo URL: {value}")
                
                elif field == 'website_url':
                    # Check if website URL is valid
                    if self._is_valid_url(value):
                        field_score = max_points
                    else:
                        score_details['issues'].append(f"Invalid website URL: {value}")
                
                elif field == 'founded_year':
                    # Check if founded year is reasonable
                    try:
                        year = int(value)
                        current_year = datetime.now().year
                        if 1900 <= year <= current_year:
                            field_score = max_points
                        else:
                            score_details['issues'].append(f"Unrealistic founded year: {year}")
                    except (ValueError, TypeError):
                        score_details['issues'].append(f"Invalid founded year format: {value}")
                
                else:  # type and other fields
                    field_score = max_points
            else:
                score_details['issues'].append(f"Missing {field}")
            
            score_details['components'][field] = {
                'score': field_score,
                'max_score': max_points,
                'percentage': round((field_score / max_points) * 100, 1) if max_points > 0 else 0
            }
            total_score += field_score
        
        score_details['score'] = round(total_score, 2)
        return score_details
    
    def calculate_contact_details_score(self, contact_details: Dict[str, Any]) -> Dict[str, Any]:
        """Score contact information quality and completeness"""
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'components': {},
            'issues': []
        }
        
        components = {
            'phones': 30.0,
            'emails': 25.0,
            'head_office': 20.0,
            'branches': 15.0,
            'office_timing': 10.0
        }
        
        total_score = 0.0
        
        for field, max_points in components.items():
            field_score = 0.0
            value = contact_details.get(field)
            
            if field == 'phones':
                phones = value if isinstance(value, list) else []
                if phones:
                    valid_phones = sum(1 for phone in phones if self._is_valid_phone_format(phone))
                    field_score = (valid_phones / len(phones)) * max_points
                    if valid_phones < len(phones):
                        score_details['issues'].append(f"Invalid phone numbers found: {len(phones) - valid_phones}")
                else:
                    score_details['issues'].append("No phone numbers found")
            
            elif field == 'emails':
                emails = value if isinstance(value, list) else []
                if emails:
                    valid_emails = sum(1 for email in emails if self._is_valid_email_format(email))
                    field_score = (valid_emails / len(emails)) * max_points
                    if valid_emails < len(emails):
                        score_details['issues'].append(f"Invalid email addresses found: {len(emails) - valid_emails}")
                else:
                    score_details['issues'].append("No email addresses found")
            
            elif field == 'head_office':
                if value and isinstance(value, dict):
                    # Score based on address completeness
                    address = value.get('address', {})
                    if address:
                        completeness = self._calculate_address_completeness(address)
                        field_score = (completeness / 100.0) * max_points
                        if completeness < 70:
                            score_details['issues'].append(f"Incomplete head office address: {completeness}%")
                    else:
                        score_details['issues'].append("Head office address missing")
                else:
                    score_details['issues'].append("Head office information missing")
            
            elif field == 'branches':
                if value and isinstance(value, list):
                    if len(value) > 0:
                        # Score based on branch information quality
                        complete_branches = sum(1 for branch in value 
                                              if branch.get('address') and 
                                              self._calculate_address_completeness(branch.get('address', {})) >= 50)
                        field_score = (complete_branches / len(value)) * max_points
                        if complete_branches < len(value):
                            score_details['issues'].append(f"Incomplete branch information: {len(value) - complete_branches} branches")
                    else:
                        field_score = max_points * 0.5  # No branches is okay for some businesses
                else:
                    field_score = max_points * 0.5
            
            elif field == 'office_timing':
                if value and isinstance(value, dict):
                    if value.get('days') and value.get('hours'):
                        field_score = max_points
                    else:
                        field_score = max_points * 0.5
                        score_details['issues'].append("Incomplete office timing information")
                else:
                    score_details['issues'].append("Office timing not available")
            
            score_details['components'][field] = {
                'score': field_score,
                'max_score': max_points,
                'percentage': round((field_score / max_points) * 100, 1) if max_points > 0 else 0
            }
            total_score += field_score
        
        score_details['score'] = round(total_score, 2)
        return score_details
    
    def calculate_online_presence_score(self, online_presence: Dict[str, Any]) -> Dict[str, Any]:
        """Score online presence and digital footprint"""
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'components': {},
            'issues': []
        }
        
        components = {
            'website': 40.0,
            'social_media': 35.0,
            'business_listings': 25.0
        }
        
        total_score = 0.0
        
        # Website presence
        website_score = 0.0
        website_url = online_presence.get('website_url', '')
        if website_url and self._is_valid_url(website_url):
            website_score = components['website']
        else:
            score_details['issues'].append("No valid website URL")
        
        # Social media presence
        social_media_score = 0.0
        social_media = online_presence.get('social_media', {})
        if social_media:
            valid_profiles = sum(1 for platform, url in social_media.items() 
                               if url and self._is_valid_url(url))
            if valid_profiles > 0:
                # Score based on number of platforms (max 4 platforms for full score)
                social_media_score = min((valid_profiles / 4.0), 1.0) * components['social_media']
            else:
                score_details['issues'].append("No valid social media profiles")
        else:
            score_details['issues'].append("No social media presence")
        
        # Business listings (assumed to be evaluated separately)
        listings_score = components['business_listings'] * 0.5  # Default moderate score
        
        score_details['components']['website'] = {
            'score': website_score,
            'max_score': components['website'],
            'percentage': round((website_score / components['website']) * 100, 1)
        }
        
        score_details['components']['social_media'] = {
            'score': social_media_score,
            'max_score': components['social_media'],
            'percentage': round((social_media_score / components['social_media']) * 100, 1)
        }
        
        score_details['components']['business_listings'] = {
            'score': listings_score,
            'max_score': components['business_listings'],
            'percentage': round((listings_score / components['business_listings']) * 100, 1)
        }
        
        total_score = website_score + social_media_score + listings_score
        score_details['score'] = round(total_score, 2)
        
        return score_details
    
    def calculate_business_details_score(self, business_details: Dict[str, Any]) -> Dict[str, Any]:
        """Score business-specific information"""
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'components': {},
            'issues': []
        }
        
        # For real estate companies, we expect certain business details
        components = {
            'services': 30.0,      # What services they offer
            'experience': 25.0,    # Years of experience
            'specialization': 20.0, # Areas of specialization
            'certifications': 15.0, # Professional certifications
            'team_size': 10.0      # Company size indicator
        }
        
        total_score = 0.0
        
        # For now, give moderate scores as business details extraction
        # is not fully implemented in the current scraper
        for field, max_points in components.items():
            field_score = max_points * 0.6  # 60% score for existing data
            score_details['components'][field] = {
                'score': field_score,
                'max_score': max_points,
                'percentage': 60.0
            }
            total_score += field_score
        
        score_details['score'] = round(total_score, 2)
        score_details['issues'].append("Business details scoring needs specialized extraction")
        
        return score_details
    
    def calculate_content_quality_score(self, full_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score overall content quality and coherence"""
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'components': {},
            'issues': []
        }
        
        components = {
            'data_consistency': 40.0,
            'content_completeness': 35.0,
            'text_quality': 25.0
        }
        
        total_score = 0.0
        
        # Data consistency check
        consistency_score = self._check_data_consistency(full_data)
        score_details['components']['data_consistency'] = {
            'score': consistency_score * components['data_consistency'] / 100,
            'max_score': components['data_consistency'],
            'percentage': consistency_score
        }
        
        # Content completeness
        completeness_score = self._check_content_completeness(full_data)
        score_details['components']['content_completeness'] = {
            'score': completeness_score * components['content_completeness'] / 100,
            'max_score': components['content_completeness'],
            'percentage': completeness_score
        }
        
        # Text quality
        text_quality_score = self._check_text_quality(full_data)
        score_details['components']['text_quality'] = {
            'score': text_quality_score * components['text_quality'] / 100,
            'max_score': components['text_quality'],
            'percentage': text_quality_score
        }
        
        for component_data in score_details['components'].values():
            total_score += component_data['score']
        
        score_details['score'] = round(total_score, 2)
        
        return score_details
    
    def calculate_overall_quality_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive quality score for the entire dataset"""
        overall_result = {
            'overall_score': 0.0,
            'quality_grade': '',
            'component_scores': {},
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Calculate component scores
        company_score = self.calculate_company_info_score(data.get('company_info', {}))
        contact_score = self.calculate_contact_details_score(data.get('contact_details', {}))
        online_score = self.calculate_online_presence_score(data.get('online_presence', {}))
        business_score = self.calculate_business_details_score(data.get('business_details', {}))
        content_score = self.calculate_content_quality_score(data)
        
        # Store component scores
        overall_result['component_scores'] = {
            'company_info': company_score,
            'contact_details': contact_score,
            'online_presence': online_score,
            'business_details': business_score,
            'content_quality': content_score
        }
        
        # Calculate weighted overall score
        weighted_score = 0.0
        for component, weight in self.business_weights.items():
            component_score = overall_result['component_scores'][component]['score']
            weighted_score += (component_score * weight)
        
        overall_result['overall_score'] = round(weighted_score, 2)
        
        # Assign quality grade
        if overall_result['overall_score'] >= self.thresholds['excellent']:
            overall_result['quality_grade'] = 'Excellent'
        elif overall_result['overall_score'] >= self.thresholds['good']:
            overall_result['quality_grade'] = 'Good'
        elif overall_result['overall_score'] >= self.thresholds['fair']:
            overall_result['quality_grade'] = 'Fair'
        elif overall_result['overall_score'] >= self.thresholds['poor']:
            overall_result['quality_grade'] = 'Poor'
        else:
            overall_result['quality_grade'] = 'Very Poor'
        
        # Generate recommendations
        overall_result['recommendations'] = self._generate_recommendations(overall_result['component_scores'])
        
        return overall_result
    
    # Helper methods
    def _contains_code_artifacts(self, text: str) -> bool:
        """Check if text contains CSS/JS/HTML artifacts"""
        code_patterns = [
            r'function\s*\(',
            r'\.css\s*\{',
            r'<[^>]+>',
            r'jQuery|javascript|console\.log',
            r'\$\(["\']',
            r'document\.',
            r'\.addClass|\.removeClass'
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, str(text), re.IGNORECASE):
                return True
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation"""
        if not url:
            return False
        return bool(re.match(r'https?://[^\s]+', url))
    
    def _is_valid_phone_format(self, phone: str) -> bool:
        """Basic phone format validation"""
        if not phone:
            return False
        return bool(re.match(r'^\+91-\d{2,4}-\d{7,8}$', phone))
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation"""
        if not email:
            return False
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
    
    def _calculate_address_completeness(self, address: Dict[str, str]) -> float:
        """Calculate address completeness percentage"""
        if not address:
            return 0.0
        
        required_fields = ['full_address', 'city', 'state', 'pin_code']
        present_fields = sum(1 for field in required_fields if address.get(field))
        return (present_fields / len(required_fields)) * 100
    
    def _check_data_consistency(self, data: Dict[str, Any]) -> float:
        """Check consistency across different data sections"""
        consistency_score = 100.0
        
        # Check if company name is consistent
        company_name = data.get('company_info', {}).get('name', '')
        
        # More consistency checks can be added here
        
        return consistency_score
    
    def _check_content_completeness(self, data: Dict[str, Any]) -> float:
        """Check overall content completeness"""
        main_sections = ['company_info', 'contact_details', 'online_presence']
        present_sections = sum(1 for section in main_sections if data.get(section))
        return (present_sections / len(main_sections)) * 100
    
    def _check_text_quality(self, data: Dict[str, Any]) -> float:
        """Check quality of text content"""
        # Check welcome message quality
        welcome_msg = data.get('company_info', {}).get('welcome_message', '')
        if welcome_msg and not self._contains_code_artifacts(welcome_msg):
            return 85.0
        elif welcome_msg:
            return 60.0
        else:
            return 40.0
    
    def _generate_recommendations(self, component_scores: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations based on scores"""
        recommendations = []
        
        for component, score_data in component_scores.items():
            score = score_data['score']
            max_score = score_data['max_score']
            percentage = (score / max_score) * 100 if max_score > 0 else 0
            
            if percentage < 60:
                if component == 'company_info':
                    recommendations.append("Improve company information completeness - add missing description, logo, or founding details")
                elif component == 'contact_details':
                    recommendations.append("Enhance contact information - verify phone numbers and email addresses")
                elif component == 'online_presence':
                    recommendations.append("Strengthen online presence - add social media profiles and business listings")
                elif component == 'business_details':
                    recommendations.append("Add business-specific details - services, specializations, and certifications")
                elif component == 'content_quality':
                    recommendations.append("Improve content quality - remove technical artifacts and ensure consistency")
        
        if not recommendations:
            recommendations.append("Data quality is good - continue monitoring and maintaining current standards")
        
        return recommendations
    
    def generate_quality_report(self, data: Dict[str, Any]) -> str:
        """Generate a comprehensive quality report"""
        quality_result = self.calculate_overall_quality_score(data)
        
        report = []
        report.append("=" * 60)
        report.append("DATA QUALITY ASSESSMENT REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Overall Score: {quality_result['overall_score']:.1f}/100")
        report.append(f"Quality Grade: {quality_result['quality_grade']}")
        report.append("")
        
        # Component breakdown
        report.append("COMPONENT SCORES:")
        report.append("-" * 30)
        for component, score_data in quality_result['component_scores'].items():
            score = score_data['score']
            max_score = score_data['max_score']
            percentage = (score / max_score) * 100 if max_score > 0 else 0
            component_name = component.replace('_', ' ').title()
            report.append(f"{component_name:<20}: {score:5.1f}/{max_score} ({percentage:5.1f}%)")
        
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 30)
        for i, rec in enumerate(quality_result['recommendations'], 1):
            report.append(f"{i}. {rec}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the quality scorer
    scorer = DataQualityScorer()
    
    # Sample data for testing
    test_data = {
        'company_info': {
            'name': 'Astha Infra Realty',
            'description': 'Leading real estate company in West Bengal',
            'welcome_message': 'Welcome to our real estate services',
            'website_url': 'https://example.com'
        },
        'contact_details': {
            'phones': ['+91-9434-74511'],
            'emails': ['info@astha.com'],
            'head_office': {
                'address': {
                    'full_address': 'Test Address',
                    'city': 'Asansol',
                    'state': 'West Bengal', 
                    'pin_code': '713304'
                }
            }
        },
        'online_presence': {
            'website_url': 'https://example.com',
            'social_media': {
                'facebook': 'https://facebook.com/company'
            }
        }
    }
    
    result = scorer.calculate_overall_quality_score(test_data)
    print(f"Overall Score: {result['overall_score']}")
    print(f"Quality Grade: {result['quality_grade']}")
    
    # Generate full report
    report = scorer.generate_quality_report(test_data)
    print(report)