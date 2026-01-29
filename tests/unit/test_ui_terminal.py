"""Unit tests for terminal UI functions."""

from unittest.mock import Mock, patch
from io import StringIO

import pytest


class TestTerminalUI:
    """Tests for terminal UI helper functions."""
    
    def test_ui_module_imports(self):
        """Test that ui module can be imported."""
        # The ui.py module should be importable
        from src import ui
        
        assert ui is not None
    
    def test_ui_has_run_web_server(self):
        """Test that ui module has run_web_server function."""
        from src.ui import run_web_server
        
        assert callable(run_web_server)
    
    def test_run_web_server_signature(self):
        """Test that run_web_server has correct signature."""
        from src.ui import run_web_server
        import inspect
        
        # Just verify the function exists and has correct signature
        sig = inspect.signature(run_web_server)
        
        params = list(sig.parameters.keys())
        assert len(params) >= 1  # Should have at least storage/repository param


class TestUICompatibility:
    """Tests for UI module compatibility layer."""
    
    def test_storage_alias_works(self):
        """Test that Storage alias from storage.py works."""
        from src.storage import Storage, get_storage
        
        # These should be callable
        assert Storage is not None
        assert callable(get_storage)
    
    def test_scraper_alias_works(self):
        """Test that scraper exports work."""
        from src.scraper import MTBScraper
        
        assert MTBScraper is not None
    
    def test_analyzer_alias_works(self):
        """Test that analyzer exports work."""
        from src.analyzer import RelevanceAnalyzer
        
        assert RelevanceAnalyzer is not None
    
    def test_parser_alias_works(self):
        """Test that parser exports work."""
        from src.parser import PDFParser
        
        assert PDFParser is not None
