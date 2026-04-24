"""Upwork platform adapter for scraping job postings."""

import asyncio
from datetime import datetime
from typing import List, Optional
from apify_client import ApifyClient

from lead_scraper.adapters.platform_adapter import PlatformAdapter
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.auth_config import AuthConfig


class UpworkAdapter(PlatformAdapter):
    """Adapter for scraping Upwork job postings via Apify."""
    
    def __init__(self, apify_token: str, actor_id: str, auth_config: Optional['AuthConfig'] = None):
            """Initialize the Upwork adapter.

            Args:
                apify_token: Apify API token for authentication
                actor_id: Apify actor ID for Upwork scraper
                auth_config: Optional authentication configuration
            """
            super().__init__(apify_token, actor_id, auth_config)
            self.client = ApifyClient(apify_token)
    
    async def scrape(self, filters: FilterCriteria) -> List[dict]:
        """Triggers the Apify Upwork actor and retrieves raw results.
        
        Args:
            filters: User-defined filter criteria
            
        Returns:
            List of raw job posting dictionaries from Upwork
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Prepare actor input
                actor_input = self._prepare_actor_input(filters)
                
                # Run the actor
                self.logger.info(f"Starting Upwork scrape with actor {self.actor_id}")
                run = self.client.actor(self.actor_id).call(run_input=actor_input)
                
                # Fetch results
                results = []
                for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                    results.append(item)
                
                self.logger.info(f"Successfully scraped {len(results)} leads from Upwork")
                return results
                
            except Exception as e:
                self.logger.error(f"Upwork scrape attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    self._exponential_backoff(attempt)
                else:
                    self.handle_error(e, max_retries)
                    return []
        
        return []
    
    def normalize(self, raw_lead: dict) -> Lead:
            """Converts Upwork-specific data to unified schema.

            Args:
                raw_lead: Raw job posting data from Upwork

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

            # Extract job details from getdataforme/upwork-jobs-scraper actor structure
            job_title = raw_lead.get('title', '')
            job_url = raw_lead.get('jobUrl', '') or raw_lead.get('url', '')

            # Get description - this actor provides it directly
            job_description = raw_lead.get('description', '')

            lead = Lead(
                job_title=job_title,
                job_description=job_description,
                platform_name='Upwork',
                budget_amount=budget_amount,
                payment_type=payment_type,
                client_info=client_info,
                job_url=job_url,
                posted_datetime=posted_datetime,
                skills_tags=skills_tags
            )

            # Set authentication status (this actor doesn't require auth)
            lead.set_auth_status(True)

            return lead
    
    def estimate_credits(self, filters: FilterCriteria) -> float:
            """Estimates Apify credit cost for Upwork scraping.

            Args:
                filters: User-defined filter criteria

            Returns:
                Estimated credit cost
            """
            # getdataforme~upwork-jobs-scraper actor: Reliable and reasonably priced
            # Based on typical Apify actor costs: approximately 0.01-0.02 credits per result
            max_results = filters.max_results_per_platform or 100
            return max_results * 0.015  # Conservative estimate for getdataforme actor
    
    def _prepare_actor_input(self, filters: FilterCriteria) -> dict:
            """Prepares input parameters for the Apify Upwork actor.

            Args:
                filters: User-defined filter criteria

            Returns:
                Dictionary of actor input parameters
            """
            # Updated for getdataforme/upwork-jobs-scraper actor format
            # This actor has a much simpler and more reliable input format
            try:
                # Combine keywords into a single search string
                search_keywords = ', '.join(filters.keywords) if filters.keywords else 'AI'

                actor_input = {
                    'searchKeywords': search_keywords,
                    'maxLimit': filters.max_results_per_platform or 100,
                    'location': 'Worldwide'  # No location filter for broader results
                }

                self.logger.info(f"Upwork actor input: {actor_input}")
                return actor_input

            except Exception as e:
                self.logger.error(f"Failed to prepare Upwork actor input: {e}")
                # Fallback to minimal input
                return {
                    'searchKeywords': 'AI',
                    'maxLimit': 50,
                    'location': 'Worldwide'
                }
    
    def _extract_budget(self, raw_lead: dict) -> Optional[float]:
            """Extracts and normalizes budget amount from raw lead data.

            Enhanced for getdataforme/upwork-jobs-scraper actor format.

            Args:
                raw_lead: Raw job posting data

            Returns:
                Budget amount in USD as float, or None if missing/malformed
            """
            try:
                # Strategy 1: Fixed price amount (most common)
                if 'fixedPriceAmount' in raw_lead and raw_lead['fixedPriceAmount']:
                    try:
                        return float(raw_lead['fixedPriceAmount'])
                    except (ValueError, TypeError):
                        pass

                # Strategy 2: Hourly budget range
                hourly_min = raw_lead.get('hourlyBudgetMin')
                hourly_max = raw_lead.get('hourlyBudgetMax')

                if hourly_min or hourly_max:
                    try:
                        if hourly_min and hourly_max:
                            avg_rate = (float(hourly_min) + float(hourly_max)) / 2
                        elif hourly_max:
                            avg_rate = float(hourly_max)
                        elif hourly_min:
                            avg_rate = float(hourly_min)
                        else:
                            avg_rate = 0

                        if avg_rate > 0:
                            # Convert hourly to monthly estimate (40 hours/week * 4 weeks)
                            return avg_rate * 160
                    except (ValueError, TypeError):
                        pass

                # Strategy 3: Weekly retainer budget
                if 'weeklyRetainerBudget' in raw_lead and raw_lead['weeklyRetainerBudget']:
                    try:
                        weekly_budget = float(raw_lead['weeklyRetainerBudget'])
                        return weekly_budget * 4  # Convert to monthly
                    except (ValueError, TypeError):
                        pass

                # Strategy 4: Text parsing from description/title
                text_fields = ['description', 'title']
                for field in text_fields:
                    if field in raw_lead and raw_lead[field]:
                        text = str(raw_lead[field])
                        budget = self._extract_budget_from_text(text)
                        if budget:
                            return budget

                # No budget found
                return None

            except Exception as e:
                job_title = raw_lead.get('title', 'Unknown')
                self.logger.debug(f"Could not parse budget for job {job_title}: {e}")
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
            
            # Budget patterns to look for
            patterns = [
                r'Budget[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)',  # Budget: $1000
                r'Price[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)',   # Price: $1000
                r'\$([0-9,]+(?:\.[0-9]{2})?)',               # $1000
                r'([0-9,]+(?:\.[0-9]{2})?)\s*USD',           # 1000 USD
                r'([0-9,]+(?:\.[0-9]{2})?)\s*dollars?',      # 1000 dollars
                r'₹([0-9,]+)',                               # ₹50000
                r'£([0-9,]+)',                               # £500
                r'€([0-9,]+)',                               # €800
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1)
                    
                    # Handle currency conversion
                    if '₹' in pattern:
                        amount = float(amount_str.replace(',', '')) * 0.012  # INR to USD
                    elif '£' in pattern:
                        amount = float(amount_str.replace(',', '')) * 1.27   # GBP to USD
                    elif '€' in pattern:
                        amount = float(amount_str.replace(',', '')) * 1.09   # EUR to USD
                    else:
                        amount = float(amount_str.replace(',', ''))
                    
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
            # Check jobType field from getdataforme actor
            job_type = raw_lead.get('jobType')

            if job_type:
                job_type = str(job_type).upper()
                if job_type == 'FIXED':
                    return 'fixed'
                elif job_type == 'HOURLY':
                    return 'hourly'

            # Fallback: infer from budget fields
            if raw_lead.get('fixedPriceAmount'):
                return 'fixed'
            elif raw_lead.get('hourlyBudgetMin') or raw_lead.get('hourlyBudgetMax'):
                return 'hourly'

            return None
    
    def _extract_posted_date(self, raw_lead: dict) -> datetime:
            """Extracts and normalizes posted date to ISO 8601 format.

            Updated for getdataforme/upwork-jobs-scraper actor format.

            Args:
                raw_lead: Raw job posting data

            Returns:
                Posted datetime in ISO 8601 format (timezone-aware)
            """
            try:
                from datetime import timezone

                # Try direct date fields from getdataforme actor
                date_fields = ['publishTime', 'createTime', 'postedOn', 'datePosted']
                for field in date_fields:
                    if field in raw_lead and raw_lead[field]:
                        try:
                            date_str = str(raw_lead[field])
                            # Handle ISO format with Z suffix
                            if date_str.endswith('Z'):
                                date_str = date_str.replace('Z', '+00:00')
                            parsed_date = datetime.fromisoformat(date_str)
                            # Ensure timezone awareness
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                            return parsed_date
                        except (ValueError, TypeError):
                            continue

                # Fallback to shared date parser
                from lead_scraper.utils.date_parser import parse_date_from_raw_lead
                job_title = raw_lead.get('title', 'Unknown')
                return parse_date_from_raw_lead(raw_lead, job_title)

            except Exception as e:
                job_title = raw_lead.get('title', 'Unknown')
                self.logger.warning(f"Date extraction failed for job '{job_title}': {e}")
                # Return current time as fallback (timezone-aware)
                return datetime.now(timezone.utc)
    
    def _extract_skills(self, raw_lead: dict) -> List[str]:
        """Extracts and parses skills tags from raw lead data.
        
        Updated for upwork-vibe actor format.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            List of individual skill strings
        """
        skills = []
        
        # Try different skill field names
        skill_fields = ['skills', 'tags', 'requiredSkills', 'skillsRequired']
        for field in skill_fields:
            if field in raw_lead and raw_lead[field]:
                skill_data = raw_lead[field]
                
                # If skills is a string, parse it
                if isinstance(skill_data, str):
                    skills = [s.strip() for s in skill_data.split(',') if s.strip()]
                    break
                
                # If skills is already a list
                elif isinstance(skill_data, list):
                    skills = [str(s).strip() for s in skill_data if s]
                    break
        
        return skills
    
    def _extract_client_info(self, raw_lead: dict) -> Optional[dict]:
        """Extracts client information from raw lead data.
        
        Args:
            raw_lead: Raw job posting data
            
        Returns:
            Dictionary with client information, or None if not available
        """
        client_data = raw_lead.get('client') or {}
        
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
