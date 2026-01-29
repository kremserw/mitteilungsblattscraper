"""
AI Analyzer for JKU MTB content.

This module provides backwards compatibility imports from the new core package.
For new code, import directly from src.core.analyzer instead.
"""

from .core.analyzer import (
    RelevanceAnalyzer,
    BulletinAnalyzer,
    analyze_edition_cli,
    analyze_all_cli,
)

__all__ = [
    'RelevanceAnalyzer',
    'BulletinAnalyzer',
    'analyze_edition_cli',
    'analyze_all_cli',
]
