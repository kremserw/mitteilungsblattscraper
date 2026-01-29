"""
Database layer for JKU MTB Analyzer.

This module provides:
- SQLAlchemy models (Edition, BulletinItem, Attachment)
- Repository pattern for data access
"""

from .models import Base, Edition, BulletinItem, Attachment
from .repository import Repository, get_repository

__all__ = [
    'Base',
    'Edition',
    'BulletinItem',
    'Attachment',
    'Repository',
    'get_repository',
]
