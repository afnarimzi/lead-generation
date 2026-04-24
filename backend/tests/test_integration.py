"""Integration tests for the complete lead generation workflow."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, PropertyMock

from lead_scraper.orchestrator import LeadGenerationOrchestrator, LeadGenerationResult
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.adapters.upwork_adapter import UpworkAdapter
from lead_scraper.adapters.fiverr_adapter import FiverrAdapter
from lead_scraper.engines.credit_monitor import CreditMonitor, CreditUsage
from lead_scraper.engines.deduplication_engine import DeduplicationEngine
from lead_scraper.engines.filter_engine import FilterEngine
from lead_scraper.engines.quality_scorer import QualityScorer


class TestEndToEndWorkflow:
    """End-to-end integration tests for complete workflow."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection."""
        db = Mock()
        db.execute = Mock(return_value=[])
        db.bulk_insert = Mock(return_value=3)
        return db
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_mocked_apify(self, mock_db_connection):
        """
        Test complete run_lead_generation flow with mocked Apify responses.
        
        Validates:
        - Parallel scraping of both platforms
        - Data normalization
        - Deduplication
        - Filtering
        - Quality scoring
        - Sorting by quality score
        - Database storage
        - Result format
        """
        upwork_response = [
            {
                'title': 'Senior Python Developer',
                'description': 'Looking for experienced Python developer for backend work',
                'url': 'https://upwork.com/jobs/python-dev-1',
                'budget': 5000,
                'payment_type': 'fixed',
                'posted': (datetime.now() - timedelta(hours=12)).isoformat(),
                'skills': ['Python', 'Django', 'PostgreSQL'],
                'client': {'name': 'Tech Corp', 'rating': 4.8}
            },
            {
                'title': 'React Frontend Developer',
                'description': 'Need React expert for new project',
                'url': 'https://upwork.com/jobs/react-dev-1',
                'budget': 3000,
                'payment_type': 'fixed',
                'posted': (datetime.now() - timedelta(hours=48)).isoformat(),
                'skills': ['React', 'JavaScript', 'CSS'],
                'client': {'name': 'Startup Inc', 'rating': 4.5}
            }
        ]
        
        fiverr_response = [
            {
                'title': 'Python Automation Script',
                'description': 'Need Python script for data automation',
                'url': 'https://fiverr.com/gigs/python-automation-1',
                'budget': 500,
                'payment_type': 'fixed',
                'posted': (datetime.now() - timedelta(hours=6)).isoformat(),
                'skills': ['Python', 'Automation'],
                'client': {'name': 'Business Owner', 'rating': 4.2}
            },
            {
                'title': 'Senior Python Developer',  # Potential duplicate
                'description': 'Looking for experienced Python developer for backend work',
                'url': 'https://fiverr.com/gigs/python-dev-duplicate',
                'budget': 5000,
                'payment_type': 'fixed',
                'posted': (datetime.now() - timedelta(hours=12)).isoformat(),
                'skills': ['Python', 'Django'],
                'client': {'name': 'Tech Corp', 'rating': 4.8}
            }
        ]
        
        with patch('lead_scraper.adapters.upwork_adapter.ApifyClient') as mock_upwork_client, \
             patch('lead_scraper.adapters.fiverr_adapter.ApifyClient') as mock_fiverr_client, \
             patch('lead_scraper.engines.credit_monitor.ApifyClient') as mock_credit_client:
            
            # Setup Upwork mock - synchronous calls
            mock_upwork_dataset = Mock()
            mock_upwork_dataset.iterate_items = Mock(return_value=iter(upwork_response))
            
            mock_upwork_actor_instance = Mock()
            mock_upwork_actor_instance.call = Mock(return_value={'defaultDatasetId': 'dataset-123'})
            
            mock_upwork_client.return_value.actor = Mock(return_value=mock_upwork_actor_instance)
            mock_upwork_client.return_value.dataset = Mock(return_value=mock_upwork_dataset)
            
            # Setup Fiverr mock - synchronous calls
            mock_fiverr_dataset = Mock()
            mock_fiverr_dataset.iterate_items = Mock(return_value=iter(fiverr_response))
            
            mock_fiverr_actor_instance = Mock()
            mock_fiverr_actor_instance.call = Mock(return_value={'defaultDatasetId': 'dataset-456'})
            
            mock_fiverr_client.return_value.actor = Mock(return_value=mock_fiverr_actor_instance)
            mock_fiverr_client.return_value.dataset = Mock(return_value=mock_fiverr_dataset)
            
            # Setup credit monitor mock
            mock_credit_client.return_value.user = Mock(return_value=Mock(
                get=Mock(return_value={
                    'plan': {'monthlyCredits': 5.0},
                    'usageStats': {'monthlyCreditsUsed': 1.0}
                })
            ))
            
            # Create real components with mocked dependencies
            upwork_adapter = UpworkAdapter(
                apify_token='test_token',
                actor_id='test_upwork_actor'
            )
            
            fiverr_adapter = FiverrAdapter(
                apify_token='test_token',
                actor_id='test_fiverr_actor'
            )
            
            credit_monitor = CreditMonitor(
                apify_token='test_token',
                free_plan_limit=5.0
            )
            
            dedup_engine = DeduplicationEngine(db_connection=mock_db_connection)
            filter_engine = FilterEngine()
            quality_scorer = QualityScorer()
            
            # Create mock adapters for Freelancer and PeoplePerHour
            freelancer_adapter = Mock()
            freelancer_adapter.estimate_credits = Mock(return_value=0.5)
            freelancer_adapter.scrape = AsyncMock(return_value=[])
            
            peopleperhour_adapter = Mock()
            peopleperhour_adapter.estimate_credits = Mock(return_value=0.5)
            peopleperhour_adapter.scrape = AsyncMock(return_value=[])
            
            orchestrator = LeadGenerationOrchestrator(
                upwork_adapter=upwork_adapter,
                fiverr_adapter=fiverr_adapter,
                freelancer_adapter=freelancer_adapter,
                peopleperhour_adapter=peopleperhour_adapter,
                credit_monitor=credit_monitor,
                dedup_engine=dedup_engine,
                filter_engine=filter_engine,
                quality_scorer=quality_scorer,
                db_connection=mock_db_connection
            )
            
            # Create filter criteria
            filters = FilterCriteria(
                keywords=['Python'],
                min_budget=400,
                posted_within_hours=72,
                prioritize_24h=True
            )
            
            # Run orchestrator
            result = await orchestrator.run(filters)
            
            # Verify result structure
            assert result.status == "success"
            assert isinstance(result, LeadGenerationResult)
            
            # Verify leads were collected from both platforms
            assert result.upwork_leads > 0, "Should have Upwork leads"
            assert result.fiverr_leads > 0, "Should have Fiverr leads"
            
            # Verify filtering worked (only Python jobs with budget >= 400)
            assert result.total_leads >= 1, "Should have at least one filtered lead"
            for lead in result.leads:
                assert 'Python' in lead.job_title or 'Python' in lead.job_description
                assert lead.budget_amount is None or lead.budget_amount >= 400
            
            # Verify deduplication worked
            assert result.duplicates_removed >= 0, "Should track duplicates removed"
            
            # Verify quality scores were assigned
            for lead in result.leads:
                assert 0 <= lead.quality_score <= 100, f"Quality score {lead.quality_score} out of bounds"
            
            # Verify sorting by quality score (descending)
            scores = [lead.quality_score for lead in result.leads]
            assert scores == sorted(scores, reverse=True), "Leads should be sorted by quality score"
            
            # Verify 24-hour prioritization
            recent_leads = [
                lead for lead in result.leads 
                if (datetime.now() - lead.posted_datetime).total_seconds() / 3600 <= 24
            ]
            if recent_leads:
                # Recent leads should have higher scores due to prioritization
                assert any(lead.quality_score > 50 for lead in recent_leads), \
                    "Recent leads should have boosted scores"
            
            # Verify database storage was called
            assert mock_db_connection.bulk_insert.called, "Should store leads in database"
            
            # Verify execution time is tracked
            assert result.execution_time_seconds > 0, "Should track execution time"
            
            # Verify credits used is tracked
            assert result.credits_used >= 0, "Should track credits used"
            
            # Verify result can be serialized to dict
            result_dict = result.to_dict()
            assert isinstance(result_dict, dict)
            assert result_dict['status'] == 'success'
            assert 'leads' in result_dict
            assert 'total_leads' in result_dict


class TestPlatformFailureHandling:
    """Integration tests for platform failure scenarios."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection."""
        db = Mock()
        db.execute = Mock(return_value=[])
        db.bulk_insert = Mock(return_value=1)
        return db
    
    @pytest.mark.asyncio
    async def test_upwork_failure_fiverr_continues(self, mock_db_connection):
        """
        Test that when Upwork fails, Fiverr scraping continues successfully.
        
        Validates:
        - One platform failure doesn't block the other
        - Error handling is graceful
        - Results are returned from successful platform
        """
        fiverr_response = [
            {
                'title': 'Python Developer',
                'description': 'Need Python expert',
                'url': 'https://fiverr.com/gigs/python-1',
                'budget': 1000,
                'payment_type': 'fixed',
                'posted': datetime.now().isoformat(),
                'skills': ['Python'],
                'client': {'name': 'Client', 'rating': 4.5}
            }
        ]
        
        with patch('lead_scraper.adapters.upwork_adapter.ApifyClient') as mock_upwork_client, \
             patch('lead_scraper.adapters.fiverr_adapter.ApifyClient') as mock_fiverr_client, \
             patch('lead_scraper.engines.credit_monitor.ApifyClient') as mock_credit_client:
            
            # Setup Upwork to fail
            mock_upwork_actor_instance = Mock()
            mock_upwork_actor_instance.call = Mock(side_effect=Exception("Upwork API error"))
            mock_upwork_client.return_value.actor = Mock(return_value=mock_upwork_actor_instance)
            
            # Setup Fiverr to succeed
            mock_fiverr_dataset = Mock()
            mock_fiverr_dataset.iterate_items = Mock(return_value=iter(fiverr_response))
            
            mock_fiverr_actor_instance = Mock()
            mock_fiverr_actor_instance.call = Mock(return_value={'defaultDatasetId': 'dataset-456'})
            
            mock_fiverr_client.return_value.actor = Mock(return_value=mock_fiverr_actor_instance)
            mock_fiverr_client.return_value.dataset = Mock(return_value=mock_fiverr_dataset)
            
            # Setup credit monitor
            mock_credit_client.return_value.user = Mock(return_value=Mock(
                get=Mock(return_value={
                    'plan': {'monthlyCredits': 5.0},
                    'usageStats': {'monthlyCreditsUsed': 1.0}
                })
            ))
            
            # Create orchestrator
            upwork_adapter = UpworkAdapter(
                apify_token='test_token',
                actor_id='test_upwork_actor'
            )
            
            fiverr_adapter = FiverrAdapter(
                apify_token='test_token',
                actor_id='test_fiverr_actor'
            )
            
            credit_monitor = CreditMonitor(
                apify_token='test_token',
                free_plan_limit=5.0
            )
            
            dedup_engine = DeduplicationEngine(db_connection=mock_db_connection)
            filter_engine = FilterEngine()
            quality_scorer = QualityScorer()
            
            # Create mock adapters for Freelancer and PeoplePerHour
            freelancer_adapter = Mock()
            freelancer_adapter.estimate_credits = Mock(return_value=0.5)
            freelancer_adapter.scrape = AsyncMock(return_value=[])
            
            peopleperhour_adapter = Mock()
            peopleperhour_adapter.estimate_credits = Mock(return_value=0.5)
            peopleperhour_adapter.scrape = AsyncMock(return_value=[])
            
            orchestrator = LeadGenerationOrchestrator(
                upwork_adapter=upwork_adapter,
                fiverr_adapter=fiverr_adapter,
                freelancer_adapter=freelancer_adapter,
                peopleperhour_adapter=peopleperhour_adapter,
                credit_monitor=credit_monitor,
                dedup_engine=dedup_engine,
                filter_engine=filter_engine,
                quality_scorer=quality_scorer,
                db_connection=mock_db_connection
            )
            
            # Run orchestrator
            filters = FilterCriteria()
            result = await orchestrator.run(filters)
            
            # Verify workflow succeeded despite Upwork failure
            assert result.status == "success", "Should succeed with partial results"
            
            # Verify Upwork failed
            assert result.upwork_leads == 0, "Upwork should have 0 leads due to failure"
            
            # Verify Fiverr succeeded
            assert result.fiverr_leads == 1, "Fiverr should have 1 lead"
            
            # Verify total leads only from Fiverr
            assert result.total_leads == 1, "Should have 1 total lead from Fiverr"
            
            # Verify leads are from Fiverr
            assert all(lead.platform_name == 'Fiverr' for lead in result.leads)
    
    @pytest.mark.asyncio
    async def test_fiverr_failure_upwork_continues(self, mock_db_connection):
        """
        Test that when Fiverr fails, Upwork scraping continues successfully.
        
        Validates:
        - One platform failure doesn't block the other
        - Error handling is graceful
        - Results are returned from successful platform
        """
        upwork_response = [
            {
                'title': 'React Developer',
                'description': 'Need React expert',
                'url': 'https://upwork.com/jobs/react-1',
                'budget': 2000,
                'payment_type': 'fixed',
                'posted': datetime.now().isoformat(),
                'skills': ['React'],
                'client': {'name': 'Client', 'rating': 4.7}
            }
        ]
        
        with patch('lead_scraper.adapters.upwork_adapter.ApifyClient') as mock_upwork_client, \
             patch('lead_scraper.adapters.fiverr_adapter.ApifyClient') as mock_fiverr_client, \
             patch('lead_scraper.engines.credit_monitor.ApifyClient') as mock_credit_client:
            
            # Setup Upwork to succeed
            mock_upwork_dataset = Mock()
            mock_upwork_dataset.iterate_items = Mock(return_value=iter(upwork_response))
            
            mock_upwork_actor_instance = Mock()
            mock_upwork_actor_instance.call = Mock(return_value={'defaultDatasetId': 'dataset-123'})
            
            mock_upwork_client.return_value.actor = Mock(return_value=mock_upwork_actor_instance)
            mock_upwork_client.return_value.dataset = Mock(return_value=mock_upwork_dataset)
            
            # Setup Fiverr to fail
            mock_fiverr_actor_instance = Mock()
            mock_fiverr_actor_instance.call = Mock(side_effect=Exception("Fiverr API error"))
            mock_fiverr_client.return_value.actor = Mock(return_value=mock_fiverr_actor_instance)
            
            # Setup credit monitor
            mock_credit_client.return_value.user = Mock(return_value=Mock(
                get=Mock(return_value={
                    'plan': {'monthlyCredits': 5.0},
                    'usageStats': {'monthlyCreditsUsed': 1.0}
                })
            ))
            
            # Create orchestrator
            upwork_adapter = UpworkAdapter(
                apify_token='test_token',
                actor_id='test_upwork_actor'
            )
            
            fiverr_adapter = FiverrAdapter(
                apify_token='test_token',
                actor_id='test_fiverr_actor'
            )
            
            credit_monitor = CreditMonitor(
                apify_token='test_token',
                free_plan_limit=5.0
            )
            
            dedup_engine = DeduplicationEngine(db_connection=mock_db_connection)
            filter_engine = FilterEngine()
            quality_scorer = QualityScorer()
            
            # Create mock adapters for Freelancer and PeoplePerHour
            freelancer_adapter = Mock()
            freelancer_adapter.estimate_credits = Mock(return_value=0.5)
            freelancer_adapter.scrape = AsyncMock(return_value=[])
            
            peopleperhour_adapter = Mock()
            peopleperhour_adapter.estimate_credits = Mock(return_value=0.5)
            peopleperhour_adapter.scrape = AsyncMock(return_value=[])
            
            orchestrator = LeadGenerationOrchestrator(
                upwork_adapter=upwork_adapter,
                fiverr_adapter=fiverr_adapter,
                freelancer_adapter=freelancer_adapter,
                peopleperhour_adapter=peopleperhour_adapter,
                credit_monitor=credit_monitor,
                dedup_engine=dedup_engine,
                filter_engine=filter_engine,
                quality_scorer=quality_scorer,
                db_connection=mock_db_connection
            )
            
            # Run orchestrator
            filters = FilterCriteria()
            result = await orchestrator.run(filters)
            
            # Verify workflow succeeded despite Fiverr failure
            assert result.status == "success", "Should succeed with partial results"
            
            # Verify Fiverr failed
            assert result.fiverr_leads == 0, "Fiverr should have 0 leads due to failure"
            
            # Verify Upwork succeeded
            assert result.upwork_leads == 1, "Upwork should have 1 lead"
            
            # Verify total leads only from Upwork
            assert result.total_leads == 1, "Should have 1 total lead from Upwork"
            
            # Verify leads are from Upwork
            assert all(lead.platform_name == 'Upwork' for lead in result.leads)
    
    @pytest.mark.asyncio
    async def test_both_platforms_fail(self, mock_db_connection):
        """
        Test that when both platforms fail, workflow completes with empty results.
        
        Validates:
        - Graceful handling of complete failure
        - No exception is raised
        - Empty result set is returned
        """
        with patch('lead_scraper.adapters.upwork_adapter.ApifyClient') as mock_upwork_client, \
             patch('lead_scraper.adapters.fiverr_adapter.ApifyClient') as mock_fiverr_client, \
             patch('lead_scraper.engines.credit_monitor.ApifyClient') as mock_credit_client:
            
            # Setup both platforms to fail
            mock_upwork_actor_instance = Mock()
            mock_upwork_actor_instance.call = Mock(side_effect=Exception("Upwork API error"))
            mock_upwork_client.return_value.actor = Mock(return_value=mock_upwork_actor_instance)
            
            mock_fiverr_actor_instance = Mock()
            mock_fiverr_actor_instance.call = Mock(side_effect=Exception("Fiverr API error"))
            mock_fiverr_client.return_value.actor = Mock(return_value=mock_fiverr_actor_instance)
            
            # Setup credit monitor
            mock_credit_client.return_value.user = Mock(return_value=Mock(
                get=Mock(return_value={
                    'plan': {'monthlyCredits': 5.0},
                    'usageStats': {'monthlyCreditsUsed': 1.0}
                })
            ))
            
            # Create orchestrator
            upwork_adapter = UpworkAdapter(
                apify_token='test_token',
                actor_id='test_upwork_actor'
            )
            
            fiverr_adapter = FiverrAdapter(
                apify_token='test_token',
                actor_id='test_fiverr_actor'
            )
            
            credit_monitor = CreditMonitor(
                apify_token='test_token',
                free_plan_limit=5.0
            )
            
            dedup_engine = DeduplicationEngine(db_connection=mock_db_connection)
            filter_engine = FilterEngine()
            quality_scorer = QualityScorer()
            
            # Create mock adapters for Freelancer and PeoplePerHour
            freelancer_adapter = Mock()
            freelancer_adapter.estimate_credits = Mock(return_value=0.5)
            freelancer_adapter.scrape = AsyncMock(return_value=[])
            
            peopleperhour_adapter = Mock()
            peopleperhour_adapter.estimate_credits = Mock(return_value=0.5)
            peopleperhour_adapter.scrape = AsyncMock(return_value=[])
            
            orchestrator = LeadGenerationOrchestrator(
                upwork_adapter=upwork_adapter,
                fiverr_adapter=fiverr_adapter,
                freelancer_adapter=freelancer_adapter,
                peopleperhour_adapter=peopleperhour_adapter,
                credit_monitor=credit_monitor,
                dedup_engine=dedup_engine,
                filter_engine=filter_engine,
                quality_scorer=quality_scorer,
                db_connection=mock_db_connection
            )
            
            # Run orchestrator
            filters = FilterCriteria()
            result = await orchestrator.run(filters)
            
            # Verify workflow completed without exception
            assert result.status == "success", "Should complete gracefully"
            
            # Verify both platforms failed
            assert result.upwork_leads == 0, "Upwork should have 0 leads"
            assert result.fiverr_leads == 0, "Fiverr should have 0 leads"
            
            # Verify no leads returned
            assert result.total_leads == 0, "Should have 0 total leads"
            assert len(result.leads) == 0, "Leads list should be empty"
