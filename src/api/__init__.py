"""
REST API layer for JKU MTB Analyzer.

This module provides Flask blueprints for:
- /api/editions - Edition management
- /api/items - Bulletin item access
- /api/tasks - Background task operations
- /api/settings - Configuration management
"""

from .app import create_app

__all__ = ['create_app']
