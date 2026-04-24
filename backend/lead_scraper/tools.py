"""
High-level tools for common lead scraper operations.

This module provides convenient functions for frequently used operations,
combining multiple lower-level functions into easy-to-use tools.
"""

import os
from typing import List, Optional, Dict
from dotenv import load_dotenv

from lead_scraper.constants import (
    DEFAULT_MAX_RESULTS_PER_PLATFORM,
    DEFAULT_POSTED_WITHIN_HOURS,
    ALL_PLATFORMS
)
from lead_scraper.utils.database import (
    check_database_connection,
    get_lead_statistics,
    count_leads_by_platform,
    get_budget_statistics_by_platform,
    get_recent_leads
)
from lead_scraper.utils.formatting import (
    format_budget,
    format_datetime,
    format_percentage,
    format_list
)
from lead_scraper.utils.validation import (
    validate_keywords,
    validate_budget,
    validate_platform_name
)


def display_system_status() -> None:
    """
    Display comprehensive system status including database connection and statistics.
    
    Examples:
        >>> display_system_status()
        ✓ Database: Connected
        📊 Total Leads: 150
        ...
    """
    print("\n" + "=" * 70)
    print("🔍 SYSTEM STATUS")
    print("=" * 70)
    
    # Check database connection
    is_connected, error = check_database_connection()
    if is_connected:
        print("\n✓ Database: Connected")
    else:
        print(f"\n✗ Database: Connection failed - {error}")
        return
    
    # Get statistics
    try:
        stats = get_lead_statistics()
        platform_counts = count_leads_by_platform()
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Leads: {stats['total_leads']}")
        print(f"   Leads with Budget: {stats['leads_with_budget']}")
        print(f"   Average Budget: {format_budget(stats['avg_budget'])}")
        print(f"   Average Quality Score: {stats['avg_quality_score']:.1f}/100")
        print(f"   Active Platforms: {stats['platforms_count']}")
        
        print(f"\n📈 Leads by Platform:")
        for platform, count in platform_counts.items():
            print(f"   {platform}: {count}")
        
    except Exception as e:
        print(f"\n⚠️  Could not retrieve statistics: {e}")
    
    print("\n" + "=" * 70)


def display_budget_report() -> None:
    """
    Display detailed budget statistics by platform.
    
    Examples:
        >>> display_budget_report()
        💰 BUDGET REPORT
        ======================================================================
        ...
    """
    print("\n" + "=" * 70)
    print("💰 BUDGET REPORT")
    print("=" * 70)
    
    try:
        stats = get_budget_statistics_by_platform()
        
        for platform, data in stats.items():
            print(f"\n📋 {platform}:")
            print(f"   Total Jobs: {data['total_jobs']}")
            print(f"   With Budget: {data['with_budget']} ({format_percentage(data['percentage'])})")
            
            if data['with_budget'] > 0:
                print(f"   Average: {format_budget(data['avg_budget'])}")
                print(f"   Range: {format_budget(data['min_budget'])} - {format_budget(data['max_budget'])}")
            else:
                print(f"   No budget data available")
        
    except Exception as e:
        print(f"\n⚠️  Could not generate budget report: {e}")
    
    print("\n" + "=" * 70)


def display_recent_leads(limit: int = 10, platform: Optional[str] = None) -> None:
    """
    Display recent leads from database.
    
    Args:
        limit: Maximum number of leads to display
        platform: Optional platform filter
        
    Examples:
        >>> display_recent_leads(5, 'Upwork')
        📋 RECENT LEADS (Upwork)
        ...
    """
    title = f"📋 RECENT LEADS ({platform})" if platform else "📋 RECENT LEADS (All Platforms)"
    
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    
    try:
        leads = get_recent_leads(limit, platform)
        
        if not leads:
            print("\nNo leads found.")
            return
        
        for i, lead in enumerate(leads, 1):
            print(f"\n{i}. {lead['job_title']}")
            print(f"   Platform: {lead['platform_name']}")
            print(f"   Budget: {format_budget(lead['budget_amount'])}")
            print(f"   Posted: {format_datetime(lead['posted_datetime'])}")
            print(f"   URL: {lead['job_url']}")
        
    except Exception as e:
        print(f"\n⚠️  Could not retrieve leads: {e}")
    
    print("\n" + "=" * 70)


def validate_search_parameters(
    keywords: List[str],
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    platforms: Optional[List[str]] = None
) -> tuple[bool, List[str]]:
    """
    Validate search parameters before running a search.
    
    Args:
        keywords: List of search keywords
        min_budget: Minimum budget filter
        max_budget: Maximum budget filter
        platforms: List of platform names
        
    Returns:
        Tuple of (is_valid, list_of_errors)
        
    Examples:
        >>> validate_search_parameters(['AI', 'ML'], 100.0, 1000.0, ['Upwork'])
        (True, [])
    """
    errors = []
    
    # Validate keywords
    keywords_valid, keyword_errors = validate_keywords(keywords)
    if not keywords_valid:
        errors.extend(keyword_errors)
    
    # Validate budgets
    if min_budget is not None and not validate_budget(min_budget):
        errors.append(f'Invalid minimum budget: {min_budget}')
    
    if max_budget is not None and not validate_budget(max_budget):
        errors.append(f'Invalid maximum budget: {max_budget}')
    
    if min_budget is not None and max_budget is not None:
        if min_budget > max_budget:
            errors.append('Minimum budget cannot be greater than maximum budget')
    
    # Validate platforms
    if platforms:
        for platform in platforms:
            if not validate_platform_name(platform):
                errors.append(f'Invalid platform name: {platform}')
    
    return len(errors) == 0, errors


def get_environment_config() -> Dict[str, any]:
    """
    Load and return environment configuration.
    
    Returns:
        Dictionary with configuration values
        
    Examples:
        >>> config = get_environment_config()
        >>> config['apify_token']
        'apify_api_...'
    """
    load_dotenv()
    
    return {
        'apify_token': os.getenv('APIFY_TOKEN'),
        'database_url': os.getenv('DATABASE_URL'),
        'credit_limit': float(os.getenv('FREE_PLAN_CREDIT_LIMIT', '5.0')),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'max_results': int(os.getenv('DEFAULT_MAX_RESULTS', str(DEFAULT_MAX_RESULTS_PER_PLATFORM))),
        'posted_within_hours': int(os.getenv('DEFAULT_POSTED_WITHIN_HOURS', str(DEFAULT_POSTED_WITHIN_HOURS))),
        
        # Actor IDs
        'upwork_actor': os.getenv('APIFY_UPWORK_ACTOR_ID', 'flash_mage~upwork'),
        'freelancer_actor': os.getenv('APIFY_FREELANCER_ACTOR_ID', 'consummate_mandala~freelancer-project-scraper'),
        'fiverr_actor': os.getenv('APIFY_FIVERR_ACTOR_ID', 'piotrv1001~fiverr-listings-scraper'),
        'peopleperhour_actor': os.getenv('APIFY_PEOPLEPERHOUR_ACTOR_ID', 'getdataforme~peopleperhour-job-scraper'),
        
        # Authentication
        'upwork_username': os.getenv('UPWORK_USERNAME'),
        'upwork_password': os.getenv('UPWORK_PASSWORD'),
        'freelancer_username': os.getenv('FREELANCER_USERNAME'),
        'freelancer_password': os.getenv('FREELANCER_PASSWORD'),
        'fiverr_username': os.getenv('FIVERR_USERNAME'),
        'fiverr_password': os.getenv('FIVERR_PASSWORD'),
        'peopleperhour_username': os.getenv('PEOPLEPERHOUR_USERNAME'),
        'peopleperhour_password': os.getenv('PEOPLEPERHOUR_PASSWORD'),
    }


def print_configuration_summary() -> None:
    """
    Print a summary of current configuration.
    
    Examples:
        >>> print_configuration_summary()
        ⚙️  CONFIGURATION SUMMARY
        ======================================================================
        ...
    """
    config = get_environment_config()
    
    print("\n" + "=" * 70)
    print("⚙️  CONFIGURATION SUMMARY")
    print("=" * 70)
    
    print("\n🔑 API Configuration:")
    print(f"   Apify Token: {'✓ Set' if config['apify_token'] else '✗ Missing'}")
    print(f"   Database URL: {'✓ Set' if config['database_url'] else '✗ Missing'}")
    
    print("\n💰 Credit Settings:")
    print(f"   Credit Limit: {config['credit_limit']}")
    
    print("\n🔍 Search Defaults:")
    print(f"   Max Results: {config['max_results']}")
    print(f"   Time Range: {config['posted_within_hours']} hours")
    
    print("\n🔐 Authentication Status:")
    platforms_auth = {
        'Upwork': bool(config['upwork_username'] and config['upwork_password']),
        'Freelancer': bool(config['freelancer_username'] and config['freelancer_password']),
        'Fiverr': bool(config['fiverr_username'] and config['fiverr_password']),
        'PeoplePerHour': bool(config['peopleperhour_username'] and config['peopleperhour_password'])
    }
    
    for platform, has_auth in platforms_auth.items():
        status = '✓ Configured' if has_auth else '○ Not configured'
        print(f"   {platform}: {status}")
    
    print("\n" + "=" * 70)
