"""
Leads API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from datetime import timezone
import os
import math
from dotenv import load_dotenv

from api.models import LeadsListResponse, LeadSummaryResponse, LeadDetailResponse, ToggleFavoriteResponse
from lead_scraper.database.connection_manager import ConnectionManager

router = APIRouter()

load_dotenv()


@router.get("/", response_model=LeadsListResponse)
async def get_leads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords"),
    platforms: Optional[str] = Query(None, description="Comma-separated platform names"),
    min_budget: Optional[float] = Query(None, ge=0, description="Minimum budget"),
    max_budget: Optional[float] = Query(None, ge=0, description="Maximum budget"),
    posted_after: Optional[str] = Query(None, description="ISO datetime string"),
    recent_only: Optional[bool] = Query(False, description="Show only recent search results (last 1 hour)")
):
    """
    Get paginated list of leads with optional filters.
    
    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - keywords: Filter by keywords in title/description
        - platforms: Filter by platform names
        - min_budget: Minimum budget amount
        - max_budget: Maximum budget amount
        - posted_after: Filter by posted date (ISO format)
    
    Returns:
        Paginated list of leads with metadata
    """
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            # Build WHERE clause
            where_clauses = []
            params = []
            
            # NO keyword filtering here - trust the semantic matching from scraping pipeline
            # The hybrid filter engine already did AI-powered semantic filtering
            # We only apply platform, budget, and date filters here
            
            # Platform filter
            if platforms:
                platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
                if platform_list:
                    placeholders = ','.join(['%s'] * len(platform_list))
                    where_clauses.append(f"platform_name IN ({placeholders})")
                    params.extend(platform_list)
            
            # Budget filters
            if min_budget is not None:
                where_clauses.append("budget_amount >= %s")
                params.append(min_budget)
            
            if max_budget is not None:
                where_clauses.append("budget_amount <= %s")
                params.append(max_budget)
            
            # Date filter
            if posted_after:
                try:
                    posted_date = datetime.fromisoformat(posted_after.replace('Z', '+00:00'))
                    where_clauses.append("posted_datetime >= %s")
                    params.append(posted_date)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid posted_after date format")
            
            # Recent only filter (for search results)
            if recent_only:
                from datetime import timedelta
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                where_clauses.append("created_at >= %s")
                params.append(recent_cutoff)
            
            # Build WHERE clause
            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)
            
            # Count total matching leads
            count_query = f"SELECT COUNT(*) FROM leads {where_sql}"
            count_result = db.execute(count_query, tuple(params))
            total = count_result[0][0] if count_result else 0
            
            # Calculate pagination
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            offset = (page - 1) * page_size
            
            # Fetch leads
            query = f'''
            SELECT 
                id, job_title, platform_name, quality_score,
                budget_amount, payment_type, posted_datetime, is_favorited
            FROM leads
            {where_sql}
            ORDER BY quality_score DESC, posted_datetime DESC
            LIMIT %s OFFSET %s
            '''
            
            results = db.execute(query, tuple(params + [page_size, offset]))
            
            leads = []
            for row in results:
                leads.append(LeadSummaryResponse(
                    id=row[0],
                    job_title=row[1],
                    platform=row[2],
                    quality_score=float(row[3]) if row[3] else 0.0,
                    budget_amount=float(row[4]) if row[4] else None,
                    payment_type=row[5],
                    posted_datetime=row[6],
                    is_favorited=row[7] if row[7] else False
                ))
            
            return LeadsListResponse(
                leads=leads,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch leads: {str(e)}")


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead_by_id(lead_id: int):
    """
    Get complete details for a specific lead.
    
    Path Parameters:
        - lead_id: The ID of the lead
    
    Returns:
        Complete lead details
    
    Raises:
        404: Lead not found
    """
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            query = '''
            SELECT 
                id, job_title, job_description, platform_name, quality_score,
                budget_amount, payment_type, client_info, job_url, posted_datetime,
                skills_tags, is_potential_duplicate, is_favorited, created_at
            FROM leads
            WHERE id = %s
            '''
            
            results = db.execute(query, (lead_id,))
            
            if not results:
                raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
            
            row = results[0]
            
            return LeadDetailResponse(
                id=row[0],
                job_title=row[1],
                job_description=row[2],
                platform=row[3],
                quality_score=float(row[4]) if row[4] else 0.0,
                budget_amount=float(row[5]) if row[5] else None,
                payment_type=row[6],
                client_info=row[7],
                job_url=row[8],
                posted_datetime=row[9],
                skills_tags=row[10] if row[10] else [],
                is_potential_duplicate=row[11] if row[11] else False,
                is_favorited=row[12] if row[12] else False,
                created_at=row[13]
            )
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch lead details: {str(e)}")


@router.post("/{lead_id}/favorite", response_model=ToggleFavoriteResponse)
async def toggle_favorite(lead_id: int):
    """
    Toggle favorite status for a lead.
    
    Path Parameters:
        - lead_id: The ID of the lead
    
    Returns:
        Updated favorite status
    
    Raises:
        404: Lead not found
    """
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            # Check if lead exists and get current status
            check_query = "SELECT id, is_favorited FROM leads WHERE id = %s"
            results = db.execute(check_query, (lead_id,))
            
            if not results:
                raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
            
            current_status = results[0][1] if results[0][1] else False
            new_status = not current_status
            
            # Update favorite status
            update_query = "UPDATE leads SET is_favorited = %s WHERE id = %s"
            db.execute(update_query, (new_status, lead_id))
            
            message = "Added to favorites" if new_status else "Removed from favorites"
            
            return ToggleFavoriteResponse(
                id=lead_id,
                is_favorited=new_status,
                message=message
            )
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle favorite: {str(e)}")


@router.get("/favorites/list", response_model=LeadsListResponse)
async def get_favorite_leads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Get paginated list of favorited leads.
    
    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
    
    Returns:
        Paginated list of favorited leads
    """
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            # Count total favorited leads
            count_query = "SELECT COUNT(*) FROM leads WHERE is_favorited = TRUE"
            count_result = db.execute(count_query, ())
            total = count_result[0][0] if count_result else 0
            
            # Calculate pagination
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            offset = (page - 1) * page_size
            
            # Fetch favorited leads
            query = '''
            SELECT 
                id, job_title, platform_name, quality_score,
                budget_amount, payment_type, posted_datetime, is_favorited
            FROM leads
            WHERE is_favorited = TRUE
            ORDER BY posted_datetime DESC
            LIMIT %s OFFSET %s
            '''
            
            results = db.execute(query, (page_size, offset))
            
            leads = []
            for row in results:
                leads.append(LeadSummaryResponse(
                    id=row[0],
                    job_title=row[1],
                    platform=row[2],
                    quality_score=float(row[3]) if row[3] else 0.0,
                    budget_amount=float(row[4]) if row[4] else None,
                    payment_type=row[5],
                    posted_datetime=row[6],
                    is_favorited=row[7] if row[7] else False
                ))
            
            return LeadsListResponse(
                leads=leads,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch favorite leads: {str(e)}")
