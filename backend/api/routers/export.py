"""
Export API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from datetime import datetime
import os
import json
import csv
import io
from dotenv import load_dotenv

from lead_scraper.database.connection_manager import ConnectionManager

router = APIRouter()

load_dotenv()


@router.get("/")
async def export_leads(
    format: str = Query(..., description="Export format: csv or json"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords"),
    platforms: Optional[str] = Query(None, description="Comma-separated platform names"),
    min_budget: Optional[float] = Query(None, ge=0, description="Minimum budget"),
    max_budget: Optional[float] = Query(None, ge=0, description="Maximum budget"),
    posted_after: Optional[str] = Query(None, description="ISO datetime string")
):
    """
    Export filtered leads to CSV or JSON format.
    
    Query Parameters:
        - format: Export format ("csv" or "json")
        - keywords: Filter by keywords
        - platforms: Filter by platforms
        - min_budget: Minimum budget
        - max_budget: Maximum budget
        - posted_after: Filter by posted date
    
    Returns:
        File download (CSV or JSON)
    """
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'json'")
    
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            # Build WHERE clause (same as leads endpoint)
            where_clauses = []
            params = []
            
            if keywords:
                keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                if keyword_list:
                    keyword_conditions = []
                    for keyword in keyword_list:
                        keyword_conditions.append(
                            "(job_title ILIKE %s OR job_description ILIKE %s)"
                        )
                        params.extend([f"%{keyword}%", f"%{keyword}%"])
                    where_clauses.append(f"({' OR '.join(keyword_conditions)})")
            
            if platforms:
                platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
                if platform_list:
                    placeholders = ','.join(['%s'] * len(platform_list))
                    where_clauses.append(f"platform_name IN ({placeholders})")
                    params.extend(platform_list)
            
            if min_budget is not None:
                where_clauses.append("budget_amount >= %s")
                params.append(min_budget)
            
            if max_budget is not None:
                where_clauses.append("budget_amount <= %s")
                params.append(max_budget)
            
            if posted_after:
                try:
                    posted_date = datetime.fromisoformat(posted_after.replace('Z', '+00:00'))
                    where_clauses.append("posted_datetime >= %s")
                    params.append(posted_date)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid posted_after date format")
            
            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)
            
            # Fetch leads
            query = f'''
            SELECT 
                id, job_title, job_description, platform_name, quality_score,
                budget_amount, payment_type, job_url, posted_datetime,
                skills_tags, created_at
            FROM leads
            {where_sql}
            ORDER BY posted_datetime DESC
            '''
            
            results = db.execute(query, tuple(params))
            
            # Convert to list of dicts
            leads = []
            for row in results:
                leads.append({
                    "id": row[0],
                    "job_title": row[1],
                    "job_description": row[2],
                    "platform": row[3],
                    "quality_score": float(row[4]) if row[4] else 0.0,
                    "budget_amount": float(row[5]) if row[5] else None,
                    "payment_type": row[6],
                    "job_url": row[7],
                    "posted_datetime": row[8].isoformat() if row[8] else None,
                    "skills_tags": row[9] if row[9] else [],
                    "created_at": row[10].isoformat() if row[10] else None
                })
            
            # Export based on format
            if format == "json":
                content = json.dumps(leads, indent=2)
                media_type = "application/json"
                filename = f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
            else:  # csv
                output = io.StringIO()
                if leads:
                    writer = csv.DictWriter(output, fieldnames=leads[0].keys())
                    writer.writeheader()
                    writer.writerows(leads)
                content = output.getvalue()
                media_type = "text/csv"
                filename = f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export leads: {str(e)}")
