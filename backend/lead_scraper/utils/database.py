"""
Database utility functions for common operations.
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

from lead_scraper.database.connection_manager import ConnectionManager


def check_database_connection() -> tuple[bool, Optional[str]]:
    """
    Check if database connection is working.
    
    Returns:
        Tuple of (is_connected, error_message)
        
    Examples:
        >>> check_database_connection()
        (True, None)
    """
    load_dotenv()
    
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        result = db.execute('SELECT 1')
        db.close()
        return True, None
    except Exception as e:
        return False, str(e)


def get_lead_statistics() -> Dict[str, any]:
    """
    Get overall lead statistics from database.
    
    Returns:
        Dictionary with statistics
        
    Examples:
        >>> stats = get_lead_statistics()
        >>> stats['total_leads']
        150
    """
    load_dotenv()
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    try:
        query = '''
        SELECT 
            COUNT(*) as total_leads,
            COUNT(budget_amount) as leads_with_budget,
            AVG(budget_amount) as avg_budget,
            AVG(quality_score) as avg_quality_score,
            COUNT(DISTINCT platform_name) as platforms_count
        FROM leads
        '''
        
        result = db.execute(query)[0]
        
        return {
            'total_leads': result[0],
            'leads_with_budget': result[1],
            'avg_budget': float(result[2]) if result[2] else 0.0,
            'avg_quality_score': float(result[3]) if result[3] else 0.0,
            'platforms_count': result[4]
        }
    finally:
        db.close()


def count_leads_by_platform() -> Dict[str, int]:
    """
    Count leads grouped by platform.
    
    Returns:
        Dictionary mapping platform names to lead counts
        
    Examples:
        >>> count_leads_by_platform()
        {'Upwork': 50, 'Freelancer': 100}
    """
    load_dotenv()
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    try:
        query = '''
        SELECT platform_name, COUNT(*) as count
        FROM leads
        GROUP BY platform_name
        ORDER BY count DESC
        '''
        
        results = db.execute(query)
        return {row[0]: row[1] for row in results}
    finally:
        db.close()


def get_budget_statistics_by_platform() -> Dict[str, Dict[str, any]]:
    """
    Get budget statistics grouped by platform.
    
    Returns:
        Dictionary mapping platform names to budget stats
        
    Examples:
        >>> get_budget_statistics_by_platform()
        {'Upwork': {'total': 10, 'with_budget': 8, 'avg': 500.0}}
    """
    load_dotenv()
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    try:
        query = '''
        SELECT 
            platform_name,
            COUNT(*) as total,
            COUNT(budget_amount) as with_budget,
            AVG(budget_amount) as avg_budget,
            MIN(budget_amount) as min_budget,
            MAX(budget_amount) as max_budget
        FROM leads
        GROUP BY platform_name
        ORDER BY platform_name
        '''
        
        results = db.execute(query)
        
        stats = {}
        for row in results:
            platform, total, with_budget, avg, min_val, max_val = row
            stats[platform] = {
                'total_jobs': total,
                'with_budget': with_budget,
                'percentage': (with_budget / total * 100) if total > 0 else 0.0,
                'avg_budget': float(avg) if avg else 0.0,
                'min_budget': float(min_val) if min_val else 0.0,
                'max_budget': float(max_val) if max_val else 0.0
            }
        
        return stats
    finally:
        db.close()


def get_recent_leads(limit: int = 10, platform: Optional[str] = None) -> list:
    """
    Get most recent leads from database.
    
    Args:
        limit: Maximum number of leads to return
        platform: Optional platform filter
        
    Returns:
        List of lead dictionaries
        
    Examples:
        >>> get_recent_leads(5, 'Upwork')
        [{'job_title': '...', 'budget_amount': 500.0}, ...]
    """
    load_dotenv()
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    try:
        if platform:
            query = '''
            SELECT job_title, platform_name, budget_amount, posted_datetime, job_url
            FROM leads
            WHERE platform_name = %s
            ORDER BY created_at DESC
            LIMIT %s
            '''
            results = db.execute(query, (platform, limit))
        else:
            query = '''
            SELECT job_title, platform_name, budget_amount, posted_datetime, job_url
            FROM leads
            ORDER BY created_at DESC
            LIMIT %s
            '''
            results = db.execute(query, (limit,))
        
        leads = []
        for row in results:
            leads.append({
                'job_title': row[0],
                'platform_name': row[1],
                'budget_amount': float(row[2]) if row[2] else None,
                'posted_datetime': row[3],
                'job_url': row[4]
            })
        
        return leads
    finally:
        db.close()
