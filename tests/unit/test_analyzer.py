"""Unit tests for AI analyzer (with mocked API calls)."""

from unittest.mock import Mock, patch

import pytest

from src.core.analyzer import RelevanceAnalyzer


class TestRelevanceAnalyzer:
    """Tests for RelevanceAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Provide a RelevanceAnalyzer instance with a mock client."""
        with patch('anthropic.Anthropic'):
            return RelevanceAnalyzer(api_key='test-key', model='claude-haiku-4-5')
    
    def test_parse_response_complete(self, analyzer):
        """Test parsing a complete AI response."""
        response = """SCORE: 75
SHORT_TITLE: Test Analysis Title Here
EXPLANATION: This is the explanation of why it's relevant.
KEY_POINTS: Point 1. Point 2. Point 3."""
        
        score, explanation, short_title = analyzer._parse_response(response)
        
        assert score == 75.0
        assert short_title == "Test Analysis Title Here"
        assert "explanation" in explanation.lower()
        assert "Key points:" in explanation
    
    def test_parse_response_score_only(self, analyzer):
        """Test parsing response with only score."""
        response = """SCORE: 85
Some general text here."""
        
        score, explanation, short_title = analyzer._parse_response(response)
        
        assert score == 85.0
        assert short_title == ""
    
    def test_parse_response_score_clamping(self, analyzer):
        """Test that scores are clamped to 0-100 range."""
        response_high = "SCORE: 150"
        response_low = "SCORE: -20"
        
        score_high, _, _ = analyzer._parse_response(response_high)
        score_low, _, _ = analyzer._parse_response(response_low)
        
        assert score_high == 100.0
        assert score_low == 0.0
    
    def test_parse_response_decimal_score(self, analyzer):
        """Test parsing response with decimal score."""
        response = "SCORE: 72.5"
        
        score, _, _ = analyzer._parse_response(response)
        
        assert score == 72.5
    
    def test_parse_response_no_key_points(self, analyzer):
        """Test parsing response without key points section."""
        response = """SCORE: 60
SHORT_TITLE: Title Without Points
EXPLANATION: Just an explanation."""
        
        score, explanation, short_title = analyzer._parse_response(response)
        
        assert "Key points:" not in explanation
    
    def test_build_analysis_prompt(self, analyzer):
        """Test that analysis prompt contains required elements."""
        prompt = analyzer._build_analysis_prompt(
            content="Test content here",
            role_description="I am a test user",
            item_title="Test Title",
            category="Curricula"
        )
        
        assert "Test content here" in prompt
        assert "I am a test user" in prompt
        assert "Test Title" in prompt
        assert "Curricula" in prompt
        assert "SCORE:" in prompt
        assert "SHORT_TITLE:" in prompt
        assert "EXPLANATION:" in prompt
    
    def test_analyze_item_success(self, analyzer, mock_anthropic_response):
        """Test successful item analysis."""
        analyzer.client.messages.create = Mock(return_value=mock_anthropic_response)
        
        score, explanation, short_title = analyzer.analyze_item(
            content="Test content",
            role_description="Test role",
            item_title="Test Title",
            category="Test Category"
        )
        
        assert score == 75.0
        assert "Test Item Analysis Result" in short_title
        assert analyzer.client.messages.create.called
    
    def test_analyze_item_api_error(self, analyzer):
        """Test handling API errors gracefully."""
        analyzer.client.messages.create = Mock(
            side_effect=Exception("API connection failed")
        )
        
        score, explanation, short_title = analyzer.analyze_item(
            content="Test content",
            role_description="Test role"
        )
        
        assert score == 0.0
        assert "Error" in explanation
        assert short_title == ""
    
    def test_batch_analyze(self, analyzer, mock_anthropic_response):
        """Test batch analysis of multiple items."""
        analyzer.client.messages.create = Mock(return_value=mock_anthropic_response)
        
        items = [
            {'content': 'Item 1', 'title': 'Title 1', 'category': 'Cat 1'},
            {'content': 'Item 2', 'title': 'Title 2', 'category': 'Cat 2'},
        ]
        
        results = analyzer.batch_analyze(items, "Test role")
        
        assert len(results) == 2
        assert analyzer.client.messages.create.call_count == 2


class TestResponseParsing:
    """Additional tests for response parsing edge cases."""
    
    @pytest.fixture
    def analyzer(self):
        """Provide a RelevanceAnalyzer instance."""
        with patch('anthropic.Anthropic'):
            return RelevanceAnalyzer(api_key='test-key')
    
    def test_parse_empty_response(self, analyzer):
        """Test parsing empty response."""
        score, explanation, short_title = analyzer._parse_response("")
        
        assert score == 0.0
        assert explanation == ""
    
    def test_parse_malformed_response(self, analyzer):
        """Test parsing malformed response."""
        response = "This is just random text without proper format"
        
        score, explanation, short_title = analyzer._parse_response(response)
        
        assert score == 0.0
        assert explanation == response  # Falls back to full response
    
    def test_parse_response_case_insensitive(self, analyzer):
        """Test that parsing is case-insensitive."""
        response = """score: 65
short_title: Lowercase Test
explanation: This works too."""
        
        score, explanation, short_title = analyzer._parse_response(response)
        
        assert score == 65.0
        assert short_title == "Lowercase Test"
