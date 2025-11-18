"""
Environment Configuration Loader for PropIntel Web Scraper

This module handles loading and validating environment variables
for the web scraping pipeline.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path


class EnvironmentConfig:
    """
    Manages environment configuration for the PropIntel scraper.
    Loads variables from .env file and provides validation.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize environment configuration.
        
        Args:
            env_file: Path to .env file. If None, looks for .env in project root.
        """
        self.env_file = env_file or self._find_env_file()
        self.config = {}
        self._load_environment()
        self._setup_logging()
    
    def _find_env_file(self) -> str:
        """Find .env file in project root."""
        current_dir = Path(__file__).resolve()
        
        # Navigate up to find project root (where .env should be)
        for parent in current_dir.parents:
            env_path = parent / '.env'
            if env_path.exists():
                return str(env_path)
        
        # Default to current directory
        return '.env'
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        load_dotenv(self.env_file)
        
        # Load all required configuration
        self.config = {
            # Website Configuration
            'website_base_url': os.getenv('WEBSITE_BASE_URL', 'https://asthainfrarealty.com/'),
            
            # Scraping Configuration
            'scraper_rate_limit': float(os.getenv('SCRAPER_RATE_LIMIT', '2.0')),
            'scraper_timeout': int(os.getenv('SCRAPER_TIMEOUT', '30')),
            'scraper_max_retries': int(os.getenv('SCRAPER_MAX_RETRIES', '3')),
            
            # Logging Configuration
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_file_path': os.getenv('LOG_FILE_PATH', './logs/propintel.log'),
            
            # Storage Configuration
            'raw_data_path': os.getenv('RAW_DATA_PATH', './data/raw'),
            'processed_data_path': os.getenv('PROCESSED_DATA_PATH', './data/processed'),
            
            # API Keys (for LLM integration)
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY'),
            'GROQ_API_KEY': os.getenv('GROQ_API_KEY'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'ebuilder_api_url': os.getenv('EBUILDER_API_URL'),
            'ebuilder_auth_token': os.getenv('EBUILDER_AUTH_TOKEN'),
        }
        
        # Validate required configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate required configuration parameters."""
        required_fields = ['website_base_url']
        
        missing_fields = []
        for field in required_fields:
            if not self.config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {missing_fields}")
        
        # Validate URL format
        website_url = self.config['website_base_url']
        if not website_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid website URL format: {website_url}")
        
        # Ensure URL ends with /
        if not website_url.endswith('/'):
            self.config['website_base_url'] = website_url + '/'
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = getattr(logging, self.config['log_level'].upper())
        log_file = self.config['log_file_path']
        
        # Create logs directory if it doesn't exist
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),  # Console output
                logging.FileHandler(log_file)  # File output
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Environment configuration loaded from: {self.env_file}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def get_website_base_url(self) -> str:
        """Get the base URL for website scraping."""
        return self.config['website_base_url']
    
    def get_scraping_params(self) -> Dict[str, Any]:
        """Get scraping-related parameters."""
        return {
            'rate_limit': self.config['scraper_rate_limit'],
            'timeout': self.config['scraper_timeout'],
            'max_retries': self.config['scraper_max_retries']
        }
    
    def get_storage_paths(self) -> Dict[str, str]:
        """Get storage paths for data."""
        return {
            'raw_data': self.config['raw_data_path'],
            'processed_data': self.config['processed_data_path']
        }
    
    def get_logger(self) -> logging.Logger:
        """Get configured logger instance."""
        return self.logger
    
    def print_config_summary(self) -> None:
        """Print configuration summary (excluding sensitive data)."""
        safe_config = {k: v for k, v in self.config.items() 
                      if 'key' not in k.lower() and 'token' not in k.lower()}
        
        self.logger.info("Configuration Summary:")
        for key, value in safe_config.items():
            self.logger.info(f"  {key}: {value}")


# Global configuration instance
_config_instance = None

def get_config() -> EnvironmentConfig:
    """Get global configuration instance (singleton pattern)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnvironmentConfig()
    return _config_instance


if __name__ == "__main__":
    # Test configuration loading
    config = EnvironmentConfig()
    config.print_config_summary()