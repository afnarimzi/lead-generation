"""
Budget enrichment engine for fetching missing budget data from job URLs.
"""
import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class BudgetEnrichmentEngine:
    """
    Enriches job leads by visiting URLs to fetch missing budget information.
    
    Only enriches top-ranked jobs to optimize performance.
    Caches results to avoid re-scraping.
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        timeout: int = 10,
        enable_caching: bool = True
    ):
        """
        Initialize budget enrichment engine.
        
        Args:
            max_concurrent: Maximum concurrent URL visits
            timeout: Timeout for each URL request (seconds)
            enable_caching: Whether to cache enriched budgets
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.enable_caching = enable_caching
        self._cache: Dict[str, float] = {}
        
    async def enrich_top_leads(
        self,
        leads: List,
        top_n: int = 50
    ) -> List:
        """
        Enrich top N leads with missing budget data.
        
        Args:
            leads: List of Lead objects (already sorted by preliminary score)
            top_n: Number of top leads to enrich
            
        Returns:
            List of leads with enriched budget data
        """
        if not leads:
            return leads
        
        # Get top N leads
        top_leads = leads[:top_n]
        
        # Find leads with missing budgets
        leads_to_enrich = [
            lead for lead in top_leads
            if lead.budget_amount is None
        ]
        
        if not leads_to_enrich:
            logger.info("No leads require budget enrichment")
            return leads
        
        logger.info(
            f"Enriching {len(leads_to_enrich)} leads (out of top {top_n})"
        )
        
        # Enrich budgets asynchronously
        await self._enrich_budgets_async(leads_to_enrich)
        
        logger.info(
            f"Budget enrichment complete. "
            f"Enriched: {sum(1 for l in leads_to_enrich if l.budget_amount is not None)}"
        )
        
        return leads
    
    async def _enrich_budgets_async(self, leads: List) -> None:
        """
        Enrich budgets for multiple leads concurrently.
        
        Args:
            leads: List of leads to enrich
        """
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Create tasks for each lead
        tasks = [
            self._enrich_single_lead(lead, semaphore)
            for lead in leads
        ]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _enrich_single_lead(self, lead, semaphore) -> None:
        """
        Enrich a single lead with budget data.
        
        Args:
            lead: Lead object to enrich
            semaphore: Semaphore for rate limiting
        """
        async with semaphore:
            try:
                # Check cache first
                if self.enable_caching and lead.job_url in self._cache:
                    lead.budget_amount = self._cache[lead.job_url]
                    logger.debug(f"Budget loaded from cache: {lead.job_url}")
                    return
                
                # Fetch budget from URL
                budget = await self._fetch_budget_from_url(
                    lead.job_url,
                    lead.platform_name
                )
                
                if budget is not None:
                    lead.budget_amount = budget
                    
                    # Cache the result
                    if self.enable_caching:
                        self._cache[lead.job_url] = budget
                    
                    logger.debug(
                        f"Enriched budget for {lead.job_title}: ${budget}"
                    )
                else:
                    logger.debug(
                        f"Could not extract budget from {lead.job_url}"
                    )
                    
            except Exception as e:
                logger.warning(
                    f"Failed to enrich budget for {lead.job_url}: {e}"
                )
    
    async def _fetch_budget_from_url(
        self,
        url: str,
        platform: str
    ) -> Optional[float]:
        """
        Fetch budget from job URL.
        
        Args:
            url: Job URL
            platform: Platform name (Upwork, Freelancer, etc.)
            
        Returns:
            Budget amount in USD, or None if not found
        """
        try:
            # Import here to avoid circular dependencies
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    
                    # Extract budget based on platform
                    if platform.lower() == 'upwork':
                        return self._extract_upwork_budget(html)
                    elif platform.lower() == 'freelancer':
                        return self._extract_freelancer_budget(html)
                    elif platform.lower() == 'fiverr':
                        return self._extract_fiverr_budget(html)
                    elif platform.lower() == 'peopleperhour':
                        return self._extract_peopleperhour_budget(html)
                    else:
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching budget from {url}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching budget from {url}: {e}")
            return None
    
    def _extract_upwork_budget(self, html: str) -> Optional[float]:
        """
        Extract budget from Upwork job page HTML with enhanced patterns.
        
        Args:
            html: HTML content
            
        Returns:
            Budget in USD or None
        """
        try:
            # Enhanced patterns for Upwork budget extraction
            patterns = [
                # Fixed price patterns
                r'"budget":\s*{\s*"amount":\s*([0-9.]+)',  # JSON data
                r'"fixedBudget":\s*([0-9.]+)',  # JSON data
                r'Fixed-price\s*-\s*\$([0-9,]+(?:\.[0-9]{2})?)',  # Fixed-price - $1000
                r'Budget:\s*\$([0-9,]+(?:\.[0-9]{2})?)',  # Budget: $1000
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*fixed',  # $1000 fixed
                r'data-budget="([0-9.]+)"',  # HTML attribute
                
                # Hourly rate patterns
                r'"hourlyBudgetMin":\s*([0-9.]+).*?"hourlyBudgetMax":\s*([0-9.]+)',  # JSON range
                r'Hourly:\s*\$([0-9,]+(?:\.[0-9]{2})?)\s*-\s*\$([0-9,]+(?:\.[0-9]{2})?)',  # Hourly: $20-$50
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*-\s*\$([0-9,]+(?:\.[0-9]{2})?)\s*/hr',  # $20-$50/hr
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*/hour',  # $25/hour
                
                # General patterns
                r'price["\']:\s*["\']?\$?([0-9,]+(?:\.[0-9]{2})?)',  # price: "$1000"
                r'amount["\']:\s*["\']?([0-9,]+(?:\.[0-9]{2})?)',  # amount: "1000"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:  # Range pattern
                        low = float(match.group(1).replace(',', ''))
                        high = float(match.group(2).replace(',', ''))
                        # For hourly, estimate monthly (160 hours)
                        if 'hour' in pattern.lower() or '/hr' in pattern:
                            return (low + high) / 2 * 160
                        else:
                            return (low + high) / 2
                    else:  # Single value
                        amount = float(match.group(1).replace(',', ''))
                        # If it's hourly rate, estimate monthly
                        if 'hour' in pattern.lower() or '/hr' in pattern:
                            return amount * 160
                        return amount
            
            # Fallback: Look for any dollar amount in reasonable range
            fallback_pattern = r'\$([0-9,]+(?:\.[0-9]{2})?)'
            matches = re.findall(fallback_pattern, html)
            if matches:
                amounts = [float(m.replace(',', '')) for m in matches]
                # Filter reasonable budget amounts (between $10 and $100,000)
                reasonable_amounts = [a for a in amounts if 10 <= a <= 100000]
                if reasonable_amounts:
                    # Return the most common amount or median
                    return sorted(reasonable_amounts)[len(reasonable_amounts)//2]
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting Upwork budget: {e}")
            return None
    
    def _extract_freelancer_budget(self, html: str) -> Optional[float]:
        """
        Extract budget from Freelancer job page HTML with enhanced patterns.
        
        Args:
            html: HTML content
            
        Returns:
            Budget in USD or None
        """
        try:
            # Enhanced patterns for Freelancer budget extraction
            patterns = [
                # JSON data patterns
                r'"budget":\s*{\s*"minimum":\s*([0-9.]+).*?"maximum":\s*([0-9.]+)',  # JSON range
                r'"minBudget":\s*([0-9.]+).*?"maxBudget":\s*([0-9.]+)',  # JSON range
                r'"budget":\s*([0-9.]+)',  # JSON single value
                r'"amount":\s*([0-9.]+)',  # JSON amount
                
                # HTML patterns with currency
                r'\$([0-9,]+)\s*-\s*\$([0-9,]+)\s*USD',  # $500 - $1000 USD
                r'\$([0-9,]+)\s*USD',  # $1000 USD
                r'USD\s*\$([0-9,]+)',  # USD $1000
                r'Budget:\s*\$([0-9,]+(?:\.[0-9]{2})?)',  # Budget: $1000
                r'Price:\s*\$([0-9,]+(?:\.[0-9]{2})?)',  # Price: $1000
                
                # Range patterns without currency symbol
                r'([0-9,]+)\s*-\s*([0-9,]+)\s*USD',  # 500 - 1000 USD
                r'Budget[:\s]*([0-9,]+)\s*-\s*([0-9,]+)',  # Budget: 500 - 1000
                
                # Hourly patterns
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*/\s*hr',  # $25/hr
                r'\$([0-9,]+(?:\.[0-9]{2})?)\s*per\s*hour',  # $25 per hour
                r'([0-9,]+(?:\.[0-9]{2})?)\s*USD\s*/\s*hr',  # 25 USD/hr
                
                # Other currency patterns
                r'₹([0-9,]+)',  # Indian Rupees
                r'£([0-9,]+)',  # British Pounds
                r'€([0-9,]+)',  # Euros
                
                # HTML attributes
                r'data-budget="([0-9.]+)"',  # HTML attribute
                r'data-amount="([0-9.]+)"',  # HTML attribute
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
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
                    
                    return amount
            
            # Fallback: Look for any reasonable amount
            fallback_patterns = [
                r'([0-9,]+)\s*(?:USD|dollars?)',  # 1000 USD
                r'\$([0-9,]+)',  # $1000
                r'([0-9,]+)\s*\$',  # 1000$
            ]
            
            for pattern in fallback_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    amounts = [float(m.replace(',', '')) for m in matches]
                    # Filter reasonable amounts
                    reasonable_amounts = [a for a in amounts if 10 <= a <= 100000]
                    if reasonable_amounts:
                        return sorted(reasonable_amounts)[len(reasonable_amounts)//2]
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting Freelancer budget: {e}")
            return None
    
    def _extract_fiverr_budget(self, html: str) -> Optional[float]:
        """
        Extract budget from Fiverr job page HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Budget in USD or None
        """
        try:
            # Fiverr uses different structure
            pattern = r'US\$([0-9,]+(?:\.[0-9]{2})?)'
            
            match = re.search(pattern, html)
            if match:
                return float(match.group(1).replace(',', ''))
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting Fiverr budget: {e}")
            return None
    
    def _extract_peopleperhour_budget(self, html: str) -> Optional[float]:
        """
        Extract budget from PeoplePerHour job page HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Budget in USD or None
        """
        try:
            # PeoplePerHour patterns
            # Pattern: £XXX (need to convert to USD)
            pattern = r'£([0-9,]+(?:\.[0-9]{2})?)'
            
            match = re.search(pattern, html)
            if match:
                gbp_amount = float(match.group(1).replace(',', ''))
                # Convert GBP to USD (approximate rate: 1.27)
                return gbp_amount * 1.27
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting PeoplePerHour budget: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the budget cache."""
        self._cache.clear()
        logger.info("Budget cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the number of cached budgets."""
        return len(self._cache)
