"""
Project Scraper for PropIntel

This module scrapes individual project pages from Astha Infra Realty website.
Extracts project information including name, location, property details, etc.
"""

import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from .base_scraper import BaseScraper


class ProjectScraper(BaseScraper):
    """
    Scraper for individual project pages.
    
    Handles three types of project page structures:
    1. Upcoming projects: Minimal format (name, place, developed_by)
    2. Running projects: Standard format (about, location, developer, floors)
    3. Completed projects: Enhanced format (includes address, contact, marketed_by)
    """
    
    def __init__(self):
        """Initialize project scraper."""
        super().__init__()
        self.logger.info("ProjectScraper initialized")
    
    def scrape(self, url: str, category: str = None) -> Optional[Dict[str, Any]]:
        """
        Scrape a single project page.
        
        Args:
            url: URL of the project page to scrape
            category: Project category (upcoming, running, completed). If None, will extract from URL.
            
        Returns:
            Dictionary containing project data or None if scraping failed
        """
        self.logger.info(f"Scraping project from: {url}")
        
        # Get page content
        soup = self.get_page(url)
        if not soup:
            self.logger.error(f"Failed to fetch page: {url}")
            return None
        
        try:
            # Extract project data
            project_data = self._extract_project_data(soup, url, category)
            
            if not project_data:
                self.logger.warning(f"No project data extracted from: {url}")
                return None
            
            self.logger.info(f"Successfully scraped project: {project_data.get('name', 'Unknown')}")
            return project_data
            
        except Exception as e:
            self.logger.error(f"Error extracting project data from {url}: {e}", exc_info=True)
            return None
    
    def _extract_project_data(self, soup: BeautifulSoup, url: str, category: str = None) -> Optional[Dict[str, Any]]:
        """
        Extract project data from parsed HTML.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page (for reference)
            category: Project category (upcoming, running, completed). If None, will extract from URL.
            
        Returns:
            Dictionary with project information in format:
            {project_name, location, number_of_floors, developed_by, category}
        """
        # Extract project name
        project_name = self._extract_project_name(soup)
        if not project_name:
            self.logger.warning(f"Could not extract project name from: {url}")
            return None
        
        # Extract table fields (Location, Developed By, Type Of Floor, etc.)
        table_fields = self._extract_table_fields(soup)
        
        # Build the required JSON structure
        project_data = {
            "project_name": project_name,
            "location": table_fields.get("Location", ""),
            "number_of_floors": table_fields.get("Type Of Floor", table_fields.get("Type Of Stores", "")),
            "developed_by": table_fields.get("Developed By", ""),
            "category": category if category else self._extract_category(url)
        }
        
        return project_data
    
    def _extract_table_fields(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract fields from HTML table structure.
        
        Tables have format:
        <table>
          <tr>
            <td><b>Label</b></td>
            <td>Value</td>
          </tr>
        </table>
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary of field_name: field_value
        """
        fields = {}
        
        # Find all tables
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                
                # Need at least 2 cells (label and value)
                if len(cells) >= 2:
                    # First cell should contain the label (usually in <b> tag)
                    label_cell = cells[0]
                    value_cell = cells[1]
                    
                    # Extract label (look for <b> tag first)
                    label_tag = label_cell.find('b')
                    if label_tag:
                        label = label_tag.get_text(strip=True).rstrip(':').strip()
                    else:
                        label = label_cell.get_text(strip=True).rstrip(':').strip()
                    
                    # Extract value and clean leading colons
                    value = value_cell.get_text(strip=True).lstrip(':').strip()
                    
                    # Store if both label and value exist
                    if label and value:
                        fields[label] = value
        
        return fields
    
    def _extract_category(self, url: str) -> str:
        """
        Extract project category from URL.
        
        Args:
            url: Project page URL
            
        Returns:
            Category string (upcoming, running, or completed)
        """
        url_lower = url.lower()
        
        # Check for category in URL path
        if 'upcoming' in url_lower or '/dev-apartment/' in url_lower or '/omkar-apartment/' in url_lower:
            return "upcoming"
        elif 'running' in url_lower or any(block in url_lower for block in ['kabi-tirtha', 'elina-tower', 'olivia-enclave', 'satsang-g']):
            return "running"
        elif 'completed' in url_lower or '/projects/' in url_lower or any(name in url_lower for name in ['nilachal', 'aastha-apartment', 'shivalaya', 'ashirwad', 'alaknanda', 'rajdeep', 'geetanjali']):
            return "completed"
        else:
            self.logger.warning(f"Unknown category for URL: {url}")
            return "unknown"
    
    def _extract_project_name(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract project name from page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Project name or None
        """
        # Strategy 1: Look for h2 with specific classes (project name header)
        h2_headline = soup.find('h2', class_='h-custom-headline')
        if h2_headline:
            span = h2_headline.find('span')
            if span:
                name = span.get_text(strip=True)
                # Check if it's actually a project name (not "About Property", "Coming Soon", etc.)
                if name and name not in ['About Property', 'Property Enquiry', 'Coming Soon', 'Typical-floor Plan', 'Ground Floor Plan']:
                    return name
        
        # Strategy 2: Look for title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Extract project name from title (format: "Project Name - Astha Infra Realty")
            if ' - ' in title_text:
                project_name = title_text.split(' - ')[0].strip()
                if project_name and project_name != "Astha Infra Realty Ltd.":
                    return project_name
        
        # Strategy 3: Look for strong tags with project names (for upcoming projects)
        strong_tags = soup.find_all('strong')
        for strong in strong_tags:
            text = strong.get_text(strip=True)
            # Skip company name, common labels, and field labels
            if text and text != "Astha Infra Realty Ltd." and ':' not in text and len(text) > 3:
                # Check if it looks like a project name (not a field label)
                if not any(label in text.lower() for label in ['about', 'location', 'developed', 'type of', 'contact', 'marketed', 'place', 'construction']):
                    return text
        
        # Strategy 4: Look for h1 tag
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
            if name and name != "Astha Infra Realty Ltd.":
                return name
        
        return None
    
    def _extract_property_fields(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract all property information fields from the page.
        
        Handles various field formats:
        - "About Property" section (multi-line text)
        - Key-value pairs like "Location : Address"
        - Fields with or without colons
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary of field_name: field_value
        """
        fields = {}
        
        # Strategy 1: Look for structured field containers (p tags with strong labels)
        p_tags = soup.find_all('p')
        
        for p in p_tags:
            # Check if this is a field with a label
            strong = p.find('strong')
            if strong:
                label = strong.get_text(strip=True)
                
                # Remove trailing colon if present
                label = label.rstrip(':').strip()
                
                # Skip empty labels
                if not label:
                    continue
                
                # Handle "About Property" section (multi-line)
                if label.lower() == "about property":
                    # Get all text after the strong tag
                    value = self._extract_multiline_value(p, strong)
                    if value:
                        fields[label] = value
                else:
                    # Single line field (extract text after the label)
                    value = self._extract_single_line_value(p, strong)
                    if value:
                        fields[label] = value
        
        # Strategy 2: Look for text patterns without strong tags (fallback)
        # Some pages might have simpler formatting
        if not fields:
            fields = self._extract_fields_from_text(soup)
        
        return fields
    
    def _extract_multiline_value(self, p_tag: Tag, label_tag: Tag) -> Optional[str]:
        """
        Extract multi-line field value (e.g., "About Property").
        
        Args:
            p_tag: Parent p tag
            label_tag: Strong tag containing the label
            
        Returns:
            Multi-line value or None
        """
        # Get all text content of the p tag
        full_text = p_tag.get_text(separator='\n', strip=True)
        
        # Remove the label from the beginning
        label_text = label_tag.get_text(strip=True).rstrip(':').strip()
        
        # Split by newlines and filter out the label line
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        
        # Find where the label appears and take everything after
        value_lines = []
        found_label = False
        
        for line in lines:
            if label_text in line and not found_label:
                found_label = True
                # Check if there's text after the label on the same line
                remainder = line.replace(label_text, '').strip().lstrip(':').strip()
                if remainder:
                    value_lines.append(remainder)
            elif found_label:
                value_lines.append(line)
        
        # Join the lines
        value = '\n'.join(value_lines)
        
        return value if value else None
    
    def _extract_single_line_value(self, p_tag: Tag, label_tag: Tag) -> Optional[str]:
        """
        Extract single-line field value.
        
        Args:
            p_tag: Parent p tag
            label_tag: Strong tag containing the label
            
        Returns:
            Single-line value or None
        """
        # Get all text from p tag
        full_text = p_tag.get_text(separator=' ', strip=True)
        
        # Get label text
        label_text = label_tag.get_text(strip=True).rstrip(':').strip()
        
        # Try to extract value after the label
        # Pattern: "Label : Value" or "Label Value"
        if ':' in full_text:
            # Split by first occurrence of label
            if label_text in full_text:
                parts = full_text.split(label_text, 1)
                if len(parts) > 1:
                    value = parts[1].strip().lstrip(':').strip()
                    return value if value else None
        else:
            # No colon, just remove the label
            value = full_text.replace(label_text, '').strip()
            return value if value else None
        
        return None
    
    def _extract_fields_from_text(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Fallback method: Extract fields from raw text patterns.
        
        Used when structured extraction fails.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary of fields
        """
        fields = {}
        
        # Get all text content
        text_content = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        # Look for patterns like "Label: Value" or "Label : Value"
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Filter out common non-field patterns
                    if label and value and len(label) < 50:
                        fields[label] = value
        
        return fields
    
    def scrape_multiple(self, urls: list) -> Dict[str, Dict[str, Any]]:
        """
        Scrape multiple project pages.
        
        Args:
            urls: List of project page URLs
            
        Returns:
            Dictionary mapping URL to project data
        """
        results = {}
        
        self.logger.info(f"Starting batch scrape of {len(urls)} projects")
        
        for i, url in enumerate(urls, 1):
            self.logger.info(f"Processing {i}/{len(urls)}: {url}")
            
            project_data = self.scrape(url)
            
            if project_data:
                results[url] = project_data
            else:
                self.logger.warning(f"Failed to scrape: {url}")
            
            # Progress update every 5 URLs
            if i % 5 == 0:
                self.logger.info(f"Progress: {i}/{len(urls)} projects processed")
        
        self.logger.info(f"Batch scrape completed: {len(results)}/{len(urls)} successful")
        return results


if __name__ == "__main__":
    # Test the scraper
    scraper = ProjectScraper()
    
    # Test with a sample URL
    test_url = "https://www.asthainfrarealty.com/completed-projects/nilachal-apartment/"
    result = scraper.scrape(test_url)
    
    if result:
        print(f"\nProject: {result['name']}")
        print(f"Category: {result['category']}")
        print(f"Fields found: {len(result['fields'])}")
        print("\nField details:")
        for key, value in result['fields'].items():
            print(f"  {key}: {value[:100] if len(value) > 100 else value}")
    else:
        print("Scraping failed")
    
    scraper.close()
