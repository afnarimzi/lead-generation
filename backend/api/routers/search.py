"""
Search API endpoints for lead generation.
"""
import asyncio
import logging
import math
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.orchestrator import LeadGenerationOrchestrator
from lead_scraper.adapters.upwork_adapter import UpworkAdapter
from lead_scraper.adapters.fiverr_adapter import FiverrAdapter
from lead_scraper.adapters.freelancer_adapter import FreelancerAdapter
from lead_scraper.adapters.peopleperhour_adapter import PeoplePerHourAdapter
from lead_scraper.database.connection_manager import ConnectionManager
from lead_scraper.engines.credit_monitor import CreditMonitor
from lead_scraper.engines.deduplication_engine import DeduplicationEngine
from lead_scraper.engines.filter_engine import FilterEngine
from lead_scraper.engines.quality_scorer import QualityScorer
from lead_scraper.config.auth_loader import load_auth_config
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

# Global search state
search_task: Optional[asyncio.Task] = None
search_status = {
    "is_running": False,
    "message": "No search in progress",
    "started_at": None,
    "completed_at": None
}


class SearchRequest(BaseModel):
    """Search request model."""
    keywords: List[str]
    platforms: Optional[List[str]] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    posted_within_hours: int = 168
    min_quality_score: float = 0.0
    max_results_per_platform: int = int(os.getenv('DEFAULT_MAX_RESULTS', '5'))  # Reduced for Vercel timeout


class SearchStatusResponse(BaseModel):
    """Search status response model."""
    is_running: bool
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# Global orchestrator instance to prevent multiple cleanups
_orchestrator_instance = None
_last_gemini_key = None  # Track API key changes

def get_orchestrator() -> LeadGenerationOrchestrator:
    """Initialize and return orchestrator instance (singleton with API key change detection)."""
    global _orchestrator_instance, _last_gemini_key
    
    current_gemini_key = os.getenv('GEMINI_API_KEY')
    
    # Force recreation if API key changed
    if _orchestrator_instance is not None and _last_gemini_key != current_gemini_key:
        logger.info(f"🔄 Gemini API key changed, recreating orchestrator instance")
        _orchestrator_instance = None
    
    if _orchestrator_instance is not None:
        logger.info("♻️ Reusing existing orchestrator instance")
        return _orchestrator_instance
    
    logger.info("🏗️ Creating new orchestrator instance")
    _last_gemini_key = current_gemini_key  # Track current key
    
    # Add timestamp to logs for debugging
    from datetime import datetime
    logger.info(f"🕐 Orchestrator creation time: {datetime.now()}")
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    credit_monitor = CreditMonitor(
        apify_token=os.getenv('APIFY_TOKEN'),
        free_plan_limit=float(os.getenv('FREE_PLAN_CREDIT_LIMIT', '5.0')),
        warning_threshold=float(os.getenv('CREDIT_WARNING_THRESHOLD', '80.0')),
        stop_threshold=float(os.getenv('CREDIT_STOP_THRESHOLD', '95.0'))
    )
    
    upwork_adapter = UpworkAdapter(
        apify_token=os.getenv('APIFY_TOKEN'),
        actor_id=os.getenv('APIFY_UPWORK_ACTOR_ID'),
        auth_config=load_auth_config('upwork')
    )
    
    fiverr_adapter = FiverrAdapter(
        apify_token=os.getenv('APIFY_TOKEN'),
        actor_id=os.getenv('APIFY_FIVERR_ACTOR_ID'),
        auth_config=load_auth_config('fiverr')
    )
    
    freelancer_adapter = FreelancerAdapter(
        apify_token=os.getenv('APIFY_TOKEN'),
        actor_id=os.getenv('APIFY_FREELANCER_ACTOR_ID'),
        auth_config=load_auth_config('freelancer')
    )
    
    peopleperhour_adapter = PeoplePerHourAdapter(
        apify_token=os.getenv('APIFY_TOKEN'),
        actor_id=os.getenv('APIFY_PEOPLEPERHOUR_ACTOR_ID'),
        auth_config=load_auth_config('peopleperhour')
    )
    
    dedup_engine = DeduplicationEngine(db_connection=db)
    filter_engine = FilterEngine()
    quality_scorer = QualityScorer()
    
    # Initialize hybrid filter engine with embedding support
    try:
        from lead_scraper.engines.hybrid_filter_engine import HybridFilterEngine
        from lead_scraper.engines.gemini_embedding_engine import GeminiEmbeddingEngine
        from lead_scraper.engines.budget_enrichment_engine import BudgetEnrichmentEngine
        
        # Initialize Gemini embedding engine
        embedding_engine = GeminiEmbeddingEngine()
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            logger.info(f"🔑 Found Gemini API key: {gemini_api_key[:10]}...{gemini_api_key[-4:]}")
            embedding_engine.initialize(api_key=gemini_api_key)
            
            # Test API connection
            if embedding_engine.test_api_connection():
                logger.info("✅ Gemini embedding engine initialized and tested successfully")
            else:
                logger.error("❌ Gemini API test failed - AI filtering will be disabled")
                logger.info("🔄 System will use basic keyword filtering instead")
        else:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            raise ValueError("Gemini API key required")
        
        budget_enrichment_engine = BudgetEnrichmentEngine()
        
        hybrid_filter_engine = HybridFilterEngine(
            embedding_engine=embedding_engine,
            budget_enrichment_engine=budget_enrichment_engine,
            similarity_threshold=0.6,  # BALANCED: Works for both AI and basic filtering
            embedding_weight=0.7,      # Prioritize relevance heavily
            quality_weight=0.15,        
            recency_weight=0.1,        
            budget_weight=0.05,        # Minimal budget weight to focus on relevance
            top_n_to_enrich=10,        
            enable_enrichment=True
        )
        logger.info("✓ Hybrid filter engine initialized with Gemini embedding support")
    except Exception as e:
        logger.warning(f"Failed to initialize hybrid filter engine: {e}")
        hybrid_filter_engine = None
    
    _orchestrator_instance = LeadGenerationOrchestrator(
        upwork_adapter=upwork_adapter,
        fiverr_adapter=fiverr_adapter,
        freelancer_adapter=freelancer_adapter,
        peopleperhour_adapter=peopleperhour_adapter,
        credit_monitor=credit_monitor,
        dedup_engine=dedup_engine,
        filter_engine=filter_engine,
        quality_scorer=quality_scorer,
        db_connection=db,
        hybrid_filter_engine=hybrid_filter_engine
    )
    
    logger.info("✅ Orchestrator instance created")
    return _orchestrator_instance


async def run_search_task(filters: FilterCriteria):
    """Background task to run search with detailed status updates."""
    global search_status
    
    try:
        search_status["message"] = "Initializing search..."
        logger.info("🚀 SEARCH TASK STARTED")
        
        orchestrator = get_orchestrator()
        
        search_status["message"] = "Clearing old results for fresh search..."
        logger.info("🧹 Starting cleanup phase...")
        
        # Update status for platform scraping progress
        search_status["message"] = "Starting platform scraping (Upwork, Freelancer, PeoplePerHour)..."
        logger.info("🔍 Starting platform scraping...")
        
        # We'll let the orchestrator handle the actual scraping
        # but we'll update status as it progresses
        result = await orchestrator.run(filters)
        
        if result.status == "success":
            # Show platform-specific results
            platform_results = []
            if result.upwork_leads > 0:
                platform_results.append(f"Upwork: {result.upwork_leads}")
            if result.freelancer_leads > 0:
                platform_results.append(f"Freelancer: {result.freelancer_leads}")
            if result.peopleperhour_leads > 0:
                platform_results.append(f"PeoplePerHour: {result.peopleperhour_leads}")
            
            platform_summary = " | ".join(platform_results) if platform_results else "No platforms successful"
            search_status["message"] = f"Search complete! Found {result.total_leads} leads ({platform_summary})"
            search_status["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"✅ SEARCH COMPLETED: {result.total_leads} leads found")
            
        else:
            # Check if it's a credit limit error
            error_msg = result.message.lower() if result.message else ""
            if "credit" in error_msg or "limit" in error_msg or "usage" in error_msg:
                search_status["message"] = "❌ Apify credits exhausted! Please update your APIFY_TOKEN with a new account or wait for monthly reset."
            else:
                search_status["message"] = f"Search failed: {result.message}"
            logger.error(f"❌ SEARCH FAILED: {result.message}")
            
    except Exception as e:
        search_status["message"] = f"Search error: {str(e)}"
        logger.error(f"💥 SEARCH TASK ERROR: {e}", exc_info=True)
    finally:
        search_status["is_running"] = False
        logger.info("🏁 SEARCH TASK FINISHED")


@router.post("/start")
async def start_search(request: SearchRequest):
    """
    Start a new lead generation search.
    
    This endpoint initiates a background search task that scrapes all platforms,
    applies filters, and stores results in the database.
    """
    global search_task, search_status
    
    if search_status["is_running"]:
        logger.warning("⚠️ Search already in progress, rejecting new request")
        raise HTTPException(status_code=400, detail="Search already in progress")
    
    try:
        logger.info(f"🚀 STARTING NEW SEARCH: keywords={request.keywords}")
        
        # Get orchestrator and reset cleanup flag for new search
        orchestrator = get_orchestrator()
        orchestrator.reset_cleanup_flag()
        logger.info("🔄 Orchestrator cleanup flag reset")
        
        # Create filter criteria
        filters = FilterCriteria(
            keywords=request.keywords,
            platforms=request.platforms,
            min_budget=request.min_budget,
            max_budget=request.max_budget,
            posted_within_hours=request.posted_within_hours,
            min_quality_score=request.min_quality_score,
            max_results_per_platform=request.max_results_per_platform,
            prioritize_24h=True
        )
        
        # Reset status
        search_status = {
            "is_running": True,
            "message": "Search started",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None
        }
        
        # Start background task
        search_task = asyncio.create_task(run_search_task(filters))
        
        logger.info("✅ Search task started successfully")
        return {
            "status": "started",
            "message": "Search initiated successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start search: {e}", exc_info=True)
        search_status["is_running"] = False
        raise HTTPException(status_code=500, detail=f"Failed to start search: {str(e)}")


@router.get("/status", response_model=SearchStatusResponse)
async def get_search_status():
    """
    Get current search status.
    
    Returns information about whether a search is running and its progress.
    """
    return SearchStatusResponse(**search_status)


@router.post("/reset-orchestrator")
async def reset_orchestrator():
    """
    Force reset the orchestrator instance to pick up new environment variables.
    Useful when API keys are updated.
    """
    global _orchestrator_instance, _last_gemini_key
    
    old_key = _last_gemini_key
    new_key = os.getenv('GEMINI_API_KEY')
    
    _orchestrator_instance = None
    _last_gemini_key = None
    
    logger.info("🔄 Orchestrator instance reset forced")
    
    return {
        "status": "success",
        "message": "Orchestrator reset successfully",
        "old_key_prefix": old_key[:10] + "..." if old_key else None,
        "new_key_prefix": new_key[:10] + "..." if new_key else None,
        "key_changed": old_key != new_key
    }


@router.get("/gemini-status")
async def get_gemini_status():
    """
    Test Gemini API status for debugging.
    """
    try:
        from lead_scraper.engines.gemini_embedding_engine import GeminiEmbeddingEngine
        import os
        
        # Test Gemini API
        embedding_engine = GeminiEmbeddingEngine()
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not gemini_api_key:
            return {
                "status": "error",
                "message": "GEMINI_API_KEY not found in environment",
                "ai_filtering": False
            }
        
        try:
            embedding_engine.initialize(api_key=gemini_api_key)
            api_working = embedding_engine.test_api_connection()
            
            return {
                "status": "success" if api_working else "quota_exceeded",
                "message": "Gemini API working" if api_working else "Gemini API quota exceeded - using fallback",
                "ai_filtering": api_working,
                "api_key_present": True,
                "api_key_prefix": gemini_api_key[:10] + "..." if gemini_api_key else None
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Gemini API error: {str(e)}",
                "ai_filtering": False,
                "api_key_present": True
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to test Gemini: {str(e)}",
            "ai_filtering": False
        }


@router.get("/results")
async def get_search_results(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    keywords: Optional[str] = Query(None, description="Filter by keywords (for re-filtering)"),
    posted_within_hours: int = Query(168, description="Show leads posted within this many hours (default: 7 days)"),
):
    """
    Get results from the most recent search.
    
    This endpoint returns leads that were found and filtered in the most recent search,
    not all leads in the database. This ensures users see only relevant, fresh results.
    """
    try:
        db = ConnectionManager(os.getenv('DATABASE_URL'))
        
        try:
            # Get leads from the most recent search - use user's time filter
            from datetime import datetime, timezone, timedelta
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=posted_within_hours)
            
            # IMPORTANT: Also check for very recent leads (last 5 minutes) to catch fresh search results
            # This handles the case where search just completed but leads are very new
            fresh_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            # Build WHERE clause for recent leads - use EITHER time filter OR very recent
            where_clauses = ["(created_at >= %s OR created_at >= %s)"]
            params = [recent_cutoff, fresh_cutoff]
            
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
            
            logger.info(f"🔍 SEARCH RESULTS DEBUG:")
            logger.info(f"  - Time cutoff: {recent_cutoff}")
            logger.info(f"  - Fresh cutoff: {fresh_cutoff}")
            logger.info(f"  - WHERE clause: {where_sql}")
            logger.info(f"  - Parameters: {params}")
            logger.info(f"  - Total matching leads: {total}")
            
            # Also check total leads in database
            total_in_db = db.execute("SELECT COUNT(*) FROM leads", ())[0][0]
            logger.info(f"  - Total leads in database: {total_in_db}")
            
            # Check very recent leads (last 5 minutes)
            very_recent = db.execute("SELECT COUNT(*) FROM leads WHERE created_at >= %s", (fresh_cutoff,))[0][0]
            logger.info(f"  - Very recent leads (5 min): {very_recent}")
            
            # Check recent leads without time filter
            recent_without_filter = db.execute("SELECT COUNT(*) FROM leads WHERE created_at >= %s", (recent_cutoff,))[0][0]
            logger.info(f"  - Recent leads (no keyword filter): {recent_without_filter}")
            
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
                "message": f"Showing {len(leads)} leads from recent search (last {posted_within_hours} hours)"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to fetch search results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch search results: {str(e)}")
