"""Unit tests for content parser."""

import pytest

from src.core.parser import ContentProcessor


class TestContentProcessor:
    """Tests for ContentProcessor class."""
    
    def test_prepare_for_analysis_basic(self):
        """Test basic content preparation."""
        processor = ContentProcessor()
        content = "This is the main bulletin content."
        
        result = processor.prepare_for_analysis(content)
        
        assert "BULLETIN CONTENT" in result
        assert "This is the main bulletin content" in result
    
    def test_prepare_for_analysis_with_attachments(self):
        """Test content preparation with attachments."""
        processor = ContentProcessor()
        content = "Main content"
        attachments = ["Attachment 1 text", "Attachment 2 text"]
        
        result = processor.prepare_for_analysis(content, attachments)
        
        assert "BULLETIN CONTENT" in result
        assert "ATTACHMENT 1" in result
        assert "ATTACHMENT 2" in result
        assert "Main content" in result
        assert "Attachment 1 text" in result
    
    def test_prepare_for_analysis_truncation(self):
        """Test that very long content is truncated."""
        processor = ContentProcessor()
        # Create content longer than MAX_CONTENT_CHARS
        long_content = "A" * 150000
        
        result = processor.prepare_for_analysis(long_content)
        
        assert len(result) <= processor.MAX_CONTENT_CHARS + 100
        assert "CONTENT TRUNCATED" in result
    
    def test_extract_key_info_dates(self, sample_pdf_content):
        """Test extracting dates from content."""
        processor = ContentProcessor()
        
        info = processor.extract_key_info(sample_pdf_content)
        
        assert len(info['dates']) > 0
    
    def test_extract_key_info_ects(self, sample_pdf_content):
        """Test extracting ECTS values from content."""
        processor = ContentProcessor()
        
        info = processor.extract_key_info(sample_pdf_content)
        
        assert '6' in info['ects']
    
    def test_extract_key_info_programs(self, sample_pdf_content):
        """Test extracting study programs from content."""
        processor = ContentProcessor()
        
        info = processor.extract_key_info(sample_pdf_content)
        
        assert len(info['programs']) > 0
        assert any('Computer Science' in p for p in info['programs'])
    
    def test_summarize_for_display_short(self):
        """Test summarizing short content."""
        processor = ContentProcessor()
        short_text = "This is a short sentence"
        
        result = processor.summarize_for_display(short_text)
        
        # Method adds period after sentences
        assert "This is a short sentence" in result
    
    def test_summarize_for_display_long(self):
        """Test summarizing long content truncates."""
        processor = ContentProcessor()
        long_text = "First sentence. Second sentence. Third sentence. " * 20
        
        result = processor.summarize_for_display(long_text, max_length=100)
        
        assert len(result) <= 110  # Some tolerance
    
    def test_summarize_for_display_empty(self):
        """Test summarizing empty content."""
        processor = ContentProcessor()
        
        result = processor.summarize_for_display("")
        
        assert result == ""
    
    def test_summarize_for_display_none(self):
        """Test summarizing None content."""
        processor = ContentProcessor()
        
        result = processor.summarize_for_display(None)
        
        assert result == ""
