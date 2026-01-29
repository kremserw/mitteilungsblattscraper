"""
Bulletin Item API endpoints.

Provides REST API for item management:
- GET /api/items - List relevant items
- GET /api/items/<id> - Get single item
- POST /api/items/<id>/read - Mark item as read
- POST /api/items/<id>/analyze-pdf - Analyze PDF attachments
"""

from flask import Blueprint, jsonify, request, current_app

from ...db.repository import Repository

items_bp = Blueprint('items', __name__)


def get_repository() -> Repository:
    """Get repository from current app context."""
    return current_app.config.get('repository')


def get_config() -> dict:
    """Get config from current app context."""
    return current_app.config.get('mtb_config', {})


@items_bp.route('/', methods=['GET'])
@items_bp.route('', methods=['GET'])
def list_items():
    """
    List relevant items.
    
    Query params:
        threshold: Minimum relevance score (default: 60)
        limit: Maximum items to return (optional)
        
    Returns:
        JSON list of bulletin items
    """
    repo = get_repository()
    threshold = request.args.get('threshold', 60.0, type=float)
    
    items = repo.get_relevant_items(threshold=threshold)
    
    return jsonify([item.to_dict() for item in items])


@items_bp.route('/recent', methods=['GET'])
def list_recent():
    """
    List recent relevant items.
    
    Query params:
        threshold: Minimum relevance score (default: 60)
        limit: Maximum items to return (default: 10)
        
    Returns:
        JSON list of bulletin items
    """
    repo = get_repository()
    threshold = request.args.get('threshold', 60.0, type=float)
    limit = request.args.get('limit', 10, type=int)
    
    items = repo.get_recent_relevant_items(threshold=threshold, limit=limit)
    
    return jsonify([item.to_dict() for item in items])


@items_bp.route('/<int:item_id>', methods=['GET'])
def get_item(item_id: int):
    """
    Get a single item by ID.
    
    Args:
        item_id: Item database ID
        
    Returns:
        JSON item object or 404
    """
    repo = get_repository()
    item = repo.get_item_by_id(item_id)
    
    if not item:
        return jsonify({'error': f'Item {item_id} not found'}), 404
    
    return jsonify(item.to_dict())


@items_bp.route('/<int:item_id>/read', methods=['POST'])
def mark_read(item_id: int):
    """
    Mark an item as read.
    
    Args:
        item_id: Item database ID
        
    Returns:
        JSON success response
    """
    repo = get_repository()
    success = repo.mark_item_read(item_id)
    
    return jsonify({'marked': success, 'item_id': item_id})


@items_bp.route('/<int:item_id>/analyze-pdf', methods=['POST'])
def analyze_pdf(item_id: int):
    """
    Analyze PDF attachments for an item.
    
    Downloads PDFs and performs AI analysis.
    
    Args:
        item_id: Item database ID
        
    Returns:
        JSON with analysis results
    """
    repo = get_repository()
    config = get_config()
    
    item = repo.get_item_by_id(item_id)
    
    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404
    
    if not item.attachments:
        return jsonify({'success': False, 'error': 'No attachments to analyze'}), 400
    
    try:
        # Import analyzer lazily to avoid loading anthropic at startup
        from ...core.analyzer import BulletinAnalyzer
        
        analyzer = BulletinAnalyzer(repo, config)
        analysis = analyzer.analyze_item_with_pdf(item)
        
        return jsonify({
            'success': True,
            'item_id': item_id,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
