"""
Utility functions for the Lead Scraper system.

This package contains reusable utility functions organized by category.
"""

from lead_scraper.utils.formatting import (
    format_budget,
    format_datetime,
    truncate_text,
    clean_text
)

from lead_scraper.utils.validation import (
    validate_email,
    validate_url,
    validate_budget,
    validate_keywords
)

from lead_scraper.utils.database import (
    check_database_connection,
    get_lead_statistics,
    count_leads_by_platform
)

__all__ = [
    # Formatting
    'format_budget',
    'format_datetime',
    'truncate_text',
    'clean_text',
    
    # Validation
    'validate_email',
    'validate_url',
    'validate_budget',
    'validate_keywords',
    
    # Database
    'check_database_connection',
    'get_lead_statistics',
    'count_leads_by_platform'
]
