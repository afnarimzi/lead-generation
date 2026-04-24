"""Abstract base class for platform-specific scrapers."""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging
import time
from datetime import datetime

from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.auth_config import AuthConfig


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific scrapers."""
    
    def __init__(self, apify_token: str, actor_id: str, auth_config: Optional[AuthConfig] = None):
        """Initialize the platform adapter.
        
        Args:
            apify_token: Apify API token for authentication
            actor_id: Apify actor ID for this platform
            auth_config: Optional authentication configuration
        """
        self.apify_token = apify_token
        self.actor_id = actor_id
        self.auth_config = auth_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Validate auth config if provided
        if self.auth_config:
            self._validate_auth_config()
    
    @abstractmethod
    async def scrape(self, filters: FilterCriteria) -> List[dict]:
        """Triggers the Apify actor and retrieves raw results.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            List of raw job posting dictionaries from the platform
        """
        pass
    
    @abstractmethod
    def normalize(self, raw_lead: dict) -> Lead:
        """Converts platform-specific data to unified schema.
        
        Args:
            raw_lead: Raw job posting data from the platform
            
        Returns:
            Normalized Lead object
        """
        pass
    
    @abstractmethod
    def estimate_credits(self, filters: FilterCriteria) -> float:
        """Estimates Apify credit cost for the scraping operation.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            Estimated credit cost
        """
        pass
    
    def handle_error(self, error: Exception, max_retries: int = 3) -> None:
        """Logs and handles scraping errors with retry logic.
        
        Args:
            error: Exception that occurred during scraping
            max_retries: Maximum number of retry attempts
        """
        self.logger.error(
            f"Error in {self.__class__.__name__}: {type(error).__name__}: {str(error)}",
            exc_info=True
        )
    
    def _exponential_backoff(self, attempt: int, base_delay: float = 1.0) -> None:
        """Implements exponential backoff delay.
        
        Args:
            attempt: Current retry attempt number (0-indexed)
            base_delay: Base delay in seconds
        """
        delay = base_delay * (2 ** attempt)
        self.logger.info(f"Retrying in {delay} seconds...")
        time.sleep(delay)
    
    def _validate_auth_config(self) -> bool:
        """Validate authentication configuration.
        
        Returns:
            True if valid, False otherwise (logs warnings)
        """
        if not self.auth_config:
            return True
        
        if not self.auth_config.is_valid():
            if self.auth_config.has_cookies() and self.auth_config.cookie_expiration:
                if datetime.now() > self.auth_config.cookie_expiration:
                    self.logger.warning(
                        f"Authentication cookies expired for {self.auth_config.platform}. "
                        "Falling back to anonymous scraping."
                    )
            else:
                self.logger.warning(
                    f"Invalid authentication configuration for {self.auth_config.platform}. "
                    "Falling back to anonymous scraping."
                )
            self.auth_config = None
            return False
        
        self.logger.info(f"Authenticated scraping enabled for {self.auth_config.platform}")
        return True
    
    def _add_auth_to_input(self, actor_input: dict) -> dict:
        """Add authentication parameters to actor input.
        
        Args:
            actor_input: Base actor input dictionary
            
        Returns:
            Actor input with auth parameters added
        """
        if not self.auth_config or not self.auth_config.is_valid():
            return actor_input
        
        # Add credentials if available
        if self.auth_config.has_credentials():
            actor_input['username'] = self.auth_config.username
            actor_input['password'] = self.auth_config.password
        
        # Add cookies if available
        if self.auth_config.has_cookies():
            actor_input['cookies'] = self.auth_config.cookies
        
        return actor_input
