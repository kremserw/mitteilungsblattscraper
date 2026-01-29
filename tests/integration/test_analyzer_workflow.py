"""Integration tests for the analyzer workflow."""

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest


class TestAnalyzerWorkflow:
    """Tests for the full analysis workflow."""
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client."""
        mock_client = Mock()
        
        class MockContent:
            text = """SCORE: 78
SHORT_TITLE: Important Curriculum Update
EXPLANATION: This bulletin item contains significant updates to the Computer Science curriculum.
KEY_POINTS: New course requirements. Updated ECTS credits. Modified prerequisites."""
        
        class MockResponse:
            content = [MockContent()]
        
        mock_client.messages.create.return_value = MockResponse()
        return mock_client
    
    def test_analyze_single_item(self, repository, sample_edition, sample_item, mock_anthropic_client):
        """Test analyzing a single bulletin item."""
        from src.core.analyzer import RelevanceAnalyzer
        
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            analyzer = RelevanceAnalyzer(api_key='test-key', model='claude-haiku-4-5')
            
            score, explanation, short_title = analyzer.analyze_item(
                content="Test curriculum content about Computer Science changes",
                role_description="I am a Computer Science student",
                item_title="Curriculum Update",
                category="Curricula"
            )
            
            assert score == 78.0
            assert "Important Curriculum Update" in short_title
            assert "curriculum" in explanation.lower()
    
    def test_analyze_item_with_empty_content(self, mock_anthropic_client):
        """Test analyzing item with empty content."""
        from src.core.analyzer import RelevanceAnalyzer
        
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            analyzer = RelevanceAnalyzer(api_key='test-key')
            
            score, explanation, short_title = analyzer.analyze_item(
                content="",
                role_description="Test role"
            )
            
            # Should still return a result (API call happens)
            assert isinstance(score, float)
    
    def test_bulletin_analyzer_process_edition(self, repository, sample_edition, test_config):
        """Test BulletinAnalyzer processing an edition."""
        from src.core.analyzer import BulletinAnalyzer
        
        # Add items to the edition
        items = []
        for i in range(3):
            item = repository.add_item(
                edition=sample_edition,
                punkt=i + 1,
                title=f"Test Item {i + 1}",
                category="Curricula",
                content=f"Content for item {i + 1}"
            )
            items.append(item)
        
        # Mark edition as scraped
        sample_edition.scraped_at = datetime.now()
        repository.commit()
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            
            class MockContent:
                text = "SCORE: 65\nSHORT_TITLE: Test\nEXPLANATION: Test explanation"
            
            class MockResponse:
                content = [MockContent()]
            
            mock_client.messages.create.return_value = MockResponse()
            mock_anthropic.return_value = mock_client
            
            # BulletinAnalyzer takes repository and config dict
            config = {
                'anthropic_api_key': 'test-key',
                'model': 'claude-haiku-4-5',
                'role_description': 'Test student role'
            }
            
            analyzer = BulletinAnalyzer(
                repository=repository,
                config=config
            )
            
            # Analyze all items
            results = analyzer.analyze_edition(sample_edition)
            
            # Results is a summary dict with items count, scores, etc.
            assert results['items'] == 3
            assert all(score == 65.0 for score in results['scores'])


class TestAnalyzerEdgeCases:
    """Tests for analyzer edge cases and error handling."""
    
    def test_analyzer_handles_api_timeout(self):
        """Test that analyzer handles API timeouts gracefully."""
        from src.core.analyzer import RelevanceAnalyzer
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = TimeoutError("API timeout")
            mock_anthropic.return_value = mock_client
            
            analyzer = RelevanceAnalyzer(api_key='test-key')
            
            score, explanation, short_title = analyzer.analyze_item(
                content="Test content",
                role_description="Test role"
            )
            
            assert score == 0.0
            assert "Error" in explanation
    
    def test_analyzer_handles_rate_limit(self):
        """Test that analyzer handles rate limit errors."""
        from src.core.analyzer import RelevanceAnalyzer
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Rate limit exceeded")
            mock_anthropic.return_value = mock_client
            
            analyzer = RelevanceAnalyzer(api_key='test-key')
            
            score, explanation, short_title = analyzer.analyze_item(
                content="Test content",
                role_description="Test role"
            )
            
            assert score == 0.0
            assert short_title == ""
    
    def test_analyzer_parses_various_score_formats(self):
        """Test that analyzer parses various score formats."""
        from src.core.analyzer import RelevanceAnalyzer
        
        with patch('anthropic.Anthropic'):
            analyzer = RelevanceAnalyzer(api_key='test-key')
            
            # Test various formats - only the standard ones
            test_cases = [
                ("SCORE: 75", 75.0),
                ("score: 80", 80.0),
                ("SCORE:90", 90.0),
                ("SCORE: 75.5", 75.5),
            ]
            
            for response, expected_score in test_cases:
                score, _, _ = analyzer._parse_response(response)
                assert score == expected_score, f"Failed for: {response}"
    
    def test_analyzer_clamps_extreme_scores(self):
        """Test that extreme scores are clamped to 0-100."""
        from src.core.analyzer import RelevanceAnalyzer
        
        with patch('anthropic.Anthropic'):
            analyzer = RelevanceAnalyzer(api_key='test-key')
            
            # Test extreme values
            score_high, _, _ = analyzer._parse_response("SCORE: 999")
            score_low, _, _ = analyzer._parse_response("SCORE: -50")
            
            assert score_high == 100.0
            assert score_low == 0.0
