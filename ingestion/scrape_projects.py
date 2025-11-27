"""
Scrape Projects Script for PropIntel

Main script to scrape all project pages from Astha Infra Realty website.
Handles SSL verification issues with curl fallback mechanism.
Saves raw scraped data to individual JSON files organized by category.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.scrapers.project_scraper import ProjectScraper
from ingestion.config.env_loader import get_config


class ProjectScraperRunner:
    """
    Main runner for project scraping with fallback mechanisms.
    
    Handles:
    - Reading URLs from input file
    - Scraping with requests (primary)
    - Curl fallback for SSL issues
    - Saving results to organized directory structure
    """
    
    def __init__(self, urls_file: str = "project-urls.txt"):
        """
        Initialize scraper runner.
        
        Args:
            urls_file: Path to file containing project URLs (one per line)
        """
        self.config = get_config()
        self.logger = self.config.get_logger()
        
        # Set up paths
        self.urls_file = urls_file
        self.output_dir = Path("data/raw/projects")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize scraper
        self.scraper = ProjectScraper()
        
        self.logger.info(f"ProjectScraperRunner initialized")
        self.logger.info(f"URLs file: {urls_file}")
        self.logger.info(f"Output directory: {self.output_dir}")
    
    def load_urls(self) -> List[tuple]:
        """
        Load project URLs from file with categories.
        
        File format:
        Upcoming:
        url1
        url2
        
        Running:
        url3
        
        Completed:
        url4
        
        Returns:
            List of tuples (full_url, category)
        """
        urls_with_categories = []
        base_url = self.config.get_website_base_url()
        current_category = None
        
        try:
            with open(self.urls_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Check if this is a category header (ends with colon)
                    if line.endswith(':') and line.count(':') == 1:
                        current_category = line.rstrip(':').lower()
                        self.logger.info(f"Reading {current_category} projects...")
                        continue
                    
                    # This is a URL (only process if we have a current category)
                    if current_category:
                        # Convert relative path to full URL
                        if line.startswith('http'):
                            full_url = line
                        else:
                            path = line.lstrip('/')
                            full_url = f"{base_url}/{path}"
                        
                        urls_with_categories.append((full_url, current_category))
                    else:
                        self.logger.warning(f"Skipping line without category: {line}")
            
            self.logger.info(f"Loaded {len(urls_with_categories)} URLs from {self.urls_file}")
            return urls_with_categories
            
        except FileNotFoundError:
            self.logger.error(f"URLs file not found: {self.urls_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading URLs: {e}")
            return []
    
    def scrape_with_curl_fallback(self, url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Scrape URL with curl fallback for SSL issues.
        
        Args:
            url: URL to scrape
            category: Project category (upcoming, running, completed)
            
        Returns:
            Scraped project data or None
        """
        # Try primary method (requests via ProjectScraper)
        self.logger.info(f"Attempting scrape with requests: {url}")
        project_data = self.scraper.scrape(url, category)
        
        if project_data:
            return project_data
        
        # Fallback to curl for SSL issues
        self.logger.warning(f"Primary scrape failed, trying curl fallback: {url}")
        return self._scrape_with_curl(url, category)
    
    def _scrape_with_curl(self, url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Scrape URL using curl command (SSL bypass).
        
        Args:
            url: URL to scrape
            category: Project category (upcoming, running, completed)
            
        Returns:
            Scraped project data or None
        """
        try:
            # Execute curl command with SSL verification disabled
            cmd = [
                'curl',
                '-k',  # Disable SSL verification
                '-L',  # Follow redirects
                '-s',  # Silent mode
                '--max-time', '30',  # Timeout
                url
            ]
            
            self.logger.debug(f"Executing curl command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35
            )
            
            if result.returncode != 0:
                self.logger.error(f"Curl failed with code {result.returncode}: {url}")
                return None
            
            # Parse the HTML with BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result.stdout, 'html.parser')
            
            # Extract project data using scraper's extraction methods
            project_data = self.scraper._extract_project_data(soup, url, category)
            
            if project_data:
                self.logger.info(f"Successfully scraped with curl: {url}")
                return project_data
            else:
                self.logger.error(f"Failed to extract data from curl response: {url}")
                return None
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Curl timeout for: {url}")
            return None
        except Exception as e:
            self.logger.error(f"Curl fallback error for {url}: {e}", exc_info=True)
            return None
    
    def get_output_path(self, project_data: Dict[str, Any]) -> Path:
        """
        Generate output file path based on project data.
        
        Args:
            project_data: Project data dictionary
            
        Returns:
            Path object for output file
        """
        category = project_data.get('category', 'unknown')
        name = project_data.get('project_name', project_data.get('name', 'unknown'))
        
        # Sanitize project name for filename
        safe_name = self._sanitize_filename(name)
        
        # Create category subdirectory
        category_dir = self.output_dir / category
        category_dir.mkdir(exist_ok=True)
        
        # Generate filename
        filename = f"{safe_name}.json"
        
        return category_dir / filename
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize string for use as filename.
        
        Args:
            name: Original name
            
        Returns:
            Safe filename string
        """
        # Replace spaces and special characters
        safe = name.lower()
        safe = safe.replace(' ', '_')
        safe = safe.replace('-', '_')
        
        # Remove non-alphanumeric characters (except underscore)
        safe = ''.join(c for c in safe if c.isalnum() or c == '_')
        
        # Limit length
        if len(safe) > 100:
            safe = safe[:100]
        
        return safe
    
    def save_project_data(self, project_data: Dict[str, Any]) -> bool:
        """
        Save project data to JSON file.
        
        Args:
            project_data: Project data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.get_output_path(project_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved project data to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving project data: {e}")
            return False
    
    def scrape_all(self) -> Dict[str, Any]:
        """
        Scrape all projects from URLs file.
        
        Returns:
            Summary statistics
        """
        # Load URLs with categories
        urls_with_categories = self.load_urls()
        
        if not urls_with_categories:
            self.logger.error("No URLs to scrape")
            return {"total": 0, "successful": 0, "failed": 0}
        
        # Track results
        stats = {
            "total": len(urls_with_categories),
            "successful": 0,
            "failed": 0,
            "by_category": {
                "upcoming": 0,
                "running": 0,
                "completed": 0
            },
            "failed_urls": []
        }
        
        self.logger.info(f"Starting scrape of {len(urls_with_categories)} project URLs")
        print(f"\n{'='*60}")
        print(f"SCRAPING {len(urls_with_categories)} PROJECT PAGES")
        print(f"{'='*60}\n")
        
        # Scrape each URL
        for i, (url, category) in enumerate(urls_with_categories, 1):
            print(f"[{i}/{len(urls_with_categories)}] Scraping: {url} ({category})")
            self.logger.info(f"Processing {i}/{len(urls_with_categories)}: {url} ({category})")
            
            # Scrape with fallback
            project_data = self.scrape_with_curl_fallback(url, category)
            
            if project_data:
                # Save to file
                if self.save_project_data(project_data):
                    stats["successful"] += 1
                    if category in stats["by_category"]:
                        stats["by_category"][category] += 1
                    
                    project_name = project_data.get('project_name', project_data.get('name', 'Unknown'))
                    print(f"  ✓ Success: {project_name} ({category})")
                else:
                    stats["failed"] += 1
                    stats["failed_urls"].append(url)
                print(f"  ✗ Failed to save: {url}")
            else:
                stats["failed"] += 1
                stats["failed_urls"].append(url)
                print(f"  ✗ Failed to scrape: {url}")
            
            # Progress update
            if i % 5 == 0 or i == len(urls_with_categories):
                print(f"\nProgress: {i}/{len(urls_with_categories)} processed")
                print(f"Success: {stats['successful']}, Failed: {stats['failed']}\n")
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETED")
        print(f"{'='*60}")
        print(f"Total URLs: {stats['total']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"\nBy Category:")
        for category, count in stats['by_category'].items():
            print(f"  {category.capitalize()}: {count}")
        
        if stats['failed_urls']:
            print(f"\nFailed URLs:")
            for url in stats['failed_urls']:
                print(f"  - {url}")
        
        print(f"\nRaw data saved to: {self.output_dir}")
        print(f"{'='*60}\n")
        
        self.logger.info(f"Scraping completed: {stats['successful']}/{stats['total']} successful")
        
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        if self.scraper:
            self.scraper.close()
        self.logger.info("ScraperRunner cleanup completed")


def main():
    """Main entry point."""
    runner = None
    
    try:
        # Initialize runner
        runner = ProjectScraperRunner()
        
        # Run scraping
        stats = runner.scrape_all()
        
        # Exit with appropriate code
        if stats['failed'] == 0:
            print("All projects scraped successfully!")
            return 0
        elif stats['successful'] > 0:
            print(f"Partially successful: {stats['failed']} URLs failed")
            return 1
        else:
            print("Scraping failed completely")
            return 2
            
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        return 130
    except Exception as e:
        print(f"\nFatal error: {e}")
        if runner:
            runner.logger.error(f"Fatal error in main: {e}", exc_info=True)
        return 1
    finally:
        if runner:
            runner.cleanup()


if __name__ == "__main__":
    import sys
    sys.exit(main())
