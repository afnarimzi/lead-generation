"""FastMCP server for lead generation system."""

import asyncio
import logging
from typing import Optional

from fastmcp import FastMCP

from lead_scraper.adapters.upwork_adapter import UpworkAdapter
from lead_scraper.adapters.fiverr_adapter import FiverrAdapter
from lead_scraper.adapters.freelancer_adapter import FreelancerAdapter
from lead_scraper.adapters.peopleperhour_adapter import PeoplePerHourAdapter
from lead_scraper.database.connection_manager import ConnectionManager
from lead_scraper.engines.credit_monitor import CreditMonitor
from lead_scraper.engines.deduplication_engine import DeduplicationEngine
from lead_scraper.engines.filter_engine import FilterEngine
from lead_scraper.engines.quality_scorer import QualityScorer
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.system_config import SystemConfig
from lead_scraper.orchestrator import LeadGenerationOrchestrator
from lead_scraper.config.auth_loader import load_auth_config
from lead_scraper.tools.embedding_lead_search_tool import EmbeddingLeadSearchTool


logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Lead Scraper")

# Global orchestrator instance (initialized on startup)
orchestrator: Optional[LeadGenerationOrchestrator] = None
embedding_search_tool: Optional[EmbeddingLeadSearchTool] = None


def initialize_orchestrator(config: SystemConfig) -> LeadGenerationOrchestrator:
    """Initialize the orchestrator with all required components.
    
    Args:
        config: System configuration
        
    Returns:
        Initialized LeadGenerationOrchestrator instance
    """
    # Initialize database connection
    db_connection = ConnectionManager(
        database_url=config.database_url,
        pool_size=config.database_pool_size
    )
    
    # Initialize credit monitor
    credit_monitor = CreditMonitor(
        apify_token=config.apify_token,
        free_plan_limit=config.free_plan_credit_limit,
        warning_threshold=config.credit_warning_threshold,
        stop_threshold=config.credit_stop_threshold
    )
    
    # Initialize platform adapters
    upwork_adapter = UpworkAdapter(
        apify_token=config.apify_token,
        actor_id=config.apify_upwork_actor_id,
        auth_config=load_auth_config('upwork')
    )
    
    fiverr_adapter = FiverrAdapter(
        apify_token=config.apify_token,
        actor_id=config.apify_fiverr_actor_id,
        auth_config=load_auth_config('fiverr')
    )
    
    freelancer_adapter = FreelancerAdapter(
        apify_token=config.apify_token,
        actor_id=config.apify_freelancer_actor_id,
        auth_config=load_auth_config('freelancer')
    )
    
    peopleperhour_adapter = PeoplePerHourAdapter(
        apify_token=config.apify_token,
        actor_id=config.apify_peopleperhour_actor_id,
        auth_config=load_auth_config('peopleperhour')
    )
    
    # Initialize engines
    dedup_engine = DeduplicationEngine(db_connection=db_connection)
    filter_engine = FilterEngine()
    quality_scorer = QualityScorer()
    
    # Initialize hybrid filter engine with Gemini embedding support
    try:
        from lead_scraper.engines.hybrid_filter_engine import HybridFilterEngine
        from lead_scraper.engines.gemini_embedding_engine import GeminiEmbeddingEngine
        from lead_scraper.engines.budget_enrichment_engine import BudgetEnrichmentEngine
        import os
        
        # Initialize Gemini embedding engine
        embedding_engine = GeminiEmbeddingEngine()
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            embedding_engine.initialize(api_key=gemini_api_key)
            logger.info("✓ Gemini embedding engine initialized")
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables")
            raise ValueError("Gemini API key required")
        
        budget_enrichment_engine = BudgetEnrichmentEngine()
        
        hybrid_filter_engine = HybridFilterEngine(
            embedding_engine=embedding_engine,
            budget_enrichment_engine=budget_enrichment_engine,
            similarity_threshold=0.15,  # Lower threshold for better recall
            embedding_weight=0.4,      # Updated weights
            quality_weight=0.2,
            recency_weight=0.1,
            budget_weight=0.3,         # Increased budget weight
            top_n_to_enrich=50,
            enable_enrichment=True
        )
        logger.info("✓ Hybrid filter engine initialized with Gemini embedding support")
    except Exception as e:
        logger.warning(f"Failed to initialize hybrid filter engine: {e}")
        logger.warning("Falling back to basic filtering")
        hybrid_filter_engine = None
    
    # Create orchestrator
    orch = LeadGenerationOrchestrator(
        upwork_adapter=upwork_adapter,
        fiverr_adapter=fiverr_adapter,
        freelancer_adapter=freelancer_adapter,
        peopleperhour_adapter=peopleperhour_adapter,
        credit_monitor=credit_monitor,
        dedup_engine=dedup_engine,
        filter_engine=filter_engine,
        quality_scorer=quality_scorer,
        db_connection=db_connection,
        hybrid_filter_engine=hybrid_filter_engine
    )
    
    # Initialize embedding search tool
    global embedding_search_tool
    try:
        embedding_search_tool = EmbeddingLeadSearchTool(
            db_connection=db_connection,
            similarity_threshold=0.6,
            embedding_weight=0.7,
            quality_weight=0.2,
            recency_weight=0.1
        )
        logger.info("✓ Embedding search tool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize embedding search tool: {e}")
        logger.warning("Embedding-based search will not be available")
        embedding_search_tool = None
    
    return orch


@mcp.tool()
async def export_leads(
    format: str = "json",
    lead_ids: Optional[list[int]] = None,
    output_path: Optional[str] = None
) -> dict:
    """
    Exports leads to specified format.
    
    Exports filtered leads to CSV, JSON, or Google Sheets format. If lead_ids
    is not provided, exports all recent leads from the database.
    
    Args:
        format: Export format - "json", "csv", or "google_sheets" (default: "json")
        lead_ids: List of specific lead IDs to export (optional, exports all if None)
        output_path: Output file path for csv/json (optional, uses default if None)
    
    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - format: Export format used
        - output_path: File path or Google Sheets URL
        - leads_exported: Number of leads exported
        - message: Status message
    """
    global orchestrator
    
    # Validate parameters
    valid_formats = ["json", "csv", "google_sheets"]
    if format not in valid_formats:
        return {
            "status": "error",
            "error_code": "INVALID_FORMAT",
            "message": f"Invalid export format: {format}",
            "details": {"valid_formats": valid_formats},
            "suggestion": f"Please use one of: {', '.join(valid_formats)}"
        }
    
    # Check if orchestrator is initialized
    if orchestrator is None:
        return {
            "status": "error",
            "error_code": "SERVER_NOT_INITIALIZED",
            "message": "Server not properly initialized",
            "details": None,
            "suggestion": "Please ensure the server is started with valid configuration"
        }
    
    try:
        # Import ExportEngine (will be implemented in task 14)
        try:
            from lead_scraper.engines.export_engine import ExportEngine
        except ImportError:
            return {
                "status": "error",
                "error_code": "EXPORT_NOT_IMPLEMENTED",
                "message": "Export functionality is not yet implemented",
                "details": None,
                "suggestion": "Export engine will be available in a future update"
            }
        
        # Initialize export engine
        export_engine = ExportEngine(db_connection=orchestrator.db)
        
        # Perform export based on format
        if format == "csv":
            result_path = await export_engine.export_to_csv(
                lead_ids=lead_ids,
                output_path=output_path
            )
        elif format == "json":
            result_path = await export_engine.export_to_json(
                lead_ids=lead_ids,
                output_path=output_path
            )
        elif format == "google_sheets":
            result_path = await export_engine.export_to_google_sheets(
                lead_ids=lead_ids
            )
        
        # Count exported leads
        if lead_ids:
            leads_exported = len(lead_ids)
        else:
            # Query database to count all leads
            query = "SELECT COUNT(*) FROM leads"
            result = orchestrator.db.execute(query)
            leads_exported = result[0][0] if result else 0
        
        return {
            "status": "success",
            "format": format,
            "output_path": result_path,
            "leads_exported": leads_exported,
            "message": f"Successfully exported {leads_exported} leads to {format}"
        }
        
    except Exception as e:
        logger.error(f"Error in export_leads: {type(e).__name__}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_code": "EXPORT_FAILED",
            "message": f"Failed to export leads: {str(e)}",
            "details": {"error_type": type(e).__name__},
            "suggestion": "Please check the logs for more details and try again"
        }


@mcp.tool()
async def check_credits() -> dict:
    """
    Checks current Apify credit usage and balance.
    
    Returns current credit statistics including total credits, used credits,
    remaining credits, usage percentage, and warning flag if approaching limits.
    
    Returns:
        Dictionary containing:
        - total_credits: Total monthly credits available
        - used_credits: Credits used this month
        - remaining_credits: Credits remaining
        - usage_percentage: Percentage of credits used
        - warning: True if usage is at or above warning threshold
        - last_updated: ISO 8601 timestamp of when data was retrieved
    """
    global orchestrator
    
    # Check if orchestrator is initialized
    if orchestrator is None:
        return {
            "status": "error",
            "error_code": "SERVER_NOT_INITIALIZED",
            "message": "Server not properly initialized",
            "details": None,
            "suggestion": "Please ensure the server is started with valid configuration"
        }
    
    try:
        # Get credit usage from monitor
        usage = orchestrator.credit_monitor.get_usage()
        
        return {
            "total_credits": usage.total_credits,
            "used_credits": usage.used_credits,
            "remaining_credits": usage.remaining_credits,
            "usage_percentage": usage.usage_percentage,
            "warning": usage.usage_percentage >= orchestrator.credit_monitor.warning_threshold,
            "last_updated": usage.last_updated.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in check_credits: {type(e).__name__}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_code": "CREDIT_CHECK_FAILED",
            "message": f"Failed to retrieve credit information: {str(e)}",
            "details": {"error_type": type(e).__name__},
            "suggestion": "Please check your Apify token and try again"
        }


@mcp.tool()
async def embedding_lead_search(
    keywords: list[str],
    platforms: Optional[list[str]] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    posted_within_hours: Optional[int] = 168,
    min_quality_score: Optional[float] = None,
    max_results: int = 50,
    use_embeddings: bool = True,
    similarity_threshold: Optional[float] = None
) -> dict:
    """
    Search for leads using semantic similarity with embeddings.
    
    Uses Gemini API to compute semantic similarity between search
    keywords and job postings. Combines embedding similarity with quality scores
    and recency for intelligent ranking.
    
    Args:
        keywords: Search keywords (e.g., ["AI", "machine learning", "python"])
        platforms: Filter by platforms (e.g., ["Upwork", "Freelancer"]) (optional)
        min_budget: Minimum budget amount (optional)
        max_budget: Maximum budget amount (optional)
        posted_within_hours: Only include jobs posted within N hours (default: 168 = 7 days)
        min_quality_score: Minimum quality score threshold (optional)
        max_results: Maximum number of results to return (default: 50)
        use_embeddings: Whether to use embedding-based filtering (default: True)
        similarity_threshold: Minimum similarity score (default: 0.6) (optional)
    
    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - total_results: Number of leads returned
        - leads: List of ranked leads with scores
        - search_params: Search parameters used
        - scoring_info: Scoring weights and thresholds
    """
    global embedding_search_tool
    
    # Check if embedding search tool is available
    if embedding_search_tool is None:
        return {
            "status": "error",
            "error_code": "EMBEDDING_SEARCH_NOT_AVAILABLE",
            "message": "Embedding search tool is not initialized",
            "details": None,
            "suggestion": "Please ensure Gemini API is configured and the server is properly initialized"
        }
    
    # Validate parameters
    validation_errors = []
    
    if not keywords:
        validation_errors.append("keywords list cannot be empty")
    
    if min_budget is not None and min_budget < 0:
        validation_errors.append("min_budget must be non-negative")
    
    if max_budget is not None and max_budget < 0:
        validation_errors.append("max_budget must be non-negative")
    
    if min_budget is not None and max_budget is not None and min_budget > max_budget:
        validation_errors.append("min_budget must be less than or equal to max_budget")
    
    if posted_within_hours and posted_within_hours < 0:
        validation_errors.append("posted_within_hours must be non-negative")
    
    if max_results < 1:
        validation_errors.append("max_results must be at least 1")
    
    if similarity_threshold is not None and (similarity_threshold < 0 or similarity_threshold > 1):
        validation_errors.append("similarity_threshold must be between 0 and 1")
    
    if validation_errors:
        return {
            "status": "error",
            "error_code": "INVALID_PARAMETERS",
            "message": "Invalid parameters provided",
            "details": {"validation_errors": validation_errors},
            "suggestion": "Please check the parameter values and try again"
        }
    
    try:
        # Update similarity threshold if provided
        if similarity_threshold is not None:
            embedding_search_tool.update_similarity_threshold(similarity_threshold)
        
        # Perform search
        result = embedding_search_tool.search(
            keywords=keywords,
            platforms=platforms,
            min_budget=min_budget,
            max_budget=max_budget,
            posted_within_hours=posted_within_hours,
            min_quality_score=min_quality_score,
            max_results=max_results,
            use_embeddings=use_embeddings
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in embedding_lead_search: {type(e).__name__}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_code": "SEARCH_FAILED",
            "message": f"Embedding search failed: {str(e)}",
            "details": {"error_type": type(e).__name__},
            "suggestion": "Please check the logs for more details and try again"
        }


@mcp.tool()
async def run_lead_generation(
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    posted_within_hours: int = 72,
    prioritize_24h: bool = True,
    experience_levels: Optional[list[str]] = None,
    max_results_per_platform: int = 100,
    min_quality_score: float = 0.0
) -> dict:
    """
    Orchestrates complete lead generation workflow.
    
    Scrapes all four platforms (Upwork, Fiverr, Freelancer, PeoplePerHour) in parallel,
    normalizes and combines results, removes duplicates, applies filters, calculates
    quality scores, sorts by relevance and recency, and returns unified lead list.
    
    Args:
        categories: List of job categories to filter by (optional)
        keywords: List of keywords to search for in job title/description (optional)
        min_budget: Minimum budget amount (optional)
        max_budget: Maximum budget amount (optional)
        posted_within_hours: Only include jobs posted within this many hours (default: 72)
        prioritize_24h: Add bonus score to jobs posted in last 24 hours (default: True)
        experience_levels: List of experience levels to filter by (optional)
        max_results_per_platform: Maximum results to fetch per platform (default: 100)
        min_quality_score: Minimum quality score threshold (default: 0.0)
    
    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - leads: List of lead dictionaries sorted by quality score
        - total_leads: Total number of leads returned
        - upwork_leads: Number of leads from Upwork
        - fiverr_leads: Number of leads from Fiverr
        - freelancer_leads: Number of leads from Freelancer
        - peopleperhour_leads: Number of leads from PeoplePerHour
        - duplicates_removed: Number of duplicates removed
        - credits_used: Estimated Apify credits consumed
        - execution_time_seconds: Time taken to complete workflow
        - message: Status message
    """
    global orchestrator
    
    # Validate parameters
    validation_errors = []
    
    if min_budget is not None and min_budget < 0:
        validation_errors.append("min_budget must be non-negative")
    
    if max_budget is not None and max_budget < 0:
        validation_errors.append("max_budget must be non-negative")
    
    if min_budget is not None and max_budget is not None and min_budget > max_budget:
        validation_errors.append("min_budget must be less than or equal to max_budget")
    
    if posted_within_hours < 0:
        validation_errors.append("posted_within_hours must be non-negative")
    
    if max_results_per_platform < 1:
        validation_errors.append("max_results_per_platform must be at least 1")
    
    if min_quality_score < 0 or min_quality_score > 100:
        validation_errors.append("min_quality_score must be between 0 and 100")
    
    if validation_errors:
        return {
            "status": "error",
            "error_code": "INVALID_PARAMETERS",
            "message": "Invalid parameters provided",
            "details": {"validation_errors": validation_errors},
            "suggestion": "Please check the parameter values and try again"
        }
    
    # Check if orchestrator is initialized
    if orchestrator is None:
        return {
            "status": "error",
            "error_code": "SERVER_NOT_INITIALIZED",
            "message": "Server not properly initialized",
            "details": None,
            "suggestion": "Please ensure the server is started with valid configuration"
        }
    
    # Create filter criteria
    filters = FilterCriteria(
        categories=categories,
        keywords=keywords,
        min_budget=min_budget,
        max_budget=max_budget,
        posted_within_hours=posted_within_hours,
        experience_levels=experience_levels,
        prioritize_24h=prioritize_24h,
        max_results_per_platform=max_results_per_platform,
        min_quality_score=min_quality_score
    )
    
    try:
        # Run orchestrator
        result = await orchestrator.run(filters)
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Error in run_lead_generation: {type(e).__name__}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": f"An error occurred during lead generation: {str(e)}",
            "details": {"error_type": type(e).__name__},
            "suggestion": "Please check the logs for more details and try again"
        }


if __name__ == "__main__":
    # Load configuration
    import os
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Create config from environment variables
    config = SystemConfig(
        apify_token=os.getenv("APIFY_TOKEN", ""),
        apify_upwork_actor_id=os.getenv("APIFY_UPWORK_ACTOR_ID", ""),
        apify_fiverr_actor_id=os.getenv("APIFY_FIVERR_ACTOR_ID", ""),
        apify_freelancer_actor_id=os.getenv("APIFY_FREELANCER_ACTOR_ID", ""),
        apify_peopleperhour_actor_id=os.getenv("APIFY_PEOPLEPERHOUR_ACTOR_ID", ""),
        database_url=os.getenv("DATABASE_URL", ""),
        free_plan_credit_limit=float(os.getenv("FREE_PLAN_CREDIT_LIMIT", "5.0")),
        credit_warning_threshold=float(os.getenv("CREDIT_WARNING_THRESHOLD", "80.0")),
        credit_stop_threshold=float(os.getenv("CREDIT_STOP_THRESHOLD", "95.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        exit(1)
    
    # Initialize orchestrator
    orchestrator = initialize_orchestrator(config)
    
    # Determine transport mode
    # If stdin is a TTY (terminal), run in HTTP mode for Chatbox
    # If stdin is a pipe (from Claude Desktop), run in stdio mode
    if sys.stdin.isatty():
        # Running from terminal - use HTTP mode for Chatbox
        print("🚀 Starting MCP server in HTTP mode...")
        print("📡 Server listening on http://localhost:3333")
        print("💡 Use this URL in Chatbox: http://localhost:3333/sse")
        print("⏹️  Press Ctrl+C to stop the server")
        mcp.run(transport="sse", host="127.0.0.1", port=3333)
    else:
        # Running from Claude Desktop or other stdio client
        mcp.run()
