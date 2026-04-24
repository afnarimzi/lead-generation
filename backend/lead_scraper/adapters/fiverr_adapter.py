"""Fiverr platform adapter for scraping job postings."""

import asyncio
from datetime import datetime
from typing import List, Optional
from apify_client import ApifyClient

from lead_scraper.adapters.platform_adapter import PlatformAdapter
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.auth_config import AuthConfig


class FiverrAdapter(PlatformAdapter):
    """Adapter for scraping Fiverr job postings via Apify."""
    
    def __init__(self, apify_token: str, actor_id: str, auth_config: Optional[AuthConfig] = None):
            """Initialize the Fiverr adapter.

            Args:
                apify_token: Apify API token for authentication
                actor_id: Apify actor ID for Fiverr scraper
                auth_config: Optional authentication configuration
            """
            super().__init__(apify_token, actor_id, auth_config)
            self.client = ApifyClient(apify_token)
    
    async def scrape(self, filters: FilterCriteria) -> List[dict]:
        """Triggers the Apify Fiverr actor and retrieves raw results.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            List of raw job posting dictionaries from Fiverr
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Prepare actor input
                actor_input = self._prepare_actor_input(filters)
                
                # Run the actor
                self.logger.info(f"Starting Fiverr scrape with actor {self.actor_id}")
                run = self.client.actor(self.actor_id).call(run_input=actor_input)
                
                # Fetch results
                results = []
                for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                    results.append(item)
                
                self.logger.info(f"Successfully scraped {len(results)} leads from Fiverr")
                return results
                
            except Exception as e:
                self.logger.error(f"Fiverr scrape attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    self._exponential_backoff(attempt)
                else:
                    self.handle_error(e, max_retries)
                    return []
        
        return []
    
    def normalize(self, raw_lead: dict) -> Lead:
            """Converts Fiverr-specific data to unified schema.

            Args:
                raw_lead: Raw job posting data from Fiverr

            Returns:
                Normalized Lead object
            """
            # Extract and normalize budget
            budget_amount = self._extract_budget(raw_lead)
            payment_type = self._extract_payment_type(raw_lead)

            # Extract and normalize date
            posted_datetime = self._extract_posted_date(raw_lead)

            # Extract and parse skills
            skills_tags = self._extract_skills(raw_lead)

            # Extract client information
            client_info = self._extract_client_info(raw_lead)

            lead = Lead(
                job_title=raw_lead.get('title', ''),
                job_description=raw_lead.get('description', ''),
                platform_name='Fiverr',
                budget_amount=budget_amount,
                payment_type=payment_type,
                client_info=client_info,
                job_url=raw_lead.get('url', ''),
                posted_datetime=posted_datetime,
                skills_tags=skills_tags
            )

            # Set authentication status in metadata
            lead.set_auth_status(self.auth_config is not None and self.auth_config.is_valid())

            return lead
    
    def estimate_credits(self, filters: FilterCriteria) -> float:
        """Estimates Apify credit cost for Fiverr scraping.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            Estimated credit cost
        """
        # Rough estimation: 0.01 credits per result
        max_results = filters.max_results_per_platform or 100
        return max_results * 0.01
    
    def _prepare_actor_input(self, filters: FilterCriteria) -> dict:
            """Prepares input parameters for the Apify Fiverr actor.

            Args:
                filters: User-defined filter criteria

            Returns:
                Dictionary of actor input parameters
            """
            actor_input = {
                'maxResults': filters.max_results_per_platform or 100
            }

            # Fiverr actor expects searchUrls parameter with constructed Fiverr search URL
            if filters.keywords:
                search_query = '+'.join(filters.keywords)
                # Construct Fiverr search URL
                search_url = f"https://www.fiverr.com/search/gigs?query={search_query}"
                actor_input['searchUrls'] = [search_url]

            # Add authentication parameters
            actor_input = self._add_auth_to_input(actor_input)

            return actor_input

    def _extract_budget(self, raw_lead: dict) -> Optional[float]:
        """Extracts and normalizes budget amount from raw lead data.
        
        Handles currency conversion to USD.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Budget amount in USD as float, or None if missing/malformed
        """
        try:
            from lead_scraper.utils.currency_converter import normalize_budget_to_usd
            
            # Try different possible field names
            budget = raw_lead.get('budget') or raw_lead.get('amount') or raw_lead.get('price')
            
            if budget is None:
                self.logger.warning(f"Missing budget for job: {raw_lead.get('title', 'Unknown')}")
                return None
            
            # Use currency converter to handle all formats and currencies
            budget_usd = normalize_budget_to_usd(budget)
            return budget_usd
            
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Malformed budget for job {raw_lead.get('title', 'Unknown')}: {budget}. Error: {e}"
            )
            return None
    
    def _extract_payment_type(self, raw_lead: dict) -> Optional[str]:
        """Extracts payment type from raw lead data.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Payment type ('fixed' or 'hourly'), or None if not specified
        """
        payment_type = raw_lead.get('paymentType') or raw_lead.get('type')
        
        if payment_type:
            # Normalize to lowercase
            payment_type = str(payment_type).lower()
            
            # Map common variations
            if 'fixed' in payment_type or 'project' in payment_type:
                return 'fixed'
            elif 'hourly' in payment_type or 'hour' in payment_type:
                return 'hourly'
        
        return payment_type
    
    def _extract_posted_date(self, raw_lead: dict) -> datetime:
        """Extracts and normalizes posted date to ISO 8601 format.
        
        Uses shared date parser utility that handles:
        - Standard date formats
        - Relative dates ("Posted 4 weeks ago")
        - Fallback to current time
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Posted datetime in ISO 8601 format
        """
        from lead_scraper.utils.date_parser import parse_date_from_raw_lead
        
        job_title = raw_lead.get('title', 'Unknown')
        return parse_date_from_raw_lead(raw_lead, job_title)
    
    def _extract_skills(self, raw_lead: dict) -> List[str]:
        """Extracts and parses skills tags from raw lead data.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            List of individual skill strings
        """
        skills = raw_lead.get('skills') or raw_lead.get('tags') or raw_lead.get('categories') or []
        
        # If skills is a string, parse it
        if isinstance(skills, str):
            # Split by comma and strip whitespace
            skills = [s.strip() for s in skills.split(',') if s.strip()]
        
        # If skills is already a list, ensure strings
        elif isinstance(skills, list):
            skills = [str(s).strip() for s in skills if s]
        
        return skills
    
    def _extract_client_info(self, raw_lead: dict) -> Optional[dict]:
        """Extracts client information from raw lead data.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Dictionary with client information, or None if not available
        """
        client_data = raw_lead.get('client') or raw_lead.get('buyer') or {}
        
        if not client_data:
            return None
        
        client_info = {}
        
        # Extract common client fields
        if 'name' in client_data:
            client_info['name'] = client_data['name']
        
        if 'rating' in client_data:
            try:
                client_info['rating'] = float(client_data['rating'])
            except (ValueError, TypeError):
                pass
        
        if 'jobsPosted' in client_data or 'jobs_posted' in client_data:
            try:
                jobs_posted = client_data.get('jobsPosted') or client_data.get('jobs_posted')
                client_info['jobs_posted'] = int(jobs_posted)
            except (ValueError, TypeError):
                pass
        
        return client_info if client_info else None
