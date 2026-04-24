"""Utility for parsing dates from various formats including relative dates."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def parse_relative_date(text: str) -> Optional[datetime]:
    """
    Parse relative date strings like "Posted 4 weeks ago" or "2 days ago".
    
    Args:
        text: Text containing relative date information
        
    Returns:
        Calculated datetime (timezone-aware) or None if no match found
    """
    if not text:
        return None
    
    # Patterns to match relative dates
    patterns = [
        # "Posted X days/weeks/months ago"
        r'Posted (\d+) (second|minute|hour|day|week|month|year)s? ago',
        # "X days/weeks/months ago"
        r'(\d+) (second|minute|hour|day|week|month|year)s? ago',
        # "Posted Xd/Xw/Xmo ago"
        r'Posted (\d+)(s|m|h|d|w|mo|y) ago',
        # Just "Xd/Xw/Xmo ago"
        r'(\d+)(s|m|h|d|w|mo|y) ago',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount = int(match.group(1))
                unit = match.group(2).lower()
                
                # Convert to timedelta
                if unit in ['second', 's']:
                    delta = timedelta(seconds=amount)
                elif unit in ['minute', 'm']:
                    delta = timedelta(minutes=amount)
                elif unit in ['hour', 'h']:
                    delta = timedelta(hours=amount)
                elif unit in ['day', 'd']:
                    delta = timedelta(days=amount)
                elif unit in ['week', 'w']:
                    delta = timedelta(weeks=amount)
                elif unit in ['month', 'mo']:
                    delta = timedelta(days=amount * 30)  # Approximate
                elif unit in ['year', 'y']:
                    delta = timedelta(days=amount * 365)  # Approximate
                else:
                    continue
                
                # Use timezone-aware current time
                calculated_date = datetime.now(timezone.utc) - delta
                logger.debug(f"Parsed relative date: '{match.group(0)}' -> {calculated_date}")
                return calculated_date
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse relative date from '{text}': {e}")
                continue
    
    return None


def parse_date_from_raw_lead(raw_lead: dict, job_title: str = "Unknown") -> datetime:
    """
    Extract and parse date from raw lead data.
    
    Tries multiple strategies:
    1. Parse from date fields (postedDate, createdAt, etc.)
    2. Parse relative date from description/title
    3. Default to current time
    
    Args:
        raw_lead: Raw job posting data
        job_title: Job title for logging
        
    Returns:
        Posted datetime (timezone-aware)
    """
    # Strategy 1: Try to get from date fields (expanded list for better coverage)
    date_fields = [
        'time_submitted', 'postedOn', 'publishTime', 'createdOn', 'datePosted', 
        'publishedAt', 'postedDate', 'createdAt', 'scrapedAt', 'timePosted', 
        'date_created', 'posted_time', 'created_time', 'publish_date'
    ]
    posted_str = None
    
    for field in date_fields:
        value = raw_lead.get(field)
        if value and value != "N/A":
            posted_str = value
            break
    
    # Special handling for hello.datawizards actor "days_left" field
    if not posted_str and raw_lead.get('days_left'):
        try:
            days_left_str = raw_lead['days_left']
            # Extract number from "6 days left" format
            import re
            match = re.search(r'(\d+)\s*days?\s*left', days_left_str, re.IGNORECASE)
            if match:
                days_left = int(match.group(1))
                # Estimate posted date (assuming project duration is ~30 days)
                estimated_posted_days_ago = max(1, 30 - days_left)
                estimated_date = datetime.now(timezone.utc) - timedelta(days=estimated_posted_days_ago)
                logger.info(f"Estimated posted date from '{days_left_str}' for job '{job_title}': {estimated_date}")
                return estimated_date
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse days_left '{raw_lead.get('days_left')}' for job '{job_title}': {e}")
    
    if posted_str:
        try:
            # Try parsing ISO 8601 and common formats
            if isinstance(posted_str, str):
                # Handle various date formats
                formats = [
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%d/%m/%Y',
                    '%m/%d/%Y'
                ]
                
                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(posted_str, fmt)
                        # Make timezone-aware if not already
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        return parsed_date
                    except ValueError:
                        continue
                
                # Try ISO format parser
                try:
                    parsed_date = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
                    # Ensure timezone-aware
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    return parsed_date
                except ValueError:
                    pass
            
            elif isinstance(posted_str, datetime):
                # Make timezone-aware if not already
                if posted_str.tzinfo is None:
                    return posted_str.replace(tzinfo=timezone.utc)
                return posted_str
            
            # Try parsing as Unix timestamp
            elif isinstance(posted_str, (int, float)):
                return datetime.fromtimestamp(posted_str, tz=timezone.utc)
                
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse date '{posted_str}' for job '{job_title}': {e}")
    
    # Strategy 2: Parse relative date from text fields
    text_fields = ['description', 'title', 'snippet', 'preview_description', 'job_description']
    text_to_search = ' '.join([
        str(raw_lead.get(field, ''))
        for field in text_fields
        if raw_lead.get(field)
    ])
    
    if text_to_search:
        relative_date = parse_relative_date(text_to_search)
        if relative_date:
            logger.info(f"Parsed relative date for job '{job_title}': {relative_date}")
            return relative_date
    
    # Strategy 3: Default to current time (timezone-aware)
    logger.warning(f"No date found for job '{job_title}', using current time")
    return datetime.now(timezone.utc)
