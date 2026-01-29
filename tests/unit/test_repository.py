"""Unit tests for Repository data access layer."""

from datetime import datetime

import pytest


class TestRepositoryEditions:
    """Tests for edition-related repository methods."""
    
    def test_get_edition(self, repository, sample_edition):
        """Test getting edition by year and stueck."""
        found = repository.get_edition(2025, 1)
        
        assert found is not None
        assert found.id == sample_edition.id
    
    def test_get_edition_not_found(self, repository):
        """Test getting non-existent edition returns None."""
        found = repository.get_edition(9999, 99)
        assert found is None
    
    def test_get_edition_by_id(self, repository, sample_edition):
        """Test getting edition by string ID."""
        found = repository.get_edition_by_id("2025-1")
        
        assert found is not None
        assert found.id == sample_edition.id
    
    def test_get_edition_by_id_invalid(self, repository):
        """Test getting edition with invalid ID format."""
        found = repository.get_edition_by_id("invalid")
        assert found is None
    
    def test_get_all_editions(self, populated_repository):
        """Test getting all editions."""
        editions = populated_repository.get_all_editions()
        
        assert len(editions) == 3
        # Should be sorted by year desc, stueck desc
        assert editions[0].stueck == 3
    
    def test_get_all_editions_by_year(self, populated_repository):
        """Test filtering editions by year."""
        editions = populated_repository.get_all_editions(year=2025)
        
        assert len(editions) == 3
        assert all(ed.year == 2025 for ed in editions)
    
    def test_update_edition(self, repository, sample_edition):
        """Test updating an edition."""
        repository.update_edition(sample_edition, title="Updated Title")
        
        found = repository.get_edition(2025, 1)
        assert found.title == "Updated Title"
    
    def test_get_unscraped_editions(self, repository):
        """Test getting unscraped editions."""
        # Create an unscraped edition
        repository.add_edition(year=2025, stueck=5)
        
        unscraped = repository.get_unscraped_editions()
        
        assert len(unscraped) >= 1
        assert all(ed.scraped_at is None for ed in unscraped)
    
    def test_get_unanalyzed_editions(self, repository, sample_edition):
        """Test getting unanalyzed (but scraped) editions."""
        # Mark as scraped but not analyzed
        sample_edition.scraped_at = datetime.now()
        repository.commit()
        
        unanalyzed = repository.get_unanalyzed_editions()
        
        assert len(unanalyzed) >= 1
        assert all(ed.analyzed_at is None for ed in unanalyzed)


class TestRepositoryItems:
    """Tests for item-related repository methods."""
    
    def test_get_item_by_id(self, repository, sample_item):
        """Test getting item by ID."""
        found = repository.get_item_by_id(sample_item.id)
        
        assert found is not None
        assert found.id == sample_item.id
    
    def test_get_item_by_id_not_found(self, repository):
        """Test getting non-existent item returns None."""
        found = repository.get_item_by_id(99999)
        assert found is None
    
    def test_get_items_for_edition(self, populated_repository):
        """Test getting all items for an edition."""
        edition = populated_repository.get_edition(2025, 1)
        items = populated_repository.get_items_for_edition(edition)
        
        assert len(items) == 3
        # Should be sorted by punkt
        assert items[0].punkt == 1
    
    def test_get_relevant_items(self, repository, sample_edition):
        """Test getting relevant items above threshold."""
        # Create items with different scores
        for i, score in enumerate([40, 60, 80], start=1):
            item = repository.add_item(
                edition=sample_edition,
                punkt=i,
                title=f"Item {i}"
            )
            repository.update_item_analysis(item, score, "Test", f"Title {i}")
        
        relevant = repository.get_relevant_items(threshold=60)
        
        assert len(relevant) == 2
        assert all(item.relevance_score >= 60 for item in relevant)
    
    def test_update_item_analysis(self, repository, sample_item):
        """Test updating item analysis results."""
        repository.update_item_analysis(
            sample_item,
            score=75.5,
            explanation="Test explanation",
            short_title="Short Test Title"
        )
        
        found = repository.get_item_by_id(sample_item.id)
        
        assert found.relevance_score == 75.5
        assert found.relevance_explanation == "Test explanation"
        assert found.short_title == "Short Test Title"
        assert found.analyzed_at is not None
    
    def test_mark_item_read(self, repository, sample_item):
        """Test marking an item as read."""
        assert sample_item.read_at is None
        
        result = repository.mark_item_read(sample_item.id)
        
        assert result is True
        found = repository.get_item_by_id(sample_item.id)
        assert found.read_at is not None
    
    def test_mark_item_read_already_read(self, repository, sample_item):
        """Test marking an already-read item returns False."""
        repository.mark_item_read(sample_item.id)
        result = repository.mark_item_read(sample_item.id)
        
        assert result is False
    
    def test_clear_items_for_edition(self, populated_repository):
        """Test clearing all items for an edition."""
        edition = populated_repository.get_edition(2025, 1)
        edition.scraped_at = datetime.now()
        edition.analyzed_at = datetime.now()
        populated_repository.commit()
        
        populated_repository.clear_items_for_edition(edition)
        
        items = populated_repository.get_items_for_edition(edition)
        assert len(items) == 0
        assert edition.scraped_at is None
        assert edition.analyzed_at is None


class TestRepositoryStats:
    """Tests for statistics methods."""
    
    def test_get_stats(self, populated_repository):
        """Test getting statistics."""
        stats = populated_repository.get_stats()
        
        assert stats['total_editions'] == 3
        assert stats['total_items'] == 9
        assert 'scraped_editions' in stats
        assert 'analyzed_editions' in stats
        assert 'relevant_items' in stats
    
    def test_get_stats_empty_db(self, repository):
        """Test getting statistics from empty database."""
        stats = repository.get_stats()
        
        assert stats['total_editions'] == 0
        assert stats['total_items'] == 0
