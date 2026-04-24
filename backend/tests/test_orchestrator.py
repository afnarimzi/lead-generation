"""Unit tests for LeadGenerationOrchestrator."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from lead_scraper.orchestrator import LeadGenerationOrchestrator, LeadGenerationResult
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria


class TestLeadGenerationOrchestrator:
    """Test suite for LeadGenerationOrchestrator class."""
    
    @pytest.fixture
    def mock_adapters(self):
        """Create mock platform adapters."""
        upwork_adapter = Mock()
        upwork_adapter.estimate_credits = Mock(return_value=0.5)
        upwork_adapter.scrape = AsyncMock(return_value=[
            {
                'title': 'Python Developer',
                'description': 'Need Python expert',
                'url': 'https://upwork.com/job1',
                'budget': 1000,
                'posted': '2024-01-01'
            }
        ])
        upwork_adapter.normalize = Mock(return_value=Lead(
            job_title='Python Developer',
            job_description='Need Python expert',
            platform_name='Upwork',
            job_url='https://upwork.com/job1',
            posted_datetime=datetime(2024, 1, 1),
            budget_amount=1000.0
        ))
        
        fiverr_adapter = Mock()
        fiverr_adapter.estimate_credits = Mock(return_value=0.5)
        fiverr_adapter.scrape = AsyncMock(return_value=[
            {
                'title': 'React Developer',
                'description': 'Need React expert',
                'url': 'https://fiverr.com/job1',
                'budget': 800,
                'posted': '2024-01-02'
            }
        ])
        fiverr_adapter.normalize = Mock(return_value=Lead(
            job_title='React Developer',
            job_description='Need React expert',
            platform_name='Fiverr',
            job_url='https://fiverr.com/job1',
            posted_datetime=datetime(2024, 1, 2),
            budget_amount=800.0
        ))
        
        freelancer_adapter = Mock()
        freelancer_adapter.estimate_credits = Mock(return_value=0.5)
        freelancer_adapter.scrape = AsyncMock(return_value=[])
        freelancer_adapter.normalize = Mock()
        
        peopleperhour_adapter = Mock()
        peopleperhour_adapter.estimate_credits = Mock(return_value=0.5)
        peopleperhour_adapter.scrape = AsyncMock(return_value=[])
        peopleperhour_adapter.normalize = Mock()
        
        return upwork_adapter, fiverr_adapter, freelancer_adapter, peopleperhour_adapter
    
    @pytest.fixture
    def mock_credit_monitor(self):
        """Create mock credit monitor."""
        monitor = Mock()
        monitor.check_can_scrape = Mock(return_value=(True, "OK"))
        return monitor
    
    @pytest.fixture
    def mock_dedup_engine(self):
        """Create mock deduplication engine."""
        engine = Mock()
        engine.remove_duplicates = Mock(side_effect=lambda leads: leads)
        return engine
    
    @pytest.fixture
    def mock_filter_engine(self):
        """Create mock filter engine."""
        engine = Mock()
        engine.apply_filters = Mock(side_effect=lambda leads, filters: leads)
        return engine
    
    @pytest.fixture
    def mock_quality_scorer(self):
        """Create mock quality scorer."""
        scorer = Mock()
        scorer.score_lead = Mock(return_value=75.0)
        return scorer
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection."""
        db = Mock()
        db.bulk_insert = Mock(return_value=2)
        return db
    
    @pytest.fixture
    def orchestrator(
        self, 
        mock_adapters, 
        mock_credit_monitor, 
        mock_dedup_engine,
        mock_filter_engine,
        mock_quality_scorer,
        mock_db_connection
    ):
        """Create orchestrator with all mocked dependencies."""
        upwork_adapter, fiverr_adapter, freelancer_adapter, peopleperhour_adapter = mock_adapters
        return LeadGenerationOrchestrator(
            upwork_adapter=upwork_adapter,
            fiverr_adapter=fiverr_adapter,
            freelancer_adapter=freelancer_adapter,
            peopleperhour_adapter=peopleperhour_adapter,
            credit_monitor=mock_credit_monitor,
            dedup_engine=mock_dedup_engine,
            filter_engine=mock_filter_engine,
            quality_scorer=mock_quality_scorer,
            db_connection=mock_db_connection
        )
    
    @pytest.mark.asyncio
    async def test_run_success(self, orchestrator, mock_adapters):
        """Test successful orchestration workflow."""
        filters = FilterCriteria(keywords=['python', 'react'])
        
        result = await orchestrator.run(filters)
        
        assert result.status == "success"
        assert result.total_leads == 2
        assert result.upwork_leads == 1
        assert result.fiverr_leads == 1
        assert len(result.leads) == 2
        assert result.execution_time_seconds > 0
    
    @pytest.mark.asyncio
    async def test_run_credit_check_failure(self, orchestrator, mock_credit_monitor):
        """Test orchestration when credit check fails."""
        mock_credit_monitor.check_can_scrape = Mock(
            return_value=(False, "Insufficient credits")
        )
        
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        assert result.status == "error"
        assert "Insufficient credits" in result.message
        assert result.total_leads == 0
        assert len(result.leads) == 0
    
    @pytest.mark.asyncio
    async def test_run_platform_failure_graceful(self, orchestrator, mock_adapters):
        """Test that one platform failure doesn't block the other."""
        upwork_adapter, fiverr_adapter, freelancer_adapter, peopleperhour_adapter = mock_adapters
        
        # Make Upwork fail
        upwork_adapter.scrape = AsyncMock(side_effect=Exception("Upwork API error"))
        upwork_adapter.handle_error = Mock()
        
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        # Should still succeed with Fiverr results
        assert result.status == "success"
        assert result.upwork_leads == 0  # Failed
        assert result.fiverr_leads == 1  # Succeeded
        assert result.total_leads == 1
        assert upwork_adapter.handle_error.called
    
    @pytest.mark.asyncio
    async def test_run_deduplication(self, orchestrator, mock_dedup_engine):
        """Test that deduplication is called."""
        mock_dedup_engine.remove_duplicates = Mock(
            side_effect=lambda leads: leads[:1]  # Remove one duplicate
        )
        
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        assert mock_dedup_engine.remove_duplicates.called
        assert result.duplicates_removed == 1
    
    @pytest.mark.asyncio
    async def test_run_quality_scoring(self, orchestrator, mock_quality_scorer):
        """Test that quality scoring is applied to all leads."""
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        # Quality scorer should be called for each lead
        assert mock_quality_scorer.score_lead.call_count == 2
        
        # All leads should have quality scores
        for lead in result.leads:
            assert lead.quality_score == 75.0
    
    @pytest.mark.asyncio
    async def test_run_sorting_by_quality_score(self, orchestrator, mock_quality_scorer):
        """Test that leads are sorted by quality score in descending order."""
        # Make scorer return different scores
        mock_quality_scorer.score_lead = Mock(side_effect=[50.0, 90.0])
        
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        # Leads should be sorted by quality score (descending)
        assert result.leads[0].quality_score == 90.0
        assert result.leads[1].quality_score == 50.0
    
    @pytest.mark.asyncio
    async def test_run_database_storage(self, orchestrator, mock_db_connection):
        """Test that leads are stored in database."""
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        assert mock_db_connection.bulk_insert.called
        assert result.status == "success"
    
    @pytest.mark.asyncio
    async def test_run_database_failure_continues(self, orchestrator, mock_db_connection):
        """Test that database failure doesn't stop the workflow."""
        mock_db_connection.bulk_insert = Mock(side_effect=Exception("DB error"))
        
        filters = FilterCriteria()
        result = await orchestrator.run(filters)
        
        # Should still return success with leads
        assert result.status == "success"
        assert result.total_leads == 2
