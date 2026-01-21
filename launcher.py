#!/usr/bin/env python3
"""
JKU MTB Analyzer Launcher
Standalone executable entry point that auto-opens the browser.
"""

import os
import sys
import time
import webbrowser
import threading
import signal

def get_app_dir():
    """Get the directory where the app/executable is located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def main():
    # Set working directory to where the executable is
    app_dir = get_app_dir()
    os.chdir(app_dir)
    
    # Add app directory to path for imports
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    
    # Import after setting up paths
    import yaml
    from src.storage import get_storage
    from src.ui import run_web_server
    
    # Configuration
    port = 8080
    config_path = os.path.join(app_dir, 'config.yaml')
    
    # Check for config file
    if not os.path.exists(config_path):
        example_config = os.path.join(app_dir, 'config.example.yaml')
        if os.path.exists(example_config):
            print(f"⚠️  No config.yaml found. Please copy config.example.yaml to config.yaml")
            print(f"   and add your Anthropic API key.")
            print(f"\n   Location: {app_dir}")
            input("\nPress Enter to exit...")
            sys.exit(1)
        else:
            print("❌ No configuration file found!")
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Store config path for saving changes
    config['_config_path'] = config_path
    
    # Initialize storage
    db_path = config.get('storage', {}).get('database', 'data/mtb.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app_dir, db_path)
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    storage = get_storage(db_path)
    
    # Print startup banner
    print("╭─────────────────────────────────────────────────────────╮")
    print("│ JKU Mitteilungsblatt Analyzer v1.0                      │")
    print("│ AI-powered relevance filtering for university bulletins │")
    print("╰─────────────────────────────────────────────────────────╯")
    print()
    print(f"📁 App directory: {app_dir}")
    print(f"🌐 Starting server at http://localhost:{port}")
    print()
    print("Opening browser...")
    print()
    print("Press Ctrl+C to stop the server and exit.")
    print()
    
    # Open browser after a short delay (give server time to start)
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n👋 Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the web server (blocks until stopped)
    try:
        run_web_server(storage, config, port=port)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        sys.exit(0)

if __name__ == '__main__':
    main()
