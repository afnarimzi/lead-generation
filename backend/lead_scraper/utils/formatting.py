"""
Formatting utility functions for displaying data.
"""

from datetime import datetime
from typing import Optional


def format_budget(amount: Optional[float], currency: str = 'USD') -> str:
    """
    Format budget amount with currency symbol.
    
    Args:
        amount: Budget amount
        currency: Currency code (USD, INR, etc.)
        
    Returns:
        Formatted budget string
        
    Examples:
        >>> format_budget(1000.50)
        '$1,000.50'
        >>> format_budget(None)
        'Not specified'
    """
    if amount is None:
        return 'Not specified'
    
    currency_symbols = {
        'USD': '$',
        'INR': '₹',
        'EUR': '€',
        'GBP': '£'
    }
    
    symbol = currency_symbols.get(currency, '$')
    return f'{symbol}{amount:,.2f}'


def format_datetime(dt: datetime, format_type: str = 'short') -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime object
        format_type: 'short', 'long', or 'iso'
        
    Returns:
        Formatted datetime string
        
    Examples:
        >>> format_datetime(datetime(2026, 2, 25, 10, 30))
        '2026-02-25 10:30'
    """
    if format_type == 'short':
        return dt.strftime('%Y-%m-%d %H:%M')
    elif format_type == 'long':
        return dt.strftime('%B %d, %Y at %I:%M %p')
    elif format_type == 'iso':
        return dt.isoformat()
    else:
        return str(dt)


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
        
    Examples:
        >>> truncate_text('This is a long text', 10)
        'This is...'
    """
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
        
    Examples:
        >>> clean_text('  Hello   World  ')
        'Hello World'
    """
    if not text:
        return ''
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    return text.strip()


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Value to format (0-100)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
        
    Examples:
        >>> format_percentage(75.5)
        '75.5%'
    """
    return f'{value:.{decimals}f}%'


def format_list(items: list, max_items: int = 5, separator: str = ', ') -> str:
    """
    Format list of items for display.
    
    Args:
        items: List of items
        max_items: Maximum items to show
        separator: Separator between items
        
    Returns:
        Formatted string
        
    Examples:
        >>> format_list(['Python', 'Java', 'C++'])
        'Python, Java, C++'
    """
    if not items:
        return 'None'
    
    if len(items) <= max_items:
        return separator.join(str(item) for item in items)
    
    shown = separator.join(str(item) for item in items[:max_items])
    remaining = len(items) - max_items
    return f'{shown} (+{remaining} more)'
