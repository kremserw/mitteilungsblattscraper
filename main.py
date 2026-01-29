#!/usr/bin/env python3
"""
JKU Mitteilungsblatt Analyzer - Main Entry Point

Usage:
    python main.py scan          # Discover and add new editions
    python main.py scrape        # Scrape all unscraped editions
    python main.py analyze       # Analyze all unanalyzed editions
    python main.py list          # List all editions
    python main.py relevant      # Show relevant items
    python main.py serve         # Start web interface
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import CLI from the cli module
from src.cli import cli

if __name__ == '__main__':
    cli()
