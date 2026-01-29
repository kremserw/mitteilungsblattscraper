"""
Web page rendering routes for JKU MTB Analyzer.

Provides routes for:
- / - Dashboard
- /editions - Editions list
- /relevant - Relevant items
- /item/<id> - Item detail
- /splash - Loading screen
- /pdf-proxy - PDF download proxy
"""

import html
from flask import Blueprint, render_template, request, Response, current_app

from ..db.repository import Repository
from ..api.services.pdf_proxy import download_pdf

web_bp = Blueprint('web', __name__)


def get_repository() -> Repository:
    """Get repository from current app context."""
    return current_app.config.get('repository')


def get_config() -> dict:
    """Get config from current app context."""
    return current_app.config.get('mtb_config', {})


@web_bp.route('/')
def dashboard():
    """Render the dashboard page."""
    repo = get_repository()
    config = get_config()
    
    stats = repo.get_stats()
    recent_items = repo.get_recent_relevant_items(threshold=60, limit=10)
    role_description = config.get('role_description', '')
    
    return render_template(
        'dashboard.html',
        active_page='dashboard',
        stats=stats,
        recent_items=recent_items,
        role_description=role_description
    )


@web_bp.route('/editions')
def editions():
    """Render the editions list page."""
    repo = get_repository()
    
    all_editions = repo.get_all_editions()
    
    return render_template(
        'editions.html',
        active_page='editions',
        editions=all_editions
    )


@web_bp.route('/relevant')
def relevant():
    """Render the relevant items page."""
    repo = get_repository()
    
    threshold = request.args.get('threshold', 60, type=float)
    items = repo.get_relevant_items(threshold=threshold)
    
    return render_template(
        'relevant.html',
        active_page='relevant',
        items=items,
        threshold=threshold
    )


@web_bp.route('/item/<int:item_id>')
def item_detail(item_id: int):
    """Render the item detail page."""
    import re
    
    repo = get_repository()
    
    item = repo.get_item_by_id(item_id)
    
    if not item:
        return render_template(
            'base.html',
            active_page=None,
            content='<div class="empty-state"><p>Item not found.</p></div>'
        ), 404
    
    # Mark as read
    repo.mark_item_read(item_id)
    
    # Parse explanation for summary, relevance, and key points
    summary = ''
    relevance = ''
    key_points = []
    
    if item.relevance_explanation:
        explanation = item.relevance_explanation
        
        # Try to extract Summary (objective description)
        summary_match = re.search(r'Summary:\s*(.+?)(?=Relevance:|Key points:|$)', explanation, re.IGNORECASE | re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # Try to extract Relevance (reasoning)
        relevance_match = re.search(r'Relevance:\s*(.+?)(?=Key points:|$)', explanation, re.IGNORECASE | re.DOTALL)
        if relevance_match:
            relevance = relevance_match.group(1).strip()
        
        # Try to extract key points
        key_points_match = re.search(r'Key points:\s*(.+?)$', explanation, re.IGNORECASE | re.DOTALL)
        if key_points_match:
            key_points_text = key_points_match.group(1).strip()
            
            # Parse bullet points
            for line in key_points_text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    key_points.append(line[1:].strip())
                elif line and not any(line.startswith(x) for x in ['SCORE', 'SHORT_TITLE', 'SUMMARY', 'RELEVANCE']):
                    key_points.append(line)
        
        # Fallback: if no structured format found, use full explanation
        if not summary and not relevance:
            # Old format - just split on Key points if present
            if 'Key points:' in explanation:
                parts = explanation.split('Key points:', 1)
                summary = parts[0].strip()
            else:
                summary = explanation
    
    # Extract URLs from content
    urls = []
    if item.content:
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        found_urls = re.findall(url_pattern, item.content)
        # Deduplicate and clean
        seen = set()
        for url in found_urls:
            # Remove trailing punctuation
            url = url.rstrip('.,;:)')
            if url not in seen:
                seen.add(url)
                urls.append(url)
    
    return render_template(
        'item_detail.html',
        active_page=None,
        item=item,
        summary=summary,
        relevance=relevance,
        key_points=key_points,
        content_urls=urls
    )


@web_bp.route('/splash')
def splash():
    """Render the loading splash screen."""
    return render_template('splash.html')


@web_bp.route('/pdf-proxy')
def pdf_proxy():
    """
    Proxy PDF downloads to handle CORS and filename issues.
    
    Query params:
        url: URL of the PDF to download
    """
    url = request.args.get('url', '')
    
    if not url:
        return 'Missing URL parameter', 400
    
    # Decode HTML entities
    url = html.unescape(url)
    
    content_iter, content_type, error = download_pdf(url)
    
    if error:
        return f'Failed to download: {error}', 500
    
    # Extract filename from URL
    filename = url.split('/')[-1].split('?')[0]
    if not filename.endswith('.pdf'):
        filename = 'document.pdf'
    
    return Response(
        content_iter,
        mimetype=content_type,
        headers={
            'Content-Disposition': f'inline; filename="{filename}"',
            'Content-Type': content_type
        }
    )
