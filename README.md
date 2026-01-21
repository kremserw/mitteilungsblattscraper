# JKU Mitteilungsblatt Analyzer v1.0

A local Python application that scrapes JKU's official bulletins (Mitteilungsblätter), analyzes them using Claude AI, and identifies content relevant to your specific role.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)

## ✨ Features

- 📰 **Automatic scraping** of JKU Mitteilungsblätter from ix.jku.at
- 📎 **Attachment handling** - Extracts and links to PDF attachments
- 🔗 **Link extraction** - Captures all URLs from bulletin content
- 🤖 **AI-powered relevance analysis** using Claude (configurable model)
- 💾 **Persistent storage** - SQLite database tracks all editions and items
- 🎯 **Role-based filtering** - Describe your role to get personalized relevance scoring
- 🌐 **Web Dashboard** - Modern UI to browse, scan, scrape, and analyze bulletins
- 📅 **Date range filtering** - Scan and scrape editions within specific date ranges

## 🖥️ Screenshots

The web interface provides:
- **Dashboard** - Overview stats, recent relevant items, and role description editor
- **Editions** - List all editions with scan/scrape/reset controls
- **Relevant Items** - Filtered view of items above your relevance threshold
- **Item Detail** - Full content, AI summary, key points, links, attachments, and reasoning

## 📋 Prerequisites

- Python 3.9+
- Anthropic API key (for Claude AI analysis)
- Chrome/Chromium browser (for Playwright web scraping)

## 🚀 Installation

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
python main.py serve
```

Open http://localhost:8080 in your browser. From there you can:
- Scan for new editions (with date range filtering)
- Scrape edition content (including attachments and links)
- Run AI analysis to score relevance
- Browse and filter relevant items
- Click items to see full details, AI summary, and reasoning

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
   - Summary of why it matters to you
   - Key points extracted
   - Detailed reasoning
5. **Storage**: All data stored in local SQLite database

## 💰 Cost Estimate

Using Claude 3.5 Haiku (recommended for cost efficiency):
- ~$0.80 per million input tokens
- ~$4.00 per million output tokens

A typical edition with 20-30 items costs approximately **$0.05-0.15** to analyze.

## 📁 Project Structure

```
mitteilungsblattscraper/
├── main.py              # CLI entry point
├── config.yaml          # Your configuration (git-ignored)
├── config.example.yaml  # Example configuration
├── requirements.txt     # Python dependencies
├── src/
│   ├── scraper.py      # Web scraping with Playwright
│   ├── parser.py       # Content parsing utilities
│   ├── analyzer.py     # Claude API integration
│   ├── storage.py      # SQLite database operations
│   └── ui.py           # Flask web interface
└── data/
    └── mtb.db          # SQLite database (git-ignored)
```

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

## 📄 License

MIT License - Use freely for personal and educational purposes.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for robust web scraping
- Powered by [Anthropic Claude](https://anthropic.com/) for AI analysis
- Uses [Flask](https://flask.palletsprojects.com/) for the web interface
