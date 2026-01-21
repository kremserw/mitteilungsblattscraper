#!/bin/bash
#
# JKU MTB Analyzer - One-Click Launcher
# Just double-click this file to start the application!
#

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "╭─────────────────────────────────────────────────────────╮"
echo "│ JKU Mitteilungsblatt Analyzer v1.0                      │"
echo "│ AI-powered relevance filtering for university bulletins │"
echo "╰─────────────────────────────────────────────────────────╯"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Setting up virtual environment (first run only)..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    echo "✅ Dependencies installed!"
else
    source venv/bin/activate
fi

# Check if Playwright browsers are installed
if ! playwright --version > /dev/null 2>&1 || [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "🌐 Installing Playwright browser (first run only)..."
    playwright install chromium
    echo "✅ Browser installed!"
fi

# Check for config file
if [ ! -f "config.yaml" ]; then
    echo ""
    echo "⚠️  No config.yaml found!"
    echo "   Please copy config.example.yaml to config.yaml"
    echo "   and add your Anthropic API key."
    echo ""
    echo "   Run: cp config.example.yaml config.yaml"
    echo "   Then edit config.yaml with your API key."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo "🚀 Starting application..."
echo "   Your browser will open automatically."
echo ""
echo "   Press Ctrl+C to stop the server."
echo ""

# Start the launcher (which opens the browser automatically)
python launcher.py
