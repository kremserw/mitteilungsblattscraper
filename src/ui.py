"""
UI components for JKU MTB Analyzer.

This module provides:
- Terminal UI using Rich library
- Web server launcher (imports from api and web modules)

For web templates and routes, see src/web/ and src/api/.
"""

import threading
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .storage import Storage, Edition, BulletinItem


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
        title="Item Detail",
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
        console.print(
            f"[bold]{item.edition.edition_id}-{item.punkt}[/bold] "
            f"[{score:.0f}%] {item.title or 'Untitled'}"
        )
        
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


# Web server launcher

def run_web_server(storage: Storage, config: dict, port: int = 8080):
    """
    Run the web server.
    
    Args:
        storage: Storage instance (will be converted to Repository)
        config: Application configuration
        port: Port to run on
    """
    from .api.app import create_app
    from .db.repository import Repository
    
    # Get repository (storage is now a Repository alias)
    repository = storage if isinstance(storage, Repository) else Repository(
        config.get('storage', {}).get('database', 'data/mtb.db')
    )
    
    # Create Flask app
    app = create_app(config, repository)
    
    # Run server
    print(f"Starting web server on http://localhost:{port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True,
        use_reloader=False
    )
