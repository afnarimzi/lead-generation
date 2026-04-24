"""Unit tests for DeduplicationEngine."""

import pytest
from datetime import datetime

from lead_scraper.engines.deduplication_engine import DeduplicationEngine
from lead_scraper.models.lead import Lead


def test_remove_duplicates_by_url():
    """Test that duplicate leads with same job_url are removed."""
    engine = DeduplicationEngine()
    
    lead1 = Lead(
        job_title="Python Developer",
        job_description="Build web apps",
        platform_name="Upwork",
        job_url="https://upwork.com/job/123",
        posted_datetime=datetime.now()
    )
    
    lead2 = Lead(
        job_title="Python Developer",
        job_description="Build web apps",
        platform_name="Upwork",
        job_url="https://upwork.com/job/123",  # Same URL
        posted_datetime=datetime.now()
    )
    
    lead3 = Lead(
        job_title="Java Developer",
        job_description="Build enterprise apps",
        platform_name="Upwork",
        job_url="https://upwork.com/job/456",  # Different URL
        posted_datetime=datetime.now()
    )
    
    leads = [lead1, lead2, lead3]
    unique_leads = engine.remove_duplicates(leads)
    
    assert len(unique_leads) == 2
    assert unique_leads[0].job_url == "https://upwork.com/job/123"
    assert unique_leads[1].job_url == "https://upwork.com/job/456"


def test_find_potential_cross_platform_duplicates():
    """Test that similar leads from different platforms are flagged."""
    engine = DeduplicationEngine()
    
    lead1 = Lead(
        job_title="Python Developer Needed",
        job_description="Build web apps",
        platform_name="Upwork",
        job_url="https://upwork.com/job/123",
        posted_datetime=datetime.now()
    )
    
    lead2 = Lead(
        job_title="Python Developer Needed",  # Same title
        job_description="Build mobile apps",
        platform_name="Fiverr",  # Different platform
        job_url="https://fiverr.com/job/456",  # Different URL
        posted_datetime=datetime.now()
    )
    
    leads = [lead1, lead2]
    unique_leads = engine.remove_duplicates(leads)
    
    assert len(unique_leads) == 2
    assert unique_leads[1].is_potential_duplicate is True


def test_calculate_similarity():
    """Test Jaccard similarity calculation."""
    engine = DeduplicationEngine()
    
    # Identical strings
    assert engine._calculate_similarity("hello world", "hello world") == 1.0
    
    # Completely different strings
    assert engine._calculate_similarity("hello world", "foo bar") == 0.0
    
    # Partial overlap
    similarity = engine._calculate_similarity("python developer needed", "python developer wanted")
    assert 0.4 < similarity < 1.0
    
    # Case insensitive
    assert engine._calculate_similarity("Hello World", "hello world") == 1.0
    
    # Empty strings
    assert engine._calculate_similarity("", "") == 0.0
    assert engine._calculate_similarity("hello", "") == 0.0


def test_remove_duplicates_preserves_order():
    """Test that first occurrence is kept when duplicates exist."""
    engine = DeduplicationEngine()
    
    lead1 = Lead(
        job_title="First",
        job_description="Description",
        platform_name="Upwork",
        job_url="https://upwork.com/job/123",
        posted_datetime=datetime.now()
    )
    
    lead2 = Lead(
        job_title="Second",
        job_description="Description",
        platform_name="Upwork",
        job_url="https://upwork.com/job/123",  # Duplicate URL
        posted_datetime=datetime.now()
    )
    
    leads = [lead1, lead2]
    unique_leads = engine.remove_duplicates(leads)
    
    assert len(unique_leads) == 1
    assert unique_leads[0].job_title == "First"


def test_remove_duplicates_empty_list():
    """Test that empty list returns empty list."""
    engine = DeduplicationEngine()
    
    unique_leads = engine.remove_duplicates([])
    
    assert unique_leads == []


def test_same_platform_not_flagged_as_duplicate():
    """Test that similar leads from same platform are not flagged as duplicates."""
    engine = DeduplicationEngine()
    
    lead1 = Lead(
        job_title="Python Developer",
        job_description="Build apps",
        platform_name="Upwork",
        job_url="https://upwork.com/job/123",
        posted_datetime=datetime.now()
    )
    
    lead2 = Lead(
        job_title="Python Developer",  # Same title
        job_description="Build apps",
        platform_name="Upwork",  # Same platform
        job_url="https://upwork.com/job/456",  # Different URL
        posted_datetime=datetime.now()
    )
    
    leads = [lead1, lead2]
    unique_leads = engine.remove_duplicates(leads)
    
    assert len(unique_leads) == 2
    assert unique_leads[0].is_potential_duplicate is False
    assert unique_leads[1].is_potential_duplicate is False
