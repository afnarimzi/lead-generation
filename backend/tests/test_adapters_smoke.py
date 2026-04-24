"""Smoke tests for adapter implementations."""

import pytest
from datetime import datetime
from lead_scraper.adapters.upwork_adapter import UpworkAdapter
from lead_scraper.adapters.fiverr_adapter import FiverrAdapter
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.lead import Lead


class TestAdapterInstantiation:
    """Test that adapters can be instantiated correctly."""
    
    def test_upwork_adapter_instantiation(self):
        """Test UpworkAdapter can be instantiated."""
        adapter = UpworkAdapter(apify_token="test_token", actor_id="test_actor")
        assert adapter is not None
        assert adapter.apify_token == "test_token"
        assert adapter.actor_id == "test_actor"
    
    def test_fiverr_adapter_instantiation(self):
        """Test FiverrAdapter can be instantiated."""
        adapter = FiverrAdapter(apify_token="test_token", actor_id="test_actor")
        assert adapter is not None
        assert adapter.apify_token == "test_token"
        assert adapter.actor_id == "test_actor"


class TestUpworkAdapterNormalization:
    """Test Upwork adapter normalization logic."""
    
    def test_normalize_basic_lead(self):
        """Test normalizing a basic Upwork lead."""
        adapter = UpworkAdapter(apify_token="test_token", actor_id="test_actor")
        
        raw_lead = {
            'title': 'Python Developer Needed',
            'description': 'Looking for an experienced Python developer',
            'url': 'https://upwork.com/job/123',
            'budget': '500',
            'paymentType': 'fixed',
            'postedDate': '2024-01-15T10:00:00Z',
            'skills': 'Python, Django, REST API'
        }
        
        lead = adapter.normalize(raw_lead)
        
        assert isinstance(lead, Lead)
        assert lead.job_title == 'Python Developer Needed'
        assert lead.job_description == 'Looking for an experienced Python developer'
        assert lead.platform_name == 'Upwork'
        assert lead.budget_amount == 500.0
        assert lead.payment_type == 'fixed'
        assert lead.job_url == 'https://upwork.com/job/123'
        assert isinstance(lead.posted_datetime, datetime)
        assert len(lead.skills_tags) == 3
        assert 'Python' in lead.skills_tags
    
    def test_normalize_lead_with_missing_budget(self):
        """Test normalizing a lead with missing budget."""
        adapter = UpworkAdapter(apify_token="test_token", actor_id="test_actor")
        
        raw_lead = {
            'title': 'Test Job',
            'description': 'Test description',
            'url': 'https://upwork.com/job/456',
            'postedDate': '2024-01-15T10:00:00Z'
        }
        
        lead = adapter.normalize(raw_lead)
        
        assert lead.budget_amount is None
        assert lead.platform_name == 'Upwork'
    
    def test_normalize_lead_with_malformed_budget(self):
        """Test normalizing a lead with malformed budget."""
        adapter = UpworkAdapter(apify_token="test_token", actor_id="test_actor")
        
        raw_lead = {
            'title': 'Test Job',
            'description': 'Test description',
            'url': 'https://upwork.com/job/789',
            'budget': 'invalid',
            'postedDate': '2024-01-15T10:00:00Z'
        }
        
        lead = adapter.normalize(raw_lead)
        
        assert lead.budget_amount is None


class TestFiverrAdapterNormalization:
    """Test Fiverr adapter normalization logic."""
    
    def test_normalize_basic_lead(self):
        """Test normalizing a basic Fiverr lead."""
        adapter = FiverrAdapter(apify_token="test_token", actor_id="test_actor")
        
        raw_lead = {
            'title': 'Web Developer Required',
            'description': 'Need a skilled web developer',
            'url': 'https://fiverr.com/job/abc',
            'price': '750',
            'paymentType': 'fixed',
            'publishedAt': '2024-01-16T12:00:00Z',
            'categories': ['Web Development', 'JavaScript']
        }
        
        lead = adapter.normalize(raw_lead)
        
        assert isinstance(lead, Lead)
        assert lead.job_title == 'Web Developer Required'
        assert lead.job_description == 'Need a skilled web developer'
        assert lead.platform_name == 'Fiverr'
        assert lead.budget_amount == 750.0
        assert lead.payment_type == 'fixed'
        assert lead.job_url == 'https://fiverr.com/job/abc'
        assert isinstance(lead.posted_datetime, datetime)
        assert len(lead.skills_tags) == 2
    
    def test_normalize_lead_with_missing_date(self):
        """Test normalizing a lead with missing posted date."""
        adapter = FiverrAdapter(apify_token="test_token", actor_id="test_actor")
        
        raw_lead = {
            'title': 'Test Job',
            'description': 'Test description',
            'url': 'https://fiverr.com/job/def'
        }
        
        lead = adapter.normalize(raw_lead)
        
        # Should default to current time
        assert isinstance(lead.posted_datetime, datetime)
        assert lead.platform_name == 'Fiverr'


class TestAdapterCreditEstimation:
    """Test credit estimation logic."""
    
    def test_upwork_credit_estimation(self):
        """Test Upwork credit estimation."""
        adapter = UpworkAdapter(apify_token="test_token", actor_id="test_actor")
        filters = FilterCriteria(max_results_per_platform=100)
        
        estimated_credits = adapter.estimate_credits(filters)
        
        assert estimated_credits == 1.0  # 100 * 0.01
    
    def test_fiverr_credit_estimation(self):
        """Test Fiverr credit estimation."""
        adapter = FiverrAdapter(apify_token="test_token", actor_id="test_actor")
        filters = FilterCriteria(max_results_per_platform=50)
        
        estimated_credits = adapter.estimate_credits(filters)
        
        assert estimated_credits == 0.5  # 50 * 0.01
