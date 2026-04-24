"""Lead generation orchestrator for coordinating the complete workflow."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

from lead_scraper.adapters.platform_adapter import PlatformAdapter
from lead_scraper.database.connection_manager import ConnectionManager
from lead_scraper.engines.credit_monitor import CreditMonitor
from lead_scraper.engines.deduplication_engine import DeduplicationEngine
from lead_scraper.engines.filter_engine import FilterEngine
from lead_scraper.engines.quality_scorer import QualityScorer
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.lead import Lead

# Import for type hints only to avoid circular imports
try:
    from lead_scraper.engines.hybrid_filter_engine import HybridFilterEngine
except ImportError:
    HybridFilterEngine = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class LeadGenerationResult:
    """Result object containing leads and metadata from orchestration."""
    
    status: str  # "success" | "error"
    leads: list[Lead]
    total_leads: int
    upwork_leads: int = 0
    fiverr_leads: int = 0
    freelancer_leads: int = 0
    peopleperhour_leads: int = 0
    duplicates_removed: int = 0
    credits_used: float = 0.0
    execution_time_seconds: float = 0.0
    message: str = ""
    
    def to_dict(self) -> dict:
        """Converts result to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "leads": [lead.to_dict() for lead in self.leads],
            "total_leads": self.total_leads,
            "upwork_leads": self.upwork_leads,
            "fiverr_leads": self.fiverr_leads,
            "freelancer_leads": self.freelancer_leads,
            "peopleperhour_leads": self.peopleperhour_leads,
            "duplicates_removed": self.duplicates_removed,
            "credits_used": self.credits_used,
            "execution_time_seconds": self.execution_time_seconds,
            "message": self.message
        }


class LeadGenerationOrchestrator:
    """Orchestrates the complete lead generation workflow."""
    
    def __init__(
        self,
        upwork_adapter: PlatformAdapter,
        fiverr_adapter: PlatformAdapter,
        freelancer_adapter: PlatformAdapter,
        peopleperhour_adapter: PlatformAdapter,
        credit_monitor: CreditMonitor,
        dedup_engine: DeduplicationEngine,
        filter_engine: FilterEngine,
        quality_scorer: QualityScorer,
        db_connection: ConnectionManager,
        hybrid_filter_engine: Optional[HybridFilterEngine] = None
    ):
        """Initialize the orchestrator with all required components.
        
        Args:
            upwork_adapter: Adapter for scraping Upwork
            fiverr_adapter: Adapter for scraping Fiverr
            freelancer_adapter: Adapter for scraping Freelancer
            peopleperhour_adapter: Adapter for scraping PeoplePerHour
            credit_monitor: Monitor for tracking Apify credit usage
            dedup_engine: Engine for removing duplicate leads
            filter_engine: Engine for applying user-defined filters
            quality_scorer: Scorer for calculating lead quality scores
            db_connection: Database connection manager
            hybrid_filter_engine: Optional engine for embedding-based filtering
        """
        self.upwork_adapter = upwork_adapter
        self.fiverr_adapter = fiverr_adapter
        self.freelancer_adapter = freelancer_adapter
        self.peopleperhour_adapter = peopleperhour_adapter
        self.credit_monitor = credit_monitor
        self.dedup_engine = dedup_engine
        self.filter_engine = filter_engine
        self.quality_scorer = quality_scorer
        self.db = db_connection
        self.hybrid_filter_engine = hybrid_filter_engine
        
        # Initialize cleanup flag - ALWAYS cleanup on first search
        self._cleanup_done = False
        
    def reset_cleanup_flag(self):
        """Reset cleanup flag to allow cleanup on next search."""
        self._cleanup_done = False
        logger.info("🔄 Cleanup flag reset - next search will perform cleanup")
    
    async def run(self, filters: FilterCriteria) -> LeadGenerationResult:
        """
        Executes the complete lead generation workflow with embedding-based filtering.
        
        NEW WORKFLOW:
        0. Clear old non-favorited leads (fresh results every search)
        1. Check credit availability
        2. Scrape three platforms in parallel (Upwork, Freelancer, PeoplePerHour)
           NOTE: Fiverr is disabled - returns gigs (seller offerings) not buyer requests
        3. Normalize and combine results
        4. Remove duplicates
        5. Calculate quality scores
        6. Apply NEW hybrid filtering pipeline:
           - Hard filters (date, quality ONLY - NO budget, NO keywords)
           - AI embedding matching (keywords used here for semantic search)
           - Preliminary ranking
           - Budget enrichment (visit URLs for top N jobs with missing budgets)
           - Final ranking (similarity + quality + recency + budget)
           - NO budget filtering (UI mode - show all jobs)
        7. Store in database
        8. Return results sorted by final score
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            LeadGenerationResult with semantically ranked leads
        """
        start_time = time.time()
        
        logger.info("🚀 STARTING LEAD GENERATION WORKFLOW")
        
        # Step 0: Clear old non-favorited leads for fresh results (ONLY ONCE PER SESSION)
        if not self._cleanup_done:
            try:
                logger.info("🧹 PERFORMING ONE-TIME CLEANUP...")
                self._clear_non_favorited_leads()
                self._cleanup_done = True
                logger.info("✅ Cleanup completed successfully")
            except Exception as e:
                logger.warning(f"⚠️ Cleanup failed: {e}. Continuing with search...")
        else:
            logger.info("🧹 CLEANUP ALREADY DONE - SKIPPING")
        
        # Step 1: Smart Credit Management - Skip expensive platforms when credits are low
        # NOTE: Fiverr excluded from credit estimation (disabled)
        upwork_cost = self.upwork_adapter.estimate_credits(filters)
        freelancer_cost = self.freelancer_adapter.estimate_credits(filters)
        peopleperhour_cost = self.peopleperhour_adapter.estimate_credits(filters)
        
        # Check available credits
        available_credits = self.credit_monitor.get_available_credits()
        logger.info(f"💰 Available credits: {available_credits}")
        logger.info(f"💰 Platform costs: Upwork={upwork_cost:.2f}, Freelancer={freelancer_cost:.2f}, PeoplePerHour={peopleperhour_cost:.2f}")
        
        # Smart platform selection based on available credits
        platforms_to_scrape = []
        estimated_cost = 0
        
        # Try all platforms if we have reasonable credits (>0.5)
        if available_credits >= 0.5:
            # Always try Freelancer first (usually cheapest and most reliable)
            if available_credits >= freelancer_cost:
                platforms_to_scrape.append(("Freelancer", self.freelancer_adapter))
                estimated_cost += freelancer_cost
                available_credits -= freelancer_cost
            
            # Try Upwork next (now much cheaper with new actor)
            if available_credits >= upwork_cost:
                platforms_to_scrape.append(("Upwork", self.upwork_adapter))
                estimated_cost += upwork_cost
                available_credits -= upwork_cost
            
            # Try PeoplePerHour last
            if available_credits >= peopleperhour_cost:
                platforms_to_scrape.append(("PeoplePerHour", self.peopleperhour_adapter))
                estimated_cost += peopleperhour_cost
        else:
            # Low credits - try just the cheapest platform
            cheapest_cost = min(upwork_cost, freelancer_cost, peopleperhour_cost)
            if available_credits >= cheapest_cost:
                if cheapest_cost == freelancer_cost:
                    platforms_to_scrape.append(("Freelancer", self.freelancer_adapter))
                elif cheapest_cost == upwork_cost:
                    platforms_to_scrape.append(("Upwork", self.upwork_adapter))
                else:
                    platforms_to_scrape.append(("PeoplePerHour", self.peopleperhour_adapter))
                estimated_cost = cheapest_cost
        
        if not platforms_to_scrape:
            logger.error("❌ Insufficient credits for any platform")
            return LeadGenerationResult(
                status="error",
                message="❌ Insufficient Apify credits! Need at least 0.05 credits to scrape any platform. Please update your APIFY_TOKEN.",
                leads=[],
                total_leads=0,
                execution_time_seconds=time.time() - start_time
            )
        
        logger.info(f"💰 Selected platforms: {[p[0] for p in platforms_to_scrape]} (estimated cost: {estimated_cost:.2f})")
        
        can_proceed, credit_message = self.credit_monitor.check_can_scrape(estimated_cost)
        if not can_proceed:
            logger.error(f"❌ Credit check failed: {credit_message}")
            return LeadGenerationResult(
                status="error",
                message=credit_message,
                leads=[],
                total_leads=0,
                execution_time_seconds=time.time() - start_time
            )
        
        logger.info(f"✅ Credit check passed: {credit_message}")
        
        # Step 2: Parallel scraping of selected platforms
        logger.info(f"🔍 Starting parallel scraping of {len(platforms_to_scrape)} platforms")
        
        # Create tasks for selected platforms only
        scraping_tasks = []
        for platform_name, adapter in platforms_to_scrape:
            task = asyncio.create_task(
                self._scrape_platform(adapter, filters, platform_name)
            )
            scraping_tasks.append((platform_name, task))
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*[task for _, task in scraping_tasks], return_exceptions=True)
        
        # Process results
        upwork_leads = []
        freelancer_leads = []
        peopleperhour_leads = []
        fiverr_leads = []  # Always empty since disabled
        
        for i, (platform_name, _) in enumerate(scraping_tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"❌ {platform_name} scraping failed: {result}")
                result = []
            
            if platform_name == "Upwork":
                upwork_leads = result
            elif platform_name == "Freelancer":
                freelancer_leads = result
            elif platform_name == "PeoplePerHour":
                peopleperhour_leads = result
        
        logger.info(
            f"📊 Scraping complete: {len(upwork_leads)} Upwork, "
            f"{len(fiverr_leads)} Fiverr (disabled), "
            f"{len(freelancer_leads)} Freelancer, "
            f"{len(peopleperhour_leads)} PeoplePerHour leads"
        )
        
        # Step 3: Combine results
        all_leads = upwork_leads + fiverr_leads + freelancer_leads + peopleperhour_leads
        logger.info(f"🔗 Combined {len(all_leads)} total leads")
        
        # Check if all platforms failed (likely due to credit exhaustion or timeout)
        if len(all_leads) == 0:
            # Check if it's likely a credit issue by looking at recent logs
            # This is a simple heuristic - if no leads from any platform, likely credits exhausted or timeout
            logger.warning("⚠️ No leads scraped from any platform - likely credit exhaustion or Vercel timeout")
            return LeadGenerationResult(
                status="error",
                message="❌ Search failed! Possible causes: 1) Apify credits exhausted 2) Vercel timeout (try fewer results) 3) Platform issues. Please check your APIFY_TOKEN or try again.",
                leads=[],
                total_leads=0,
                upwork_leads=len(upwork_leads),
                fiverr_leads=len(fiverr_leads),
                freelancer_leads=len(freelancer_leads),
                peopleperhour_leads=len(peopleperhour_leads),
                duplicates_removed=0,
                credits_used=estimated_cost,
                execution_time_seconds=time.time() - start_time
            )
        
        # Step 4: Deduplicate
        unique_leads = self.dedup_engine.remove_duplicates(all_leads)
        duplicates_removed = len(all_leads) - len(unique_leads)
        logger.info(f"🔄 Removed {duplicates_removed} duplicates, {len(unique_leads)} unique leads remain")
        
        # Step 5: Calculate quality scores with 24h prioritization
        for lead in unique_leads:
            lead.quality_score = self.quality_scorer.score_lead(
                lead, 
                filters,
                prioritize_24h=filters.prioritize_24h
            )
        
        logger.info("⭐ Quality scores calculated for all leads")
        
        # Step 6: Apply NEW hybrid filtering pipeline with budget enrichment
        # Try Gemini AI filtering first, fallback to basic filtering if it fails
        if self.hybrid_filter_engine and filters.keywords:
            try:
                logger.info("🤖 Attempting AI-powered semantic filtering with Gemini...")
                scored_leads = self.hybrid_filter_engine.filter_and_rank(
                    leads=unique_leads,  # Pass ALL leads, no pre-filtering
                    filters=filters,
                    use_embeddings=True,  # TRY AI FILTERING FIRST
                    apply_budget_filter=False  # UI mode: show all jobs, no budget filtering
                )
                # Convert ScoredLead objects back to Lead objects with updated quality_score
                filtered_leads = []
                for scored_lead in scored_leads:
                    lead = scored_lead.lead
                    # Use final_score as the quality_score for consistent sorting
                    lead.quality_score = scored_lead.final_score * 100  # Scale to 0-100
                    filtered_leads.append(lead)
                logger.info(f"✅ Gemini AI filtering successful: {len(filtered_leads)} semantically relevant leads")
                
            except Exception as e:
                logger.warning(f"⚠️ Gemini AI filtering failed: {e}")
                logger.info("🔄 Falling back to basic keyword filtering...")
                
                # Fallback: Try hybrid engine without embeddings
                try:
                    scored_leads = self.hybrid_filter_engine.filter_and_rank(
                        leads=unique_leads,
                        filters=filters,
                        use_embeddings=False,  # FALLBACK: Basic filtering
                        apply_budget_filter=False
                    )
                    filtered_leads = []
                    for scored_lead in scored_leads:
                        lead = scored_lead.lead
                        lead.quality_score = scored_lead.final_score * 100
                        filtered_leads.append(lead)
                    logger.info(f"✅ Basic filtering successful: {len(filtered_leads)} leads")
                    
                except Exception as e2:
                    logger.error(f"❌ Hybrid engine completely failed: {e2}")
                    # Final fallback: Use old filter engine
                    filtered_leads = self.filter_engine.apply_filters(unique_leads, filters)
                    filtered_leads.sort(key=lambda l: l.quality_score, reverse=True)
                    logger.info(f"✅ Old filter engine fallback: {len(filtered_leads)} leads")
        else:
            # No hybrid engine or no keywords: Use old filter engine
            logger.info("📊 Using basic filter engine (no AI)")
            filtered_leads = self.filter_engine.apply_filters(unique_leads, filters)
            filtered_leads.sort(key=lambda l: l.quality_score, reverse=True)
            logger.info(f"📊 Basic filtering complete: {len(filtered_leads)} leads")
        
        # Step 7: Store in database
        logger.info(f"💾 SAVING {len(filtered_leads)} leads to database...")
        try:
            # Log sample of leads being saved
            if filtered_leads:
                sample_lead = filtered_leads[0]
                logger.info(f"💾 SAMPLE LEAD: {sample_lead.job_title[:50]}... | {sample_lead.platform_name} | Score: {sample_lead.quality_score}")
            
            # Check database state before insert
            pre_count_result = self.db.execute("SELECT COUNT(*) FROM leads", ())
            pre_count = pre_count_result[0][0] if pre_count_result else 0
            logger.info(f"💾 PRE-INSERT: {pre_count} leads in database")
            
            inserted_count = self.db.bulk_insert(filtered_leads)
            logger.info(f"✅ BULK INSERT RETURNED: {inserted_count} leads inserted")
            
            # Check database state after insert
            post_count_result = self.db.execute("SELECT COUNT(*) FROM leads", ())
            post_count = post_count_result[0][0] if post_count_result else 0
            logger.info(f"💾 POST-INSERT: {post_count} leads in database")
            
            # Verify some leads are actually there
            recent_leads = self.db.execute(
                "SELECT id, job_title, platform_name, created_at FROM leads ORDER BY created_at DESC LIMIT 3", 
                ()
            )
            logger.info(f"💾 RECENT LEADS IN DB: {len(recent_leads)} found")
            for lead in recent_leads:
                logger.info(f"  - ID:{lead[0]} | {lead[2]} | {lead[1][:30]}... | {lead[3]}")
                
        except Exception as e:
            logger.error(f"❌ Failed to store leads in database: {e}")
            # Continue even if database storage fails
        
        # Step 8: Return results
        execution_time = time.time() - start_time
        
        # Final database verification before returning
        try:
            final_count_result = self.db.execute("SELECT COUNT(*) FROM leads", ())
            final_count = final_count_result[0][0] if final_count_result else 0
            logger.info(f"🔍 FINAL VERIFICATION: {final_count} leads in database at end of workflow")
        except Exception as e:
            logger.warning(f"Failed to verify final database state: {e}")
        
        result = LeadGenerationResult(
            status="success",
            leads=filtered_leads,
            total_leads=len(filtered_leads),
            upwork_leads=len(upwork_leads),
            fiverr_leads=len(fiverr_leads),
            freelancer_leads=len(freelancer_leads),
            peopleperhour_leads=len(peopleperhour_leads),
            duplicates_removed=duplicates_removed,
            credits_used=estimated_cost,
            execution_time_seconds=execution_time,
            message=f"Successfully generated {len(filtered_leads)} leads in {execution_time:.2f}s"
        )
        
        logger.info(f"🎉 {result.message}")
        return result
    
    async def _scrape_platform(
        self, 
        adapter: PlatformAdapter, 
        filters: FilterCriteria,
        platform_name: str
    ) -> list[Lead]:
        """Scrapes a single platform with error handling.
        
        Ensures that one platform failure doesn't block the other platform.
        
        Args:
            adapter: Platform adapter to use for scraping
            filters: User-defined filter criteria
            platform_name: Name of the platform (for logging)
            
        Returns:
            List of normalized Lead objects, or empty list on failure
        """
        try:
            logger.info(f"Scraping {platform_name}...")
            raw_leads = await adapter.scrape(filters)
            logger.info(f"Retrieved {len(raw_leads)} raw leads from {platform_name}")
            
            normalized_leads = [adapter.normalize(raw) for raw in raw_leads]
            logger.info(f"Normalized {len(normalized_leads)} leads from {platform_name}")
            
            return normalized_leads
            
        except Exception as e:
            logger.error(
                f"Failed to scrape {platform_name}: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            adapter.handle_error(e)
            return []  # Return empty list on failure, don't block other platforms
    
    def _clear_non_favorited_leads(self) -> None:
        """
        Clear all non-favorited leads from database before each search.
        
        This ensures fresh results every time while preserving user's starred jobs.
        AGGRESSIVE VERSION - Guarantees fresh results on Vercel.
        """
        try:
            logger.info("🧹 STARTING AGGRESSIVE CLEANUP for fresh results")
            
            # Count leads before cleanup
            count_query = "SELECT COUNT(*) FROM leads"
            total_result = self.db.execute(count_query, ())
            total_before = total_result[0][0] if total_result else 0
            
            # Count favorited leads
            fav_query = "SELECT COUNT(*) FROM leads WHERE is_favorited = TRUE"
            fav_result = self.db.execute(fav_query, ())
            favorited_count = fav_result[0][0] if fav_result else 0
            
            logger.info(f"🧹 BEFORE CLEANUP: {total_before} total leads, {favorited_count} favorited")
            
            if total_before == 0:
                logger.info("Database is empty, no cleanup needed")
                return
            
            if total_before == favorited_count:
                logger.info(f"All {total_before} leads are favorited, no cleanup needed")
                return
            
            # AGGRESSIVE CLEANUP: Delete ALL non-favorited leads
            # This guarantees fresh results every search
            delete_query = """
                DELETE FROM leads 
                WHERE (is_favorited = FALSE OR is_favorited IS NULL)
            """
            logger.info("🧹 AGGRESSIVE CLEANUP: Deleting ALL non-favorited leads for fresh results")
            self.db.execute(delete_query, ())
            
            # Count remaining leads
            remaining_result = self.db.execute(count_query, ())
            total_after = remaining_result[0][0] if remaining_result else 0
            
            deleted_count = total_before - total_after
            logger.info(
                f"🧹 CLEANUP COMPLETE: Deleted {deleted_count} old leads, "
                f"kept {total_after} favorited leads - FRESH RESULTS GUARANTEED!"
            )
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            # Don't re-raise - continue with search even if cleanup fails
            logger.warning("Continuing with search despite cleanup failure")
