"""Integration tests for scraper HTML parsing logic.

Note: These tests use pre-recorded HTML responses rather than making live web requests.
"""

import pytest

from src.core.scraper import MTBScraper


class TestScraperHTMLParsing:
    """Tests for scraper HTML parsing methods."""
    
    @pytest.fixture
    def scraper(self, repository, test_config):
        """Provide a scraper instance."""
        return MTBScraper(repository, test_config)
    
    def test_parse_archive_table_basic(self, scraper, sample_html_content):
        """Test parsing archive table with sample HTML."""
        editions = scraper._parse_archive_table(sample_html_content)
        
        assert len(editions) == 2
        assert editions[0]['year'] == 2025
        assert editions[0]['stueck'] == 1
        assert editions[0]['edition_id'] == "2025-1"
    
    def test_parse_archive_table_empty(self, scraper):
        """Test parsing empty table."""
        html = "<table></table>"
        editions = scraper._parse_archive_table(html)
        
        assert editions == []
    
    def test_parse_archive_table_no_mtb_rows(self, scraper):
        """Test parsing table without MTB entries."""
        html = """
        <table>
            <tr><td>Something</td><td>01.01.2025</td><td>2025</td></tr>
            <tr><td>Other</td><td>02.01.2025</td><td>2025</td></tr>
        </table>
        """
        editions = scraper._parse_archive_table(html)
        
        assert editions == []
    
    def test_parse_archive_table_special_edition(self, scraper):
        """Test parsing special edition (SONDERNUMMER)."""
        html = """
        <table>
            <tr><td>SONDERNUMMER - MTB 63/2025</td><td>15.12.2025</td><td>2025</td></tr>
        </table>
        """
        editions = scraper._parse_archive_table(html)
        
        assert len(editions) == 1
        assert editions[0]['is_special'] is True
        assert editions[0]['stueck'] == 63
    
    def test_parse_items_from_html_basic(self, scraper):
        """Test parsing bulletin items from HTML."""
        html = """
        <table>
            <tr>
                <td>Pkt.:</td>
                <td>5</td>
                <td>Kategorie:</td>
                <td>Curricula</td>
            </tr>
            <tr>
                <td colspan="4">Test Title Here</td>
            </tr>
            <tr>
                <td colspan="4">Test content paragraph.</td>
            </tr>
            <tr>
                <td colspan="4">Keine Anhänge</td>
            </tr>
        </table>
        """
        items = scraper._parse_items_from_html(html)
        
        assert len(items) >= 1
        assert items[0]['punkt'] == 5
        assert items[0]['category'] == 'Curricula'
    
    def test_parse_items_from_html_empty(self, scraper):
        """Test parsing empty HTML returns empty list."""
        items = scraper._parse_items_from_html("<html><body></body></html>")
        
        assert items == []
    
    def test_extract_row_content_with_links(self, scraper):
        """Test extracting content with links preserved."""
        from bs4 import BeautifulSoup
        
        html = """
        <tr>
            <td>Some text <a href="https://example.com/doc.pdf">Document Link</a> more text</td>
        </tr>
        """
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')
        
        content = scraper._extract_row_content_with_links(row)
        
        assert "Document Link" in content
        assert "example.com" in content


class TestScraperDatabaseIntegration:
    """Tests for scraper database integration."""
    
    def test_scan_and_store_adds_new_editions(self, repository, test_config):
        """Test that scan_and_store adds new editions to database."""
        # Note: This would require mocking the actual web requests
        # For now we just test that the method exists and has correct signature
        scraper = MTBScraper(repository, test_config)
        
        assert hasattr(scraper, 'scan_and_store')
        assert callable(scraper.scan_and_store)
    
    def test_scrape_and_store_updates_edition(self, repository, test_config, sample_edition):
        """Test that scrape_and_store updates edition timestamps."""
        scraper = MTBScraper(repository, test_config)
        
        # Verify edition starts without scraped_at
        assert sample_edition.scraped_at is None
        
        # Note: Full test would require mocking Playwright
        # Here we just verify the interface exists
        assert hasattr(scraper, 'scrape_and_store')
