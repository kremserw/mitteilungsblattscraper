#!/bin/bash
#
# JKU MTB Analyzer - One-Click Launcher
# Just double-click this file (or run the .bat file on Windows) to start!
#
# This script can be run from anywhere - just copy the entire folder.
#

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "╭─────────────────────────────────────────────────────────╮"
echo "│ JKU Mitteilungsblatt Analyzer v1.0                      │"
echo "│ AI-powered relevance filtering for university bulletins │"
echo "╰─────────────────────────────────────────────────────────╯"
echo ""
echo "📁 Running from: $SCRIPT_DIR"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Setting up virtual environment (first run only)..."
    echo "   This may take a few minutes..."
    echo ""
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment!"
        echo "   Make sure Python 3.9+ is installed."
        read -p "Press Enter to exit..."
        exit 1
    fi
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies!"
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "✅ Dependencies installed!"
    echo ""
else
    source venv/bin/activate
fi

# Check if Playwright browsers are installed
PLAYWRIGHT_CHECK=$(venv/bin/python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.executable_path; p.stop()" 2>&1)
if echo "$PLAYWRIGHT_CHECK" | grep -q "Executable doesn't exist"; then
    echo "🌐 Installing Playwright browser (first run only)..."
    echo "   This may take a few minutes..."
    echo ""
    venv/bin/playwright install chromium
    if [ $? -ne 0 ]; then
        echo "⚠️  Browser installation may have issues."
        echo "   Scraping might not work, but other features will."
    else
        echo "✅ Browser installed!"
    fi
    echo ""
fi

# Check for config file
if [ ! -f "config.yaml" ]; then
    echo ""
    echo "⚠️  No config.yaml found!"
    echo ""
    echo "   Please create config.yaml with your settings:"
    echo "   1. Copy config.example.yaml to config.yaml"
    echo "   2. Edit config.yaml and add your Anthropic API key"
    echo ""
    
    # Offer to copy the example file
    if [ -f "config.example.yaml" ]; then
        read -p "   Copy config.example.yaml to config.yaml now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp config.example.yaml config.yaml
            echo "   ✅ config.yaml created!"
            echo "   ⚠️  Please edit it to add your Anthropic API key before running again."
            echo ""
        fi
    fi
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo "🚀 Starting application..."
echo "   Your browser will open automatically to http://localhost:8080"
echo ""
echo "   Press Ctrl+C to stop the server."
echo ""

# Start the launcher (which opens the browser automatically)
venv/bin/python launcher.py
