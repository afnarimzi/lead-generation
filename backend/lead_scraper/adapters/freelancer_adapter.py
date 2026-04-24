"""Freelancer platform adapter for scraping job postings."""

import asyncio
from datetime import datetime
from typing import List, Optional
from apify_client import ApifyClient

from lead_scraper.adapters.platform_adapter import PlatformAdapter
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.auth_config import AuthConfig


class FreelancerAdapter(PlatformAdapter):
    """Adapter for scraping Freelancer job postings via Apify."""
    
    def __init__(self, apify_token: str, actor_id: str, auth_config: Optional[AuthConfig] = None):
            """Initialize the Freelancer adapter.

            Args:
                apify_token: Apify API token for authentication
                actor_id: Apify actor ID for Freelancer scraper
                auth_config: Optional authentication configuration
            """
            super().__init__(apify_token, actor_id, auth_config)
            self.client = ApifyClient(apify_token)
    
    async def scrape(self, filters: FilterCriteria) -> List[dict]:
        """Triggers the Apify Freelancer actor and retrieves raw results.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            List of raw job posting dictionaries from Freelancer
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Prepare actor input
                actor_input = self._prepare_actor_input(filters)
                
                # Run the actor
                self.logger.info(f"Starting Freelancer scrape with actor {self.actor_id}")
                run = self.client.actor(self.actor_id).call(run_input=actor_input)
                
                # Fetch results
                results = []
                for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                    results.append(item)
                
                self.logger.info(f"Successfully scraped {len(results)} leads from Freelancer")
                return results
                
            except Exception as e:
                self.logger.error(f"Freelancer scrape attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    self._exponential_backoff(attempt)
                else:
                    self.handle_error(e, max_retries)
                    return []
        
        return []
    
    def normalize(self, raw_lead: dict) -> Lead:
            """Converts Freelancer-specific data to unified schema.

            Args:
                raw_lead: Raw job posting data from Freelancer

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

            # Debug: Log raw data to understand janbruinier actor structure
            import logging
            logger = logging.getLogger(__name__)
            if raw_lead:
                logger.info(f"Freelancer raw data keys: {list(raw_lead.keys())}")
                # Log first few key-value pairs to understand structure
                sample_data = {k: v for k, v in list(raw_lead.items())[:8]}
                logger.info(f"Freelancer sample data: {sample_data}")
            
            # Extract job title - try all possible field names for janbruinier actor
            job_title = (
                raw_lead.get('title') or 
                raw_lead.get('projectTitle') or 
                raw_lead.get('name') or 
                raw_lead.get('project_title') or
                raw_lead.get('job_title') or
                raw_lead.get('jobTitle') or
                raw_lead.get('project_name') or
                raw_lead.get('heading') or
                raw_lead.get('job_name') or
                'Unknown'
            )

            # Extract job description
            job_description = (
                raw_lead.get('description') or 
                raw_lead.get('preview_description') or
                raw_lead.get('job_description') or
                raw_lead.get('summary') or
                ''
            )

            # Extract job URL
            job_url = (
                raw_lead.get('url') or
                raw_lead.get('project_url') or
                raw_lead.get('link') or
                ''
            )

            lead = Lead(
                job_title=job_title,
                job_description=job_description,
                platform_name='Freelancer',
                budget_amount=budget_amount,
                payment_type=payment_type,
                client_info=client_info,
                job_url=job_url,
                posted_datetime=posted_datetime,
                skills_tags=skills_tags
            )

            # Set authentication status in metadata
            lead.set_auth_status(self.auth_config is not None and self.auth_config.is_valid())

            return lead
    
    def estimate_credits(self, filters: FilterCriteria) -> float:
        """Estimates Apify credit cost for Freelancer scraping.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            Estimated credit cost
        """
        # Rough estimation: 0.01 credits per result
        max_results = filters.max_results_per_platform or 100
        return max_results * 0.01
    
    def _prepare_actor_input(self, filters: FilterCriteria) -> dict:
        """Prepares input parameters for the janbruinier Freelancer actor.

        Args:
            filters: User-defined filter criteria

        Returns:
            Dictionary of actor input parameters
        """
        # Updated for janbruinier~jan-freelancer-job-scraper format
        search_query = ' '.join(filters.keywords) if filters.keywords else 'python'
        
        actor_input = {
            'searchQuery': search_query,
            'maxResults': filters.max_results_per_platform or 10,
            'minBudget': filters.min_budget or 0,
            'maxBudget': filters.max_budget or 10000,
            'sortBy': 'newest'
        }

        return actor_input
    
    def _extract_budget(self, raw_lead: dict) -> Optional[float]:
        """Extracts and normalizes budget amount from raw lead data.
        
        Enhanced with multiple extraction strategies for better coverage.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Budget amount in USD as float, or None if missing/malformed
        """
        try:
            from lead_scraper.utils.currency_converter import normalize_budget_to_usd, extract_currency_and_amount, convert_to_usd
            import re
            
            # Strategy 1: Direct budget fields (hello.datawizards actor format)
            budget_fields = ['price', 'budget', 'amount', 'budgetAmount', 'totalBudget', 'projectBudget']
            for field in budget_fields:
                if field in raw_lead and raw_lead[field] is not None:
                    budget_usd = normalize_budget_to_usd(raw_lead[field])
                    if budget_usd and budget_usd > 0:
                        return budget_usd
            
            # Strategy 2: Min/Max budget range (janbruinier actor format)
            budget_min = raw_lead.get('budget_min') or raw_lead.get('budgetMin') or raw_lead.get('minBudget') or 0
            budget_max = raw_lead.get('budget_max') or raw_lead.get('budgetMax') or raw_lead.get('maxBudget') or 0
            currency = raw_lead.get('currency', 'USD')
            
            # Convert to numbers if they're strings
            if isinstance(budget_min, str):
                budget_min = float(re.sub(r'[^\d.]', '', budget_min)) if re.search(r'\d', budget_min) else 0
            if isinstance(budget_max, str):
                budget_max = float(re.sub(r'[^\d.]', '', budget_max)) if re.search(r'\d', budget_max) else 0
            
            # Calculate amount from range
            amount = None
            if budget_min > 0 and budget_max > 0:
                amount = (budget_min + budget_max) / 2
            elif budget_max > 0:
                amount = float(budget_max)
            elif budget_min > 0:
                amount = float(budget_min)
            
            if amount and amount > 0:
                if currency and currency.upper() != 'USD':
                    return convert_to_usd(amount, currency)
                return amount
            
            # Strategy 3: Hourly rate fields
            hourly_fields = ['hourlyRate', 'hourly_rate', 'rate', 'pricePerHour', 'avgBid']
            for field in hourly_fields:
                if field in raw_lead and raw_lead[field]:
                    rate = normalize_budget_to_usd(raw_lead[field])
                    if rate and rate > 0:
                        # If it's clearly an hourly rate (< $200), estimate monthly
                        if rate < 200:
                            return rate * 160  # 40 hours/week * 4 weeks
                        else:
                            return rate  # Assume it's already a project budget
            
            # Strategy 4: Text parsing from description/title
            text_fields = ['description', 'projectTitle', 'title', 'job_description']
            for field in text_fields:
                if field in raw_lead and raw_lead[field]:
                    text = str(raw_lead[field])
                    budget = self._extract_budget_from_text(text)
                    if budget:
                        return budget
            
            # Strategy 5: Look for bid-related fields (including janbruinier actor format)
            bid_fields = ['bid_avg', 'avgBid', 'averageBid', 'startingBid', 'minBid', 'maxBid']
            for field in bid_fields:
                if field in raw_lead and raw_lead[field]:
                    bid = normalize_budget_to_usd(raw_lead[field])
                    if bid and bid > 0:
                        return bid
            
            # Strategy 6: Parse from any string field that might contain budget
            for key, value in raw_lead.items():
                if isinstance(value, str) and ('budget' in key.lower() or 'price' in key.lower() or 'amount' in key.lower()):
                    budget = self._extract_budget_from_text(value)
                    if budget:
                        return budget
            
            return None
            
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Malformed budget for job {raw_lead.get('projectTitle', 'Unknown')}: {e}"
            )
            return None
    
    def _extract_budget_from_text(self, text: str) -> Optional[float]:
        """Extract budget from text using regex patterns.
        
        Args:
            text: Text to search for budget information
            
        Returns:
            Budget amount in USD or None
        """
        try:
            from lead_scraper.utils.currency_converter import normalize_budget_to_usd
            import re
            
            # Enhanced budget patterns
            patterns = [
                # Range patterns
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*-\s*\$([0-9,]+(?:\.[0-9]{2})?)',  # $500-$1000
                r'([0-9,]+)\s*-\s*([0-9,]+)\s*USD',                              # 500-1000 USD
                r'Budget[:\s]*\$?([0-9,]+)\s*-\s*\$?([0-9,]+)',                  # Budget: $500-$1000
                
                # Single amount patterns
                r'Budget[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)',                      # Budget: $1000
                r'Price[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)',                       # Price: $1000
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*USD',                             # $1000 USD
                r'([0-9,]+(?:\.[0-9]{2})?)\s*USD',                               # 1000 USD
                r'([0-9,]+(?:\.[0-9]{2})?)\s*dollars?',                          # 1000 dollars
                r'\$([0-9,]+(?:\.[0-9]{2})?)',                                   # $1000
                
                # Other currencies
                r'₹([0-9,]+)',                                                   # ₹50000 (INR)
                r'£([0-9,]+)',                                                   # £500 (GBP)
                r'€([0-9,]+)',                                                   # €800 (EUR)
                r'AUD\s*\$?([0-9,]+)',                                           # AUD $1000
                r'CAD\s*\$?([0-9,]+)',                                           # CAD $1000
                
                # Hourly patterns
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*/\s*hr',                          # $25/hr
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*per\s*hour',                      # $25 per hour
                r'([0-9,]+(?:\.[0-9]{2})?)\s*USD\s*/\s*hr',                      # 25 USD/hr
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:  # Range pattern
                        low = float(match.group(1).replace(',', ''))
                        high = float(match.group(2).replace(',', ''))
                        amount = (low + high) / 2
                    else:  # Single value
                        amount = float(match.group(1).replace(',', ''))
                        
                        # Handle hourly rates
                        if '/hr' in pattern or 'hour' in pattern:
                            amount = amount * 160  # Estimate monthly
                        
                        # Handle currency conversion
                        if '₹' in pattern:  # INR to USD
                            amount = amount * 0.012
                        elif '£' in pattern:  # GBP to USD
                            amount = amount * 1.27
                        elif '€' in pattern:  # EUR to USD
                            amount = amount * 1.09
                        elif 'AUD' in pattern:  # AUD to USD
                            amount = amount * 0.65
                        elif 'CAD' in pattern:  # CAD to USD
                            amount = amount * 0.74
                    
                    # Filter reasonable amounts
                    if 10 <= amount <= 100000:
                        return amount
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error extracting budget from text: {e}")
            return None
    
    def _extract_payment_type(self, raw_lead: dict) -> Optional[str]:
        """Extracts payment type from raw lead data.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Payment type ('fixed' or 'hourly'), or None if not specified
        """
        payment_type = raw_lead.get('paymentType') or raw_lead.get('type') or raw_lead.get('projectType')
        
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
        
        job_title = raw_lead.get('projectTitle', 'Unknown')
        return parse_date_from_raw_lead(raw_lead, job_title)
    
    def _extract_skills(self, raw_lead: dict) -> List[str]:
        """Extracts and parses skills tags from raw lead data.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            List of individual skill strings
        """
        # Extract skills - try multiple field names for janbruinier actor
        skills = (
            raw_lead.get('skills') or 
            raw_lead.get('tags') or 
            raw_lead.get('categories') or
            raw_lead.get('skillsRequired') or
            []
        )
        
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
        # hello.datawizards actor doesn't provide client info, so return None
        # but keep fallback for other actors
        client_info = {}
        
        # Fallback to nested client object (for other actors)
        client_data = raw_lead.get('client') or raw_lead.get('employer') or {}
        
        if client_data:
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
