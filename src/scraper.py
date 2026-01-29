"""
Web scraper for JKU Mitteilungsblatt (MTB) system.

This module provides backwards compatibility imports from the new core package.
For new code, import directly from src.core.scraper instead.
"""

from .core.scraper import (
    MTBScraper,
    get_scraper,
    run_scraper,
    scrape_edition,
)

__all__ = [
    'MTBScraper',
    'get_scraper',
    'run_scraper',
    'scrape_edition',
]
