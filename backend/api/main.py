"""
FastAPI application entry point - Complete Backend.
"""
import os
import sys
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="Freelance Lead Scraper API",
    description="REST API for managing freelance job leads with AI ranking and live scraping",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Freelance Lead Scraper API - Complete Backend",
        "version": "1.0.0",
        "status": "working",
        "docs": "/docs",
        "features": ["Live Scraping", "AI Ranking", "Favorites", "Multi-Platform"]
    }

@app.get("/api/")
def api_root():
    """API root endpoint."""
    return {
        "message": "Complete API is working",
        "version": "1.0.0",
        "features": ["search", "leads", "favorites", "ai_ranking"]
    }

@app.get("/api/cleanup")
def manual_cleanup():
    """Manual database cleanup - removes all non-favorited leads for fresh results."""
    try:
        from lead_scraper.database.connection_manager import ConnectionManager
        
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        # Count before
        count_result = db.execute("SELECT COUNT(*) FROM leads", ())
        total_before = count_result[0][0] if count_result else 0
        
        fav_result = db.execute("SELECT COUNT(*) FROM leads WHERE is_favorited = TRUE", ())
        favorited_count = fav_result[0][0] if fav_result else 0
        
        # Delete all non-favorited leads
        db.execute("DELETE FROM leads WHERE (is_favorited = FALSE OR is_favorited IS NULL)", ())
        
        # Count after
        count_after = db.execute("SELECT COUNT(*) FROM leads", ())
        total_after = count_after[0][0] if count_after else 0
        
        deleted_count = total_before - total_after
        
        return {
            "status": "cleanup_complete",
            "deleted_leads": deleted_count,
            "remaining_leads": total_after,
            "favorited_leads": favorited_count,
            "message": f"Deleted {deleted_count} old leads, kept {favorited_count} favorites - ready for fresh search!"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/health")
def api_health_check(recent_search: bool = False):
    """API Health check endpoint with optional recent search results."""
    try:
        # Test database connection
        from lead_scraper.database.connection_manager import ConnectionManager
        
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            return {"status": "error", "message": "DATABASE_URL not configured"}
        
        db = ConnectionManager(db_url)
        if db.health_check():
            # Count leads
            result = db.execute("SELECT COUNT(*) FROM leads", ())
            count = result[0][0] if result else 0
            
            response = {
                "status": "healthy", 
                "database": "connected",
                "leads_count": count,
                "backend": "complete"
            }
            
            # If recent_search=true, add recent search results
            if recent_search:
                try:
                    from datetime import datetime, timezone, timedelta
                    recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                    
                    # Get recent leads
                    recent_query = """
                    SELECT id, job_title, platform_name, quality_score, budget_amount, posted_datetime, is_favorited
                    FROM leads 
                    WHERE created_at >= %s 
                    ORDER BY quality_score DESC 
                    LIMIT 20
                    """
                    recent_results = db.execute(recent_query, (recent_cutoff,))
                    
                    recent_leads = []
                    for row in recent_results:
                        recent_leads.append({
                            "id": row[0],
                            "job_title": row[1],
                            "platform": row[2],
                            "quality_score": float(row[3]) if row[3] else 0.0,
                            "budget_amount": float(row[4]) if row[4] else None,
                            "posted_datetime": row[5],
                            "is_favorited": row[6] if row[6] else False
                        })
                    
                    response["recent_leads"] = recent_leads
                    response["recent_count"] = len(recent_leads)
                    response["cutoff_time"] = recent_cutoff.isoformat()
                    
                except Exception as e:
                    response["recent_search_error"] = str(e)
            
            return response
        else:
            return {"status": "unhealthy", "database": "disconnected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/search/results")
def get_search_results_direct(
    page: int = 1,
    page_size: int = 20,
    keywords: str = None
):
    """
    TEMPORARY: Direct search results endpoint to bypass router caching.
    Get results from the most recent search.
    """
    try:
        from lead_scraper.database.connection_manager import ConnectionManager
        from datetime import datetime, timezone, timedelta
        import math
        
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            # Get leads from the most recent search (last 1 hour)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            
            # Build WHERE clause for recent leads
            where_clauses = ["created_at >= %s"]
            params = [recent_cutoff]
            
            # Optional keyword filtering for re-filtering results
            if keywords:
                keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
                if keyword_list:
                    keyword_conditions = []
                    for keyword in keyword_list:
                        keyword_conditions.append("(LOWER(job_title) LIKE %s OR LOWER(job_description) LIKE %s)")
                        params.extend([f"%{keyword}%", f"%{keyword}%"])
                    
                    if keyword_conditions:
                        where_clauses.append(f"({' OR '.join(keyword_conditions)})")
            
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
            # Count total matching leads
            count_query = f"SELECT COUNT(*) FROM leads {where_sql}"
            count_result = db.execute(count_query, tuple(params))
            total = count_result[0][0] if count_result else 0
            
            # Calculate pagination
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            offset = (page - 1) * page_size
            
            # Fetch recent search results
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
                leads.append({
                    "id": row[0],
                    "job_title": row[1],
                    "platform": row[2],
                    "quality_score": float(row[3]) if row[3] else 0.0,
                    "budget_amount": float(row[4]) if row[4] else None,
                    "payment_type": row[5],
                    "posted_datetime": row[6],
                    "is_favorited": row[7] if row[7] else False
                })
            
            return {
                "leads": leads,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "search_timestamp": recent_cutoff.isoformat(),
                "message": f"Showing {len(leads)} leads from recent search (DIRECT ENDPOINT)"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        return {"error": f"Failed to fetch search results: {str(e)}"}

# Import and register routers - FORCE REBUILD 2026-03-07
try:
    # Force reload modules to bypass Vercel caching
    import importlib
    import sys
    
    # Clear module cache
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith('api.routers')]
    for module in modules_to_clear:
        del sys.modules[module]
    
    from api.routers.search import router as search_router
    from api.routers.leads import router as leads_router  
    from api.admin import router as admin_router
    
    app.include_router(search_router, prefix="/api/search", tags=["search"])
    app.include_router(leads_router, prefix="/api/leads", tags=["leads"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    
    @app.get("/api/status")
    def api_status():
        return {
            "status": "complete backend loaded - REBUILD 2026-03-07",
            "routers": ["search", "leads", "admin"],
            "message": "All functionality available",
            "cache_cleared": True
        }
    
except Exception as e:
    # Fallback endpoints if routers fail to load
    @app.get("/api/status")
    def api_status_fallback():
        return {
            "status": "router import failed",
            "error": str(e),
            "message": "Using fallback endpoints"
        }
    
    # Add basic fallback endpoints
    @app.post("/api/search/start")
    async def fallback_search(request: dict):
        return {
            "status": "error",
            "message": f"Router import failed: {str(e)}",
            "fallback": True
        }
    
    @app.get("/api/search/status")
    async def fallback_status():
        return {
            "is_running": False,
            "message": f"Router import failed: {str(e)}",
            "fallback": True
        }
