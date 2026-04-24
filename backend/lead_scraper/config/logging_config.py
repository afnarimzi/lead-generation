"""Logging configuration for the lead scraper system."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lead_scraper.models.system_config import SystemConfig


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5
) -> None:
    """
    Configure structured logging for the application.
    
    Sets up logging to both console and file with rotation support.
    Logs are formatted with timestamp, logger name, level, and message.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, logs only to console
        max_bytes: Maximum size of log file before rotation (default: 100MB)
        backup_count: Number of backup files to keep
    """
    # Create structured formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Console handler - always enabled
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {log_level} level")
    if log_file:
        logger.info(f"Logging to file: {log_file} (rotation at {max_bytes / (1024 * 1024):.0f}MB)")


def setup_logging_from_config(config: 'SystemConfig') -> None:
    """
    Configure logging using SystemConfig settings.
    
    This is a convenience function that extracts logging parameters
    from SystemConfig and calls setup_logging().
    
    Args:
        config: SystemConfig instance with logging settings
    """
    setup_logging(
        log_level=config.log_level,
        log_file=config.log_file_path,
        max_bytes=config.log_max_size_mb * 1024 * 1024,  # Convert MB to bytes
        backup_count=5
    )
