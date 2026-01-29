"""
Background Task API endpoints.

Provides REST API for task management:
- GET /api/tasks/status - Get current task status
- POST /api/tasks/scan - Start scan task
- POST /api/tasks/scrape - Start scrape task
- POST /api/tasks/analyze - Start analyze task
- POST /api/tasks/sync - Start full sync
- POST /api/tasks/clear-logs - Clear task logs
"""

from flask import Blueprint, jsonify, request, current_app

from ..services.task_manager import (
    get_task_manager,
    run_scan_task,
    run_scrape_task,
    run_analyze_task,
    run_sync_all_task,
)

tasks_bp = Blueprint('tasks', __name__)


def get_config() -> dict:
    """Get config from current app context."""
    return current_app.config.get('mtb_config', {})


@tasks_bp.route('/status', methods=['GET'])
def get_status():
    """
    Get current task status.
    
    Returns:
        JSON with running, task, logs, progress, total, error
    """
    task_manager = get_task_manager()
    return jsonify(task_manager.status)


@tasks_bp.route('/scan', methods=['POST'])
def start_scan():
    """
    Start a scan task.
    
    Query params:
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
        
    Returns:
        JSON with started status
    """
    config = get_config()
    task_manager = get_task_manager()
    
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    started = task_manager.start_task(
        'scan',
        run_scan_task,
        config,
        task_manager,
        date_from,
        date_to
    )
    
    if not started:
        return jsonify({
            'started': False,
            'error': 'Another task is running'
        }), 409
    
    return jsonify({'started': True})


@tasks_bp.route('/scrape', methods=['POST'])
def start_scrape():
    """
    Start a scrape task.
    
    Query params:
        edition: Specific edition to scrape (optional)
        
    Returns:
        JSON with started status
    """
    config = get_config()
    task_manager = get_task_manager()
    
    edition_id = request.args.get('edition')
    
    task_name = f'scrape {edition_id}' if edition_id else 'scrape all'
    
    started = task_manager.start_task(
        task_name,
        run_scrape_task,
        config,
        task_manager,
        edition_id
    )
    
    if not started:
        return jsonify({
            'started': False,
            'error': 'Another task is running'
        }), 409
    
    return jsonify({'started': True})


@tasks_bp.route('/analyze', methods=['POST'])
def start_analyze():
    """
    Start an analyze task.
    
    Query params:
        edition: Specific edition to analyze (optional)
        
    Returns:
        JSON with started status
    """
    config = get_config()
    task_manager = get_task_manager()
    
    edition_id = request.args.get('edition')
    
    task_name = f'analyze {edition_id}' if edition_id else 'analyze all'
    
    started = task_manager.start_task(
        task_name,
        run_analyze_task,
        config,
        task_manager,
        edition_id
    )
    
    if not started:
        return jsonify({
            'started': False,
            'error': 'Another task is running'
        }), 409
    
    return jsonify({'started': True})


@tasks_bp.route('/sync', methods=['POST'])
def start_sync():
    """
    Start a full sync task (scan + scrape + analyze).
    
    Only processes editions newer than the last fully processed one.
    
    Returns:
        JSON with started status
    """
    config = get_config()
    task_manager = get_task_manager()
    
    started = task_manager.start_task(
        'sync: starting',
        run_sync_all_task,
        config,
        task_manager
    )
    
    if not started:
        return jsonify({
            'started': False,
            'error': 'Another task is running'
        }), 409
    
    return jsonify({'started': True})


@tasks_bp.route('/clear-logs', methods=['POST'])
def clear_logs():
    """
    Clear task logs.
    
    Returns:
        JSON with cleared status
    """
    task_manager = get_task_manager()
    task_manager.clear_logs()
    return jsonify({'cleared': True})
