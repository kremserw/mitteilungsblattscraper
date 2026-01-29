"""
JKU MTB Analyzer - AI-powered relevance filtering for university bulletins.

This package uses lazy imports to optimize startup time.
Import specific modules as needed rather than using wildcard imports.
"""

__version__ = "1.15.0"
__all__ = ['__version__']

# Note: All imports are lazy. Use explicit imports like:
#   from src.db.repository import Repository
#   from src.core.scraper import MTBScraper
#   from src.core.analyzer import RelevanceAnalyzer
