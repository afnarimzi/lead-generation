"""
Hybrid filter engine combining rule-based and embedding-based filtering.
"""
import logging
import asyncio
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.engines.gemini_embedding_engine import GeminiEmbeddingEngine
from lead_scraper.engines.budget_enrichment_engine import BudgetEnrichmentEngine
from lead_scraper.engines.budget_estimator import BudgetEstimator

logger = logging.getLogger(__name__)


@dataclass
class ScoredLead:
    """Lead with computed scores."""
    lead: Lead
    embedding_similarity: float
    quality_score_normalized: float
    recency_score: float
    budget_score: float
    final_score: float



class HybridFilterEngine:
    """
    Hybrid filtering engine with budget enrichment pipeline.
    
    NEW PIPELINE:
    1. Hard filters (date, quality ONLY - NO budget, NO keywords)
    2. AI embedding matching (keywords used here for semantic search)
    3. Preliminary ranking (similarity + quality + recency)
    4. Budget enrichment (visit URLs for top N jobs with missing budgets)
    5. Final ranking (similarity + quality + recency + budget)
    6. Optional budget filter (API mode only, after enrichment)
    
    Key Features:
    - Budget is a RANKING factor, not a filter
    - Only top N jobs are enriched (performance optimization)
    - Budget enrichment is async and cached
    - All jobs are visible by default (UI mode)
    - Budget filtering only when explicitly requested (API mode)
    """
    
    def __init__(
        self,
        embedding_engine: Optional[GeminiEmbeddingEngine] = None,
        budget_enrichment_engine: Optional[BudgetEnrichmentEngine] = None,
        budget_estimator: Optional[BudgetEstimator] = None,
        similarity_threshold: float = 0.70,  # Stricter threshold to exclude unrelated jobs
        embedding_weight: float = 0.6,
        quality_weight: float = 0.2,
        recency_weight: float = 0.1,
        budget_weight: float = 0.1,
        top_n_to_enrich: int = 50,
        enable_enrichment: bool = True,
        enable_estimation: bool = True
    ):
        """
        Initialize hybrid filter engine.

        Args:
            embedding_engine: EmbeddingEngine instance (creates new if None)
            budget_enrichment_engine: BudgetEnrichmentEngine instance (creates new if None)
            budget_estimator: BudgetEstimator instance (creates new if None)
            similarity_threshold: Minimum similarity score to keep leads
            embedding_weight: Weight for embedding similarity in final score (default: 0.6)
            quality_weight: Weight for quality score in final score (default: 0.2)
            recency_weight: Weight for recency in final score (default: 0.1)
            budget_weight: Weight for budget score in final score (default: 0.1)
            top_n_to_enrich: Number of top leads to enrich with budget data
            enable_enrichment: Whether to enable budget enrichment from URLs
            enable_estimation: Whether to enable budget estimation for missing budgets
        """
        self.embedding_engine = embedding_engine or GeminiEmbeddingEngine()
        self.budget_enrichment_engine = budget_enrichment_engine or BudgetEnrichmentEngine()
        self.budget_estimator = budget_estimator or BudgetEstimator()
        self.similarity_threshold = similarity_threshold
        self.embedding_weight = embedding_weight
        self.quality_weight = quality_weight
        self.recency_weight = recency_weight
        self.budget_weight = budget_weight
        self.top_n_to_enrich = top_n_to_enrich
        self.enable_enrichment = enable_enrichment
        self.enable_estimation = enable_estimation

        # Validate weights sum to 1.0
        total_weight = embedding_weight + quality_weight + recency_weight + budget_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                f"Weights sum to {total_weight}, not 1.0. "
                "Normalizing weights."
            )
            self.embedding_weight /= total_weight
            self.quality_weight /= total_weight
            self.recency_weight /= total_weight
            self.budget_weight /= total_weight

    
    def filter_and_rank(
        self,
        leads: List[Lead],
        filters: FilterCriteria,
        use_embeddings: bool = True,
        apply_budget_filter: bool = False
    ) -> List[ScoredLead]:
        """
        Apply hybrid filtering and ranking pipeline with budget enrichment.

        NEW PIPELINE:
        1. Apply hard filters (date, quality ONLY - NO budget, NO keywords!)
        2. Compute embedding similarities (if enabled)
        3. Filter by similarity threshold
        4. Compute preliminary scores (similarity + quality + recency)
        5. Sort by preliminary score
        6. Enrich top N leads with missing budget data (visit URLs)
        7. Compute final scores (including budget)
        8. Sort by final score
        9. Optionally apply budget filter (API mode only)

        Note: Budget enrichment only happens for top-ranked jobs to optimize performance.

        Args:
            leads: List of leads to filter
            filters: Filter criteria
            use_embeddings: Whether to use embedding-based filtering
            apply_budget_filter: Whether to apply budget filtering (API mode only)

        Returns:
            List of ScoredLead objects, sorted by final_score descending
        """
        if not leads:
            return []

        logger.info(f"Starting hybrid filtering on {len(leads)} leads")

        # Step 1: Apply hard filters (NO budget, NO keywords!)
        filtered_leads = self._apply_hard_filters(leads, filters)
        logger.info(
            f"After hard filters: {len(filtered_leads)}/{len(leads)} leads remain"
        )

        if not filtered_leads:
            return []

        # Step 2-3: Compute embedding similarities and filter by threshold
        if use_embeddings and filters.keywords:
            try:
                logger.info(f"Computing embedding similarities for {len(filtered_leads)} leads...")
                scored_leads = self._compute_embedding_scores(
                    filtered_leads, 
                    filters
                )

                before_similarity = len(scored_leads)
                scored_leads = [
                    sl for sl in scored_leads 
                    if sl.embedding_similarity >= self.similarity_threshold
                ]
                after_similarity = len(scored_leads)

                logger.info(
                    f"After similarity filter: {after_similarity} leads remain "
                    f"(threshold: {self.similarity_threshold}, removed: {before_similarity - after_similarity})"
                )

            except Exception as e:
                logger.error(f"Embedding filtering failed: {e}. Falling back to keyword matching.")
                # Use keyword-based filtering instead of giving all leads high similarity
                scored_leads = []
                for lead in filtered_leads:
                    # Calculate keyword similarity instead of defaulting to 0.7
                    keyword_similarity = self._calculate_keyword_similarity(lead, filters.keywords)
                    if keyword_similarity >= self.similarity_threshold:
                        scored_leads.append(
                            self._create_scored_lead(lead, embedding_similarity=keyword_similarity, filters=filters)
                        )
        else:
            # No embedding engine - use keyword matching
            scored_leads = []
            for lead in filtered_leads:
                keyword_similarity = self._calculate_keyword_similarity(lead, filters.keywords)
                if keyword_similarity >= self.similarity_threshold:
                    scored_leads.append(
                        self._create_scored_lead(lead, embedding_similarity=keyword_similarity, filters=filters)
                    )

        if not scored_leads:
            return []

        # Step 4-5: Sort by preliminary score (without budget)
        scored_leads.sort(key=lambda x: x.final_score, reverse=True)

        logger.info(
            f"Preliminary ranking complete: {len(scored_leads)} leads ranked"
        )

        # Step 6: Enrich top N leads with missing budget data
        if self.enable_enrichment:
            try:
                # Extract Lead objects for enrichment
                top_leads = [sl.lead for sl in scored_leads[:self.top_n_to_enrich]]

                # Run async enrichment
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, create a new task
                    asyncio.create_task(
                        self.budget_enrichment_engine.enrich_top_leads(
                            top_leads,
                            self.top_n_to_enrich
                        )
                    )
                else:
                    # Run in new event loop
                    loop.run_until_complete(
                        self.budget_enrichment_engine.enrich_top_leads(
                            top_leads,
                            self.top_n_to_enrich
                        )
                    )

                logger.info(
                    f"Budget enrichment complete for top {self.top_n_to_enrich} leads"
                )

            except Exception as e:
                logger.warning(f"Budget enrichment failed: {e}. Continuing without enrichment.")

        # Step 6.5: Estimate budgets for remaining jobs without budget data
        if self.enable_estimation:
            try:
                estimation_count = 0
                for scored_lead in scored_leads:
                    if scored_lead.lead.budget_amount is None:
                        estimate = self.budget_estimator.estimate_budget(
                            job_title=scored_lead.lead.job_title or "",
                            job_description=scored_lead.lead.job_description or "",
                            skills=scored_lead.lead.skills_tags or [],
                            platform=scored_lead.lead.platform_name.lower()
                        )
                        
                        if estimate and estimate.confidence > 0.3:  # Only use confident estimates
                            scored_lead.lead.budget_amount = estimate.amount
                            # Mark as estimated in metadata
                            if not hasattr(scored_lead.lead, 'metadata'):
                                scored_lead.lead.metadata = {}
                            scored_lead.lead.metadata['budget_estimated'] = True
                            scored_lead.lead.metadata['budget_confidence'] = estimate.confidence
                            scored_lead.lead.metadata['budget_method'] = estimate.method
                            estimation_count += 1
                
                if estimation_count > 0:
                    logger.info(f"Estimated budgets for {estimation_count} additional leads")
                    
            except Exception as e:
                logger.warning(f"Budget estimation failed: {e}. Continuing without estimation.")

        # Step 7: Recalculate scores with enriched budget data
        for scored_lead in scored_leads:
            # Recalculate budget score with potentially enriched data
            budget_score = self._compute_budget_score(scored_lead.lead, filters)
            scored_lead.budget_score = budget_score

            # Recalculate final score
            scored_lead.final_score = (
                self.embedding_weight * scored_lead.embedding_similarity +
                self.quality_weight * scored_lead.quality_score_normalized +
                self.recency_weight * scored_lead.recency_score +
                self.budget_weight * budget_score
            )

        # Step 8: Sort by final score (with budget)
        scored_leads.sort(key=lambda x: x.final_score, reverse=True)

        logger.info(
            f"Final ranking complete: {len(scored_leads)} leads ranked"
        )

        # Step 9: Optionally apply budget filter (API mode only)
        if apply_budget_filter and (filters.min_budget or filters.max_budget):
            original_count = len(scored_leads)
            scored_leads = self._apply_budget_filter_post_enrichment(
                scored_leads,
                filters
            )
            logger.info(
                f"Budget filter applied: {len(scored_leads)}/{original_count} leads remain"
            )

        return scored_leads

    
    def _apply_hard_filters(
        self, 
        leads: List[Lead], 
        filters: FilterCriteria
    ) -> List[Lead]:
        """
        Apply rule-based hard filters for STRICT CONSTRAINTS ONLY.

        Hard filters are used ONLY for:
        - Posted date (within hours) - strict time constraint
        - Experience level - strict requirement
        - Minimum quality score - strict threshold

        IMPORTANT: 
        - Keywords/categories are NOT filtered here! They are handled by AI embeddings.
        - Budget is NOT filtered here! It's now a SCORING factor, not a filter.

        This allows:
        - "Machine Learning Engineer" to match "AI developer" (semantic matching)
        - Users to see all relevant jobs regardless of budget (flexible budget)

        Args:
            leads: List of leads to filter
            filters: Filter criteria

        Returns:
            Filtered list of leads
        """
        filtered = leads

        # ❌ REMOVED: Budget filtering - now a scoring factor
        # ❌ REMOVED: Category/keyword filtering - handled by AI embeddings

        # ✅ Filter by posted date (strict constraint)
        if filters.posted_within_hours:
            from datetime import timezone
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                hours=filters.posted_within_hours
            )
            before_count = len(filtered)
            # Keep jobs with missing dates for budget enrichment
            new_filtered = []
            for lead in filtered:
                if lead.posted_datetime is None:
                    # Keep leads with missing dates
                    new_filtered.append(lead)
                else:
                    # Ensure both datetimes are timezone-aware for comparison
                    lead_datetime = lead.posted_datetime
                    if lead_datetime.tzinfo is None:
                        lead_datetime = lead_datetime.replace(tzinfo=timezone.utc)
                    
                    if lead_datetime >= cutoff_time:
                        new_filtered.append(lead)
            
            filtered = new_filtered
            after_count = len(filtered)
            if before_count != after_count:
                logger.info(f"Date filter removed {before_count - after_count} leads (cutoff: {cutoff_time})")
                logger.info(f"Note: Leads with missing dates are kept for budget enrichment")

        # ✅ Filter by experience level (strict constraint)
        if filters.experience_levels:
            # This would require experience_level field in Lead model
            # For now, skip this filter
            pass

        # ✅ Filter by minimum quality score (strict constraint)
        if filters.min_quality_score:
            filtered = [
                lead for lead in filtered
                if lead.quality_score >= filters.min_quality_score
            ]

        return filtered
    def _apply_budget_filter_post_enrichment(
        self,
        scored_leads: List[ScoredLead],
        filters: FilterCriteria
    ) -> List[ScoredLead]:
        """
        Apply budget filtering AFTER enrichment (API mode only).

        This is only used when explicitly requested via API (e.g., Cursor).
        UI mode does NOT use this filter.

        Args:
            scored_leads: List of scored leads
            filters: Filter criteria with budget range

        Returns:
            Filtered list of scored leads
        """
        filtered = scored_leads

        # Filter by minimum budget
        if filters.min_budget is not None:
            filtered = [
                sl for sl in filtered
                if sl.lead.budget_amount is not None
                and sl.lead.budget_amount >= filters.min_budget
            ]

        # Filter by maximum budget
        if filters.max_budget is not None:
            filtered = [
                sl for sl in filtered
                if sl.lead.budget_amount is not None
                and sl.lead.budget_amount <= filters.max_budget
            ]

        return filtered


    
    def _compute_embedding_scores(
        self,
        leads: List[Lead],
        filters: FilterCriteria
    ) -> List[ScoredLead]:
        """
        Compute embedding similarities and create scored leads.

        Args:
            leads: List of leads
            filters: Filter criteria with keywords

        Returns:
            List of ScoredLead objects
        """
        # Build query text from keywords
        query_text = ' '.join(filters.keywords)

        # Generate query embedding
        query_embedding = self.embedding_engine.generate_embedding(query_text)

        # Generate lead embeddings and compute similarities
        similarities = []
        lead_texts = [
            f"{lead.job_title} {lead.job_description}"
            for lead in leads
        ]
        
        # Process in batches for efficiency
        lead_embeddings = self.embedding_engine.generate_embeddings_batch(lead_texts)
        
        # Compute similarities
        for lead_embedding in lead_embeddings:
            similarity = self.embedding_engine.calculate_similarity(
                query_embedding, 
                lead_embedding
            )
            similarities.append(similarity)

        # Create scored leads with budget preferences
        scored_leads = [
            self._create_scored_lead(lead, similarity, filters)
            for lead, similarity in zip(leads, similarities)
        ]

        return scored_leads

    
    def _create_scored_lead(
        self,
        lead: Lead,
        embedding_similarity: float,
        filters: Optional[FilterCriteria] = None
    ) -> ScoredLead:
        """
        Create a ScoredLead with all computed scores.

        Args:
            lead: Lead object
            embedding_similarity: Embedding similarity score
            filters: Filter criteria (for budget preferences)

        Returns:
            ScoredLead object with all scores computed
        """
        # Normalize quality score to [0, 1]
        quality_normalized = self._normalize_quality_score(lead.quality_score)

        # Compute recency score
        recency = self._compute_recency_score(lead.posted_datetime)

        # Compute budget score
        budget_score = self._compute_budget_score(lead, filters)

        # Compute final score
        final_score = (
            self.embedding_weight * embedding_similarity +
            self.quality_weight * quality_normalized +
            self.recency_weight * recency +
            self.budget_weight * budget_score
        )

        return ScoredLead(
            lead=lead,
            embedding_similarity=embedding_similarity,
            quality_score_normalized=quality_normalized,
            recency_score=recency,
            budget_score=budget_score,
            final_score=final_score
        )

    
    def _normalize_quality_score(self, quality_score: float) -> float:
        """
        Normalize quality score to [0, 1] range.
        
        Assumes quality_score is in [0, 100] range.
        
        Args:
            quality_score: Raw quality score
            
        Returns:
            Normalized score in [0, 1]
        """
        if quality_score is None:
            return 0.5  # Neutral score
        
        # Convert to float if Decimal (from database)
        quality_score = float(quality_score)
        
        # Clamp to [0, 100] and normalize
        clamped = max(0.0, min(100.0, quality_score))
        return clamped / 100.0
    
    def _calculate_keyword_similarity(self, lead: Lead, keywords: List[str]) -> float:
        """
        Calculate similarity based on keyword matching when embeddings are not available.
        
        Args:
            lead: Lead to evaluate
            keywords: Search keywords
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not keywords:
            return 0.5  # Neutral score if no keywords
        
        # Combine title and description for matching
        text = f"{lead.job_title or ''} {lead.job_description or ''}".lower()
        
        # Count keyword matches
        matches = 0
        for keyword in keywords:
            if keyword.lower() in text:
                matches += 1
        
        # Calculate similarity as percentage of keywords found
        similarity = matches / len(keywords)
        
        # Boost score if multiple keywords found in title (more relevant)
        title_text = (lead.job_title or '').lower()
        title_matches = sum(1 for kw in keywords if kw.lower() in title_text)
        if title_matches > 0:
            similarity += (title_matches / len(keywords)) * 0.2  # 20% boost for title matches
        
        return min(1.0, similarity)  # Cap at 1.0
    
    def _compute_recency_score(self, posted_datetime: datetime) -> float:
        """
        Compute recency score favoring newer jobs.
        
        Score decay:
        - Last 24h: 1.0
        - Last 7 days: 0.8
        - Last 30 days: 0.5
        - Older: 0.2
        
        Args:
            posted_datetime: When job was posted
            
        Returns:
            Recency score in [0, 1]
        """
        if posted_datetime is None:
            return 0.5  # Neutral score
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Ensure both datetimes are timezone-aware for comparison
        if posted_datetime.tzinfo is None:
            posted_datetime = posted_datetime.replace(tzinfo=timezone.utc)
        
        age_hours = (now - posted_datetime).total_seconds() / 3600
        
        if age_hours < 24:
            return 1.0
        elif age_hours < 24 * 7:
            return 0.8
        elif age_hours < 24 * 30:
            return 0.5
        else:
            return 0.2
    def _compute_budget_score(
        self, 
        lead: Lead, 
        filters: Optional[FilterCriteria] = None
    ) -> float:
        """
        Compute budget score as a ranking factor.

        Scoring strategy:
        - Higher budget → higher score (more valuable opportunity)
        - Missing budget → neutral score (0.5)
        - Very low budget → lower score
        - Budget preferences (if provided) influence scoring

        This is a RANKING factor, not a filter. All jobs are kept.

        Args:
            lead: Lead object
            filters: Filter criteria with budget preferences (optional)

        Returns:
            Budget score in [0, 1]
        """
        # No budget info available
        if lead.budget_amount is None:
            return 0.5  # Neutral score

        budget = lead.budget_amount

        # If user provided budget preferences, use them for scoring
        if filters and (filters.min_budget is not None or filters.max_budget is not None):
            min_budget = filters.min_budget or 0
            max_budget = filters.max_budget or float('inf')

            # Perfect match: within user's preferred range
            if min_budget <= budget <= max_budget:
                # Higher budgets within range get slightly better scores
                if max_budget != float('inf'):
                    range_position = (budget - min_budget) / (max_budget - min_budget)
                    return 0.8 + (range_position * 0.2)  # Range: 0.8-1.0
                else:
                    return 0.9

            # Below minimum budget
            if budget < min_budget:
                deficit_pct = (min_budget - budget) / min_budget

                if deficit_pct <= 0.2:  # Within 20% below
                    return 0.6
                elif deficit_pct <= 0.5:  # 20-50% below
                    return 0.4
                else:  # More than 50% below
                    return 0.2

            # Above maximum budget
            if budget > max_budget:
                excess_pct = (budget - max_budget) / max_budget

                if excess_pct <= 0.2:  # Within 20% above
                    return 0.7
                elif excess_pct <= 0.5:  # 20-50% above
                    return 0.5
                else:  # More than 50% above
                    return 0.3

        # No budget preferences: score based on absolute value
        # Higher budget = better opportunity
        # Normalize to reasonable range: $0-$10,000
        if budget <= 0:
            return 0.1
        elif budget >= 10000:
            return 1.0
        else:
            # Linear scale from 0.3 to 1.0
            return 0.3 + (budget / 10000.0) * 0.7


    
    def update_weights(
        self,
        embedding_weight: Optional[float] = None,
        quality_weight: Optional[float] = None,
        recency_weight: Optional[float] = None,
        budget_weight: Optional[float] = None
    ):
        """
        Update scoring weights.

        Args:
            embedding_weight: New embedding weight
            quality_weight: New quality weight
            recency_weight: New recency weight
            budget_weight: New budget weight
        """
        if embedding_weight is not None:
            self.embedding_weight = embedding_weight
        if quality_weight is not None:
            self.quality_weight = quality_weight
        if recency_weight is not None:
            self.recency_weight = recency_weight
        if budget_weight is not None:
            self.budget_weight = budget_weight

        # Normalize weights
        total = (self.embedding_weight + self.quality_weight + 
                 self.recency_weight + self.budget_weight)
        self.embedding_weight /= total
        self.quality_weight /= total
        self.recency_weight /= total
        self.budget_weight /= total

        logger.info(
            f"Updated weights: embedding={self.embedding_weight:.2f}, "
            f"quality={self.quality_weight:.2f}, recency={self.recency_weight:.2f}, "
            f"budget={self.budget_weight:.2f}"
        )

