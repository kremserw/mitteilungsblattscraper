"""
UI components for JKU MTB Analyzer.
Provides both terminal (Rich) and web (Flask) interfaces.
"""

import threading
import os
import yaml
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from flask import Flask, render_template_string, request, jsonify, redirect, url_for

from .storage import Storage, Edition, BulletinItem, get_storage


# Terminal UI using Rich
console = Console()


def print_header():
    """Print application header."""
    console.print(Panel.fit(
        "[bold blue]JKU Mitteilungsblatt Analyzer[/bold blue]\n"
        "[dim]AI-powered relevance filtering for university bulletins[/dim]",
        border_style="blue"
    ))


def print_stats(storage: Storage):
    """Print summary statistics."""
    stats = storage.get_stats()
    
    table = Table(title="Database Statistics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total editions", str(stats['total_editions']))
    table.add_row("Scraped editions", str(stats['scraped_editions']))
    table.add_row("Analyzed editions", str(stats['analyzed_editions']))
    table.add_row("Total items", str(stats['total_items']))
    table.add_row("Analyzed items", str(stats['analyzed_items']))
    table.add_row("Relevant items", f"[bold]{stats['relevant_items']}[/bold]")
    
    console.print(table)


def print_editions_list(editions: List[Edition], show_status: bool = True):
    """Print list of editions."""
    table = Table(title="Mitteilungsblatt Editions")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Published", style="dim")
    
    if show_status:
        table.add_column("Status", style="yellow")
    
    for ed in editions:
        status = ""
        if show_status:
            if ed.analyzed_at:
                status = "[green]✓ Analyzed[/green]"
            elif ed.scraped_at:
                status = "[yellow]○ Scraped[/yellow]"
            else:
                status = "[dim]· Pending[/dim]"
        
        row = [
            ed.edition_id,
            (ed.title or "")[:50],
            ed.published_date.strftime("%Y-%m-%d") if ed.published_date else "-",
        ]
        
        if show_status:
            row.append(status)
        
        table.add_row(*row)
    
    console.print(table)


def print_items_list(items: List[BulletinItem], threshold: float = 60.0):
    """Print list of bulletin items with relevance scores."""
    table = Table(title="Bulletin Items")
    table.add_column("Edition", style="cyan")
    table.add_column("Punkt", style="dim")
    table.add_column("Category", style="blue")
    table.add_column("Title", max_width=40)
    table.add_column("Score", justify="right")
    
    for item in items:
        score = item.relevance_score or 0
        
        # Color code score
        if score >= 80:
            score_str = f"[bold green]{score:.0f}%[/bold green]"
        elif score >= threshold:
            score_str = f"[green]{score:.0f}%[/green]"
        elif score >= 40:
            score_str = f"[yellow]{score:.0f}%[/yellow]"
        else:
            score_str = f"[dim]{score:.0f}%[/dim]"
        
        table.add_row(
            item.edition.edition_id if item.edition else "?",
            str(item.punkt or "-"),
            item.category or "-",
            (item.title or "")[:40],
            score_str
        )
    
    console.print(table)


def print_item_detail(item: BulletinItem):
    """Print detailed view of a bulletin item."""
    score = item.relevance_score or 0
    
    # Score indicator
    if score >= 80:
        score_style = "bold green"
        indicator = "🟢"
    elif score >= 60:
        score_style = "green"
        indicator = "🟡"
    elif score >= 40:
        score_style = "yellow"
        indicator = "🟠"
    else:
        score_style = "dim"
        indicator = "⚪"
    
    console.print(Panel(
        f"[bold]{item.title or 'Untitled'}[/bold]\n\n"
        f"Edition: {item.edition.edition_id if item.edition else '?'} | "
        f"Punkt: {item.punkt or '-'} | "
        f"Category: {item.category or '-'}\n\n"
        f"Relevance: [{score_style}]{indicator} {score:.0f}%[/{score_style}]\n\n"
        f"[bold]Analysis:[/bold]\n{item.relevance_explanation or 'Not analyzed'}\n\n"
        f"[bold]Content Preview:[/bold]\n{(item.content or '')[:500]}{'...' if len(item.content or '') > 500 else ''}",
        title=f"Item Detail",
        border_style="blue"
    ))
    
    # Show attachments if any
    if item.attachments:
        console.print("\n[bold]Attachments:[/bold]")
        for att in item.attachments:
            console.print(f"  • {att.get('filename', 'Unknown')} ({att.get('type', '?')})")


def print_relevant_summary(items: List[BulletinItem]):
    """Print summary of relevant items."""
    if not items:
        console.print("[yellow]No relevant items found.[/yellow]")
        return
    
    console.print(f"\n[bold green]Found {len(items)} relevant items:[/bold green]\n")
    
    for item in items:
        score = item.relevance_score or 0
        console.print(f"[bold]{item.edition.edition_id}-{item.punkt}[/bold] "
                     f"[{score:.0f}%] {item.title or 'Untitled'}")
        
        # Show first sentence of explanation
        if item.relevance_explanation:
            explanation = item.relevance_explanation.split('.')[0] + '.'
            console.print(f"  [dim]{explanation}[/dim]")
        console.print()


def create_progress():
    """Create a progress indicator."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    )


# Web UI using Flask

# Global state for background tasks
task_status = {
    'running': False,
    'task': None,
    'logs': [],
    'progress': 0,
    'total': 0,
    'error': None
}
task_lock = threading.Lock()

# Store config path globally for updates
config_path = 'config.yaml'


def add_log(message: str):
    """Add a log message to the task status."""
    with task_lock:
        timestamp = datetime.now().strftime("%H:%M:%S")
        task_status['logs'].append(f"[{timestamp}] {message}")
        # Keep only last 100 logs
        if len(task_status['logs']) > 100:
            task_status['logs'] = task_status['logs'][-100:]


def run_scan_task(config: dict, date_from: str = None, date_to: str = None):
    """Run the scan task in background."""
    from .scraper import run_scraper
    from datetime import datetime
    
    try:
        add_log("Starting scan for new editions...")
        
        # Parse date strings (expected format: MM/DD/YYYY or YYYY-MM-DD)
        from_date = None
        to_date = None
        
        if date_from:
            try:
                # Try MM/DD/YYYY format first
                if '/' in date_from:
                    from_date = datetime.strptime(date_from, '%m/%d/%Y')
                else:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d')
                add_log(f"From date: {from_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                add_log(f"Warning: Could not parse from date '{date_from}': {e}")
        
        if date_to:
            try:
                # Try MM/DD/YYYY format first
                if '/' in date_to:
                    to_date = datetime.strptime(date_to, '%m/%d/%Y')
                else:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d')
                add_log(f"To date: {to_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                add_log(f"Warning: Could not parse to date '{date_to}': {e}")
        
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        storage = Storage(db_path)
        
        editions = run_scraper(storage, config, from_date=from_date, to_date=to_date)
        
        # Count new editions added
        new_count = sum(1 for ed in editions if storage.get_edition_by_id(ed['edition_id']))
        add_log(f"Found {len(editions)} editions in date range, {new_count} stored")
        
        with task_lock:
            task_status['running'] = False
            task_status['task'] = None
        
        add_log("Scan complete!")
        storage.close()
        
    except Exception as e:
        import traceback
        add_log(f"ERROR: {str(e)}")
        add_log(f"Traceback: {traceback.format_exc()}")
        with task_lock:
            task_status['running'] = False
            task_status['error'] = str(e)


def run_scrape_task(config: dict, edition_id: str = None, date_from: str = None, date_to: str = None):
    """Run the scrape task in background."""
    from .scraper import scrape_edition
    
    try:
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        storage = Storage(db_path)
        
        if edition_id:
            # Scrape specific edition
            year, stueck = map(int, edition_id.split('-'))
            add_log(f"Scraping edition {edition_id}...")
            
            ed, items = scrape_edition(storage, config, year, stueck)
            add_log(f"Scraped {len(items)} items from {edition_id}")
        else:
            # Scrape all unscraped editions, optionally filtered by date
            unscraped = storage.get_unscraped_editions()
            
            # Filter by date range if specified
            if date_from or date_to:
                filtered = []
                for ed in unscraped:
                    if ed.published_date:
                        if date_from:
                            try:
                                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                                if ed.published_date < from_date:
                                    continue
                            except:
                                pass
                        if date_to:
                            try:
                                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                                if ed.published_date > to_date:
                                    continue
                            except:
                                pass
                    filtered.append(ed)
                unscraped = filtered
                add_log(f"Filtered to {len(unscraped)} editions in date range")
            
            if not unscraped:
                add_log("No unscraped editions found. Run scan first.")
            else:
                with task_lock:
                    task_status['total'] = len(unscraped)
                    task_status['progress'] = 0
                
                add_log(f"Scraping {len(unscraped)} editions...")
                
                for i, ed in enumerate(unscraped):
                    add_log(f"Scraping {ed.edition_id}...")
                    try:
                        scrape_edition(storage, config, ed.year, ed.stueck)
                        add_log(f"  ✓ {ed.edition_id} done")
                    except Exception as e:
                        add_log(f"  ✗ {ed.edition_id} failed: {str(e)}")
                    
                    with task_lock:
                        task_status['progress'] = i + 1
        
        with task_lock:
            task_status['running'] = False
            task_status['task'] = None
        
        add_log("Scraping complete!")
        storage.close()
        
    except Exception as e:
        add_log(f"ERROR: {str(e)}")
        with task_lock:
            task_status['running'] = False
            task_status['error'] = str(e)


def run_analyze_task(config: dict, edition_id: str = None):
    """Run the analyze task in background."""
    from .analyzer import BulletinAnalyzer
    
    try:
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        storage = Storage(db_path)
        analyzer = BulletinAnalyzer(storage, config)
        
        if edition_id:
            # Analyze specific edition
            edition = storage.get_edition_by_id(edition_id)
            if not edition:
                add_log(f"Edition {edition_id} not found")
                return
            
            add_log(f"Analyzing edition {edition_id}...")
            result = analyzer.analyze_edition(edition, force=True)
            add_log(f"Analyzed {result.get('items', 0)} items, {result.get('relevant', 0)} relevant")
        else:
            # Analyze all unanalyzed editions
            unanalyzed = storage.get_unanalyzed_editions()
            
            if not unanalyzed:
                add_log("No unanalyzed editions found. Run scrape first.")
            else:
                with task_lock:
                    task_status['total'] = len(unanalyzed)
                    task_status['progress'] = 0
                
                add_log(f"Analyzing {len(unanalyzed)} editions...")
                
                for i, ed in enumerate(unanalyzed):
                    add_log(f"Analyzing {ed.edition_id}...")
                    try:
                        result = analyzer.analyze_edition(ed)
                        items = result.get('items', 0)
                        relevant = result.get('relevant', 0)
                        add_log(f"  ✓ {ed.edition_id}: {items} items, {relevant} relevant")
                    except Exception as e:
                        add_log(f"  ✗ {ed.edition_id} failed: {str(e)}")
                    
                    with task_lock:
                        task_status['progress'] = i + 1
        
        with task_lock:
            task_status['running'] = False
            task_status['task'] = None
        
        add_log("Analysis complete!")
        storage.close()
        
    except Exception as e:
        add_log(f"ERROR: {str(e)}")
        with task_lock:
            task_status['running'] = False
            task_status['error'] = str(e)


def create_web_app(storage: Storage, config: dict) -> Flask:
    """Create Flask web application."""
    app = Flask(__name__)
    
    # Store config reference for updates
    app.config['mtb_config'] = config
    
    # Base HTML template with modern styling
    BASE_TEMPLATE = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>JKU MTB Analyzer</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --bg-tertiary: #334155;
                --accent: #06b6d4;
                --accent-hover: #22d3ee;
                --success: #10b981;
                --warning: #f59e0b;
                --error: #ef4444;
                --text-primary: #f1f5f9;
                --text-secondary: #94a3b8;
                --text-muted: #64748b;
                --border: #475569;
            }
            
            * { box-sizing: border-box; margin: 0; padding: 0; }
            
            body {
                font-family: 'Space Grotesk', -apple-system, sans-serif;
                background: var(--bg-primary);
                color: var(--text-primary);
                min-height: 100vh;
                background-image: 
                    radial-gradient(ellipse at top, rgba(6, 182, 212, 0.1) 0%, transparent 50%),
                    radial-gradient(ellipse at bottom right, rgba(139, 92, 246, 0.08) 0%, transparent 50%);
            }
            
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--border);
            }
            
            .logo {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .logo-icon { font-size: 2.5em; }
            
            h1 {
                font-size: 1.8em;
                font-weight: 700;
                background: linear-gradient(135deg, var(--accent), #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .subtitle {
                color: var(--text-secondary);
                font-size: 0.9em;
                margin-top: 4px;
            }
            
            nav { display: flex; gap: 8px; }
            
            nav a {
                color: var(--text-secondary);
                text-decoration: none;
                padding: 10px 20px;
                border-radius: 8px;
                transition: all 0.2s;
                font-weight: 500;
            }
            
            nav a:hover, nav a.active {
                background: var(--bg-secondary);
                color: var(--accent);
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: var(--bg-secondary);
                padding: 24px;
                border-radius: 16px;
                border: 1px solid var(--border);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .stat-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
            }
            
            .stat-value {
                font-size: 2.5em;
                font-weight: 700;
                color: var(--accent);
                font-family: 'JetBrains Mono', monospace;
            }
            
            .stat-label {
                color: var(--text-secondary);
                margin-top: 8px;
                font-size: 0.95em;
            }
            
            .panel {
                background: var(--bg-secondary);
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 30px;
                border: 1px solid var(--border);
            }
            
            .panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .panel-header h2 {
                font-size: 1.2em;
                color: var(--text-primary);
            }
            
            .action-buttons {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                align-items: center;
            }
            
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 10px;
                font-family: inherit;
                font-size: 0.95em;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                text-decoration: none;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, var(--accent), #0891b2);
                color: white;
            }
            
            .btn-primary:hover:not(:disabled) {
                background: linear-gradient(135deg, var(--accent-hover), var(--accent));
                transform: translateY(-1px);
                box-shadow: 0 4px 20px rgba(6, 182, 212, 0.4);
            }
            
            .btn-secondary {
                background: var(--bg-tertiary);
                color: var(--text-primary);
                border: 1px solid var(--border);
            }
            
            .btn-secondary:hover:not(:disabled) {
                background: var(--border);
            }
            
            .btn-danger {
                background: linear-gradient(135deg, #dc2626, #b91c1c);
                color: white;
            }
            
            .btn-danger:hover:not(:disabled) {
                background: linear-gradient(135deg, #b91c1c, #991b1b);
            }
            
            .btn-success {
                background: linear-gradient(135deg, var(--success), #059669);
                color: white;
            }
            
            .btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .btn-sm {
                padding: 6px 12px;
                font-size: 0.8em;
            }
            
            .log-panel {
                background: var(--bg-primary);
                border: 1px solid var(--border);
                border-radius: 12px;
                margin-top: 20px;
                max-height: 250px;
                overflow-y: auto;
            }
            
            .log-header {
                padding: 12px 16px;
                background: var(--bg-tertiary);
                border-bottom: 1px solid var(--border);
                font-weight: 600;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: sticky;
                top: 0;
            }
            
            .log-content {
                padding: 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85em;
                line-height: 1.8;
            }
            
            .log-content:empty::before {
                content: "No activity yet. Click an action button to start.";
                color: var(--text-muted);
            }
            
            .log-line { color: var(--text-secondary); }
            .log-line.success { color: var(--success); }
            .log-line.error { color: var(--error); }
            .log-line.info { color: var(--accent); }
            
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .status-dot {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: var(--text-muted);
            }
            
            .status-dot.running {
                background: var(--warning);
                animation: pulse 1.5s infinite;
            }
            
            .status-dot.success { background: var(--success); }
            .status-dot.error { background: var(--error); }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .progress-bar {
                height: 4px;
                background: var(--bg-tertiary);
                border-radius: 2px;
                margin-top: 16px;
                overflow: hidden;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--accent), #8b5cf6);
                transition: width 0.3s;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                background: var(--bg-secondary);
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid var(--border);
            }
            
            th, td {
                padding: 16px;
                text-align: left;
                border-bottom: 1px solid var(--border);
            }
            
            th {
                background: var(--bg-tertiary);
                color: var(--text-secondary);
                font-weight: 600;
                font-size: 0.85em;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            tr:last-child td { border-bottom: none; }
            
            tr:hover td { background: rgba(6, 182, 212, 0.05); }
            
            tr.clickable { cursor: pointer; }
            
            .score {
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9em;
            }
            
            .score-high { background: rgba(16, 185, 129, 0.2); color: var(--success); }
            .score-medium { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
            .score-low { background: var(--bg-tertiary); color: var(--text-muted); }
            
            .status-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 0.85em;
            }
            
            .status-analyzed { background: rgba(16, 185, 129, 0.15); color: var(--success); }
            .status-scraped { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
            .status-pending { background: var(--bg-tertiary); color: var(--text-muted); }
            
            .section-title {
                font-size: 1.3em;
                margin-bottom: 20px;
                color: var(--text-primary);
            }
            
            .filter-form {
                display: flex;
                gap: 12px;
                align-items: center;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            
            .form-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            
            .form-group label {
                font-size: 0.85em;
                color: var(--text-secondary);
            }
            
            input, textarea, select {
                background: var(--bg-primary);
                border: 1px solid var(--border);
                color: var(--text-primary);
                padding: 10px 16px;
                border-radius: 8px;
                font-family: inherit;
            }
            
            input:focus, textarea:focus, select:focus {
                outline: none;
                border-color: var(--accent);
            }
            
            textarea {
                min-height: 150px;
                resize: vertical;
                font-size: 0.9em;
                line-height: 1.6;
            }
            
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: var(--text-muted);
            }
            
            .empty-state-icon {
                font-size: 3em;
                margin-bottom: 16px;
            }
            
            .item-link {
                color: var(--accent);
                text-decoration: none;
            }
            
            .item-link:hover {
                text-decoration: underline;
            }
            
            .edition-actions {
                display: flex;
                gap: 8px;
            }
            
            .detail-card {
                background: var(--bg-secondary);
                border-radius: 16px;
                padding: 32px;
                border: 1px solid var(--border);
            }
            
            .detail-header {
                margin-bottom: 24px;
                padding-bottom: 24px;
                border-bottom: 1px solid var(--border);
            }
            
            .detail-title {
                font-size: 1.5em;
                margin-bottom: 16px;
            }
            
            .detail-meta {
                display: flex;
                gap: 24px;
                flex-wrap: wrap;
                color: var(--text-secondary);
                font-size: 0.95em;
            }
            
            .detail-meta span {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .detail-section {
                margin-bottom: 24px;
            }
            
            .detail-section h3 {
                color: var(--text-secondary);
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 12px;
            }
            
            .detail-content {
                background: var(--bg-primary);
                border-radius: 12px;
                padding: 20px;
                line-height: 1.8;
                white-space: pre-wrap;
                font-size: 0.95em;
            }
            
            .external-link {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                color: var(--accent);
                text-decoration: none;
                padding: 12px 20px;
                background: rgba(6, 182, 212, 0.1);
                border-radius: 8px;
                transition: all 0.2s;
            }
            
            .external-link:hover {
                background: rgba(6, 182, 212, 0.2);
            }
            
            .back-link {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                color: var(--text-secondary);
                text-decoration: none;
                margin-bottom: 24px;
                transition: color 0.2s;
            }
            
            .back-link:hover {
                color: var(--accent);
            }
            
            .role-editor {
                width: 100%;
            }
            
            .role-editor textarea {
                width: 100%;
            }
            
            .date-filters {
                display: flex;
                gap: 12px;
                align-items: flex-end;
                padding: 16px;
                background: var(--bg-primary);
                border-radius: 12px;
                margin-bottom: 16px;
            }
            
            .date-filters input[type="date"] {
                width: 160px;
            }
            
            .save-indicator {
                color: var(--success);
                font-size: 0.9em;
                margin-left: 12px;
                opacity: 0;
                transition: opacity 0.3s;
            }
            
            .save-indicator.show {
                opacity: 1;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="logo">
                    <span class="logo-icon">🎓</span>
                    <div>
                        <h1>JKU MTB Analyzer</h1>
                        <div class="subtitle">AI-powered relevance filtering for university bulletins</div>
            </div>
                </div>
                <nav>
                    <a href="/" class="{{ 'active' if active_page == 'dashboard' else '' }}">Dashboard</a>
                    <a href="/editions" class="{{ 'active' if active_page == 'editions' else '' }}">Editions</a>
                    <a href="/relevant" class="{{ 'active' if active_page == 'relevant' else '' }}">Relevant Items</a>
                </nav>
            </header>
            
            {% block content %}{% endblock %}
        </div>
        
        <script>
            let pollInterval = null;
            
            function updateStatus() {
                fetch('/api/task-status')
                    .then(r => r.json())
                    .then(data => {
                        const statusDot = document.querySelector('.status-dot');
                        const statusText = document.querySelector('.status-text');
                        const logContent = document.querySelector('.log-content');
                        const progressFill = document.querySelector('.progress-fill');
                        const buttons = document.querySelectorAll('.action-buttons .btn');
                        
                        if (statusDot) {
                            statusDot.className = 'status-dot ' + (data.running ? 'running' : (data.error ? 'error' : 'success'));
                        }
                        
                        if (statusText) {
                            statusText.textContent = data.running ? 
                                `Running: ${data.task || 'task'}` : 
                                (data.error ? 'Error' : 'Idle');
                        }
                        
                        if (logContent && data.logs) {
                            logContent.innerHTML = data.logs.map(log => {
                                let cls = 'log-line';
                                if (log.includes('ERROR')) cls += ' error';
                                else if (log.includes('✓') || log.includes('complete')) cls += ' success';
                                else if (log.includes('Starting') || log.includes('Found')) cls += ' info';
                                return `<div class="${cls}">${log}</div>`;
                            }).join('');
                            logContent.scrollTop = logContent.scrollHeight;
                        }
                        
                        if (progressFill && data.total > 0) {
                            const pct = (data.progress / data.total) * 100;
                            progressFill.style.width = pct + '%';
                        }
                        
                        buttons.forEach(btn => {
                            if (!btn.classList.contains('no-disable')) {
                                btn.disabled = data.running;
                            }
                        });
                        
                        if (window.location.pathname === '/') {
                            fetch('/api/stats')
                                .then(r => r.json())
                                .then(stats => {
                                    const values = document.querySelectorAll('.stat-value');
                                    if (values.length >= 4) {
                                        values[0].textContent = stats.total_editions;
                                        values[1].textContent = stats.scraped_editions;
                                        values[2].textContent = stats.analyzed_editions;
                                        values[3].textContent = stats.relevant_items;
                                    }
                                });
                        }
                        
                        if (!data.running && pollInterval) {
                            setTimeout(() => {
                                if (!data.running) {
                                    clearInterval(pollInterval);
                                    pollInterval = null;
                                }
                            }, 2000);
                        }
                    });
            }
            
            function startTask(task, editionId = null) {
                let url = `/api/${task}`;
                const params = new URLSearchParams();
                
                if (editionId) {
                    params.append('edition', editionId);
                }
                
                // Check for date filters
                const dateFrom = document.getElementById('date-from');
                const dateTo = document.getElementById('date-to');
                if (dateFrom && dateFrom.value) {
                    params.append('date_from', dateFrom.value);
                }
                if (dateTo && dateTo.value) {
                    params.append('date_to', dateTo.value);
                }
                
                if (params.toString()) {
                    url += '?' + params.toString();
                }
                
                fetch(url, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.started) {
                            if (!pollInterval) {
                                pollInterval = setInterval(updateStatus, 1000);
                            }
                            updateStatus();
                        } else {
                            alert(data.error || 'Failed to start task');
                        }
                    });
            }
            
            function saveRoleDescription() {
                const textarea = document.getElementById('role-description');
                const indicator = document.getElementById('save-indicator');
                
                fetch('/api/save-role', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role_description: textarea.value })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.saved) {
                        indicator.classList.add('show');
                        setTimeout(() => indicator.classList.remove('show'), 2000);
                    } else {
                        alert('Failed to save: ' + (data.error || 'Unknown error'));
                    }
                });
            }
            
            function resetEdition(editionId) {
                fetch('/api/reset-edition?edition=' + editionId, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.reset) {
                            location.reload();
                        } else {
                            alert('Failed to reset: ' + (data.error || 'Unknown error'));
                        }
                    });
            }
            
            document.addEventListener('DOMContentLoaded', () => {
                updateStatus();
                pollInterval = setInterval(updateStatus, 2000);
            });
        </script>
    </body>
    </html>
    '''
    
    DASHBOARD_CONTENT = '''
    {% block content %}
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{{ stats.total_editions }}</div>
            <div class="stat-label">Total Editions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ stats.scraped_editions }}</div>
            <div class="stat-label">Scraped</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ stats.analyzed_editions }}</div>
            <div class="stat-label">Analyzed</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ stats.relevant_items }}</div>
            <div class="stat-label">Relevant Items</div>
        </div>
    </div>
    
    <div class="panel">
        <div class="panel-header">
            <h2>⚡ Actions</h2>
            <div class="status-indicator">
                <span class="status-dot"></span>
                <span class="status-text">Idle</span>
            </div>
        </div>
        <div class="action-buttons">
            <button class="btn btn-primary" onclick="startTask('scan')">
                🔍 Scan for New Editions
            </button>
            <button class="btn btn-primary" onclick="startTask('scrape')">
                📥 Scrape All Unscraped
            </button>
            <button class="btn btn-primary" onclick="startTask('analyze')">
                🤖 Analyze All Unanalyzed
            </button>
            <button class="btn btn-secondary no-disable" onclick="location.reload()">
                🔄 Refresh
            </button>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 0%"></div>
        </div>
        <div class="log-panel">
            <div class="log-header">
                <span>Activity Log</span>
                <button class="btn btn-secondary btn-sm no-disable" onclick="fetch('/api/clear-logs', {method:'POST'}).then(() => updateStatus())">Clear</button>
            </div>
            <div class="log-content"></div>
        </div>
    </div>
    
    <div class="panel">
        <div class="panel-header">
            <h2>👤 Your Role Description</h2>
            <div>
                <button class="btn btn-success btn-sm no-disable" onclick="saveRoleDescription()">💾 Save</button>
                <span id="save-indicator" class="save-indicator">✓ Saved!</span>
            </div>
        </div>
        <p style="color: var(--text-secondary); margin-bottom: 16px; font-size: 0.9em;">
            Describe your role and interests. The AI uses this to determine relevance of bulletin items.
        </p>
        <div class="role-editor">
            <textarea id="role-description" placeholder="Describe your role, interests, and what you want to be notified about...">{{ role_description }}</textarea>
        </div>
    </div>
    
    <h2 class="section-title">📌 Recent Relevant Items</h2>
    {% if recent_items %}
    <table>
        <tr>
            <th>Edition</th>
            <th>Category</th>
            <th>Title</th>
            <th>Score</th>
        </tr>
        {% for item in recent_items %}
        <tr class="clickable" onclick="window.location='/item/{{ item.id }}'">
            <td>{{ item.edition.edition_id if item.edition else '?' }}</td>
            <td>{{ item.category or '-' }}</td>
            <td>{{ item.title[:60] if item.title else '-' }}{% if item.title and item.title|length > 60 %}...{% endif %}</td>
            <td><span class="score {{ 'score-high' if item.relevance_score >= 80 else ('score-medium' if item.relevance_score >= 60 else 'score-low') }}">
                {{ item.relevance_score|round|int }}%
            </span></td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <div class="empty-state">
        <div class="empty-state-icon">📭</div>
        <p>No relevant items yet. Run Scan → Scrape → Analyze to find content.</p>
    </div>
    {% endif %}
    {% endblock %}
    '''
    
    EDITIONS_CONTENT = '''
    {% block content %}
    <div class="panel">
        <div class="panel-header">
            <h2>📚 All Editions</h2>
            <div class="status-indicator">
                <span class="status-dot"></span>
                <span class="status-text">Idle</span>
            </div>
        </div>
        
        <div class="date-filters">
            <div class="form-group">
                <label>From Date</label>
                <input type="date" id="date-from" />
            </div>
            <div class="form-group">
                <label>To Date</label>
                <input type="date" id="date-to" />
            </div>
            <button class="btn btn-secondary btn-sm no-disable" onclick="document.getElementById('date-from').value=''; document.getElementById('date-to').value='';">
                Clear Dates
            </button>
        </div>
        
        <div class="action-buttons">
            <button class="btn btn-primary" onclick="startTask('scan')">
                🔍 Scan for New
            </button>
            <button class="btn btn-primary" onclick="startTask('scrape')">
                📥 Scrape (in date range)
            </button>
            <button class="btn btn-primary" onclick="startTask('analyze')">
                🤖 Analyze All
            </button>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 0%"></div>
        </div>
        <div class="log-panel">
            <div class="log-header">
                <span>Activity Log</span>
                <button class="btn btn-secondary btn-sm no-disable" onclick="fetch('/api/clear-logs', {method:'POST'}).then(() => updateStatus())">Clear</button>
            </div>
            <div class="log-content"></div>
        </div>
    </div>
    
    {% if editions %}
        <table>
            <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Published</th>
                <th>Status</th>
            <th>Actions</th>
            </tr>
            {% for ed in editions %}
        <tr id="{{ ed.edition_id }}">
            <td><strong>{{ ed.edition_id }}</strong></td>
            <td>{{ ed.title[:50] if ed.title else '-' }}{% if ed.title and ed.title|length > 50 %}...{% endif %}</td>
                <td>{{ ed.published_date.strftime('%Y-%m-%d') if ed.published_date else '-' }}</td>
                <td>
                    {% if ed.analyzed_at %}
                <span class="status-badge status-analyzed">✓ Analyzed</span>
                    {% elif ed.scraped_at %}
                <span class="status-badge status-scraped">○ Scraped</span>
                    {% else %}
                <span class="status-badge status-pending">· Pending</span>
                {% endif %}
            </td>
            <td class="edition-actions">
                {% if not ed.scraped_at %}
                <button class="btn btn-secondary btn-sm" onclick="startTask('scrape', '{{ ed.edition_id }}')">Scrape</button>
                {% elif not ed.analyzed_at %}
                <button class="btn btn-secondary btn-sm" onclick="startTask('analyze', '{{ ed.edition_id }}')">Analyze</button>
                {% else %}
                <button class="btn btn-secondary btn-sm" onclick="startTask('analyze', '{{ ed.edition_id }}')">Re-analyze</button>
                {% endif %}
                {% if ed.scraped_at %}
                <button class="btn btn-danger btn-sm no-disable" onclick="if(confirm('Reset {{ ed.edition_id }}? This will delete all items and require re-scraping.')) resetEdition('{{ ed.edition_id }}')">Reset</button>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    {% else %}
    <div class="empty-state">
        <div class="empty-state-icon">📭</div>
        <p>No editions found. Click "Scan for New" to discover editions.</p>
    </div>
    {% endif %}
    {% endblock %}
    '''
    
    RELEVANT_CONTENT = '''
    {% block content %}
    <h2 class="section-title">🎯 Relevant Items</h2>
    <div class="filter-form">
        <form method="get" style="display: flex; gap: 12px; align-items: center;">
            <label>Minimum Score:</label>
            <input type="number" name="threshold" value="{{ threshold }}" min="0" max="100" style="width: 80px;" />
            <button type="submit" class="btn btn-secondary">Filter</button>
            </form>
        </div>
    
    {% if items %}
        <table>
            <tr>
                <th>Edition</th>
            <th>Pkt.</th>
                <th>Category</th>
                <th>Title</th>
                <th>Score</th>
            <th>Summary</th>
            </tr>
            {% for item in items %}
        <tr class="clickable" onclick="window.location='/item/{{ item.id }}'">
                <td>{{ item.edition.edition_id if item.edition else '?' }}</td>
            <td style="font-weight: 600; color: var(--accent-color);">{{ item.punkt or '-' }}</td>
                <td>{{ item.category or '-' }}</td>
            <td>{{ item.title[:50] if item.title else '-' }}{% if item.title and item.title|length > 50 %}...{% endif %}</td>
                <td><span class="score {{ 'score-high' if item.relevance_score >= 80 else 'score-medium' }}">
                    {{ item.relevance_score|round|int }}%
                </span></td>
            <td style="max-width: 250px; font-size: 0.9em; color: var(--text-secondary);">
                {{ item.relevance_explanation[:100] if item.relevance_explanation else '-' }}{% if item.relevance_explanation and item.relevance_explanation|length > 100 %}...{% endif %}
            </td>
            </tr>
            {% endfor %}
        </table>
    <p style="margin-top: 16px; color: var(--text-muted); font-size: 0.9em;">💡 Click on any row to see full details</p>
    {% else %}
    <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <p>No items found with relevance >= {{ threshold }}%</p>
        <p style="margin-top: 10px; font-size: 0.9em;">Try lowering the threshold or run analysis first.</p>
    </div>
    {% endif %}
    {% endblock %}
    '''
    
    ITEM_DETAIL_CONTENT = '''
    {% block content %}
    <a href="/relevant" class="back-link">← Back to Relevant Items</a>
    
    <div class="detail-card">
        <div class="detail-header">
            <h1 class="detail-title">{{ item.title or 'Untitled Item' }}</h1>
            <div class="detail-meta">
                <span>📅 Edition: <strong>{{ item.edition.edition_id if item.edition else '?' }}</strong></span>
                <span>📌 Punkt: <strong>{{ item.punkt or '-' }}</strong></span>
                <span>🏷️ Category: <strong>{{ item.category or '-' }}</strong></span>
                <span class="score {{ 'score-high' if (item.relevance_score or 0) >= 80 else ('score-medium' if (item.relevance_score or 0) >= 60 else 'score-low') }}">
                    {{ item.relevance_score|round|int if item.relevance_score else 0 }}% Relevant
                </span>
            </div>
        </div>
        
        <!-- Summary Section - What's Important -->
        <div class="detail-section" style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1)); border-left: 4px solid var(--accent-color); padding: 16px 20px; border-radius: 8px;">
            <h3 style="margin: 0 0 12px 0; color: var(--accent-color);">💡 Summary</h3>
            {% if summary %}
            <p style="margin: 0 0 10px 0; line-height: 1.5;">{{ summary }}</p>
            {% if key_points %}
            <ul style="margin: 0; padding-left: 20px; line-height: 1.4;">
                {% for point in key_points %}<li style="margin-bottom: 4px;">{{ point }}</li>{% endfor %}
            </ul>
            {% endif %}
            {% else %}
            <p style="margin: 0; color: var(--text-secondary);">No analysis available yet. Run the analyzer to get insights.</p>
            {% endif %}
        </div>
        
        {% if item.edition and item.edition.url %}
        <div class="detail-section">
            <h3>🔗 Original Source</h3>
            <a href="{{ item.edition.url }}" target="_blank" rel="noopener" class="external-link">
                Open in JKU Portal →
            </a>
        </div>
        {% endif %}
        
        <!-- Full Content -->
        <div class="detail-section">
            <h3>📄 Full Content</h3>
            <div class="detail-content" style="white-space: pre-wrap;">{{ content_text }}</div>
        </div>
        
        <!-- Links extracted from content -->
        {% if content_links %}
        <div class="detail-section">
            <h3>🔗 Links</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                {% for link in content_links %}
                <a href="{{ link.url }}" target="_blank" rel="noopener" class="external-link" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: var(--bg-tertiary); border-radius: 6px; text-decoration: none;">
                    🌐 {{ link.text[:50] if link.text|length > 50 else link.text }}{% if link.text|length > 50 %}...{% endif %}
                </a>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- Attachments -->
        {% if item.attachments %}
        <div class="detail-section">
            <h3>📎 Attachments</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                {% for att in item.attachments %}
                <a href="{{ att.url }}" target="_blank" rel="noopener" class="external-link" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: var(--bg-tertiary); border-radius: 6px; text-decoration: none;">
                    📄 {{ att.name or att.url.split('/')[-1] or 'Download' }}
                </a>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- Detailed Reasoning (at the bottom, separate section) -->
        {% if reasoning %}
        <div class="detail-section" style="margin-top: 40px; border-top: 1px solid var(--border-color); padding-top: 24px;">
            <details open>
                <summary style="cursor: pointer; font-size: 1.1em; color: var(--text-secondary); margin-bottom: 16px;">
                    🔍 <strong>AI Reasoning</strong>
                </summary>
                <div class="detail-content" style="padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 0.95em; color: var(--text-secondary); line-height: 1.6;">
                    {{ reasoning }}
                </div>
            </details>
        </div>
        {% endif %}
    </div>
    {% endblock %}
    '''
    
    @app.route('/')
    def dashboard():
        stats = storage.get_stats()
        recent_items = storage.get_relevant_items(threshold=60)[:10]
        role_description = config.get('role_description', '')
        template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', DASHBOARD_CONTENT)
        return render_template_string(template, stats=stats, recent_items=recent_items, 
                                      role_description=role_description, active_page='dashboard')
    
    @app.route('/editions')
    def editions():
        editions_list = storage.get_all_editions()
        template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', EDITIONS_CONTENT)
        return render_template_string(template, editions=editions_list, active_page='editions')
    
    @app.route('/relevant')
    def relevant():
        threshold = float(request.args.get('threshold', 60))
        items = storage.get_relevant_items(threshold=threshold)
        template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', RELEVANT_CONTENT)
        return render_template_string(template, items=items, threshold=threshold, active_page='relevant')
    
    @app.route('/item/<int:item_id>')
    def item_detail(item_id):
        item = storage.session.query(BulletinItem).filter_by(id=item_id).first()
        if not item:
            return redirect(url_for('relevant'))
        
        # Process content to extract links and clean text
        content = item.content or ''
        content_links = []
        content_text = content
        
        import re
        
        # Extract [Link: ...] URL: ... patterns (from our scraper annotation)
        link_pattern = r'\[Link:\s*([^\]]+)\]\s*\n?\s*URL:\s*(https?://[^\s\n]+)'
        matches = re.findall(link_pattern, content)
        for text, url in matches:
            # Clean up URL - remove trailing punctuation or German words that got attached
            clean_url = re.sub(r'[a-zA-ZäöüÄÖÜß]+\.$', '', url.strip())
            clean_url = clean_url.rstrip('.,;:')
            content_links.append({'text': text.strip(), 'url': clean_url})
        
        # Extract URLs that follow "URL: " label (from scraped job postings etc.)
        url_label_pattern = r'URL:\s*(https?://[^\s\n]+)'
        url_label_matches = re.findall(url_label_pattern, content)
        for url in url_label_matches:
            clean_url = url.rstrip('.,;:')
            # Don't add duplicates
            if clean_url and not any(clean_url == link['url'] for link in content_links):
                # Try to find the job title that precedes this URL
                # Look for "• [title]\nURL:" pattern
                title_pattern = r'•\s*([^\n•]+?)\s*\n?\s*URL:\s*' + re.escape(url)
                title_match = re.search(title_pattern, content)
                if title_match:
                    title = title_match.group(1).strip()[:80]  # Truncate long titles
                    content_links.append({'text': title, 'url': clean_url})
                else:
                    # Use domain as text
                    domain = re.search(r'https?://([^/]+)', clean_url)
                    domain_text = domain.group(1) if domain else clean_url
                    content_links.append({'text': domain_text, 'url': clean_url})
        
        # Also extract any other raw URLs in the text (not already captured)
        # Strict pattern - URLs end at whitespace or certain characters
        raw_url_pattern = r'(?<!URL:\s)(https?://[^\s\)\]\n<>]+)'
        raw_urls = re.findall(raw_url_pattern, content)
        for url in raw_urls:
            clean_url = url.rstrip('.,;:')
            # Remove trailing German words that got stuck
            clean_url = re.sub(r'[a-zA-ZäöüÄÖÜß]{4,}\.$', '', clean_url)
            # Don't add duplicates
            if clean_url and not any(clean_url in link['url'] or link['url'] in clean_url for link in content_links):
                domain = re.search(r'https?://([^/]+)', clean_url)
                domain_text = domain.group(1) if domain else clean_url
                content_links.append({'text': domain_text, 'url': clean_url})
        
        # Clean the content text by removing link annotations (keep the readable text)
        content_text = re.sub(r'\n*\[Link:[^\]]+\]\s*\n?\s*URL:\s*https?://[^\s\n]+', '', content)
        content_text = content_text.strip()
        
        # Parse AI explanation into summary and reasoning
        explanation = item.relevance_explanation or ''
        summary = ''
        key_points = []
        reasoning = ''
        
        if explanation:
            # Extract summary (everything before "Key points:" or first paragraph)
            if 'Key points:' in explanation:
                parts = explanation.split('Key points:')
                summary = parts[0].strip()
                rest = parts[1]
                # Extract key points
                if 'Rationale' in rest:
                    key_points_text = rest.split('Rationale')[0].strip()
                    reasoning = 'Rationale' + rest.split('Rationale')[1] if len(rest.split('Rationale')) > 1 else ''
                else:
                    key_points_text = rest.strip()
                # Parse bullet points
                for point in key_points_text.split('- '):
                    point = point.strip().rstrip(':').strip()
                    if point and not point.startswith('Rationale'):
                        key_points.append(point)
            elif 'Rationale' in explanation:
                parts = explanation.split('Rationale')
                summary = parts[0].strip()
                reasoning = 'Rationale' + parts[1] if len(parts) > 1 else ''
            else:
                summary = explanation[:500] + ('...' if len(explanation) > 500 else '')
        
        template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', ITEM_DETAIL_CONTENT)
        return render_template_string(template, item=item, content_text=content_text, 
                                      content_links=content_links, summary=summary,
                                      key_points=key_points, reasoning=reasoning,
                                      active_page='relevant')
    
    @app.route('/api/stats')
    def api_stats():
        return jsonify(storage.get_stats())
    
    @app.route('/api/task-status')
    def api_task_status():
        with task_lock:
            return jsonify({
                'running': task_status['running'],
                'task': task_status['task'],
                'logs': task_status['logs'][-50:],
                'progress': task_status['progress'],
                'total': task_status['total'],
                'error': task_status['error']
            })
    
    @app.route('/api/clear-logs', methods=['POST'])
    def api_clear_logs():
        with task_lock:
            task_status['logs'] = []
            task_status['error'] = None
        return jsonify({'cleared': True})
    
    @app.route('/api/save-role', methods=['POST'])
    def api_save_role():
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
            return jsonify({'saved': False, 'error': str(e)})
    
    @app.route('/api/scan', methods=['POST'])
    def api_scan():
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        with task_lock:
            if task_status['running']:
                return jsonify({'started': False, 'error': 'Another task is running'})
            task_status['running'] = True
            task_status['task'] = 'scan'
            task_status['progress'] = 0
            task_status['total'] = 0
            task_status['error'] = None
        
        thread = threading.Thread(target=run_scan_task, args=(config, date_from, date_to))
        thread.daemon = True
        thread.start()
        
        return jsonify({'started': True})
    
    @app.route('/api/scrape', methods=['POST'])
    def api_scrape():
        edition_id = request.args.get('edition')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        with task_lock:
            if task_status['running']:
                return jsonify({'started': False, 'error': 'Another task is running'})
            task_status['running'] = True
            task_status['task'] = f'scrape {edition_id}' if edition_id else 'scrape all'
            task_status['progress'] = 0
            task_status['total'] = 0
            task_status['error'] = None
        
        thread = threading.Thread(target=run_scrape_task, args=(config, edition_id, date_from, date_to))
        thread.daemon = True
        thread.start()
        
        return jsonify({'started': True})
    
    @app.route('/api/analyze', methods=['POST'])
    def api_analyze():
        edition_id = request.args.get('edition')
        
        with task_lock:
            if task_status['running']:
                return jsonify({'started': False, 'error': 'Another task is running'})
            task_status['running'] = True
            task_status['task'] = f'analyze {edition_id}' if edition_id else 'analyze all'
            task_status['progress'] = 0
            task_status['total'] = 0
            task_status['error'] = None
        
        thread = threading.Thread(target=run_analyze_task, args=(config, edition_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'started': True})
    
    @app.route('/api/reset-edition', methods=['POST'])
    def api_reset_edition():
        """Reset an edition for re-scraping."""
        edition_id = request.args.get('edition')
        if not edition_id:
            return jsonify({'reset': False, 'error': 'No edition specified'})
        
        try:
            edition = storage.get_edition_by_id(edition_id)
            if edition:
                storage.reset_edition(edition)
                add_log(f"✓ Reset edition {edition_id}")
                return jsonify({'reset': True})
            else:
                return jsonify({'reset': False, 'error': f'Edition {edition_id} not found'})
        except Exception as e:
            return jsonify({'reset': False, 'error': str(e)})
    
    @app.route('/api/reset-all', methods=['POST'])
    def api_reset_all():
        """Reset all data for re-scraping."""
        try:
            storage.reset_all_data()
            add_log("✓ Reset all data")
            return jsonify({'reset': True})
        except Exception as e:
            return jsonify({'reset': False, 'error': str(e)})
    
    return app


def run_web_server(storage: Storage, config: dict, port: int = 8080):
    """Run the web server."""
    # Store config path for saving
    config['_config_path'] = config.get('_config_path', 'config.yaml')
    
    app = create_web_app(storage, config)
    console.print(f"[green]Starting web server at http://localhost:{port}[/green]")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
