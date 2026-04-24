"""Tests for logging configuration."""

import logging
import tempfile
from pathlib import Path

import pytest

from lead_scraper.config.logging_config import setup_logging, setup_logging_from_config
from lead_scraper.models.system_config import SystemConfig


class TestSetupLogging:
    """Unit tests for setup_logging function."""
    
    def test_console_logging_only(self):
        """Test logging to console without file output."""
        setup_logging(log_level="INFO", log_file=None)
        
        # Verify that only console handler is configured (no file handler)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        # Should have only 1 handler (console)
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)
        assert not isinstance(root_logger.handlers[0], logging.handlers.RotatingFileHandler)
    
    def test_log_level_configuration(self):
        """Test that log level is correctly set."""
        setup_logging(log_level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG
        
        setup_logging(log_level="WARNING")
        assert logging.getLogger().level == logging.WARNING
        
        setup_logging(log_level="ERROR")
        assert logging.getLogger().level == logging.ERROR
    
    def test_file_logging_creates_directory(self):
        """Test that log file directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "test.log"
            setup_logging(log_level="INFO", log_file=str(log_file))
            
            assert log_file.parent.exists()
            assert log_file.exists()
    
    def test_file_logging_writes_messages(self):
        """Test that messages are written to log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_level="INFO", log_file=str(log_file))
            
            logger = logging.getLogger("test_logger")
            logger.info("Test file message")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            content = log_file.read_text()
            assert "Test file message" in content
    
    def test_log_rotation_configuration(self):
        """Test that log rotation is configured with correct parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            max_bytes = 50 * 1024 * 1024  # 50MB
            backup_count = 3
            
            setup_logging(
                log_level="INFO",
                log_file=str(log_file),
                max_bytes=max_bytes,
                backup_count=backup_count
            )
            
            # Find the RotatingFileHandler
            root_logger = logging.getLogger()
            rotating_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    rotating_handler = handler
                    break
            
            assert rotating_handler is not None
            assert rotating_handler.maxBytes == max_bytes
            assert rotating_handler.backupCount == backup_count
    
    def test_structured_log_format(self):
        """Test that logs have structured format with timestamp, name, level, message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_level="INFO", log_file=str(log_file))
            
            logger = logging.getLogger("test_module")
            logger.warning("Test warning message")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            content = log_file.read_text()
            # Check format: timestamp - name - level - message
            assert "test_module" in content
            assert "WARNING" in content
            assert "Test warning message" in content
            # Check timestamp format (YYYY-MM-DD HH:MM:SS)
            assert "-" in content.split(" - ")[0]  # Date separator
    
    def test_multiple_handlers_configured(self):
        """Test that both console and file handlers are configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_level="INFO", log_file=str(log_file))
            
            root_logger = logging.getLogger()
            handlers = root_logger.handlers
            
            # Should have 2 handlers: console and file
            assert len(handlers) == 2
            
            handler_types = [type(h).__name__ for h in handlers]
            assert "StreamHandler" in handler_types
            assert "RotatingFileHandler" in handler_types
    
    def test_handlers_cleared_on_reconfiguration(self):
        """Test that existing handlers are cleared when reconfiguring."""
        setup_logging(log_level="INFO")
        initial_handler_count = len(logging.getLogger().handlers)
        
        setup_logging(log_level="DEBUG")
        reconfigured_handler_count = len(logging.getLogger().handlers)
        
        # Should have same number of handlers, not accumulated
        assert reconfigured_handler_count == initial_handler_count


class TestSetupLoggingFromConfig:
    """Unit tests for setup_logging_from_config function."""
    
    def test_uses_config_log_level(self):
        """Test that log level from SystemConfig is used."""
        config = SystemConfig(
            apify_token="test_token",
            apify_upwork_actor_id="upwork_id",
            apify_fiverr_actor_id="fiverr_id",
            apify_freelancer_actor_id="freelancer_id",
            apify_peopleperhour_actor_id="pph_id",
            database_url="postgresql://test",
            log_level="DEBUG",
            log_file_path="logs/test.log"
        )
        
        setup_logging_from_config(config)
        assert logging.getLogger().level == logging.DEBUG
    
    def test_uses_config_log_file_path(self):
        """Test that log file path from SystemConfig is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "config_test.log"
            
            config = SystemConfig(
            apify_token="test_token",
            apify_upwork_actor_id="upwork_id",
            apify_fiverr_actor_id="fiverr_id",
            apify_freelancer_actor_id="freelancer_id",
            apify_peopleperhour_actor_id="pph_id",
            database_url="postgresql://test",
                log_level="INFO",
                log_file_path=str(log_file)
            )
            
            setup_logging_from_config(config)
            
            logger = logging.getLogger("test")
            logger.info("Config test message")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            assert log_file.exists()
            content = log_file.read_text()
            assert "Config test message" in content
    
    def test_uses_config_max_size_mb(self):
        """Test that log max size from SystemConfig is converted to bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            config = SystemConfig(
            apify_token="test_token",
            apify_upwork_actor_id="upwork_id",
            apify_fiverr_actor_id="fiverr_id",
            apify_freelancer_actor_id="freelancer_id",
            apify_peopleperhour_actor_id="pph_id",
            database_url="postgresql://test",
                log_level="INFO",
                log_file_path=str(log_file),
                log_max_size_mb=50  # 50MB
            )
            
            setup_logging_from_config(config)
            
            # Find the RotatingFileHandler
            root_logger = logging.getLogger()
            rotating_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    rotating_handler = handler
                    break
            
            assert rotating_handler is not None
            # 50MB = 50 * 1024 * 1024 bytes
            assert rotating_handler.maxBytes == 50 * 1024 * 1024
    
    def test_default_config_values(self):
        """Test that default SystemConfig values work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "default_test.log"
            
            config = SystemConfig(
            apify_token="test_token",
            apify_upwork_actor_id="upwork_id",
            apify_fiverr_actor_id="fiverr_id",
            apify_freelancer_actor_id="freelancer_id",
            apify_peopleperhour_actor_id="pph_id",
            database_url="postgresql://test",
                log_file_path=str(log_file)
                # Using defaults: log_level="INFO", log_max_size_mb=100
            )
            
            setup_logging_from_config(config)
            
            assert logging.getLogger().level == logging.INFO
            
            # Find the RotatingFileHandler
            root_logger = logging.getLogger()
            rotating_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    rotating_handler = handler
                    break
            
            assert rotating_handler is not None
            # Default 100MB = 100 * 1024 * 1024 bytes
            assert rotating_handler.maxBytes == 100 * 1024 * 1024


class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_log_rotation_creates_backup_files(self):
        """Test that log rotation creates backup files when size limit is exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "rotation_test.log"
            # Use very small max_bytes to trigger rotation
            max_bytes = 1024  # 1KB
            
            setup_logging(
                log_level="INFO",
                log_file=str(log_file),
                max_bytes=max_bytes,
                backup_count=3
            )
            
            logger = logging.getLogger("rotation_test")
            
            # Write enough data to trigger rotation
            for i in range(100):
                logger.info(f"Log message {i} " + "x" * 100)
            
            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            # Check that backup files were created
            log_dir = log_file.parent
            log_files = list(log_dir.glob("rotation_test.log*"))
            
            # Should have main log file and at least one backup
            assert len(log_files) >= 2
    
    def test_different_loggers_write_to_same_file(self):
        """Test that different loggers write to the same configured file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "multi_logger.log"
            setup_logging(log_level="INFO", log_file=str(log_file))
            
            logger1 = logging.getLogger("module1")
            logger2 = logging.getLogger("module2")
            
            logger1.info("Message from module1")
            logger2.warning("Message from module2")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            content = log_file.read_text()
            assert "module1" in content
            assert "Message from module1" in content
            assert "module2" in content
            assert "Message from module2" in content
    
    def test_log_levels_filter_correctly(self):
        """Test that log level filtering works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "level_test.log"
            setup_logging(log_level="WARNING", log_file=str(log_file))
            
            logger = logging.getLogger("level_test")
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            content = log_file.read_text()
            
            # DEBUG and INFO should not appear
            assert "Debug message" not in content
            assert "Info message" not in content
            
            # WARNING and ERROR should appear
            assert "Warning message" in content
            assert "Error message" in content
