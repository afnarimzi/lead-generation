"""
FastMCP tool for embedding-based lead search.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.lead import Lead
from lead_scraper.engines.hybrid_filter_engine import HybridFilterEngine, ScoredLead
from lead_scraper.engines.embedding_engine import EmbeddingEngine
from lead_scraper.database.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class EmbeddingLeadSearchTool:
    """
    MCP tool for semantic lead search using embeddings.
    """
    
    def __init__(
        self,
        db_connection: ConnectionManager,
        similarity_threshold: float = 0.6,
        embedding_weight: float = 0.7,
        quality_weight: float = 0.2,
        recency_weight: float = 0.1
    ):
        """
        Initialize embedding lead search tool.
        
        Args:
            db_connection: Database connection manager
            similarity_threshold: Minimum similarity score
            embedding_weight: Weight for embedding similarity
            quality_weight: Weight for quality score
            recency_weight: Weight for recency
        """
        self.db = db_connection
        
        # Initialize engines (singleton pattern ensures single model load)
        self.embedding_engine = GeminiEmbeddingEngine()
        self.hybrid_filter = HybridFilterEngine(
            embedding_engine=self.embedding_engine,
            similarity_threshold=similarity_threshold,
            embedding_weight=embedding_weight,
            quality_weight=quality_weight,
            recency_weight=recency_weight
        )
        
        logger.info("EmbeddingLeadSearchTool initialized")
    
    def search(
        self,
        keywords: List[str],
        platforms: Optional[List[str]] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        posted_within_hours: Optional[int] = None,
        min_quality_score: Optional[float] = None,
        max_results: int = 50,
        use_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Search for leads using hybrid filtering.
        
        Args:
            keywords: Search keywords
            platforms: Filter by platforms (e.g., ['Upwork', 'Freelancer'])
            min_budget: Minimum budget
            max_budget: Maximum budget
            posted_within_hours: Only include jobs posted within N hours
            min_quality_score: Minimum quality score
            max_results: Maximum number of results to return
            use_embeddings: Whether to use embedding-based filtering
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            logger.info(
                f"Embedding search: keywords={keywords}, "
                f"use_embeddings={use_embeddings}"
            )
            
            # Build filter criteria
            filters = FilterCriteria(
                keywords=keywords,
                categories=None,
                min_budget=min_budget,
                max_budget=max_budget,
                posted_within_hours=posted_within_hours or 168,  # Default 7 days
                experience_levels=None,
                prioritize_24h=True,
                max_results_per_platform=max_results,
                min_quality_score=min_quality_score or 0.0
            )
            
            # Fetch leads from database
            leads = self._fetch_leads_from_db(
                platforms=platforms,
                posted_within_hours=posted_within_hours
            )
            
            if not leads:
                return {
                    "status": "success",
                    "total_results": 0,
                    "leads": [],
                    "message": "No leads found matching criteria"
                }
            
            logger.info(f"Fetched {len(leads)} leads from database")
            
            # Apply hybrid filtering
            scored_leads = self.hybrid_filter.filter_and_rank(
                leads=leads,
                filters=filters,
                use_embeddings=use_embeddings
            )
            
            # Limit results
            scored_leads = scored_leads[:max_results]
            
            # Convert to response format
            results = [
                self._scored_lead_to_dict(sl) 
                for sl in scored_leads
            ]
            
            return {
                "status": "success",
                "total_results": len(results),
                "leads": results,
                "search_params": {
                    "keywords": keywords,
                    "platforms": platforms,
                    "min_budget": min_budget,
                    "max_budget": max_budget,
                    "posted_within_hours": posted_within_hours,
                    "use_embeddings": use_embeddings
                },
                "scoring_info": {
                    "similarity_threshold": self.hybrid_filter.similarity_threshold,
                    "embedding_weight": self.hybrid_filter.embedding_weight,
                    "quality_weight": self.hybrid_filter.quality_weight,
                    "recency_weight": self.hybrid_filter.recency_weight
                }
            }
            
        except Exception as e:
            logger.error(f"Embedding search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "total_results": 0,
                "leads": []
            }
    
    def _fetch_leads_from_db(
        self,
        platforms: Optional[List[str]] = None,
        posted_within_hours: Optional[int] = None,
        limit: int = 1000
    ) -> List[Lead]:
        """
        Fetch leads from database with optional filters.
        
        Args:
            platforms: Filter by platforms
            posted_within_hours: Only fetch recent leads
            limit: Maximum leads to fetch
            
        Returns:
            List of Lead objects
        """
        try:
            # Build SQL query
            query = "SELECT * FROM leads WHERE 1=1"
            params = []
            
            # Platform filter
            if platforms:
                placeholders = ','.join(['%s'] * len(platforms))
                query += f" AND platform_name IN ({placeholders})"
                params.extend(platforms)
            
            # Date filter
            if posted_within_hours:
                from datetime import timezone
                cutoff = datetime.now(timezone.utc) - timedelta(hours=posted_within_hours)
                query += " AND posted_datetime >= %s"
                params.append(cutoff)
            
            # Order by recency and limit
            query += " ORDER BY posted_datetime DESC LIMIT %s"
            params.append(limit)
            
            # Execute query
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                # Convert rows to Lead objects
                leads = []
                for row in cursor.fetchall():
                    lead = self._row_to_lead(row, cursor.description)
                    if lead:
                        leads.append(lead)
                
                cursor.close()
            
            return leads
            
        except Exception as e:
            logger.error(f"Failed to fetch leads from database: {e}")
            return []
    
    def _row_to_lead(self, row: tuple, description: list) -> Optional[Lead]:
        """
        Convert database row to Lead object.
        
        Args:
            row: Database row tuple
            description: Cursor description with column names
            
        Returns:
            Lead object or None if conversion fails
        """
        try:
            # Build column name to value mapping
            columns = {desc[0]: value for desc, value in zip(description, row)}
            
            lead = Lead(
                job_title=columns.get('job_title', ''),
                job_description=columns.get('job_description', ''),
                platform_name=columns.get('platform_name', ''),
                budget_amount=columns.get('budget_amount'),
                payment_type=columns.get('payment_type'),
                client_info=columns.get('client_info'),
                job_url=columns.get('job_url', ''),
                posted_datetime=columns.get('posted_datetime', datetime.now(timezone.utc)),
                skills_tags=columns.get('skills_tags', [])
            )
            
            # Set additional fields
            lead.quality_score = columns.get('quality_score', 0.0)
            lead.is_potential_duplicate = columns.get('is_potential_duplicate', False)
            
            return lead
            
        except Exception as e:
            logger.error(f"Failed to convert row to Lead: {e}")
            return None
    
    def _scored_lead_to_dict(self, scored_lead: ScoredLead) -> Dict[str, Any]:
        """
        Convert ScoredLead to dictionary for API response.
        
        Args:
            scored_lead: ScoredLead object
            
        Returns:
            Dictionary representation
        """
        lead = scored_lead.lead
        
        return {
            "id": id(lead),  # Use object id as temporary ID
            "job_title": lead.job_title,
            "job_description": lead.job_description[:500],  # Truncate for response
            "platform": lead.platform_name,
            "budget_amount": float(lead.budget_amount) if lead.budget_amount else None,
            "payment_type": lead.payment_type,
            "job_url": lead.job_url,
            "posted_datetime": lead.posted_datetime.isoformat() if lead.posted_datetime else None,
            "skills_tags": lead.skills_tags or [],
            "quality_score": float(lead.quality_score) if lead.quality_score else 0.0,
            "scores": {
                "embedding_similarity": round(scored_lead.embedding_similarity, 3),
                "quality_score_normalized": round(scored_lead.quality_score_normalized, 3),
                "recency_score": round(scored_lead.recency_score, 3),
                "final_score": round(scored_lead.final_score, 3)
            }
        }
    
    def update_similarity_threshold(self, threshold: float):
        """Update similarity threshold."""
        self.hybrid_filter.similarity_threshold = threshold
        logger.info(f"Updated similarity threshold to {threshold}")
    
    def update_scoring_weights(
        self,
        embedding_weight: Optional[float] = None,
        quality_weight: Optional[float] = None,
        recency_weight: Optional[float] = None
    ):
        """Update scoring weights."""
        self.hybrid_filter.update_weights(
            embedding_weight=embedding_weight,
            quality_weight=quality_weight,
            recency_weight=recency_weight
        )
    
    def get_embedding_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        return {
            "cache_size": self.embedding_engine.get_cache_size(),
            "embedding_dimension": self.embedding_engine.embedding_dimension,
            "model_name": self.embedding_engine.model_name
        }
