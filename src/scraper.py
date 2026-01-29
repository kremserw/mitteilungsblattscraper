"""
Web scraper for JKU Mitteilungsblatt (MTB) system.
Uses Playwright for JavaScript-rendered content.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import time

from playwright.async_api import async_playwright, Browser, Page

from bs4 import BeautifulSoup
import requests

from .storage import Storage, Edition, BulletinItem


class MTBScraper:
    """Scraper for the JKU Mitteilungsblatt Intrexx portal."""
    
    BASE_URL = "https://ix.jku.at"
    # Archive search page URL
    ARCHIVE_URL = "https://ix.jku.at/path/app/?qs_link=17D85C9AC0FFEB214A26C47CAD8895ADD20FB680"
    
    def __init__(self, storage: Storage, config: dict):
        """Initialize scraper with storage and configuration."""
        self.storage = storage
        self.config = config
        self.browser: Optional[Browser] = None
        self.headless = config.get('scraping', {}).get('headless', True)
        self.delay_between_requests = config.get('scraping', {}).get('delay_seconds', 2)
    
    async def _init_browser(self):
        """Initialize Playwright browser."""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=self.headless)
    
    async def _new_page(self) -> Page:
        """Create a new browser page with proper settings."""
        await self._init_browser()
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        return page
    
    async def _wait_and_delay(self):
        """Wait between requests to be respectful to the server."""
        await asyncio.sleep(self.delay_between_requests)
    
    async def discover_editions(self, from_date: datetime = None, to_date: datetime = None) -> List[Dict]:
        """
        Discover all available editions from the MTB archive page.
        
        Args:
            from_date: Optional start date to filter editions
            to_date: Optional end date to filter editions
        
        Returns list of dicts with year, stueck, url, title, and published_date.
        """
        page = await self._new_page()
        editions = []
        all_editions_seen = set()  # Track unique editions to avoid duplicates
        
        try:
            print(f"Navigating to MTB archive page...")
            if from_date:
                print(f"  Filtering from: {from_date.strftime('%Y-%m-%d')}")
            if to_date:
                print(f"  Filtering to: {to_date.strftime('%Y-%m-%d')}")
            
            await page.goto(self.ARCHIVE_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)  # Wait for dynamic content
            
            # Get all editions from the archive table
            # We need to handle pagination - set to max items per page first
            try:
                # Try to set maximum items per page (500)
                pagination_select = page.locator('select[title*="Datensätze"]').first
                if await pagination_select.count() > 0:
                    await pagination_select.select_option('500')
                    await asyncio.sleep(2)
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"Could not change pagination: {e}")
            
            # Now parse editions from all pages
            page_num = 1
            max_pages = 10  # Safety limit
            stop_scanning = False
            
            while page_num <= max_pages and not stop_scanning:
                print(f"Scanning archive page {page_num}...")
                
                # Parse the current page
                content = await page.content()
                page_editions = self._parse_archive_table(content)
                
                if not page_editions:
                    print(f"No editions found on page {page_num}, stopping")
                    break
                
                # Process each edition
                for ed in page_editions:
                    edition_id = ed['edition_id']
                    pub_date = ed.get('published_date')
                    
                    # Skip if we've already seen this edition
                    if edition_id in all_editions_seen:
                        continue
                    all_editions_seen.add(edition_id)
                    
                    # Apply date filter - the archive is sorted newest first
                    # If to_date is set and this edition is after it, skip
                    if to_date and pub_date and pub_date > to_date:
                        continue
                    
                    # If from_date is set and this edition is before it, we've passed our window
                    # so stop scanning (since results are sorted newest first)
                    if from_date and pub_date and pub_date < from_date:
                        print(f"  Reached {edition_id} ({pub_date.strftime('%Y-%m-%d')}) - before start date, stopping")
                        stop_scanning = True
                        break
                    
                    editions.append(ed)
                
                if stop_scanning:
                    break
                
                # Check if there are more pages
                next_button = page.locator('button:has-text("Weiter")').first
                if await next_button.count() == 0 or not await next_button.is_enabled():
                    print("No more pages")
                    break
                
                # Click next page
                await next_button.click()
                await asyncio.sleep(2)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)
                
                page_num += 1
            
            print(f"Found {len(editions)} editions in date range")
            return editions
        
        finally:
            await page.close()
    
    def _parse_archive_table(self, html_content: str) -> List[Dict]:
        """Parse the archive table to extract edition information."""
        soup = BeautifulSoup(html_content, 'html.parser')
        editions = []
        
        # Find all table rows with edition data
        # Each row has: Kurzbezeichnung (short name), Veröffentlicht am (date), Jahr (year)
        rows = soup.select('table tr')
        
        for row in rows:
            cells = row.find_all('td', recursive=False)  # Only direct children
            if len(cells) < 3:
                # Try finding cells within the row more broadly
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
            
            short_name = cells[0].get_text(strip=True)
            date_str = cells[1].get_text(strip=True)
            year_str = cells[2].get_text(strip=True)
            
            # Parse MTB number from short name (e.g., "MTB 3/2026" or "SONDERNUMMER - MTB 63/2025")
            mtb_match = re.search(r'MTB\s+(\d+)/(\d{4})', short_name)
            if not mtb_match:
                continue
            
            stueck = int(mtb_match.group(1))
            year = int(mtb_match.group(2))
            
            # Parse publication date (format: DD.MM.YYYY)
            published_date = None
            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_str)
            if date_match:
                try:
                    published_date = datetime(
                        int(date_match.group(3)),
                        int(date_match.group(2)),
                        int(date_match.group(1))
                    )
                except:
                    pass
            
            # Build the edition URL
            edition_url = f"{self.BASE_URL}/?app=mtb&jahr={year}&stk={stueck}"
            
            # Create edition_id (e.g., "2026-3")
            edition_id = f"{year}-{stueck}"
            
            # Extract clean title - just the MTB designation part
            # Look for patterns like "MTB 3/2026" or "SONDERNUMMER - MTB 63/2025"
            title_match = re.search(r'((?:SONDERNUMMER[^-]*-\s*)?MTB\s+\d+/\d{4})', short_name)
            clean_title = title_match.group(1) if title_match else f"MTB {stueck}/{year}"
            
            editions.append({
                'year': year,
                'stueck': stueck,
                'edition_id': edition_id,
                'title': clean_title,
                'url': edition_url,
                'published_date': published_date,
                'is_special': 'SONDERNUMMER' in short_name
            })
        
        return editions
    
    def scan_and_store(self, from_date: datetime = None, to_date: datetime = None) -> int:
        """Discover editions and store new ones in the database."""
        editions = asyncio.run(self.discover_editions(from_date=from_date, to_date=to_date))
        new_count = 0
        
        for ed in editions:
            edition_id = ed['edition_id']
            
            # Check if already exists
            existing = self.storage.get_edition_by_id(edition_id)
            if existing:
                continue
            
            # Add new edition using storage API (positional: year, stueck; kwargs: title, url, published_date)
            self.storage.add_edition(
                ed['year'],
                ed['stueck'],
                title=ed['title'],
                url=ed['url'],
                published_date=ed.get('published_date')
            )
            new_count += 1
            print(f"  Added: {edition_id} - {ed['title']}")
        
        return new_count
    
    async def scrape_edition(self, edition: Edition) -> List[BulletinItem]:
        """
        Scrape all items from a specific MTB edition.
        
        This navigates to the edition page and extracts each individual
        Punkt (item) with its number, title, category, content, and attachments.
        """
        page = await self._new_page()
        items = []
        
        try:
            print(f"Scraping edition {edition.edition_id}...")
            
            # Navigate to the edition page
            url = edition.url or f"{self.BASE_URL}/?app=mtb&jahr={edition.year}&stk={edition.stueck}"
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)  # Wait for JS content
            
            # Extract items using BeautifulSoup - more reliable for complex nested tables
            html_content = await page.content()
            items_data = self._parse_items_from_html(html_content)
            
            # If JavaScript extraction didn't work well, try a different approach
            if not items_data or len(items_data) == 0:
                print("  Trying alternative extraction method...")
                items_data = await self._extract_items_alternative(page)
            
            # Deduplicate by punkt number
            seen_punkts = set()
            unique_items = []
            for item in items_data:
                if item['punkt'] not in seen_punkts:
                    seen_punkts.add(item['punkt'])
                    unique_items.append(item)
            
            print(f"  Found {len(unique_items)} items")
            
            # Now fetch attachment URLs for each item
            await self._extract_attachments(page, unique_items)
            
            # Convert to BulletinItem objects
            for item_data in unique_items:
                # Get attachment list - already in dict format from _extract_attachments
                attachment_list = item_data.get('attachments', [])
                # Ensure all items are dicts (in case some are still strings)
                attachment_list = [
                    att if isinstance(att, dict) else {'url': att, 'name': att.split('/')[-1] if att else ''}
                    for att in attachment_list
                ]
                
                item = BulletinItem(
                    edition_id=edition.id,
                    punkt=item_data['punkt'],
                    title=item_data.get('title', ''),
                    category=item_data.get('category', ''),
                    content=item_data.get('content', ''),
                    attachments_json=json.dumps(attachment_list)
                )
                items.append(item)
            
            return items
        
        finally:
            await page.close()
    
    def _extract_row_content_with_links(self, row) -> str:
        """
        Extract content from a row, preserving links with their URLs.
        
        For rows containing links, the full text is preserved and links are 
        annotated with their URLs in brackets.
        
        For regular text, just returns the text.
        """
        links = row.find_all('a', href=True)
        
        if links:
            # Row contains links - we need to preserve the full text with link URLs
            # First get the full row text
            full_text = row.get_text(strip=True)
            
            # Collect link annotations
            link_annotations = []
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href', '')
                
                # Skip internal anchors and empty links
                if not text or href == '#':
                    continue
                
                # Make relative URLs absolute
                if href.startswith('/'):
                    href = f"https://ix.jku.at{href}"
                elif not href.startswith('http'):
                    href = f"https://ix.jku.at/{href}"
                
                link_annotations.append(f"[Link: {text}]\n  URL: {href}")
            
            # If we have link annotations, append them after the text
            if link_annotations:
                return full_text + '\n\n' + '\n\n'.join(link_annotations)
            else:
                return full_text
        else:
            # Regular text content
            return row.get_text(strip=True)
    
    def _parse_items_from_html(self, html_content: str) -> List[Dict]:
        """
        Parse bulletin items from HTML using BeautifulSoup.
        
        Structure of each item (in nested tables):
        - Row 1: "Pkt.: XX" + "Kategorie: XXX" in same row
        - Row 2: (empty)
        - Row 3: Title (e.g., "Bevollmächtigung gemäß § 27 Abs. 2 UG")
        - Row 4: (empty)
        - Row 5: Content (the actual text/details)
        - Row 6: (empty)
        - Row 7: Signature ("DER REKTOR: Koch")
        - Row 8: Attachments ("Keine Anhänge" or "Anhänge anzeigen (N)")
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        # Find all cells that contain exactly "Pkt.:" as their text
        all_tds = soup.find_all('td')
        pkt_cells = [td for td in all_tds if td.get_text(strip=True) == 'Pkt.:']
        
        for pkt_cell in pkt_cells:
            try:
                # Get the row containing "Pkt.:"
                pkt_row = pkt_cell.find_parent('tr')
                if not pkt_row:
                    continue
                
                # Extract punkt number and category from sibling cells
                cells = pkt_row.find_all('td')
                punkt = None
                kategorie = None
                
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if text == 'Pkt.:' and i + 1 < len(cells):
                        try:
                            punkt = int(cells[i + 1].get_text(strip=True))
                        except ValueError:
                            continue
                    if text == 'Kategorie:' and i + 1 < len(cells):
                        kategorie = cells[i + 1].get_text(strip=True)
                
                if not punkt:
                    continue
                
                # Find the innermost table containing this item's details
                item_table = pkt_row.find_parent('table')
                if not item_table:
                    continue
                
                # Get all rows in this item's table
                rows = item_table.find_all('tr')
                
                # Find the index of our pkt_row
                pkt_row_idx = None
                for idx, r in enumerate(rows):
                    if r == pkt_row:
                        pkt_row_idx = idx
                        break
                
                if pkt_row_idx is None:
                    continue
                
                # Extract title and content from subsequent rows
                title = ''
                content = ''
                content_links = []  # Store links found in content
                has_attachments = False
                
                # Skip the Pkt row and iterate through subsequent rows
                for row in rows[pkt_row_idx + 1:]:
                    row_text = row.get_text(strip=True)
                    
                    # Skip empty rows
                    if not row_text or len(row_text) < 3:
                        continue
                    
                    # Skip if this is another Pkt row (nested tables issue)
                    if row_text.startswith('Pkt.:') or 'Pkt.:' in row_text[:20]:
                        continue
                    
                    # Check for end-of-item markers
                    if any(marker in row_text for marker in [
                        'DER REKTOR:', 'FÜR DAS REKTORAT:', 'DER VORSITZENDE',
                        'Permalink kopieren'
                    ]):
                        break  # Stop parsing this item
                    
                    # Check for attachment info
                    if 'Anhänge anzeigen' in row_text:
                        has_attachments = True
                        break
                    if 'Keine Anhänge' in row_text:
                        break
                    
                    # First non-empty, non-metadata row is the title
                    if not title:
                        title = row_text[:500]
                        continue
                    
                    # Check if this row contains links
                    links_in_row = row.find_all('a', href=True)
                    
                    if links_in_row:
                        # Extract content with links preserved
                        row_content = self._extract_row_content_with_links(row)
                        if row_content:
                            if content:
                                content += '\n\n' + row_content
                            else:
                                content = row_content
                    else:
                        # Regular text content
                        if not content:
                            content = row_text[:5000]
                        elif len(content) < 4500:
                            content += '\n' + row_text[:500]
                
                items.append({
                    'punkt': punkt,
                    'category': kategorie or '',
                    'title': title,
                    'content': content,
                    'attachments': [],
                    'has_attachments': has_attachments
                })
                
            except Exception as e:
                print(f"    Error parsing item: {e}")
                continue
        
        return items
    
    async def _extract_items_alternative(self, page: Page) -> List[Dict]:
        """Alternative method to extract items using BeautifulSoup."""
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        items = []
        
        # Find all text containing "Pkt.:" 
        all_text = soup.get_text()
        
        # Find patterns like "Pkt.: 45" and "Kategorie: Satzung"
        punkt_pattern = re.compile(r'Pkt\.:\s*(\d+)')
        kategorie_pattern = re.compile(r'Kategorie:\s*([^\n]+)')
        
        punkt_matches = list(punkt_pattern.finditer(all_text))
        
        for i, match in enumerate(punkt_matches):
            punkt = int(match.group(1))
            
            # Find the section of text for this item
            start_pos = match.start()
            end_pos = punkt_matches[i + 1].start() if i + 1 < len(punkt_matches) else len(all_text)
            section = all_text[start_pos:end_pos]
            
            # Extract category
            kat_match = kategorie_pattern.search(section)
            category = kat_match.group(1).strip() if kat_match else ''
            
            # Extract title and content from the section
            lines = [l.strip() for l in section.split('\n') if l.strip()]
            
            title = ''
            content = ''
            
            # Skip metadata lines, find title
            skip_patterns = ['Pkt.:', 'Kategorie:', 'Permalink', 'Anhänge', 'DER REKTOR', 'FÜR DAS REKTORAT']
            
            for line in lines:
                if any(p in line for p in skip_patterns):
                    continue
                if not title and len(line) > 5:
                    title = line[:500]
                elif title and not content and len(line) > 10:
                    content = line[:5000]
                    break
            
            items.append({
                'punkt': punkt,
                'category': category,
                'title': title,
                'content': content,
                'attachments': []
            })
        
        return items
    
    async def _extract_attachments(self, page: Page, items: List[Dict]):
        """
        Extract attachment URLs by clicking each "Anhänge anzeigen" button.
        
        Each button opens a dialog containing attachment links.
        We need to:
        1. Click the button
        2. Extract attachment link from the dialog
        3. Close the dialog
        4. Associate attachment with the correct item
        """
        try:
            # Create a lookup dict for items by punkt number
            items_by_punkt = {item['punkt']: item for item in items}
            
            # Get the initial page content to find attachment buttons and their context
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all attachment buttons and their parent context
            # The "Anhänge anzeigen" buttons are actually links with role="button" and title="Anhänge anzeigen"
            attachment_buttons = await page.locator('[title="Anhänge anzeigen"]').all()
            
            for i, button in enumerate(attachment_buttons):
                try:
                    # Get the text context around this button to determine which Punkt it belongs to
                    # We'll use Playwright to evaluate the Punkt from the button's ancestor table
                    punkt_number = await page.evaluate('''(button) => {
                        // Find the closest table container that has "Pkt.:" text
                        let element = button;
                        for (let j = 0; j < 15; j++) {
                            element = element.parentElement;
                            if (!element) break;
                            
                            // Look for a cell containing "Pkt.:" in this container
                            const pktCells = element.querySelectorAll('td');
                            for (let cell of pktCells) {
                                if (cell.textContent.trim() === 'Pkt.:') {
                                    // The next sibling cell should contain the number
                                    const nextCell = cell.nextElementSibling;
                                    if (nextCell) {
                                        const num = parseInt(nextCell.textContent.trim());
                                        if (!isNaN(num)) return num;
                                    }
                                }
                            }
                        }
                        return null;
                    }''', await button.element_handle())
                    
                    if punkt_number is None:
                        continue
                    
                    # Click the button to open the attachment dialog
                    await button.click()
                    await asyncio.sleep(1.5)
                    
                    # Look for the attachment link in the dialog
                    # The dialog contains links with downloadIxServlet in the URL
                    dialog_content = await page.content()
                    dialog_soup = BeautifulSoup(dialog_content, 'html.parser')
                    
                    # Find download links in the dialog
                    download_links = dialog_soup.find_all('a', href=re.compile(r'downloadIxServlet'))
                    
                    for link in download_links:
                        href = link.get('href', '')
                        link_text = link.get_text(strip=True)
                        
                        # Decode HTML entities in the URL (e.g., &amp; -> &)
                        import html
                        href = html.unescape(href)
                        
                        # Skip empty or icon-only links
                        if not href:
                            continue
                        # Skip the "Diese Datei anzeigen" image link (it points to same file)
                        if not link_text or 'Diese Datei anzeigen' in link_text:
                            continue
                        # Skip if the link text is too short (likely an icon/image link)
                        if len(link_text) < 5:
                            continue
                        
                        # Make URL absolute
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # Add to the correct item as a dict with name and URL
                        if punkt_number in items_by_punkt:
                            item = items_by_punkt[punkt_number]
                            attachment_dict = {'name': link_text, 'url': full_url}
                            # Check if not already added
                            existing_urls = [a.get('url') for a in item.get('attachments', []) if isinstance(a, dict)]
                            if full_url not in existing_urls:
                                item.setdefault('attachments', []).append(attachment_dict)
                    
                    # Close the dialog by clicking the "Schließen" button or pressing Escape
                    try:
                        close_button = page.locator('button:has-text("Schließen")')
                        if await close_button.count() > 0:
                            await close_button.click()
                            await asyncio.sleep(0.5)
                        else:
                            await page.keyboard.press('Escape')
                            await asyncio.sleep(0.5)
                    except:
                        await page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"    Warning: Could not extract attachment for button {i}: {e}")
                    # Try to close any open dialog
                    try:
                        await page.keyboard.press('Escape')
                        await asyncio.sleep(0.3)
                    except:
                        pass
                    
        except Exception as e:
            print(f"  Warning: Could not extract attachments: {e}")
    
    def scrape_and_store(self, edition: Edition) -> int:
        """Scrape an edition and store its items."""
        items = asyncio.run(self.scrape_edition(edition))
        
        # Add items directly to session (they're already BulletinItem objects)
        for item in items:
            self.storage.session.add(item)
        
        # Update edition as scraped
        edition.scraped_at = datetime.now()
        self.storage.session.commit()
        
        return len(items)
    
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None


def get_scraper(storage: Storage, config: dict) -> MTBScraper:
    """Factory function to create a scraper instance."""
    return MTBScraper(storage, config)


def run_scraper(storage: Storage, config: dict, from_date: datetime = None, to_date: datetime = None) -> List[Dict]:
    """
    Run the scraper to discover and store new editions.
    
    This is a convenience function that wraps the MTBScraper class.
    """
    scraper = MTBScraper(storage, config)
    
    # Discover editions
    editions = asyncio.run(scraper.discover_editions(from_date=from_date, to_date=to_date))
    
    # Store new editions
    new_count = 0
    for ed in editions:
        edition_id = ed['edition_id']
        
        # Check if already exists
        existing = storage.get_edition_by_id(edition_id)
        if existing:
            continue
        
        # Add new edition using storage API (positional: year, stueck; kwargs: title, url, published_date)
        storage.add_edition(
            ed['year'],
            ed['stueck'],
            title=ed['title'],
            url=ed['url'],
            published_date=ed.get('published_date')
        )
        new_count += 1
    
    return editions


def scrape_edition(storage: Storage, config: dict, year: int, stueck: int) -> Tuple[Edition, List[BulletinItem]]:
    """
    Scrape a specific edition and store its items.
    
    Args:
        storage: Storage instance
        config: Configuration dict
        year: Edition year (e.g., 2026)
        stueck: Edition number (e.g., 3 for "3. Stück")
    
    Returns tuple of (edition, items_list).
    """
    # Look up the edition
    edition_id = f"{year}-{stueck}"
    edition = storage.get_edition_by_id(edition_id)
    
    if not edition:
        raise ValueError(f"Edition {edition_id} not found in database")
    
    scraper = MTBScraper(storage, config)
    num_items = scraper.scrape_and_store(edition)
    
    # Get the items that were just scraped
    items = storage.get_items_for_edition(edition)
    
    return edition, items
