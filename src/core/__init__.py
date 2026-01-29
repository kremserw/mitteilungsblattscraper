"""
Core business logic for JKU MTB Analyzer.

This module provides:
- MTBScraper: Web scraping with Playwright
- RelevanceAnalyzer: AI-powered content analysis
- PDFParser: PDF text extraction
"""

# Lazy imports to avoid loading heavy dependencies at startup
# Import these explicitly when needed:
#   from src.core.scraper import MTBScraper
#   from src.core.analyzer import RelevanceAnalyzer, BulletinAnalyzer
#   from src.core.parser import PDFParser, ContentProcessor

__all__ = [
    'MTBScraper',
    'RelevanceAnalyzer',
    'BulletinAnalyzer',
    'PDFParser',
    'ContentProcessor',
]


def __getattr__(name):
    """Lazy import implementation."""
    if name == 'MTBScraper':
        from .scraper import MTBScraper
        return MTBScraper
    elif name == 'RelevanceAnalyzer':
        from .analyzer import RelevanceAnalyzer
        return RelevanceAnalyzer
    elif name == 'BulletinAnalyzer':
        from .analyzer import BulletinAnalyzer
        return BulletinAnalyzer
    elif name == 'PDFParser':
        from .parser import PDFParser
        return PDFParser
    elif name == 'ContentProcessor':
        from .parser import ContentProcessor
        return ContentProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
