"""
Content parser for JKU MTB Analyzer.

This module provides backwards compatibility imports from the new core package.
For new code, import directly from src.core.parser instead.
"""

from .core.parser import (
    PDFParser,
    ContentProcessor,
    process_bulletin_item,
)

__all__ = [
    'PDFParser',
    'ContentProcessor',
    'process_bulletin_item',
]
