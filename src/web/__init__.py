"""
Web UI layer for JKU MTB Analyzer.

This module provides:
- Jinja2 templates for the web interface
- Static assets (CSS, JavaScript)
- Page rendering routes
"""

from .views import web_bp

__all__ = ['web_bp']
