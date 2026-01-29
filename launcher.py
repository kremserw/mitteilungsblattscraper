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
import subprocess
import shutil

def get_app_dir():
    """Get the directory where the app/executable is located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def find_firefox():
    """
    Find Firefox browser executable.
    Returns the path to Firefox if found, None otherwise.
    """
    firefox_candidates = []
    
    if sys.platform == 'win32':
        firefox_candidates = [
            os.path.expandvars(r'%PROGRAMFILES%\Mozilla Firefox\firefox.exe'),
            os.path.expandvars(r'%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe'),
        ]
    elif sys.platform == 'darwin':
        firefox_candidates = [
            '/Applications/Firefox.app/Contents/MacOS/firefox',
        ]
    else:
        # Linux - check common executable names
        for name in ['firefox', 'firefox-esr']:
            path = shutil.which(name)
            if path:
                return path
        
        firefox_candidates = [
            '/usr/bin/firefox',
            '/usr/bin/firefox-esr',
            '/snap/bin/firefox',
        ]
    
    for path in firefox_candidates:
        if os.path.exists(path):
            return path
    
    return None


def find_chrome():
    """
    Find Chrome/Chromium browser executable.
    Returns the path to Chrome if found, None otherwise.
    """
    # List of possible Chrome executable names/paths
    chrome_candidates = []
    
    if sys.platform == 'win32':
        # Windows paths
        chrome_candidates = [
            os.path.expandvars(r'%PROGRAMFILES%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        ]
    elif sys.platform == 'darwin':
        # macOS paths
        chrome_candidates = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
        ]
    else:
        # Linux - check common executable names
        for name in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']:
            path = shutil.which(name)
            if path:
                return path
        
        # Also check common Linux paths
        chrome_candidates = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
        ]
    
    # Check each candidate path
    for path in chrome_candidates:
        if os.path.exists(path):
            return path
    
    return None


def open_browser(url: str):
    """
    Open URL in a browser. Prefers Firefox (better PDF handling), falls back to Chrome, then default.
    Returns the browser name that was used.
    """
    # Try Firefox first (works better with PDF downloads)
    firefox_path = find_firefox()
    if firefox_path:
        try:
            subprocess.Popen([firefox_path, url],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            return 'Firefox'
        except Exception as e:
            print(f"⚠️  Could not launch Firefox: {e}")
    
    # Fall back to Chrome
    chrome_path = find_chrome()
    if chrome_path:
        try:
            subprocess.Popen([chrome_path, '--new-window', url], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return 'Chrome'
        except Exception as e:
            print(f"⚠️  Could not launch Chrome: {e}")
    
    # Fallback to default browser
    print("⚠️  Firefox/Chrome not found, using default browser")
    webbrowser.open(url)
    return 'default'


# Keep old function for compatibility
def open_chrome(url: str):
    """Deprecated: Use open_browser() instead."""
    return open_browser(url)

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
    print("│ JKU Mitteilungsblatt Analyzer v1.1                      │")
    print("│ AI-powered relevance filtering for university bulletins │")
    print("╰─────────────────────────────────────────────────────────╯")
    print()
    print(f"📁 App directory: {app_dir}")
    print(f"🌐 Starting server at http://localhost:{port}")
    print()
    
    # Check for browsers (prefer Firefox for better PDF handling)
    firefox_path = find_firefox()
    chrome_path = find_chrome()
    if firefox_path:
        print(f"🌐 Found Firefox: {firefox_path} (preferred for PDF downloads)")
    elif chrome_path:
        print(f"🌐 Found Chrome: {chrome_path}")
    else:
        print("⚠️  No Firefox/Chrome found - will use default browser")
    
    print()
    print("Opening browser with splash screen...")
    print()
    print("Close the browser tab to stop the server and exit.")
    print("Or press Ctrl+C in this terminal.")
    print()
    
    # Open browser after a short delay (give server time to start)
    # Open to splash screen which will redirect when ready
    def open_browser():
        time.sleep(1.5)
        open_chrome(f'http://localhost:{port}/splash')
    
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
