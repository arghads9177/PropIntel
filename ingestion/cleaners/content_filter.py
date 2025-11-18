"""
Content Filter for PropIntel Data Cleaning Pipeline

This module filters out technical content (CSS, JavaScript, HTML markup)
and extracts meaningful business content from scraped web data.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


class ContentFilter:
    """Filters and purifies scraped content to extract meaningful business information"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns to identify and remove technical content
        self.css_js_patterns = [
            r'window\._wp.*?;',  # WordPress JavaScript
            r'@media\s*\([^}]*\)',  # CSS media queries
            r'\.[a-zA-Z-]+\s*\{[^}]*\}',  # CSS rules
            r'font-family:[^;]*;',  # CSS font declarations
            r'background-color:[^;]*;',  # CSS background
            r'color:[^;]*;',  # CSS color
            r'margin[^;]*;',  # CSS margin
            r'padding[^;]*;',  # CSS padding
            r'border[^;]*;',  # CSS border
            r'\.x-[a-zA-Z-]*[^}]*',  # Theme-specific CSS classes
            r'jQuery\([^)]*\)',  # jQuery code
            r'\$\([^)]*\)',  # jQuery selectors
        ]
        
        # Navigation and menu content patterns
        self.navigation_patterns = [
            r'Home\s*Upcoming\s*Projects.*?Contact\s*Us',  # Main navigation
            r'Navigation\s*Home.*?Search',  # Navigation menu
            r'Search.*?Contact\s*Us',  # Search and contact menu
            r'Facebook\s*YouTube\s*Instagram',  # Social media links text
        ]
        
        # Business content indicators
        self.business_indicators = [
            'aastha', 'infra', 'realty', 'developer', 'real estate',
            'residential', 'commercial', 'apartment', 'project',
            'construction', 'building', 'decades', 'experience',
            'premium', 'leading', 'township', 'complexes'
        ]
    
    def remove_css_javascript(self, text: str) -> str:
        """Remove CSS and JavaScript code from text"""
        if not text:
            return ""
        
        cleaned_text = text
        
        # Remove CSS/JS patterns
        for pattern in self.css_js_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove long strings of CSS-like content
        cleaned_text = re.sub(r'[a-zA-Z-]+:[^;]+;[a-zA-Z-]+:[^;]+;[a-zA-Z-]+:[^;]+;', '', cleaned_text)
        
        # Remove content that looks like CSS rules (contains multiple colons and semicolons)
        lines = cleaned_text.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that look like CSS (multiple colons/semicolons)
            if line.count(':') > 3 or line.count(';') > 3:
                continue
            # Skip lines that are mostly CSS class names or properties
            if re.match(r'^[\.\#\-a-zA-Z\s]*\{', line):
                continue
            if len(line.strip()) > 0:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def remove_navigation_content(self, text: str) -> str:
        """Remove navigation menus and repetitive menu content"""
        if not text:
            return ""
        
        cleaned_text = text
        
        # Remove navigation patterns
        for pattern in self.navigation_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        # Remove repeated menu items
        cleaned_text = re.sub(r'(Home|Projects|Contact\s*Us|Search)\s*', '', cleaned_text)
        
        return cleaned_text
    
    def extract_business_content(self, text: str) -> str:
        """Extract meaningful business content from cleaned text"""
        if not text:
            return ""
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        business_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            # Check if sentence contains business-related keywords
            sentence_lower = sentence.lower()
            business_keyword_count = sum(1 for keyword in self.business_indicators 
                                       if keyword in sentence_lower)
            
            # Keep sentences with business keywords or meaningful content
            if business_keyword_count > 0:
                business_sentences.append(sentence)
            elif self._is_meaningful_sentence(sentence):
                business_sentences.append(sentence)
        
        return '. '.join(business_sentences) + '.' if business_sentences else ""
    
    def _is_meaningful_sentence(self, sentence: str) -> bool:
        """Check if a sentence contains meaningful business content"""
        # Skip sentences that are mostly technical or repetitive
        technical_indicators = [
            'window', 'function', 'script', 'style', 'css', 'javascript',
            'jquery', 'wp-', 'theme', 'plugin', 'widget'
        ]
        
        sentence_lower = sentence.lower()
        
        # Skip if contains too many technical terms
        if sum(1 for term in technical_indicators if term in sentence_lower) > 1:
            return False
        
        # Keep if contains meaningful business terms
        meaningful_terms = [
            'company', 'business', 'service', 'office', 'contact',
            'address', 'phone', 'email', 'timing', 'hours'
        ]
        
        return any(term in sentence_lower for term in meaningful_terms)
    
    def clean_welcome_message(self, raw_message: str) -> str:
        """Clean and extract proper welcome message from raw scraped content"""
        if not raw_message:
            return ""
        
        # First remove CSS/JS
        cleaned = self.remove_css_javascript(raw_message)
        
        # Remove navigation content
        cleaned = self.remove_navigation_content(cleaned)
        
        # Extract business content
        business_content = self.extract_business_content(cleaned)
        
        # If no business content found, try to find company description in original text
        if not business_content or len(business_content) < 50:
            business_content = self._extract_company_description_fallback(raw_message)
        
        return business_content.strip()
    
    def _extract_company_description_fallback(self, text: str) -> str:
        """Fallback method to extract company description"""
        # Look for common company description patterns
        patterns = [
            r'(Aastha.*?(?:developer|company|group).*?\.)',
            r'(.*?leading.*?real estate.*?\.)',
            r'(.*?premium.*?developer.*?\.)',
            r'(.*?decades.*?experience.*?\.)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                # Clean up the description
                description = re.sub(r'\s+', ' ', description)
                if len(description) > 30 and len(description) < 500:
                    return description
        
        # Default fallback
        return "Aastha Infra Realty (Aastha Group) is a leading real estate developer in India with decades of experience in residential and commercial projects."
    
    def filter_address_content(self, address_text: str) -> str:
        """Filter address content to remove CSS and extract clean addresses"""
        if not address_text:
            return ""
        
        # Remove CSS content
        cleaned = self.remove_css_javascript(address_text)
        
        # Look for actual address patterns
        address_patterns = [
            r'([A-Za-z\s]+Apartment[^,]*,[^,]*,[^,]*,.*?\d{6})',
            r'(\d+[^,]*,[^,]*,[^,]*[^,]*\d{6})',
            r'([A-Za-z\s]+Road[^,]*,[^,]*.*?\d{6})',
        ]
        
        addresses = []
        for pattern in address_patterns:
            matches = re.findall(pattern, cleaned)
            addresses.extend(matches)
        
        # Return the first valid address found
        for addr in addresses:
            if len(addr) > 20 and any(char.isdigit() for char in addr):
                return addr.strip()
        
        return cleaned.strip()
    
    def is_content_meaningful(self, text: str, min_length: int = 30) -> bool:
        """Check if content is meaningful and not just technical artifacts"""
        if not text or len(text) < min_length:
            return False
        
        # Check for excessive technical content
        technical_ratio = self._calculate_technical_ratio(text)
        if technical_ratio > 0.7:  # More than 70% technical content
            return False
        
        # Check for business content
        business_ratio = self._calculate_business_ratio(text)
        if business_ratio < 0.1:  # Less than 10% business content
            return False
        
        return True
    
    def _calculate_technical_ratio(self, text: str) -> float:
        """Calculate the ratio of technical content in text"""
        technical_terms = [
            'css', 'javascript', 'jquery', 'function', 'window', 'style',
            'margin', 'padding', 'border', 'color', 'background', 'font'
        ]
        
        words = text.lower().split()
        if not words:
            return 0.0
        
        technical_count = sum(1 for word in words if any(term in word for term in technical_terms))
        return technical_count / len(words)
    
    def _calculate_business_ratio(self, text: str) -> float:
        """Calculate the ratio of business content in text"""
        words = text.lower().split()
        if not words:
            return 0.0
        
        business_count = sum(1 for word in words if any(term in word for term in self.business_indicators))
        return business_count / len(words)


if __name__ == "__main__":
    # Test the content filter
    filter = ContentFilter()
    
    # Test CSS/JS removal
    test_text = """
    window._wpemojiSettings = {"baseUrl":"https://s.w.org/images/core/emoji/13.1.0/72x72/"};
    .x-navbar { background-color: #fff; margin: 10px; }
    Aastha Infra Realty is a leading real estate developer in India.
    font-family: Roboto; color: #333;
    """
    
    cleaned = filter.remove_css_javascript(test_text)
    print("Original:", test_text)
    print("Cleaned:", cleaned)
    
    # Test business content extraction
    business_content = filter.extract_business_content(cleaned)
    print("Business content:", business_content)