"""Unit tests for QualityScorer."""

import pytest
from datetime import datetime, timedelta
from lead_scraper.engines.quality_scorer import QualityScorer
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria


class TestQualityScorer:
    """Test suite for QualityScorer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = QualityScorer()
    
    def test_score_lead_with_high_budget(self):
        """Test that higher budget leads get higher scores."""
        filters = FilterCriteria()
        
        lead_high = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now(),
            budget_amount=5000.0
        )
        
        lead_low = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/2",
            posted_datetime=datetime.now(),
            budget_amount=500.0
        )
        
        score_high = self.scorer.score_lead(lead_high, filters, prioritize_24h=False)
        score_low = self.scorer.score_lead(lead_low, filters, prioritize_24h=False)
        
        assert score_high > score_low
    
    def test_score_lead_with_keyword_matches(self):
        """Test that keyword matches increase score."""
        filters = FilterCriteria(keywords=["Python", "Django"])
        
        lead_match = Lead(
            job_title="Python Django Developer",
            job_description="Build a Django web app",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now()
        )
        
        lead_no_match = Lead(
            job_title="Java Developer",
            job_description="Build a Spring app",
            platform_name="Upwork",
            job_url="https://example.com/2",
            posted_datetime=datetime.now()
        )
        
        score_match = self.scorer.score_lead(lead_match, filters, prioritize_24h=False)
        score_no_match = self.scorer.score_lead(lead_no_match, filters, prioritize_24h=False)
        
        assert score_match > score_no_match
    
    def test_score_lead_with_24h_priority(self):
        """Test that 24-hour priority boost works."""
        filters = FilterCriteria()
        
        lead_recent = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now() - timedelta(hours=12)
        )
        
        lead_old = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/2",
            posted_datetime=datetime.now() - timedelta(hours=48)
        )
        
        score_recent_with_boost = self.scorer.score_lead(lead_recent, filters, prioritize_24h=True)
        score_recent_no_boost = self.scorer.score_lead(lead_recent, filters, prioritize_24h=False)
        score_old = self.scorer.score_lead(lead_old, filters, prioritize_24h=True)
        
        # Recent lead with boost should score higher than without boost
        assert score_recent_with_boost > score_recent_no_boost
        # Recent lead should score higher than old lead
        assert score_recent_with_boost > score_old
    
    def test_score_lead_bounds(self):
        """Test that scores are bounded between 0 and 100."""
        filters = FilterCriteria(keywords=["Python", "Django", "React"])
        
        # Create a lead with maximum possible score factors
        lead = Lead(
            job_title="Python Django React Developer",
            job_description="Build a Python Django React web app",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now(),
            budget_amount=10000.0,  # Very high budget
            client_info={"rating": 5.0}
        )
        
        score = self.scorer.score_lead(lead, filters, prioritize_24h=True)
        
        assert 0 <= score <= 100
    
    def test_score_lead_with_client_reputation(self):
        """Test that client reputation affects score."""
        filters = FilterCriteria()
        
        lead_good_client = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now(),
            client_info={"rating": 5.0}
        )
        
        lead_no_rating = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/2",
            posted_datetime=datetime.now()
        )
        
        score_good = self.scorer.score_lead(lead_good_client, filters, prioritize_24h=False)
        score_no_rating = self.scorer.score_lead(lead_no_rating, filters, prioritize_24h=False)
        
        assert score_good > score_no_rating
    
    def test_count_keyword_matches(self):
        """Test keyword counting helper method."""
        lead = Lead(
            job_title="Python Django Developer",
            job_description="Build a Django web app with Python",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now()
        )
        
        keywords = ["Python", "Django", "React"]
        matches = self.scorer._count_keyword_matches(lead, keywords)
        
        # Should match Python and Django (2 matches)
        assert matches == 2
    
    def test_recency_scoring(self):
        """Test that more recent leads score higher."""
        filters = FilterCriteria()
        
        lead_1h = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/1",
            posted_datetime=datetime.now() - timedelta(hours=1)
        )
        
        lead_48h = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/2",
            posted_datetime=datetime.now() - timedelta(hours=48)
        )
        
        lead_100h = Lead(
            job_title="Python Developer",
            job_description="Build a web app",
            platform_name="Upwork",
            job_url="https://example.com/3",
            posted_datetime=datetime.now() - timedelta(hours=100)
        )
        
        score_1h = self.scorer.score_lead(lead_1h, filters, prioritize_24h=False)
        score_48h = self.scorer.score_lead(lead_48h, filters, prioritize_24h=False)
        score_100h = self.scorer.score_lead(lead_100h, filters, prioritize_24h=False)
        
        assert score_1h > score_48h > score_100h
