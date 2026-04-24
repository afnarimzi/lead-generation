"""Tests for FilterEngine."""

import pytest
from datetime import datetime, timedelta

from lead_scraper.engines.filter_engine import FilterEngine
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria


@pytest.fixture
def sample_leads():
    """Create sample leads for testing."""
    now = datetime.now()
    
    return [
        Lead(
            job_title="Python Developer Needed",
            job_description="Looking for an experienced Python developer for web scraping project",
            platform_name="Upwork",
            job_url="https://upwork.com/job1",
            posted_datetime=now - timedelta(hours=12),
            budget_amount=500.0,
            payment_type="fixed",
            skills_tags=["Python", "Web Scraping", "BeautifulSoup"],
            quality_score=75.0
        ),
        Lead(
            job_title="React Frontend Developer",
            job_description="Need a React expert for building a dashboard",
            platform_name="Fiverr",
            job_url="https://fiverr.com/job1",
            posted_datetime=now - timedelta(hours=48),
            budget_amount=1000.0,
            payment_type="fixed",
            skills_tags=["React", "JavaScript", "CSS"],
            quality_score=85.0
        ),
        Lead(
            job_title="Entry Level Data Entry",
            job_description="Simple data entry task for beginners",
            platform_name="Upwork",
            job_url="https://upwork.com/job2",
            posted_datetime=now - timedelta(hours=100),
            budget_amount=50.0,
            payment_type="hourly",
            skills_tags=["Data Entry"],
            quality_score=30.0
        ),
        Lead(
            job_title="Senior Python Engineer",
            job_description="Expert level Python engineer needed for machine learning project",
            platform_name="Upwork",
            job_url="https://upwork.com/job3",
            posted_datetime=now - timedelta(hours=6),
            budget_amount=2000.0,
            payment_type="fixed",
            skills_tags=["Python", "Machine Learning", "TensorFlow"],
            quality_score=95.0
        ),
    ]


@pytest.fixture
def filter_engine():
    """Create FilterEngine instance."""
    return FilterEngine()


def test_filter_by_keywords(filter_engine, sample_leads):
    """Test filtering by keywords."""
    filters = FilterCriteria(keywords=["Python"])
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 2
    assert all("python" in lead.job_title.lower() or "python" in lead.job_description.lower() 
               for lead in filtered)


def test_filter_by_budget_range(filter_engine, sample_leads):
    """Test filtering by budget range."""
    filters = FilterCriteria(min_budget=100.0, max_budget=1000.0)
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 2
    assert all(100.0 <= lead.budget_amount <= 1000.0 for lead in filtered)


def test_filter_by_posted_within_hours(filter_engine, sample_leads):
    """Test filtering by posting date."""
    filters = FilterCriteria(posted_within_hours=24)
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 2
    cutoff = datetime.now() - timedelta(hours=24)
    assert all(lead.posted_datetime >= cutoff for lead in filtered)


def test_filter_by_categories(filter_engine, sample_leads):
    """Test filtering by categories (skills tags)."""
    filters = FilterCriteria(categories=["Python", "React"])
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 3
    assert all(any(cat.lower() in [tag.lower() for tag in lead.skills_tags] 
                   for cat in ["Python", "React"]) for lead in filtered)


def test_filter_by_experience_levels(filter_engine, sample_leads):
    """Test filtering by experience levels."""
    filters = FilterCriteria(experience_levels=["entry", "beginner"], posted_within_hours=None)
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 1
    assert "entry" in filtered[0].job_title.lower() or "beginner" in filtered[0].job_description.lower()


def test_filter_by_quality_score(filter_engine, sample_leads):
    """Test filtering by minimum quality score."""
    filters = FilterCriteria(min_quality_score=80.0)
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 2
    assert all(lead.quality_score >= 80.0 for lead in filtered)


def test_multiple_filters_combined(filter_engine, sample_leads):
    """Test applying multiple filters simultaneously."""
    filters = FilterCriteria(
        keywords=["Python"],
        min_budget=400.0,
        max_budget=1500.0,  # Exclude the 2000 budget lead
        posted_within_hours=24
    )
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 1
    lead = filtered[0]
    assert "python" in lead.job_title.lower() or "python" in lead.job_description.lower()
    assert 400.0 <= lead.budget_amount <= 1500.0
    cutoff = datetime.now() - timedelta(hours=24)
    assert lead.posted_datetime >= cutoff


def test_no_filters_returns_all(filter_engine, sample_leads):
    """Test that no filters returns all leads."""
    filters = FilterCriteria(posted_within_hours=None)
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == len(sample_leads)


def test_filter_with_no_matches(filter_engine, sample_leads):
    """Test filtering with criteria that matches nothing."""
    filters = FilterCriteria(keywords=["Blockchain", "Cryptocurrency"])
    
    filtered = filter_engine.apply_filters(sample_leads, filters)
    
    assert len(filtered) == 0
