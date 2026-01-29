# JKU Mitteilungsblatt Analyzer v1.1

A local Python application that scrapes JKU's official bulletins (Mitteilungsblätter), analyzes them using Claude AI, and identifies content relevant to your specific role.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)

## ✨ Features

- 📰 **Automatic scraping** of JKU Mitteilungsblätter from ix.jku.at
- 📎 **Attachment handling** - Extracts and links to PDF attachments with reliable download proxy
- 🔗 **Link extraction** - Captures all URLs from bulletin content
- 🤖 **AI-powered relevance analysis** using Claude Haiku 4.5 (fast and cost-effective)
- 💾 **Persistent storage** - SQLite database with automatic migrations
- 🎯 **Role-based filtering** - Describe your role to get personalized relevance scoring
- 🌐 **Web Dashboard** - Modern dark-themed UI with animated splash screen
- 📅 **Date range filtering** - Scan and scrape editions within specific date ranges
- 📊 **Sortable tables** - Click column headers to sort by any field
- ✅ **Read tracking** - Items you've viewed are greyed out
- 📝 **AI-generated titles** - Short 5-7 word summaries for each item
- 📄 **On-demand PDF analysis** - Deep AI analysis of PDF attachments

## 🆕 What's New in v1.1

- **Splash Screen** - Animated loading screen while the server starts
- **Unified Sync** - One-click "Sync New Editions" button (only processes editions newer than your last fully-processed one)
- **Shutdown Button** - Gracefully stop the server from the dashboard
- **Read Tracking** - Items you've viewed are visually marked as read
- **AI Short Titles** - Each item gets a concise AI-generated title
- **PDF Download Proxy** - Reliable PDF downloads through server-side proxy
- **PDF AI Analysis** - Click to get deep AI analysis of PDF attachments
- **Sortable Tables** - Click headers to sort (works correctly with edition IDs like 2026-10)
- **Dark Mode Improvements** - White calendar icons, better contrast
- **Firefox Preference** - App prefers Firefox for better PDF download handling
- **Database Migrations** - Automatic schema updates for existing databases
- **Performance** - SQLite optimizations (WAL mode, increased cache)

## 🖥️ Screenshots

The web interface provides:
- **Dashboard** - Overview stats, one-click sync, recent relevant items, role description editor
- **Editions** - List all editions with scan/scrape/reset controls, date filtering
- **Relevant Items** - Filtered view with sortable columns, read tracking
- **Item Detail** - Full content, AI summary, key points, PDF analysis button, links, attachments

## 📋 Prerequisites

- Python 3.9+
- Anthropic API key (for Claude AI analysis)
- Chrome or Firefox browser (Firefox preferred for PDF downloads)
- Playwright browsers (auto-installed on first run)

## 🚀 Quick Start (One-Click Launch)

The easiest way to run the application:

### On Windows (with WSL)
1. Copy the entire folder anywhere you like
2. Double-click `Start-MTB-Analyzer.bat`
3. First run installs everything automatically (~3-5 min)
4. Browser opens to http://localhost:8080

### On Linux/Mac
1. Copy the folder anywhere
2. Run `./start-mtb-analyzer.sh`
3. First run installs everything automatically
4. Browser opens automatically

**That's it!** The launcher handles virtual environment setup, dependency installation, and Playwright browser installation automatically on first run.

## 🔧 Manual Installation

If you prefer manual setup:

```bash
# Clone the repository
git clone https://github.com/kremserw/mitteilungsblattscraper.git
cd mitteilungsblattscraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for dynamic content scraping)
playwright install chromium
```

## ⚙️ Configuration

1. Copy the example config file:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml`:
   - Add your Anthropic API key
   - Describe your role and interests in detail
   - Adjust relevance threshold (default: 60%)

Example role description:
```yaml
role_description: |
  I am a professor at the Business School with the following responsibilities:
  - Division Speaker for Management & Marketing
  - Member of the University Senate
  - Research focus on strategic management and innovation
  
  I'm interested in:
  - Personnel changes in my division
  - New policies affecting research or teaching
  - Grant opportunities and funding announcements
  - Governance decisions from the Rectorate
```

## 📖 Usage

### Web Interface (Recommended)

```bash
python launcher.py
# or
python main.py serve
```

Open http://localhost:8080 in your browser. From there you can:
- **Sync New Editions** - One click to scan, scrape, and analyze new content
- Browse editions with date range filtering
- View AI-analyzed items with relevance scores
- Click items to see full details, AI summary, and key points
- Analyze PDF attachments on-demand with AI
- Sort tables by clicking column headers

### Command Line

```bash
# Scan for new editions
python main.py scan

# Scrape content from all unscraped editions
python main.py scrape

# Analyze all unanalyzed editions
python main.py analyze

# Analyze a specific edition
python main.py analyze --edition 2026-1

# List all editions and their status
python main.py list

# Show relevant items (above threshold)
python main.py relevant

# Show details for specific edition
python main.py show 2026-1
```

## 🔧 How It Works

1. **Discovery**: Navigates the JKU archive to find all published editions
2. **Scraping**: Uses Playwright to render JavaScript-heavy pages and extract:
   - Individual bulletin items (Punkte)
   - Categories and titles
   - Full text content
   - Links within content
   - Attachment URLs
3. **Analysis**: Sends each item to Claude AI with your role description
4. **Scoring**: Each item receives:
   - Relevance score (0-100%)
   - Short AI-generated title (5-7 words)
   - Summary of why it matters to you
   - Key points extracted
   - Detailed reasoning
5. **Storage**: All data stored in local SQLite database with automatic migrations

## 💰 Cost Estimate

Using Claude Haiku 4.5 (recommended for cost efficiency):
- $1 per million input tokens
- $5 per million output tokens

A typical edition with 20-30 items costs approximately **$0.05-0.15** to analyze.

## 📁 Project Structure

```
jku-mtb-analyzer/
├── Start-MTB-Analyzer.bat  # 🖱️ Windows one-click launcher
├── start-mtb-analyzer.sh   # 🖱️ Linux/Mac one-click launcher
├── launcher.py             # Auto-opens browser with splash screen
├── main.py                 # CLI entry point
├── config.yaml             # Your configuration (git-ignored)
├── config.example.yaml     # Example configuration template
├── requirements.txt        # Python dependencies
├── jku-mtb-analyzer.spec   # PyInstaller build specification
├── src/
│   ├── scraper.py         # Web scraping with Playwright
│   ├── parser.py          # Content parsing and PDF extraction
│   ├── analyzer.py        # Claude API integration
│   ├── storage.py         # SQLite database with migrations
│   └── ui.py              # Flask web interface
├── data/
│   └── mtb.db             # SQLite database (git-ignored)
└── venv/                   # Virtual environment (auto-created)
```

### Portable Deployment

To deploy anywhere, copy these files:
- ✅ `Start-MTB-Analyzer.bat` and `start-mtb-analyzer.sh` (launchers)
- ✅ `launcher.py`, `main.py`, `requirements.txt`
- ✅ `config.yaml` (with your API key)
- ✅ `config.example.yaml`
- ✅ `src/` folder (all source code)
- ✅ `data/` folder (optional - keeps your existing data)
- ❌ `venv/` folder (auto-created on first run)

## 🔒 Privacy & Security

- All data is stored locally on your machine
- Your API key is stored only in your local config file
- No data is sent anywhere except to Anthropic's API for analysis
- The config.yaml file is git-ignored to protect your API key

## 🐛 Troubleshooting

**Scraping fails with timeout errors**
- The JKU portal can be slow; try again later
- Ensure you have a stable internet connection

**Playwright browser issues**
- Run `playwright install chromium` to reinstall the browser
- On Linux, you may need additional dependencies: `playwright install-deps`

**API errors**
- Verify your Anthropic API key is correct
- Check your API quota/credits
- Ensure you're using the correct model name (claude-haiku-4-5)

**PDF downloads show wrong filename (Chrome on WSL2)**
- The app now uses a proxy for PDF downloads which should fix this
- If issues persist, try using Firefox instead of Chrome

**Database migration errors**
- The app automatically migrates existing databases
- If issues occur, backup `data/mtb.db` and delete it to start fresh

## 📄 License

MIT License - Use freely for personal and educational purposes.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for robust web scraping
- Powered by [Anthropic Claude](https://anthropic.com/) for AI analysis
- Uses [Flask](https://flask.palletsprojects.com/) for the web interface
