"""Unit tests for database models."""

import json
from datetime import datetime

import pytest

from src.db.models import Edition, BulletinItem, Attachment


class TestEdition:
    """Tests for Edition model."""
    
    def test_edition_creation(self, repository):
        """Test creating an edition."""
        edition = repository.add_edition(
            year=2025,
            stueck=10,
            title="MTB 10/2025",
            url="https://example.com/mtb"
        )
        
        assert edition.id is not None
        assert edition.year == 2025
        assert edition.stueck == 10
        assert edition.title == "MTB 10/2025"
    
    def test_edition_id_property(self, sample_edition):
        """Test edition_id property returns correct format."""
        assert sample_edition.edition_id == "2025-1"
    
    def test_edition_to_dict(self, sample_edition):
        """Test edition to_dict conversion."""
        data = sample_edition.to_dict()
        
        assert data['year'] == 2025
        assert data['stueck'] == 1
        assert data['edition_id'] == "2025-1"
        assert data['title'] == "MTB 1/2025"
        assert 'published_date' in data
    
    def test_edition_repr(self, sample_edition):
        """Test edition string representation."""
        assert "2025-1" in repr(sample_edition)


class TestBulletinItem:
    """Tests for BulletinItem model."""
    
    def test_item_creation(self, repository, sample_edition):
        """Test creating a bulletin item."""
        item = repository.add_item(
            edition=sample_edition,
            punkt=5,
            title="Test Item",
            category="Curricula",
            content="Test content"
        )
        
        assert item.id is not None
        assert item.punkt == 5
        assert item.title == "Test Item"
        assert item.edition_id == sample_edition.id
    
    def test_item_attachments_property(self, repository, sample_edition):
        """Test attachments JSON property."""
        item = repository.add_item(
            edition=sample_edition,
            punkt=1,
            title="Item with attachments"
        )
        
        # Set attachments
        attachments = [
            {'name': 'doc1.pdf', 'url': 'https://example.com/doc1.pdf'},
            {'name': 'doc2.pdf', 'url': 'https://example.com/doc2.pdf'},
        ]
        item.attachments = attachments
        repository.commit()
        
        # Get attachments
        retrieved = item.attachments
        assert len(retrieved) == 2
        assert retrieved[0]['name'] == 'doc1.pdf'
    
    def test_item_attachments_html_unescape(self, repository, sample_edition):
        """Test that attachments URLs are HTML-unescaped."""
        item = repository.add_item(
            edition=sample_edition,
            punkt=1,
            title="Item with escaped URL"
        )
        
        # Set attachment with HTML-escaped URL
        item.attachments_json = json.dumps([
            {'name': 'doc.pdf', 'url': 'https://example.com/path?a=1&amp;b=2'}
        ])
        repository.commit()
        
        # Get attachments - URL should be unescaped
        retrieved = item.attachments
        assert '&amp;' not in retrieved[0]['url']
        assert '&' in retrieved[0]['url']
    
    def test_item_to_dict(self, sample_item):
        """Test item to_dict conversion."""
        data = sample_item.to_dict()
        
        assert data['punkt'] == 1
        assert data['title'] == "Test Bulletin Item"
        assert data['category'] == "Curricula"
        assert 'content' in data
    
    def test_item_repr(self, sample_item):
        """Test item string representation."""
        repr_str = repr(sample_item)
        assert "BulletinItem" in repr_str


class TestAttachment:
    """Tests for Attachment model."""
    
    def test_attachment_creation(self, repository, sample_item):
        """Test creating an attachment."""
        attachment = repository.add_attachment(
            item_id=sample_item.id,
            filename="test.pdf",
            url="https://example.com/test.pdf",
            file_type="pdf"
        )
        
        assert attachment.id is not None
        assert attachment.filename == "test.pdf"
        assert attachment.file_type == "pdf"
    
    def test_attachment_to_dict(self, repository, sample_item):
        """Test attachment to_dict conversion."""
        attachment = repository.add_attachment(
            item_id=sample_item.id,
            filename="test.pdf",
            url="https://example.com/test.pdf",
            file_type="pdf"
        )
        
        data = attachment.to_dict()
        
        assert data['filename'] == "test.pdf"
        assert data['url'] == "https://example.com/test.pdf"
        assert data['file_type'] == "pdf"
