"""Credit monitoring for Apify API usage."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
from apify_client import ApifyClient


@dataclass
class CreditUsage:
    """Credit usage statistics."""
    
    total_credits: float
    used_credits: float
    remaining_credits: float
    usage_percentage: float
    last_updated: datetime


class CreditMonitor:
    """Monitors and manages Apify credit consumption."""
    
    def __init__(self, apify_token: str, free_plan_limit: float = 5.0,
                 warning_threshold: float = 80.0, stop_threshold: float = 95.0):
        """Initialize credit monitor.
        
        Args:
            apify_token: Apify API token
            free_plan_limit: Monthly credit limit for free plan
            warning_threshold: Percentage threshold for warnings (default 80%)
            stop_threshold: Percentage threshold for blocking scraping (default 95%)
        """
        self.apify_client = ApifyClient(apify_token)
        self.free_plan_limit = free_plan_limit
        self.warning_threshold = warning_threshold
        self.stop_threshold = stop_threshold
        self.cache: Optional[CreditUsage] = None
        self.cache_timestamp: Optional[datetime] = None
        self.cache_ttl = timedelta(minutes=5)  # 5-minute cache
    
    def get_usage(self) -> CreditUsage:
        """Retrieves current credit usage from Apify API with caching.
        
        Caches results for 5 minutes to avoid excessive API calls.
        
        Returns:
            CreditUsage object with current statistics
        
        Raises:
            Exception: If Apify API call fails
        """
        # Check if cache is valid
        if self._is_cache_valid():
            return self.cache
        
        # Fetch fresh data from Apify API
        try:
            user_data = self.apify_client.user().get()
            
            # Extract credit information
            total_credits = user_data.get('plan', {}).get('monthlyCredits', self.free_plan_limit)
            used_credits = user_data.get('usageStats', {}).get('monthlyCreditsUsed', 0.0)
            remaining_credits = total_credits - used_credits
            usage_percentage = (used_credits / total_credits * 100) if total_credits > 0 else 0.0
            
            # Create usage object
            usage = CreditUsage(
                total_credits=total_credits,
                used_credits=used_credits,
                remaining_credits=remaining_credits,
                usage_percentage=usage_percentage,
                last_updated=datetime.now()
            )
            
            # Update cache
            self.cache = usage
            self.cache_timestamp = datetime.now()
            
            return usage
            
        except Exception as e:
            # If cache exists, return stale data rather than failing
            if self.cache is not None:
                return self.cache
            raise Exception(f"Failed to fetch credit usage from Apify API: {e}")
    
    def check_can_scrape(self, estimated_cost: float) -> Tuple[bool, str]:
        """Checks if scraping can proceed without exceeding limits.
        
        Args:
            estimated_cost: Estimated credit cost for the operation
        
        Returns:
            Tuple of (can_proceed, message)
            - can_proceed: True if scraping can proceed, False otherwise
            - message: Descriptive message about credit status
        """
        try:
            usage = self.get_usage()
        except Exception as e:
            # If we can't get usage, log warning but allow scraping
            return True, f"Warning: Could not check credit usage ({e}). Proceeding anyway."
        
        # Check if already at stop threshold
        if usage.usage_percentage >= self.stop_threshold:
            return False, (
                f"Credit limit reached ({usage.usage_percentage:.1f}% of {usage.total_credits} credits used). "
                f"Cannot proceed with scraping."
            )
        
        # Check if operation would exceed remaining credits
        if usage.remaining_credits < estimated_cost:
            return False, (
                f"Insufficient credits. Operation requires {estimated_cost:.2f} credits, "
                f"but only {usage.remaining_credits:.2f} credits remaining."
            )
        
        # Check if at warning threshold
        if usage.usage_percentage >= self.warning_threshold:
            return True, (
                f"Warning: Credit usage at {usage.usage_percentage:.1f}% "
                f"({usage.used_credits:.2f}/{usage.total_credits:.2f} credits used). "
                f"Proceeding with operation."
            )
        
        # All good
        return True, (
            f"Credit check passed. {usage.remaining_credits:.2f} credits remaining "
            f"({usage.usage_percentage:.1f}% used)."
        )
    
    def get_available_credits(self) -> float:
        """Get the number of available credits.
        
        Returns:
            Number of remaining credits
        """
        try:
            usage = self.get_usage()
            return usage.remaining_credits
        except Exception:
            # If we can't get usage, assume we have some credits
            return 1.0
    
    def _is_cache_valid(self) -> bool:
        """Checks if cached credit data is still valid.
        
        Returns:
            True if cache exists and is within TTL, False otherwise
        """
        if self.cache is None or self.cache_timestamp is None:
            return False
        
        age = datetime.now() - self.cache_timestamp
        return age < self.cache_ttl
