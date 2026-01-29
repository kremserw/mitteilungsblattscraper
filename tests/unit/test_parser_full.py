"""Additional unit tests for the parser module."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from src.core.parser import PDFParser, ContentProcessor, process_bulletin_item


class TestPDFParser:
    """Tests for PDFParser class."""
    
    @pytest.fixture
    def parser(self, tmp_path):
        """Provide a PDFParser instance with temp cache dir."""
        return PDFParser(cache_dir=str(tmp_path))
    
    def test_parser_init_creates_cache_dir(self, tmp_path):
        """Test that parser creates cache directory on init."""
        cache_dir = tmp_path / "test_cache"
        parser = PDFParser(cache_dir=str(cache_dir))
        
        assert cache_dir.exists()
    
    def test_clean_text_removes_excessive_whitespace(self, parser):
        """Test that _clean_text removes excessive whitespace."""
        text = "Line 1\n\n\n\n\nLine 2"
        
        cleaned = parser._clean_text(text)
        
        assert "\n\n\n" not in cleaned
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned
    
    def test_clean_text_fixes_ligatures(self, parser):
        """Test that _clean_text fixes common ligatures."""
        text = "ﬁrst ﬂoor ﬀect"
        
        cleaned = parser._clean_text(text)
        
        assert "fi" in cleaned
        assert "fl" in cleaned
        assert "ff" in cleaned
    
    def test_clean_text_removes_page_numbers(self, parser):
        """Test that _clean_text removes page number lines."""
        text = "Content here\nSeite 5 von 10\nMore content"
        
        cleaned = parser._clean_text(text)
        
        assert "Content here" in cleaned
        assert "More content" in cleaned
        # Page number should be filtered
        assert "Seite 5 von 10" not in cleaned
    
    def test_clean_text_handles_empty(self, parser):
        """Test _clean_text with empty input."""
        assert parser._clean_text("") == ""
        assert parser._clean_text(None) == ""
    
    def test_get_pdf_metadata_nonexistent(self, parser):
        """Test get_pdf_metadata with non-existent file."""
        result = parser.get_pdf_metadata("/nonexistent/file.pdf")
        
        assert 'error' in result
    
    def test_extract_text_nonexistent(self, parser):
        """Test extract_text with non-existent file."""
        result = parser.extract_text("/nonexistent/file.pdf")
        
        # Should return empty string or handle gracefully
        assert isinstance(result, str)


class TestContentProcessorAdvanced:
    """Advanced tests for ContentProcessor."""
    
    def test_prepare_multiple_attachments(self):
        """Test preparing content with multiple attachments."""
        processor = ContentProcessor()
        
        content = "Main bulletin content"
        attachments = [
            "First attachment content about curriculum",
            "Second attachment about regulations",
            "Third attachment with ECTS information"
        ]
        
        result = processor.prepare_for_analysis(content, attachments)
        
        assert "BULLETIN CONTENT" in result
        assert "ATTACHMENT 1" in result
        assert "ATTACHMENT 2" in result
        assert "ATTACHMENT 3" in result
        assert "curriculum" in result
    
    def test_prepare_very_long_content(self):
        """Test that very long content is properly truncated."""
        processor = ContentProcessor()
        
        # Create content much longer than MAX_CONTENT_CHARS
        long_content = "Important content. " * 10000  # ~180k chars
        
        result = processor.prepare_for_analysis(long_content)
        
        assert len(result) <= processor.MAX_CONTENT_CHARS + 200
        assert "TRUNCATED" in result
    
    def test_extract_key_info_comprehensive(self):
        """Test comprehensive key info extraction."""
        processor = ContentProcessor()
        
        content = """
        This curriculum change affects the Bachelorstudium Informatik.
        The new requirements include 6 ECTS and 3 ECTS courses.
        Deadline: 15.03.2025
        Another date is 2025-06-30.
        Contact: Professor at JKU.
        """
        
        info = processor.extract_key_info(content)
        
        assert len(info['dates']) >= 1
        assert '6' in info['ects'] or '3' in info['ects']
        assert len(info['programs']) >= 1
    
    def test_extract_key_info_no_matches(self):
        """Test extract_key_info with content having no matches."""
        processor = ContentProcessor()
        
        content = "This is generic content without specific information."
        
        info = processor.extract_key_info(content)
        
        assert info['dates'] == []
        assert info['ects'] == []
        assert info['programs'] == []
    
    def test_summarize_preserves_first_sentences(self):
        """Test that summarize keeps first sentences intact."""
        processor = ContentProcessor()
        
        content = "First important sentence. Second sentence here. Third one follows. Fourth sentence. Fifth sentence is also here."
        
        result = processor.summarize_for_display(content, max_length=100)
        
        assert "First important sentence" in result
    
    def test_summarize_handles_no_periods(self):
        """Test summarize with content lacking periods."""
        processor = ContentProcessor()
        
        content = "This is content without any period at the end"
        
        result = processor.summarize_for_display(content)
        
        assert len(result) > 0


class TestProcessBulletinItem:
    """Tests for the process_bulletin_item function."""
    
    def test_process_item_basic(self, tmp_path):
        """Test processing a basic bulletin item."""
        parser = PDFParser(cache_dir=str(tmp_path))
        
        item_content = "This is the bulletin item content about curriculum changes."
        attachments = []
        
        result = process_bulletin_item(
            item_content=item_content,
            attachments=attachments,
            pdf_parser=parser,
            cache_dir=str(tmp_path)
        )
        
        assert 'combined_text' in result
        assert 'extracted_info' in result
        assert 'summary' in result
        assert "curriculum" in result['combined_text']
    
    def test_process_item_with_attachment_data(self, tmp_path):
        """Test processing item with attachment metadata."""
        parser = PDFParser(cache_dir=str(tmp_path))
        
        item_content = "Main content"
        attachments = [
            {'filename': 'doc.pdf', 'type': 'pdf', 'url': 'https://example.com/doc.pdf'}
        ]
        
        result = process_bulletin_item(
            item_content=item_content,
            attachments=attachments,
            pdf_parser=parser,
            cache_dir=str(tmp_path)
        )
        
        assert 'combined_text' in result
        assert 'attachment_texts' in result
