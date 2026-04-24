"""Authentication configuration loader."""

import os
import json
import logging
from typing import Optional

from lead_scraper.models.auth_config import AuthConfig

logger = logging.getLogger(__name__)


def load_auth_config(platform: str) -> Optional[AuthConfig]:
    """Load authentication configuration for a platform.
    
    Reads authentication credentials from environment variables.
    Supports both credential-based auth (username/password) and
    cookie-based auth (session cookies as JSON string).
    
    Args:
        platform: Platform name (upwork, freelancer, fiverr, peopleperhour)
        
    Returns:
        AuthConfig object if credentials found, None otherwise
        
    Examples:
        >>> # With environment variables set:
        >>> # UPWORK_USERNAME=myuser
        >>> # UPWORK_PASSWORD=mypass
        >>> config = load_auth_config('upwork')
        >>> config.has_credentials()
        True
        
        >>> # Without credentials
        >>> config = load_auth_config('unknown_platform')
        >>> config is None
        True
    """
    platform_upper = platform.upper()
    
    # Try environment variables first
    username = os.getenv(f'{platform_upper}_USERNAME')
    password = os.getenv(f'{platform_upper}_PASSWORD')
    cookies_str = os.getenv(f'{platform_upper}_COOKIES')
    
    # Parse cookies if provided
    cookies = None
    if cookies_str:
        try:
            cookies = json.loads(cookies_str)
            if not isinstance(cookies, dict):
                logger.warning(f"Invalid cookie format for {platform}: expected JSON object")
                cookies = None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid cookie JSON for {platform}: {e}")
            cookies = None
    
    # Check if any auth method is provided
    if not (username or cookies):
        return None
    
    return AuthConfig(
        username=username,
        password=password,
        cookies=cookies,
        platform=platform
    )
