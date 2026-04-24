"""Deduplication engine for identifying and removing duplicate leads."""

import logging
from typing import Optional

from lead_scraper.models.lead import Lead
from lead_scraper.database.connection_manager import ConnectionManager


logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """Identifies and removes duplicate leads."""
    
    def __init__(self, db_connection: Optional[ConnectionManager] = None):
        """Initialize deduplication engine.
        
        Args:
            db_connection: Optional database connection manager for checking existing leads
        """
        self.db = db_connection
        self.seen_urls = set()
    
    def remove_duplicates(self, leads: list[Lead]) -> list[Lead]:
        """Remove duplicate leads based on job_url.
        
        Also flags potential cross-platform duplicates.
        
        Args:
            leads: List of leads to deduplicate
            
        Returns:
            List of unique leads
        """
        unique_leads = []
        
        for lead in leads:
            # Check against in-memory set for this batch
            if lead.job_url in self.seen_urls:
                continue
            
            # Check against database if available
            if self.db and self.is_duplicate_in_db(lead):
                continue
            
            # Check for potential cross-platform duplicates
            potential_dupes = self.find_potential_duplicates(lead, unique_leads)
            if potential_dupes:
                lead.is_potential_duplicate = True
            
            self.seen_urls.add(lead.job_url)
            unique_leads.append(lead)
        
        duplicates_removed = len(leads) - len(unique_leads)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate leads")
        
        return unique_leads
    
    def is_duplicate_in_db(self, lead: Lead) -> bool:
        """Check if a lead with the same job_url already exists in database.
        
        Args:
            lead: The lead to check
            
        Returns:
            True if duplicate exists, False otherwise
        """
        query = "SELECT COUNT(*) FROM leads WHERE job_url = %s"
        try:
            result = self.db.execute(query, (lead.job_url,))
            return result[0][0] > 0
        except Exception as e:
            logger.error(f"Error checking for duplicate in database: {e}")
            return False
    
    def find_potential_duplicates(self, lead: Lead, existing_leads: list[Lead]) -> list[Lead]:
        """Find leads with similar titles and descriptions but different URLs.
        
        Uses simple similarity check for cross-platform duplicates.
        
        Args:
            lead: The lead to compare
            existing_leads: List of leads to compare against
            
        Returns:
            List of potentially duplicate leads
        """
        potential_dupes = []
        
        for existing in existing_leads:
            # Skip if same platform
            if existing.platform_name == lead.platform_name:
                continue
            
            # Check title similarity
            if self._calculate_similarity(lead.job_title, existing.job_title) > 0.8:
                potential_dupes.append(existing)
        
        return potential_dupes
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using Jaccard similarity.
        
        Args:
            str1: First string to compare
            str2: Second string to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        # Simple Jaccard similarity on words
        words1 = set(str1_lower.split())
        words2 = set(str2_lower.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
