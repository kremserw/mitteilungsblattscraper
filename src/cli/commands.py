"""
CLI commands for JKU MTB Analyzer.

All Click commands are defined here, with lazy imports for heavy dependencies.
"""

import sys

import click

from ..config import load_config, ConfigError
from ..ui import (
    console, print_header, print_stats, print_editions_list,
    print_items_list, print_item_detail, print_relevant_summary,
    run_web_server
)


def load_config_safe(config_path: str) -> dict:
    """
    Load configuration with user-friendly error handling.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dict
    """
    try:
        return load_config(config_path)
    except ConfigError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


def get_repository(config: dict):
    """Get repository instance from config."""
    from ..db.repository import get_repository
    db_path = config.get('storage', {}).get('database', 'data/mtb.db')
    return get_repository(db_path)


@click.group()
@click.option('--config', '-c', default='config.yaml', help='Path to config file')
@click.pass_context
def cli(ctx, config):
    """JKU Mitteilungsblatt Analyzer - AI-powered relevance filtering."""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.pass_context
def scan(ctx):
    """Discover and add new editions from the JKU MTB portal."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    
    # Lazy import
    from ..core.scraper import run_scraper
    
    repository = get_repository(config)
    
    console.print("[blue]Scanning for new editions...[/blue]")
    
    try:
        editions = run_scraper(repository, config)
        console.print(f"[green]Found {len(editions)} editions.[/green]")
        print_stats(repository)
    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        raise


@cli.command()
@click.option('--edition', '-e', help='Specific edition to scrape (e.g., 2025-15)')
@click.pass_context
def scrape(ctx, edition):
    """Scrape content from editions."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    
    # Lazy import
    from ..core.scraper import scrape_edition
    
    repository = get_repository(config)
    
    if edition:
        # Scrape specific edition
        try:
            year, stueck = map(int, edition.split('-'))
            console.print(f"[blue]Scraping edition {edition}...[/blue]")
            
            ed, items = scrape_edition(repository, config, year, stueck)
            console.print(f"[green]Scraped {len(items)} items from {edition}.[/green]")
        except ValueError:
            console.print("[red]Invalid edition format. Use YYYY-NN (e.g., 2025-15)[/red]")
            return
        except Exception as e:
            console.print(f"[red]Error scraping: {e}[/red]")
            raise
    else:
        # Scrape all unscraped editions
        unscraped = repository.get_unscraped_editions()
        if not unscraped:
            console.print("[yellow]No unscraped editions found. Run 'scan' first.[/yellow]")
            return
        
        console.print(f"[blue]Scraping {len(unscraped)} editions...[/blue]")
        
        for ed in unscraped:
            try:
                console.print(f"  Scraping {ed.edition_id}...")
                scrape_edition(repository, config, ed.year, ed.stueck)
            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
        
        console.print("[green]Scraping complete.[/green]")
        print_stats(repository)


@cli.command()
@click.option('--edition', '-e', help='Specific edition to analyze (e.g., 2025-15)')
@click.option('--force', '-f', is_flag=True, help='Re-analyze already analyzed editions')
@click.pass_context
def analyze(ctx, edition, force):
    """Analyze scraped content for relevance."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    
    # Lazy import
    from ..core.analyzer import analyze_edition_cli, analyze_all_cli
    
    if edition:
        analyze_edition_cli(config, edition, force=force)
    else:
        analyze_all_cli(config)
    
    repository = get_repository(config)
    print_stats(repository)


@cli.command('list')
@click.option('--year', '-y', type=int, help='Filter by year')
@click.pass_context
def list_editions(ctx, year):
    """List all known editions."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    repository = get_repository(config)
    
    editions = repository.get_all_editions(year=year)
    
    if not editions:
        console.print("[yellow]No editions found. Run 'scan' to discover editions.[/yellow]")
        return
    
    print_editions_list(editions)


@cli.command()
@click.option('--threshold', '-t', type=float, default=60.0, help='Minimum relevance score')
@click.pass_context
def relevant(ctx, threshold):
    """Show items marked as relevant."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    repository = get_repository(config)
    
    items = repository.get_relevant_items(threshold=threshold)
    
    if not items:
        console.print(f"[yellow]No items found with relevance >= {threshold}%[/yellow]")
        console.print("Run 'analyze' to analyze editions first.")
        return
    
    print_relevant_summary(items)


@cli.command()
@click.argument('edition_id')
@click.pass_context
def show(ctx, edition_id):
    """Show details for a specific edition."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    repository = get_repository(config)
    
    edition = repository.get_edition_by_id(edition_id)
    
    if not edition:
        console.print(f"[red]Edition {edition_id} not found.[/red]")
        return
    
    console.print(f"[bold]Edition: {edition.edition_id}[/bold]")
    console.print(f"Title: {edition.title or 'N/A'}")
    console.print(f"Published: {edition.published_date or 'N/A'}")
    console.print(f"Scraped: {edition.scraped_at or 'Not scraped'}")
    console.print(f"Analyzed: {edition.analyzed_at or 'Not analyzed'}")
    console.print()
    
    items = repository.get_items_for_edition(edition)
    if items:
        print_items_list(items, threshold=config.get('relevance_threshold', 60))
    else:
        console.print("[yellow]No items found for this edition.[/yellow]")


@cli.command()
@click.argument('item_id')
@click.pass_context
def item(ctx, item_id):
    """Show details for a specific item (format: edition-punkt, e.g., 2025-15-3)."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    repository = get_repository(config)
    
    try:
        parts = item_id.split('-')
        if len(parts) == 3:
            year, stueck, punkt = map(int, parts)
        else:
            console.print("[red]Invalid item ID. Use format: YYYY-NN-P (e.g., 2025-15-3)[/red]")
            return
    except ValueError:
        console.print("[red]Invalid item ID format.[/red]")
        return
    
    edition = repository.get_edition(year, stueck)
    if not edition:
        console.print(f"[red]Edition {year}-{stueck} not found.[/red]")
        return
    
    items = repository.get_items_for_edition(edition)
    target_item = next((i for i in items if i.punkt == punkt), None)
    
    if not target_item:
        console.print(f"[red]Item {punkt} not found in edition {year}-{stueck}.[/red]")
        return
    
    print_item_detail(target_item)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    repository = get_repository(config)
    print_stats(repository)


@cli.command()
@click.option('--port', '-p', type=int, default=8080, help='Port to run server on')
@click.pass_context
def serve(ctx, port):
    """Start the web interface."""
    print_header()
    config_path = ctx.obj['config_path']
    config = load_config(config_path)
    # Store config path for saving role description changes
    config['_config_path'] = config_path
    repository = get_repository(config)
    run_web_server(repository, config, port=port)


@cli.command()
@click.pass_context
def quicktest(ctx):
    """Quick test of the Claude API connection."""
    print_header()
    config = load_config_safe(ctx.obj['config_path'])
    
    console.print("[blue]Testing Claude API connection...[/blue]")
    
    try:
        from ..core.analyzer import RelevanceAnalyzer
        
        analyzer = RelevanceAnalyzer(
            api_key=config['anthropic_api_key'],
            model=config.get('model')
        )
        
        score, explanation, short_title = analyzer.analyze_item(
            content="Curriculum für das Masterstudium Artificial Intelligence - Änderung der ECTS-Punkte für das Fach Machine Learning von 6 auf 9 ECTS.",
            role_description=config['role_description'],
            item_title="Test Item",
            category="Curricula"
        )
        
        console.print("[green]API connection successful![/green]")
        console.print(f"Test score: {score:.0f}%")
        console.print(f"Short title: {short_title}")
        console.print(f"Explanation: {explanation}")
        
    except Exception as e:
        console.print(f"[red]API test failed: {e}[/red]")
        raise
