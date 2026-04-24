"""
Validation utility functions for input data.
"""

import re
from typing import List, Optional
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
        
    Examples:
        >>> validate_email('user@example.com')
        True
        >>> validate_email('invalid-email')
        False
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
        
    Examples:
        >>> validate_url('https://example.com')
        True
        >>> validate_url('not-a-url')
        False
    """
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_budget(amount: Optional[float], min_value: float = 0.0) -> bool:
    """
    Validate budget amount.
    
    Args:
        amount: Budget amount to validate
        min_value: Minimum allowed value
        
    Returns:
        True if valid, False otherwise
        
    Examples:
        >>> validate_budget(100.0)
        True
        >>> validate_budget(-50.0)
        False
    """
    if amount is None:
        return True  # None is valid (means not specified)
    
    try:
        return float(amount) >= min_value
    except (ValueError, TypeError):
        return False


def validate_keywords(keywords: List[str], min_length: int = 2) -> tuple[bool, List[str]]:
    """
    Validate list of keywords.
    
    Args:
        keywords: List of keywords to validate
        min_length: Minimum keyword length
        
    Returns:
        Tuple of (is_valid, list_of_errors)
        
    Examples:
        >>> validate_keywords(['AI', 'machine learning'])
        (True, [])
        >>> validate_keywords(['a', ''])
        (False, ['Keyword too short: a', 'Empty keyword'])
    """
    if not keywords:
        return False, ['No keywords provided']
    
    errors = []
    
    for keyword in keywords:
        if not keyword or not keyword.strip():
            errors.append('Empty keyword')
        elif len(keyword.strip()) < min_length:
            errors.append(f'Keyword too short: {keyword}')
    
    return len(errors) == 0, errors


def validate_platform_name(platform: str) -> bool:
    """
    Validate platform name.
    
    Args:
        platform: Platform name to validate
        
    Returns:
        True if valid, False otherwise
        
    Examples:
        >>> validate_platform_name('Upwork')
        True
        >>> validate_platform_name('InvalidPlatform')
        False
    """
    from lead_scraper.constants import ALL_PLATFORMS
    return platform in ALL_PLATFORMS


def validate_date_range(start_hours: Optional[int], end_hours: Optional[int] = None) -> bool:
    """
    Validate date range in hours.
    
    Args:
        start_hours: Start of range (hours ago)
        end_hours: End of range (hours ago)
        
    Returns:
        True if valid, False otherwise
        
    Examples:
        >>> validate_date_range(24, 168)
        True
        >>> validate_date_range(-10)
        False
    """
    if start_hours is not None and start_hours < 0:
        return False
    
    if end_hours is not None and end_hours < 0:
        return False
    
    if start_hours is not None and end_hours is not None:
        if start_hours > end_hours:
            return False
    
    return True
