"""
Background task management for JKU MTB Analyzer.

Handles async execution of scan, scrape, and analyze operations.
"""

import threading
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Callable

from ...db.repository import Repository


class TaskManager:
    """
    Manages background task execution with status tracking.
    
    Only one task can run at a time.
    """
    
    def __init__(self):
        """Initialize task manager."""
        self._lock = threading.Lock()
        self._running = False
        self._task_name: Optional[str] = None
        self._logs: List[str] = []
        self._progress = 0
        self._total = 0
        self._error: Optional[str] = None
    
    @property
    def is_running(self) -> bool:
        """Check if a task is currently running."""
        with self._lock:
            return self._running
    
    @property
    def status(self) -> dict:
        """Get current task status."""
        with self._lock:
            return {
                'running': self._running,
                'task': self._task_name,
                'logs': self._logs[-50:],  # Last 50 log entries
                'progress': self._progress,
                'total': self._total,
                'error': self._error,
            }
    
    def add_log(self, message: str):
        """Add a log message."""
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._logs.append(f"[{timestamp}] {message}")
            # Keep only last 100 logs
            if len(self._logs) > 100:
                self._logs = self._logs[-100:]
    
    def clear_logs(self):
        """Clear all logs."""
        with self._lock:
            self._logs = []
            self._error = None
    
    def set_progress(self, progress: int, total: int = 0):
        """Update progress."""
        with self._lock:
            self._progress = progress
            if total > 0:
                self._total = total
    
    def start_task(self, name: str, func: Callable, *args, **kwargs) -> bool:
        """
        Start a background task.
        
        Args:
            name: Task name for display
            func: Function to run
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            True if task started, False if another task is running
        """
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._task_name = name
            self._progress = 0
            self._total = 0
            self._error = None
        
        thread = threading.Thread(
            target=self._run_task,
            args=(func, args, kwargs),
            daemon=True
        )
        thread.start()
        return True
    
    def _run_task(self, func: Callable, args: tuple, kwargs: dict):
        """Run a task in the background thread."""
        try:
            func(*args, **kwargs)
        except Exception as e:
            self.add_log(f"ERROR: {str(e)}")
            self.add_log(f"Traceback: {traceback.format_exc()}")
            with self._lock:
                self._error = str(e)
        finally:
            with self._lock:
                self._running = False
                self._task_name = None


# Singleton instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get or create the task manager singleton."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


# Task functions

def run_scan_task(
    config: dict,
    task_manager: TaskManager,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Run the scan task.
    
    Args:
        config: Application config
        task_manager: Task manager instance
        date_from: Optional start date string
        date_to: Optional end date string
    """
    from ...db.repository import Repository
    from ...core.scraper import run_scraper
    
    try:
        task_manager.add_log("Starting scan for new editions...")
        
        # Parse dates
        from_date = None
        to_date = None
        
        if date_from:
            try:
                if '/' in date_from:
                    from_date = datetime.strptime(date_from, '%m/%d/%Y')
                else:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d')
                task_manager.add_log(f"From date: {from_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                task_manager.add_log(f"Warning: Could not parse from date: {e}")
        
        if date_to:
            try:
                if '/' in date_to:
                    to_date = datetime.strptime(date_to, '%m/%d/%Y')
                else:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d')
                task_manager.add_log(f"To date: {to_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                task_manager.add_log(f"Warning: Could not parse to date: {e}")
        
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        repository = Repository(db_path)
        
        editions = run_scraper(repository, config, from_date=from_date, to_date=to_date)
        
        task_manager.add_log(f"Found {len(editions)} editions")
        task_manager.add_log("Scan complete!")
        
        repository.close()
        
    except Exception as e:
        task_manager.add_log(f"ERROR: {str(e)}")
        raise


def run_scrape_task(
    config: dict,
    task_manager: TaskManager,
    edition_id: Optional[str] = None
):
    """
    Run the scrape task.
    
    Args:
        config: Application config
        task_manager: Task manager instance
        edition_id: Optional specific edition to scrape
    """
    from ...db.repository import Repository
    from ...core.scraper import scrape_edition
    
    try:
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        repository = Repository(db_path)
        
        if edition_id:
            year, stueck = map(int, edition_id.split('-'))
            task_manager.add_log(f"Scraping edition {edition_id}...")
            
            ed, items = scrape_edition(repository, config, year, stueck)
            task_manager.add_log(f"Scraped {len(items)} items from {edition_id}")
        else:
            unscraped = repository.get_unscraped_editions()
            
            if not unscraped:
                task_manager.add_log("No unscraped editions found. Run scan first.")
            else:
                task_manager.set_progress(0, len(unscraped))
                task_manager.add_log(f"Scraping {len(unscraped)} editions...")
                
                for i, ed in enumerate(unscraped):
                    task_manager.add_log(f"Scraping {ed.edition_id}...")
                    try:
                        scrape_edition(repository, config, ed.year, ed.stueck)
                        task_manager.add_log(f"  ✓ {ed.edition_id} done")
                    except Exception as e:
                        task_manager.add_log(f"  ✗ {ed.edition_id} failed: {str(e)}")
                    
                    task_manager.set_progress(i + 1)
        
        task_manager.add_log("Scraping complete!")
        repository.close()
        
    except Exception as e:
        task_manager.add_log(f"ERROR: {str(e)}")
        raise


def run_analyze_task(
    config: dict,
    task_manager: TaskManager,
    edition_id: Optional[str] = None
):
    """
    Run the analyze task.
    
    Args:
        config: Application config
        task_manager: Task manager instance
        edition_id: Optional specific edition to analyze
    """
    from ...db.repository import Repository
    from ...core.analyzer import BulletinAnalyzer
    
    try:
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        repository = Repository(db_path)
        analyzer = BulletinAnalyzer(repository, config)
        
        if edition_id:
            edition = repository.get_edition_by_id(edition_id)
            if not edition:
                task_manager.add_log(f"Edition {edition_id} not found")
                return
            
            task_manager.add_log(f"Analyzing edition {edition_id}...")
            result = analyzer.analyze_edition(edition, force=True)
            task_manager.add_log(
                f"Analyzed {result.get('items', 0)} items, "
                f"{result.get('relevant', 0)} relevant"
            )
        else:
            unanalyzed = repository.get_unanalyzed_editions()
            
            if not unanalyzed:
                task_manager.add_log("No unanalyzed editions found. Run scrape first.")
            else:
                task_manager.set_progress(0, len(unanalyzed))
                task_manager.add_log(f"Analyzing {len(unanalyzed)} editions...")
                
                for i, ed in enumerate(unanalyzed):
                    task_manager.add_log(f"Analyzing {ed.edition_id}...")
                    try:
                        result = analyzer.analyze_edition(ed)
                        items = result.get('items', 0)
                        relevant = result.get('relevant', 0)
                        task_manager.add_log(
                            f"  ✓ {ed.edition_id}: {items} items, {relevant} relevant"
                        )
                    except Exception as e:
                        task_manager.add_log(f"  ✗ {ed.edition_id} failed: {str(e)}")
                    
                    task_manager.set_progress(i + 1)
        
        task_manager.add_log("Analysis complete!")
        repository.close()
        
    except Exception as e:
        task_manager.add_log(f"ERROR: {str(e)}")
        raise


def run_sync_all_task(config: dict, task_manager: TaskManager):
    """
    Run scan, scrape, and analyze for NEW editions only.
    
    Only processes editions that are newer than the most recent
    already-scraped and analyzed edition.
    """
    from ...db.repository import Repository
    from ...core.scraper import run_scraper, scrape_edition
    from ...core.analyzer import BulletinAnalyzer
    
    try:
        db_path = config.get('storage', {}).get('database', 'data/mtb.db')
        repository = Repository(db_path)
        
        # Find the latest fully processed edition
        all_editions = repository.get_all_editions()
        latest_processed = None
        for ed in all_editions:
            if ed.scraped_at and ed.analyzed_at:
                latest_processed = ed
                break
        
        # Phase 1: Scan
        task_manager.add_log("📡 Phase 1/3: Scanning for new editions...")
        task_manager._task_name = 'sync: scanning'
        
        from_date = None
        if latest_processed and latest_processed.published_date:
            from_date = latest_processed.published_date
            task_manager.add_log(
                f"Looking for editions newer than {latest_processed.edition_id} "
                f"({from_date.strftime('%Y-%m-%d')})"
            )
        else:
            task_manager.add_log("No fully processed editions found - scanning recent")
            from_date = datetime.now() - timedelta(days=30)
        
        editions = run_scraper(repository, config, from_date=from_date)
        task_manager.add_log(f"Found {len(editions)} editions in date range")
        
        # Phase 2: Scrape
        task_manager.add_log("📥 Phase 2/3: Scraping new editions...")
        task_manager._task_name = 'sync: scraping'
        
        unscraped = repository.get_unscraped_editions()
        if latest_processed:
            new_unscraped = []
            for ed in unscraped:
                if ed.year > latest_processed.year:
                    new_unscraped.append(ed)
                elif ed.year == latest_processed.year and ed.stueck > latest_processed.stueck:
                    new_unscraped.append(ed)
            unscraped = new_unscraped
        
        if unscraped:
            task_manager.add_log(f"Found {len(unscraped)} new editions to scrape")
            task_manager.set_progress(0, len(unscraped))
            
            for i, ed in enumerate(unscraped):
                task_manager.add_log(f"Scraping {ed.edition_id}...")
                try:
                    scrape_edition(repository, config, ed.year, ed.stueck)
                    task_manager.add_log(f"  ✓ {ed.edition_id}")
                except Exception as e:
                    task_manager.add_log(f"  ✗ {ed.edition_id}: {str(e)}")
                
                task_manager.set_progress(i + 1)
        else:
            task_manager.add_log("No new editions to scrape")
        
        # Phase 3: Analyze
        task_manager.add_log("🤖 Phase 3/3: Analyzing new editions...")
        task_manager._task_name = 'sync: analyzing'
        
        repository.close()
        repository = Repository(db_path)
        analyzer = BulletinAnalyzer(repository, config)
        
        unanalyzed = repository.get_unanalyzed_editions()
        if latest_processed:
            new_unanalyzed = []
            for ed in unanalyzed:
                if ed.year > latest_processed.year:
                    new_unanalyzed.append(ed)
                elif ed.year == latest_processed.year and ed.stueck > latest_processed.stueck:
                    new_unanalyzed.append(ed)
            unanalyzed = new_unanalyzed
        
        if unanalyzed:
            task_manager.add_log(f"Found {len(unanalyzed)} editions to analyze")
            task_manager.set_progress(0, len(unanalyzed))
            
            for i, ed in enumerate(unanalyzed):
                task_manager.add_log(f"Analyzing {ed.edition_id}...")
                try:
                    result = analyzer.analyze_edition(ed)
                    items = result.get('items', 0)
                    relevant = result.get('relevant', 0)
                    task_manager.add_log(
                        f"  ✓ {ed.edition_id}: {items} items, {relevant} relevant"
                    )
                except Exception as e:
                    task_manager.add_log(f"  ✗ {ed.edition_id}: {str(e)}")
                
                task_manager.set_progress(i + 1)
        else:
            task_manager.add_log("No editions need analysis")
        
        task_manager.add_log("✅ Sync complete!")
        repository.close()
        
    except Exception as e:
        task_manager.add_log(f"ERROR: {str(e)}")
        raise
