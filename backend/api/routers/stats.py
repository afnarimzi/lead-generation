"""
Statistics API endpoints.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from api.models import StatsResponse
from lead_scraper.database.connection_manager import ConnectionManager
from lead_scraper.utils.database import get_lead_statistics, count_leads_by_platform

router = APIRouter()

load_dotenv()


@router.get("/", response_model=StatsResponse)
async def get_stats():
    """
    Get dashboard statistics.
    
    Returns:
        - total_leads: Total number of leads in database
        - leads_by_platform: Count of leads per platform
        - leads_last_24h: Leads posted in last 24 hours
        - leads_last_7d: Leads posted in last 7 days
    """
    try:
        # Get basic stats
        basic_stats = get_lead_statistics()
        platform_counts = count_leads_by_platform()
        
        # Get time-based stats
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        try:
            # Leads from last 24 hours
            query_24h = '''
            SELECT COUNT(*) FROM leads
            WHERE posted_datetime >= %s
            '''
            now = datetime.now()
            result_24h = db.execute(query_24h, (now - timedelta(hours=24),))
            leads_24h = result_24h[0][0] if result_24h else 0
            
            # Leads from last 7 days
            query_7d = '''
            SELECT COUNT(*) FROM leads
            WHERE posted_datetime >= %s
            '''
            result_7d = db.execute(query_7d, (now - timedelta(days=7),))
            leads_7d = result_7d[0][0] if result_7d else 0
            
        finally:
            db.close()
        
        return StatsResponse(
            total_leads=basic_stats['total_leads'],
            leads_by_platform=platform_counts,
            leads_last_24h=leads_24h,
            leads_last_7d=leads_7d
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
