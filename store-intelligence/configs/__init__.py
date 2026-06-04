"""
Configuration module for the Store Intelligence System.

This module handles all environment configuration, settings validation,
and logging setup using Pydantic v2.
"""

from .logging_config import setup_logging
from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "setup_logging"]
