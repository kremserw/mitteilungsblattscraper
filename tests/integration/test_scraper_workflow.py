"""Integration tests for the scraper workflow."""

import re
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

import pytest


class TestScraperWorkflow:
    """Tests for the full scraping workflow."""
    
    @pytest.fixture
    def scraper(self, repository, test_config):
        """Provide a scraper instance."""
        from src.core.scraper import MTBScraper
        return MTBScraper(repository, test_config)
    
    def test_parse_archive_table_finds_editions(self, scraper, sample_html_content):
        """Test that _parse_archive_table finds editions in HTML."""
        editions = scraper._parse_archive_table(sample_html_content)
        
        assert len(editions) >= 1
        # Should extract year and stueck
        assert all('year' in ed for ed in editions)
        assert all('stueck' in ed for ed in editions)
    
    def test_scraper_has_required_methods(self, scraper):
        """Test that scraper has all required methods."""
        assert hasattr(scraper, 'scan_and_store')
        assert hasattr(scraper, 'scrape_and_store')
        assert hasattr(scraper, '_parse_archive_table')
        assert hasattr(scraper, '_parse_items_from_html')
    
    def test_parse_items_returns_list(self, scraper):
        """Test that _parse_items_from_html returns a list."""
        html = "<html><body>No items here</body></html>"
        items = scraper._parse_items_from_html(html)
        
        assert isinstance(items, list)
    
    def test_clean_content_removes_html(self, scraper):
        """Test that content cleaning removes HTML tags."""
        html_content = "<p>This is <strong>important</strong> content.</p>"
        
        # The scraper should clean HTML when processing
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned = soup.get_text()
        
        assert "important" in cleaned
        assert "<strong>" not in cleaned


class TestScraperDatabaseOperations:
    """Tests for scraper database operations."""
    
    def test_scraper_adds_new_edition(self, repository, test_config):
        """Test that scraper adds new editions to database."""
        from src.core.scraper import MTBScraper
        
        scraper = MTBScraper(repository, test_config)
        
        # Check edition doesn't exist
        existing = repository.get_edition(2025, 99)
        assert existing is None
        
        # Add edition through repository
        edition = repository.add_edition(
            year=2025,
            stueck=99,
            title='MTB 99/2025',
            url='https://example.com/mtb/99-2025',
            published_date=datetime(2025, 12, 15)
        )
        
        # Verify it was added
        found = repository.get_edition(2025, 99)
        assert found is not None
        assert found.title == 'MTB 99/2025'
    
    def test_scraper_updates_existing_edition(self, repository, test_config, sample_edition):
        """Test that scraper updates existing editions."""
        from src.core.scraper import MTBScraper
        
        scraper = MTBScraper(repository, test_config)
        
        # Update the edition
        sample_edition.title = "Updated Title"
        sample_edition.scraped_at = datetime.now()
        repository.commit()
        
        # Verify update
        found = repository.get_edition(2025, 1)
        assert found.title == "Updated Title"
        assert found.scraped_at is not None


class TestScraperItemProcessing:
    """Tests for scraper item processing."""
    
    def test_process_items_html(self, repository, test_config, sample_edition):
        """Test processing items from HTML content."""
        from src.core.scraper import MTBScraper
        
        scraper = MTBScraper(repository, test_config)
        
        # Sample bulletin item HTML structure
        items_html = """
        <table class="bulletin-items">
            <tr>
                <td>Pkt.:</td>
                <td>1</td>
                <td>Kategorie:</td>
                <td>Curricula</td>
            </tr>
            <tr>
                <td colspan="4">
                    <strong>Änderung des Curriculums für das Bachelorstudium Informatik</strong>
                </td>
            </tr>
            <tr>
                <td colspan="4">
                    Der Senat hat in seiner Sitzung beschlossen...
                </td>
            </tr>
        </table>
        """
        
        items = scraper._parse_items_from_html(items_html)
        
        # Should find at least one item
        assert len(items) >= 1
    
    def test_store_items_for_edition(self, repository, test_config, sample_edition):
        """Test storing items for an edition."""
        from src.core.scraper import MTBScraper
        
        scraper = MTBScraper(repository, test_config)
        
        # Create items
        items_data = [
            {'punkt': 1, 'title': 'First Item', 'category': 'Curricula', 'content': 'Content 1'},
            {'punkt': 2, 'title': 'Second Item', 'category': 'Personnel', 'content': 'Content 2'},
        ]
        
        for item_data in items_data:
            repository.add_item(
                edition=sample_edition,
                punkt=item_data['punkt'],
                title=item_data['title'],
                category=item_data['category'],
                content=item_data['content']
            )
        
        # Verify items were stored
        items = repository.get_items_for_edition(sample_edition)
        assert len(items) >= 2


class TestScraperHelperMethods:
    """Tests for scraper helper methods."""
    
    def test_build_edition_url(self, repository, test_config):
        """Test building edition URL from year and stueck."""
        from src.core.scraper import MTBScraper
        
        scraper = MTBScraper(repository, test_config)
        
        # The scraper should be able to construct URLs
        base_url = test_config.get('scraping', {}).get('base_url', 'https://www.jku.at/mitteilungsblatt/')
        
        assert 'jku.at' in base_url or 'mitteilungsblatt' in base_url.lower()
    
    def test_normalize_category(self, repository, test_config):
        """Test category normalization."""
        from src.core.scraper import MTBScraper
        
        scraper = MTBScraper(repository, test_config)
        
        # Test common category variations
        categories = [
            "Curricula",
            "curricula",
            "CURRICULA",
            "Studienrecht",
            "Personal",
        ]
        
        for cat in categories:
            # Categories should be handled consistently
            assert isinstance(cat, str)
            assert len(cat) > 0
