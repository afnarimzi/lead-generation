"""Tests for FastMCP server and tool registration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from lead_scraper.models.system_config import SystemConfig
from lead_scraper.orchestrator import LeadGenerationResult
from lead_scraper.models.lead import Lead
from datetime import datetime


@pytest.fixture
def mock_config():
    """Create a mock system configuration."""
    return SystemConfig(
        apify_token="test_token",
        apify_upwork_actor_id="test_upwork_actor",
        apify_fiverr_actor_id="test_fiverr_actor",
        apify_freelancer_actor_id="test_freelancer_actor",
        apify_peopleperhour_actor_id="test_peopleperhour_actor",
        database_url="postgresql://test:test@localhost/test",
        free_plan_credit_limit=5.0,
        credit_warning_threshold=80.0,
        credit_stop_threshold=95.0
    )


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = Mock()
    orchestrator.credit_monitor = Mock()
    orchestrator.db = Mock()
    return orchestrator


def test_server_imports():
    """Test that server module can be imported."""
    import lead_scraper.server
    assert lead_scraper.server is not None


def test_initialize_orchestrator(mock_config):
    """Test orchestrator initialization with valid config."""
    with patch('lead_scraper.server.ConnectionManager'), \
         patch('lead_scraper.server.CreditMonitor'), \
         patch('lead_scraper.server.UpworkAdapter'), \
         patch('lead_scraper.server.FiverrAdapter'), \
         patch('lead_scraper.server.FreelancerAdapter'), \
         patch('lead_scraper.server.PeoplePerHourAdapter'), \
         patch('lead_scraper.server.DeduplicationEngine'), \
         patch('lead_scraper.server.FilterEngine'), \
         patch('lead_scraper.server.QualityScorer'):
        
        from lead_scraper.server import initialize_orchestrator
        orchestrator = initialize_orchestrator(mock_config)
        
        assert orchestrator is not None


@pytest.mark.asyncio
async def test_run_lead_generation_invalid_parameters():
    """Test run_lead_generation with invalid parameters."""
    from lead_scraper.server import run_lead_generation, orchestrator
    
    # Test with negative min_budget
    result = await run_lead_generation(min_budget=-100)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_PARAMETERS"
    assert "min_budget must be non-negative" in result["details"]["validation_errors"]
    
    # Test with min_budget > max_budget
    result = await run_lead_generation(min_budget=1000, max_budget=500)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_PARAMETERS"
    assert any("min_budget must be less than or equal to max_budget" in err 
               for err in result["details"]["validation_errors"])
    
    # Test with invalid posted_within_hours
    result = await run_lead_generation(posted_within_hours=-10)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_PARAMETERS"
    
    # Test with invalid max_results_per_platform
    result = await run_lead_generation(max_results_per_platform=0)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_PARAMETERS"
    
    # Test with invalid min_quality_score
    result = await run_lead_generation(min_quality_score=150)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_PARAMETERS"


@pytest.mark.asyncio
async def test_run_lead_generation_not_initialized():
    """Test run_lead_generation when orchestrator is not initialized."""
    import lead_scraper.server as server_module
    
    # Save original orchestrator
    original_orchestrator = server_module.orchestrator
    
    try:
        # Set orchestrator to None
        server_module.orchestrator = None
        
        result = await server_module.run_lead_generation()
        assert result["status"] == "error"
        assert result["error_code"] == "SERVER_NOT_INITIALIZED"
    finally:
        # Restore original orchestrator
        server_module.orchestrator = original_orchestrator


@pytest.mark.asyncio
async def test_run_lead_generation_success(mock_orchestrator):
    """Test successful run_lead_generation."""
    import lead_scraper.server as server_module
    
    # Save original orchestrator
    original_orchestrator = server_module.orchestrator
    
    try:
        # Set mock orchestrator
        server_module.orchestrator = mock_orchestrator
        
        # Create mock result
        mock_result = LeadGenerationResult(
            status="success",
            leads=[],
            total_leads=0,
            upwork_leads=0,
            fiverr_leads=0,
            duplicates_removed=0,
            credits_used=0.5,
            execution_time_seconds=1.5,
            message="Test successful"
        )
        
        # Mock the run method
        mock_orchestrator.run = AsyncMock(return_value=mock_result)
        
        result = await server_module.run_lead_generation(keywords=["python"])
        
        assert result["status"] == "success"
        assert result["total_leads"] == 0
        assert result["message"] == "Test successful"
        
        # Verify run was called
        mock_orchestrator.run.assert_called_once()
    finally:
        # Restore original orchestrator
        server_module.orchestrator = original_orchestrator


@pytest.mark.asyncio
async def test_check_credits_not_initialized():
    """Test check_credits when orchestrator is not initialized."""
    import lead_scraper.server as server_module
    
    # Save original orchestrator
    original_orchestrator = server_module.orchestrator
    
    try:
        # Set orchestrator to None
        server_module.orchestrator = None
        
        result = await server_module.check_credits()
        assert result["status"] == "error"
        assert result["error_code"] == "SERVER_NOT_INITIALIZED"
    finally:
        # Restore original orchestrator
        server_module.orchestrator = original_orchestrator


@pytest.mark.asyncio
async def test_check_credits_success(mock_orchestrator):
    """Test successful check_credits."""
    import lead_scraper.server as server_module
    from lead_scraper.engines.credit_monitor import CreditUsage
    
    # Save original orchestrator
    original_orchestrator = server_module.orchestrator
    
    try:
        # Set mock orchestrator
        server_module.orchestrator = mock_orchestrator
        
        # Create mock usage
        mock_usage = CreditUsage(
            total_credits=5.0,
            used_credits=2.5,
            remaining_credits=2.5,
            usage_percentage=50.0,
            last_updated=datetime.now()
        )
        
        # Mock the get_usage method
        mock_orchestrator.credit_monitor.get_usage.return_value = mock_usage
        mock_orchestrator.credit_monitor.warning_threshold = 80.0
        
        result = await server_module.check_credits()
        
        assert result["total_credits"] == 5.0
        assert result["used_credits"] == 2.5
        assert result["remaining_credits"] == 2.5
        assert result["usage_percentage"] == 50.0
        assert result["warning"] is False
        assert "last_updated" in result
    finally:
        # Restore original orchestrator
        server_module.orchestrator = original_orchestrator


@pytest.mark.asyncio
async def test_export_leads_invalid_format():
    """Test export_leads with invalid format."""
    from lead_scraper.server import export_leads
    
    result = await export_leads(format="invalid_format")
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_FORMAT"


@pytest.mark.asyncio
async def test_export_leads_not_initialized():
    """Test export_leads when orchestrator is not initialized."""
    import lead_scraper.server as server_module
    
    # Save original orchestrator
    original_orchestrator = server_module.orchestrator
    
    try:
        # Set orchestrator to None
        server_module.orchestrator = None
        
        result = await server_module.export_leads()
        assert result["status"] == "error"
        assert result["error_code"] == "SERVER_NOT_INITIALIZED"
    finally:
        # Restore original orchestrator
        server_module.orchestrator = original_orchestrator


@pytest.mark.asyncio
async def test_export_leads_success(mock_orchestrator, tmp_path):
    """Test export_leads successfully exports leads."""
    import lead_scraper.server as server_module
    from lead_scraper.models.lead import Lead
    from datetime import datetime
    
    # Save original orchestrator
    original_orchestrator = server_module.orchestrator
    
    try:
        # Set mock orchestrator with proper database mock
        server_module.orchestrator = mock_orchestrator
        
        # Mock database execute to return sample leads
        sample_leads = [
            (1, "Test Job", "Description", "Upwork", 100.0, "fixed", 
             {"name": "Client"}, "http://test.com", datetime.now(), 
             ["python"], 85.0, False, datetime.now())
        ]
        mock_orchestrator.db.execute.return_value = sample_leads
        
        # Test JSON export
        output_path = str(tmp_path / "test_export.json")
        result = await server_module.export_leads(format="json", output_path=output_path)
        
        assert result["status"] == "success"
        assert result["format"] == "json"
        assert "test_export.json" in result["output_path"]
        assert result["leads_exported"] == 1
    finally:
        # Restore original orchestrator
        server_module.orchestrator = original_orchestrator
