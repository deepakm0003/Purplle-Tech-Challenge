"""
Logging Configuration Module

This module sets up structured logging for the entire application.
Supports both JSON and text log formats with file rotation and console output.

All services log with:
- Structured fields (service, endpoint, latency, trace_id)
- UTC timestamps
- Consistent formatting across the application
"""

import logging
import logging.config
import logging.handlers
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .settings import Settings


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Converts log records to JSON format with all relevant metadata,
    enabling easy parsing and indexing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted string representation of the log record
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        if hasattr(record, "service"):
            log_data["service"] = record.service

        # Include exception if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Human-readable text formatter for logs.
    
    Useful for development environments where JSON is harder to read.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as human-readable text.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted string representation of the log record
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_line = (
            f"[{timestamp}] [{record.levelname}] "
            f"{record.name}:{record.funcName}:{record.lineno} - "
            f"{record.getMessage()}"
        )

        # Add extra fields if present
        if hasattr(record, "trace_id"):
            log_line += f" [trace_id={record.trace_id}]"
        if hasattr(record, "latency_ms"):
            log_line += f" [latency={record.latency_ms}ms]"

        # Include exception if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"

        return log_line


def setup_logging(settings: Settings) -> None:
    """
    Configure application logging based on settings.
    
    Sets up:
    - Console handler (stdout/stderr)
    - File handler with rotation (if log_dir specified)
    - Appropriate formatters based on settings.log_format
    - Root logger configuration
    
    Args:
        settings: Application settings instance
        
    Example:
        ```python
        from configs import get_settings, setup_logging
        
        settings = get_settings()
        setup_logging(settings)
        logging.info("Logger initialized")
        ```
    """
    # Ensure log directory exists
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Choose formatter based on settings
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ========================================================================
    # Console Handler (stdout for INFO+, stderr for ERROR+)
    # ========================================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ========================================================================
    # File Handler with Rotation
    # ========================================================================
    log_file = log_dir / settings.log_file
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # ========================================================================
    # Configure Root Logger
    # ========================================================================
    root_logger.setLevel(getattr(logging, settings.log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # ========================================================================
    # Suppress noisy third-party loggers
    # ========================================================================
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)

    root_logger.info(
        f"Logging initialized | "
        f"Level: {settings.log_level} | "
        f"Format: {settings.log_format} | "
        f"File: {log_file}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    This is a convenience function that follows the standard Python
    logging pattern of using module names as logger names.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        ```python
        from configs.logging_config import get_logger
        
        logger = get_logger(__name__)
        logger.info("Module initialized")
        ```
    """
    return logging.getLogger(name)
