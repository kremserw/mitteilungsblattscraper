"""
Settings API endpoints.

Provides REST API for configuration management:
- GET /api/settings/role - Get role description
- PUT /api/settings/role - Update role description
- POST /api/settings/shutdown - Shutdown the server
"""

import os
import threading
from flask import Blueprint, jsonify, request, current_app

import yaml

settings_bp = Blueprint('settings', __name__)


def get_config() -> dict:
    """Get config from current app context."""
    return current_app.config.get('mtb_config', {})


@settings_bp.route('/role', methods=['GET'])
def get_role():
    """
    Get the current role description.
    
    Returns:
        JSON with role_description
    """
    config = get_config()
    role_description = config.get('role_description', '')
    
    return jsonify({'role_description': role_description})


@settings_bp.route('/role', methods=['PUT', 'POST'])
def update_role():
    """
    Update the role description.
    
    Request body:
        role_description: New role description text
        
    Returns:
        JSON with saved status
    """
    config = get_config()
    
    try:
        data = request.get_json()
        new_role = data.get('role_description', '')
        
        # Update in-memory config
        config['role_description'] = new_role
        
        # Save to config file
        config_file = config.get('_config_path', 'config.yaml')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f)
            
            file_config['role_description'] = new_role
            
            with open(config_file, 'w') as f:
                yaml.dump(file_config, f, default_flow_style=False, allow_unicode=True)
        
        return jsonify({'saved': True})
    except Exception as e:
        return jsonify({'saved': False, 'error': str(e)}), 500


@settings_bp.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Shutdown the server gracefully.
    
    Returns:
        JSON with shutdown status
    """
    from ..services.task_manager import get_task_manager
    
    task_manager = get_task_manager()
    task_manager.add_log("🛑 Shutdown requested...")
    
    def shutdown_server():
        import time
        time.sleep(0.5)  # Give time for response to be sent
        os._exit(0)
    
    shutdown_thread = threading.Thread(target=shutdown_server)
    shutdown_thread.daemon = True
    shutdown_thread.start()
    
    return jsonify({
        'shutdown': True,
        'message': 'Server shutting down...'
    })


@settings_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get database statistics.
    
    Returns:
        JSON with statistics
    """
    repo = current_app.config.get('repository')
    
    if repo is None:
        return jsonify({'error': 'Repository not configured'}), 500
    
    stats = repo.get_stats()
    
    return jsonify(stats)
