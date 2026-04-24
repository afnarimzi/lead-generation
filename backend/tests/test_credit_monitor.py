"""Unit tests for CreditMonitor."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from lead_scraper.engines.credit_monitor import CreditMonitor, CreditUsage


class TestCreditMonitor:
    """Test suite for CreditMonitor class."""
    
    @pytest.fixture
    def mock_apify_client(self):
        """Create a mock Apify client."""
        with patch('lead_scraper.engines.credit_monitor.ApifyClient') as mock_client:
            yield mock_client
    
    @pytest.fixture
    def credit_monitor(self, mock_apify_client):
        """Create a CreditMonitor instance with mocked client."""
        return CreditMonitor(
            apify_token="test_token",
            free_plan_limit=5.0,
            warning_threshold=80.0,
            stop_threshold=95.0
        )
    
    def test_get_usage_success(self, credit_monitor, mock_apify_client):
        """Test successful credit usage retrieval."""
        # Mock Apify API response
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 2.5}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # Get usage
        usage = credit_monitor.get_usage()
        
        # Verify results
        assert usage.total_credits == 5.0
        assert usage.used_credits == 2.5
        assert usage.remaining_credits == 2.5
        assert usage.usage_percentage == 50.0
        assert isinstance(usage.last_updated, datetime)
    
    def test_get_usage_caching(self, credit_monitor, mock_apify_client):
        """Test that credit usage is cached for 5 minutes."""
        # Mock Apify API response
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 1.0}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # First call should hit API
        usage1 = credit_monitor.get_usage()
        assert mock_user.get.call_count == 1
        
        # Second call within 5 minutes should use cache
        usage2 = credit_monitor.get_usage()
        assert mock_user.get.call_count == 1  # Still 1, not called again
        assert usage1.used_credits == usage2.used_credits
    
    def test_check_can_scrape_sufficient_credits(self, credit_monitor, mock_apify_client):
        """Test check_can_scrape with sufficient credits."""
        # Mock Apify API response - 50% usage
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 2.5}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # Check if can scrape with 1.0 credit cost
        can_proceed, message = credit_monitor.check_can_scrape(1.0)
        
        assert can_proceed is True
        assert "Credit check passed" in message
        assert "2.50 credits remaining" in message
    
    def test_check_can_scrape_warning_threshold(self, credit_monitor, mock_apify_client):
        """Test check_can_scrape at warning threshold (80%)."""
        # Mock Apify API response - 85% usage
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 4.25}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # Check if can scrape with 0.5 credit cost
        can_proceed, message = credit_monitor.check_can_scrape(0.5)
        
        assert can_proceed is True
        assert "Warning" in message
        assert "85.0%" in message
    
    def test_check_can_scrape_stop_threshold(self, credit_monitor, mock_apify_client):
        """Test check_can_scrape at stop threshold (95%)."""
        # Mock Apify API response - 96% usage
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 4.8}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # Check if can scrape
        can_proceed, message = credit_monitor.check_can_scrape(0.1)
        
        assert can_proceed is False
        assert "Credit limit reached" in message
        assert "96.0%" in message
    
    def test_check_can_scrape_insufficient_credits(self, credit_monitor, mock_apify_client):
        """Test check_can_scrape with insufficient remaining credits."""
        # Mock Apify API response - 1.0 credit remaining
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 4.0}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # Try to scrape with 2.0 credit cost (more than remaining)
        can_proceed, message = credit_monitor.check_can_scrape(2.0)
        
        assert can_proceed is False
        assert "Insufficient credits" in message
        assert "requires 2.00 credits" in message
        assert "1.00 credits remaining" in message
    
    def test_cache_expiration(self, credit_monitor, mock_apify_client):
        """Test that cache expires after 5 minutes."""
        # Mock Apify API response
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 1.0}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        # First call
        credit_monitor.get_usage()
        assert mock_user.get.call_count == 1
        
        # Manually expire cache by setting old timestamp
        credit_monitor.cache_timestamp = datetime.now() - timedelta(minutes=6)
        
        # Second call should hit API again
        credit_monitor.get_usage()
        assert mock_user.get.call_count == 2
    
    def test_get_usage_api_failure_with_cache(self, credit_monitor, mock_apify_client):
        """Test that stale cache is returned if API fails."""
        # First, populate cache with successful call
        mock_user = Mock()
        mock_user.get.return_value = {
            'plan': {'monthlyCredits': 5.0},
            'usageStats': {'monthlyCreditsUsed': 1.0}
        }
        credit_monitor.apify_client.user.return_value = mock_user
        
        usage1 = credit_monitor.get_usage()
        
        # Now make API fail
        mock_user.get.side_effect = Exception("API Error")
        
        # Expire cache to force API call
        credit_monitor.cache_timestamp = datetime.now() - timedelta(minutes=6)
        
        # Should return stale cache instead of raising
        usage2 = credit_monitor.get_usage()
        assert usage2.used_credits == usage1.used_credits
    
    def test_get_usage_api_failure_no_cache(self, credit_monitor, mock_apify_client):
        """Test that exception is raised if API fails and no cache exists."""
        # Make API fail
        mock_user = Mock()
        mock_user.get.side_effect = Exception("API Error")
        credit_monitor.apify_client.user.return_value = mock_user
        
        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            credit_monitor.get_usage()
        
        assert "Failed to fetch credit usage" in str(exc_info.value)
