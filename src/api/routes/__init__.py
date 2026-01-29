"""
API route blueprints for JKU MTB Analyzer.
"""

from .editions import editions_bp
from .items import items_bp
from .tasks import tasks_bp
from .settings import settings_bp

__all__ = [
    'editions_bp',
    'items_bp',
    'tasks_bp',
    'settings_bp',
]
