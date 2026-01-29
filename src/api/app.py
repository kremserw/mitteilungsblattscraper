"""
Flask application factory for JKU MTB Analyzer.

Creates and configures the Flask application with all blueprints.
"""

import os
from flask import Flask

from ..db.repository import Repository


def create_app(config: dict, repository: Repository) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config: Application configuration dict
        repository: Database repository instance
        
    Returns:
        Configured Flask application
    """
    # Determine template and static paths
    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
    template_dir = os.path.join(web_dir, 'templates')
    static_dir = os.path.join(web_dir, 'static')
    
    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
        static_url_path='/static'
    )
    
    # Store config and repository in app context
    app.config['mtb_config'] = config
    app.config['repository'] = repository
    
    # Register API blueprints
    from .routes.editions import editions_bp
    from .routes.items import items_bp
    from .routes.tasks import tasks_bp
    from .routes.settings import settings_bp
    
    app.register_blueprint(editions_bp, url_prefix='/api/editions')
    app.register_blueprint(items_bp, url_prefix='/api/items')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    
    # Register web views (pages)
    from ..web.views import web_bp
    app.register_blueprint(web_bp)
    
    return app


def get_repository_from_app(app: Flask) -> Repository:
    """Get repository instance from Flask app."""
    return app.config.get('repository')


def get_config_from_app(app: Flask) -> dict:
    """Get configuration dict from Flask app."""
    return app.config.get('mtb_config', {})
