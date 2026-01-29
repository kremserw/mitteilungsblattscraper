"""
Edition API endpoints.

Provides REST API for edition management:
- GET /api/editions - List all editions
- GET /api/editions/<id> - Get single edition
- POST /api/editions/<id>/reset - Reset an edition
"""

from flask import Blueprint, jsonify, request, current_app

from ...db.repository import Repository

editions_bp = Blueprint('editions', __name__)


def get_repository() -> Repository:
    """Get repository from current app context."""
    return current_app.config.get('repository')


@editions_bp.route('/', methods=['GET'])
@editions_bp.route('', methods=['GET'])
def list_editions():
    """
    List all editions.
    
    Query params:
        year: Filter by year (optional)
        
    Returns:
        JSON list of editions
    """
    repo = get_repository()
    year = request.args.get('year', type=int)
    
    editions = repo.get_all_editions(year=year)
    
    return jsonify([ed.to_dict() for ed in editions])


@editions_bp.route('/<edition_id>', methods=['GET'])
def get_edition(edition_id: str):
    """
    Get a single edition by ID.
    
    Args:
        edition_id: Edition ID string (e.g., "2025-15")
        
    Returns:
        JSON edition object or 404
    """
    repo = get_repository()
    edition = repo.get_edition_by_id(edition_id)
    
    if not edition:
        return jsonify({'error': f'Edition {edition_id} not found'}), 404
    
    return jsonify(edition.to_dict())


@editions_bp.route('/<edition_id>/items', methods=['GET'])
def get_edition_items(edition_id: str):
    """
    Get all items for an edition.
    
    Args:
        edition_id: Edition ID string
        
    Returns:
        JSON list of bulletin items
    """
    repo = get_repository()
    edition = repo.get_edition_by_id(edition_id)
    
    if not edition:
        return jsonify({'error': f'Edition {edition_id} not found'}), 404
    
    items = repo.get_items_for_edition(edition)
    
    return jsonify([item.to_dict() for item in items])


@editions_bp.route('/<edition_id>/reset', methods=['POST'])
def reset_edition(edition_id: str):
    """
    Reset an edition for re-scraping.
    
    Deletes all items and clears scraped/analyzed timestamps.
    
    Args:
        edition_id: Edition ID string
        
    Returns:
        JSON success/error response
    """
    repo = get_repository()
    edition = repo.get_edition_by_id(edition_id)
    
    if not edition:
        return jsonify({'error': f'Edition {edition_id} not found'}), 404
    
    try:
        repo.reset_edition(edition)
        return jsonify({'reset': True, 'edition_id': edition_id})
    except Exception as e:
        return jsonify({'reset': False, 'error': str(e)}), 500


@editions_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get summary statistics.
    
    Returns:
        JSON stats object
    """
    repo = get_repository()
    stats = repo.get_stats()
    return jsonify(stats)


@editions_bp.route('/unscraped', methods=['GET'])
def get_unscraped():
    """
    Get editions that haven't been scraped yet.
    
    Returns:
        JSON list of editions
    """
    repo = get_repository()
    editions = repo.get_unscraped_editions()
    return jsonify([ed.to_dict() for ed in editions])


@editions_bp.route('/unanalyzed', methods=['GET'])
def get_unanalyzed():
    """
    Get editions that have been scraped but not analyzed.
    
    Returns:
        JSON list of editions
    """
    repo = get_repository()
    editions = repo.get_unanalyzed_editions()
    return jsonify([ed.to_dict() for ed in editions])
