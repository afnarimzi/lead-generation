"""Quality scorer for ranking leads based on relevance, value, and recency."""

from datetime import datetime
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria


class QualityScorer:
    """Ranks leads based on relevance, value, and recency."""
    
    def score_lead(
        self, 
        lead: Lead, 
        filters: FilterCriteria, 
        prioritize_24h: bool = True
    ) -> float:
        """
        Calculates quality score (0-100) for a lead.
        
        Scoring factors:
        - Budget amount (higher is better): 0-30 points
        - Keyword matches: 0-25 points
        - Recency (newer is better): 0-25 points
        - 24-hour boost (if prioritize_24h=True): +20 points
        - Client reputation (if available): 0-10 points
        
        Args:
            lead: The lead to score
            filters: User filters (for keyword matching)
            prioritize_24h: If True, boost score for leads posted in last 24 hours
            
        Returns:
            Quality score between 0 and 100
        """
        score = 0.0
        
        # Budget scoring (0-30 points)
        if lead.budget_amount:
            # Convert to float if Decimal (from database)
            budget = float(lead.budget_amount)
            # Normalize budget to 0-30 scale (assuming max budget of $5000)
            score += min(30, (budget / 5000) * 30)
        
        # Keyword matching (0-25 points)
        if filters.keywords:
            matches = self._count_keyword_matches(lead, filters.keywords)
            score += min(25, matches * 8)  # Up to 3 keyword matches
        
        # Recency scoring (0-25 points)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Ensure posted_datetime is timezone-aware
        posted_dt = lead.posted_datetime
        if posted_dt and posted_dt.tzinfo is None:
            posted_dt = posted_dt.replace(tzinfo=timezone.utc)
        
        if posted_dt:
            hours_old = (now - posted_dt).total_seconds() / 3600
        else:
            hours_old = 999  # Very old if no date
            
        if hours_old <= 24:
            score += 25  # Full points for last 24 hours
        elif hours_old <= 72:
            score += 25 * (1 - (hours_old - 24) / 48)  # Linear decay from 24-72 hours
        # else: 0 points for older than 72 hours
        
        # 24-hour priority boost (+20 points)
        if prioritize_24h and hours_old <= 24:
            score += 20
        
        # Client reputation (0-10 points)
        if lead.client_info and lead.client_info.get('rating'):
            score += lead.client_info['rating'] * 2  # Assuming rating is 0-5
        
        return min(100, score)
    
    def _count_keyword_matches(self, lead: Lead, keywords: list[str]) -> int:
        """Counts how many keywords appear in the lead title or description.
        
        Args:
            lead: The lead to check
            keywords: List of keywords to search for
            
        Returns:
            Number of keywords found in the lead
        """
        text = f"{lead.job_title} {lead.job_description}".lower()
        return sum(1 for kw in keywords if kw.lower() in text)
