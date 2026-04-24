"""Filter engine for applying user-defined criteria to leads."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria


class FilterEngine:
    """Applies filters to leads and returns matching results."""

    def apply_filters(self, leads: list[Lead], filters: FilterCriteria) -> list[Lead]:
        """
        Applies all filter criteria to the lead list.

        Args:
            leads: List of leads to filter
            filters: User-defined filter criteria

        Returns:
            Filtered list of leads matching all criteria
        """
        filtered = leads

        # Filter by categories
        if filters.categories:
            filtered = [l for l in filtered if self._matches_category(l, filters.categories)]

        # Filter by keywords
        if filters.keywords:
            filtered = [l for l in filtered if self._matches_keywords(l, filters.keywords)]

        # Filter by minimum budget
        # Only filter out leads with budget below minimum; keep leads with no budget
        if filters.min_budget is not None:
            filtered = [l for l in filtered if l.budget_amount is None or l.budget_amount >= filters.min_budget]

        # Filter by maximum budget
        # Only filter out leads with budget above maximum; keep leads with no budget
        if filters.max_budget is not None:
            filtered = [l for l in filtered if l.budget_amount is None or l.budget_amount <= filters.max_budget]

        # Filter by posting date
        if filters.posted_after is not None:
            new_filtered = []
            for lead in filtered:
                if lead.posted_datetime is not None:
                    # Ensure both datetimes are timezone-aware for comparison
                    lead_datetime = lead.posted_datetime
                    if lead_datetime.tzinfo is None:
                        lead_datetime = lead_datetime.replace(tzinfo=timezone.utc)
                    
                    posted_after = filters.posted_after
                    if posted_after.tzinfo is None:
                        posted_after = posted_after.replace(tzinfo=timezone.utc)
                    
                    if lead_datetime >= posted_after:
                        new_filtered.append(lead)
            filtered = new_filtered
        elif filters.posted_within_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=filters.posted_within_hours)
            new_filtered = []
            for lead in filtered:
                if lead.posted_datetime is not None:
                    # Ensure both datetimes are timezone-aware for comparison
                    lead_datetime = lead.posted_datetime
                    if lead_datetime.tzinfo is None:
                        lead_datetime = lead_datetime.replace(tzinfo=timezone.utc)
                    
                    if lead_datetime >= cutoff:
                        new_filtered.append(lead)
            filtered = new_filtered

        # Filter by experience levels
        if filters.experience_levels:
            filtered = [l for l in filtered if self._matches_experience(l, filters.experience_levels)]

        # Filter by minimum quality score
        if filters.min_quality_score > 0:
            filtered = [l for l in filtered if l.quality_score >= filters.min_quality_score]

        return filtered

    def _matches_category(self, lead: Lead, categories: list[str]) -> bool:
        """
        Checks if lead matches any of the specified categories.

        Categories are matched against skills_tags in the lead.

        Args:
            lead: The lead to check
            categories: List of category strings to match

        Returns:
            True if lead matches any category, False otherwise
        """
        if not lead.skills_tags:
            return False

        # Convert both to lowercase for case-insensitive matching
        lead_tags_lower = [tag.lower() for tag in lead.skills_tags]
        categories_lower = [cat.lower() for cat in categories]

        # Check if any category appears in the lead's skills tags
        return any(cat in lead_tags_lower for cat in categories_lower)

    def _compile_keyword_pattern(self, keyword: str):
        """
        Compiles a regex pattern for keyword matching with word boundaries.

        Args:
            keyword: A single keyword string (may be single word or phrase)

        Returns:
            Compiled regex pattern with word boundaries, or None if keyword is empty
        """
        import re

        # Strip whitespace and check if empty
        keyword = keyword.strip()
        if not keyword:
            return None

        # Escape special regex characters
        escaped = re.escape(keyword)

        # Check if it's a phrase (contains spaces after escaping)
        if r'\ ' in escaped:
            # For phrases: replace escaped spaces with \s+ to match any whitespace
            pattern_str = escaped.replace(r'\ ', r'\s+')
        else:
            # For single words: use as-is
            pattern_str = escaped

        # Add word boundaries intelligently:
        # - Use \b only if the edge character is a word character (\w)
        # - Otherwise use lookahead/lookbehind for whitespace or start/end of string
        
        # Check first character of original keyword
        if keyword[0].isalnum() or keyword[0] == '_':
            # First char is word character, use \b
            left_boundary = r'\b'
        else:
            # First char is special, use lookahead for whitespace or start
            left_boundary = r'(?<!\S)'
        
        # Check last character of original keyword
        if keyword[-1].isalnum() or keyword[-1] == '_':
            # Last char is word character, use \b
            right_boundary = r'\b'
        else:
            # Last char is special, use lookahead for whitespace or end
            right_boundary = r'(?!\S)'
        
        # Wrap with appropriate boundaries
        pattern_str = left_boundary + pattern_str + right_boundary

        # Compile with case-insensitive and unicode flags
        return re.compile(pattern_str, re.IGNORECASE | re.UNICODE)

    def _matches_keywords(self, lead: Lead, keywords: list[str]) -> bool:
        """
        Checks if lead title or description contains any keyword using word-boundary matching.
        
        Uses word boundaries to prevent false positives:
        - "AI" matches "AI engineer" but NOT "Elume.ai" or "API"
        - "machine learning" matches as a complete phrase
        
        Args:
            lead: The lead to check
            keywords: List of keyword strings to search for

        Returns:
            True if any keyword is found in title or description, False otherwise
        """
        # Handle empty or None fields
        job_title = lead.job_title if lead.job_title else ""
        job_description = lead.job_description if lead.job_description else ""
        text = f"{job_title} {job_description}"

        # Check each keyword
        for kw in keywords:
            if not kw or not kw.strip():
                continue
            
            # Compile pattern using helper method
            pattern = self._compile_keyword_pattern(kw)
            if pattern and pattern.search(text):
                return True

        return False

    def _matches_experience(self, lead: Lead, levels: list[str]) -> bool:
        """
        Checks if lead matches any of the specified experience levels.

        Experience levels are matched against the job description and title.
        Common levels: "entry", "intermediate", "expert", "beginner", "advanced"

        Args:
            lead: The lead to check
            levels: List of experience level strings to match

        Returns:
            True if lead matches any experience level, False otherwise
        """
        text = f"{lead.job_title} {lead.job_description}".lower()

        # Check if any experience level keyword appears in the text
        return any(level.lower() in text for level in levels)
