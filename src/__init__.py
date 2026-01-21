"""
JKU MTB Analyzer - AI-powered relevance filtering for university bulletins.
"""

from .storage import Storage, get_storage
from .scraper import MTBScraper, run_scraper, scrape_edition
from .parser import PDFParser, ContentProcessor
from .analyzer import RelevanceAnalyzer, BulletinAnalyzer

__version__ = "1.0.0"
__all__ = [
    'Storage', 'get_storage',
    'MTBScraper', 'run_scraper', 'scrape_edition',
    'PDFParser', 'ContentProcessor',
    'RelevanceAnalyzer', 'BulletinAnalyzer',
]
