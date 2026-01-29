"""
Database storage module for JKU MTB Analyzer.

This module provides backwards compatibility imports from the new db package.
For new code, import directly from src.db instead.
"""

# Import everything from the new db package for backwards compatibility
from .db.models import Base, Edition, BulletinItem, Attachment
from .db.repository import Repository, get_repository

# Backwards compatibility aliases
Storage = Repository
get_storage = get_repository

__all__ = [
    'Base',
    'Edition',
    'BulletinItem',
    'Attachment',
    'Storage',
    'get_storage',
    'Repository',
    'get_repository',
]
