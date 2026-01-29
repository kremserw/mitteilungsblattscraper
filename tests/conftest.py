"""
Pytest fixtures for JKU MTB Analyzer tests.

Provides:
- Test database (in-memory SQLite)
- Mock configuration
- Flask test client
- Sample Edition and BulletinItem fixtures
"""

import os
import sys
import tempfile
from datetime import datetime

import pytest

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def test_config():
    """Provide a test configuration dict."""
    return {
        'anthropic_api_key': 'test-api-key-not-real',
        'model': 'claude-haiku-4-5',
        'role_description': 'Test role: I am a test user interested in all bulletin items.',
        'relevance_threshold': 60.0,
        'storage': {
            'database': ':memory:',
            'cache_dir': tempfile.mkdtemp(),
        },
        'scraping': {
            'headless': True,
            'delay_seconds': 0,
        },
    }


@pytest.fixture
def temp_db_path():
    """Provide a temporary database file path."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def repository(temp_db_path):
    """Provide a test repository with a temporary database."""
    from src.db.repository import Repository
    
    repo = Repository(temp_db_path)
    yield repo
    repo.close()


@pytest.fixture
def sample_edition(repository):
    """Provide a sample Edition for testing."""
    return repository.add_edition(
        year=2025,
        stueck=1,
        title="MTB 1/2025",
        url="https://ix.jku.at/?app=mtb&jahr=2025&stk=1",
        published_date=datetime(2025, 1, 15)
    )


@pytest.fixture
def sample_item(repository, sample_edition):
    """Provide a sample BulletinItem for testing."""
    return repository.add_item(
        edition=sample_edition,
        punkt=1,
        title="Test Bulletin Item",
        category="Curricula",
        content="This is test content for the bulletin item."
    )


@pytest.fixture
def flask_app(repository, test_config):
    """Provide a Flask test application."""
    from src.api.app import create_app
    
    app = create_app(test_config, repository)
    app.config['TESTING'] = True
    
    return app


@pytest.fixture
def client(flask_app):
    """Provide a Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def runner(flask_app):
    """Provide a Flask CLI test runner."""
    return flask_app.test_cli_runner()


# Unit test specific fixtures

@pytest.fixture
def mock_anthropic_response():
    """Provide a mock Anthropic API response structure."""
    class MockContent:
        text = """SCORE: 75
SHORT_TITLE: Test Item Analysis Result
EXPLANATION: This is a test explanation of the relevance analysis.
KEY_POINTS: Important test point 1. Important test point 2."""

    class MockResponse:
        content = [MockContent()]

    return MockResponse()


@pytest.fixture
def sample_pdf_content():
    """Provide sample PDF-like text content for parsing tests."""
    return """
    This is a sample document content.
    
    Page 1
    
    Some important curriculum information here.
    This course is worth 6 ECTS credits.
    
    Bachelorstudium Computer Science
    
    Deadline: 15.03.2025
    
    Page 2
    
    More content continues here.
    """


@pytest.fixture
def sample_html_content():
    """Provide sample HTML content for scraper parsing tests."""
    return """
    <table>
        <tr>
            <td>MTB 1/2025</td>
            <td>15.01.2025</td>
            <td>2025</td>
        </tr>
        <tr>
            <td>MTB 2/2025</td>
            <td>30.01.2025</td>
            <td>2025</td>
        </tr>
    </table>
    """


# Integration test fixtures

@pytest.fixture
def populated_repository(repository):
    """Provide a repository with multiple editions and items."""
    # Create multiple editions
    for i in range(1, 4):
        edition = repository.add_edition(
            year=2025,
            stueck=i,
            title=f"MTB {i}/2025",
            url=f"https://ix.jku.at/?app=mtb&jahr=2025&stk={i}",
            published_date=datetime(2025, 1, i * 10)
        )
        
        # Add items to each edition
        for j in range(1, 4):
            repository.add_item(
                edition=edition,
                punkt=j,
                title=f"Item {j} of Edition {i}",
                category=["Curricula", "Personnel", "Regulations"][j - 1],
                content=f"Content for item {j} in edition {i}"
            )
    
    return repository
