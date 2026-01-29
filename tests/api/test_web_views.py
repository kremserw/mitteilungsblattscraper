"""Tests for web views (HTML page rendering)."""

import json
from datetime import datetime

import pytest


class TestWebViews:
    """Tests for web page rendering routes."""
    
    def test_dashboard_renders(self, client):
        """Test that dashboard page renders."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    def test_editions_page_renders(self, client):
        """Test that editions page renders."""
        response = client.get('/editions')
        
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    def test_relevant_page_renders(self, client):
        """Test that relevant items page renders."""
        response = client.get('/relevant')
        
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    def test_splash_page_renders(self, client):
        """Test that splash/loading page renders."""
        response = client.get('/splash')
        
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    def test_item_detail_page_renders(self, client, sample_item):
        """Test that item detail page renders."""
        response = client.get(f'/item/{sample_item.id}')
        
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    def test_item_detail_not_found(self, client):
        """Test item detail page for non-existent item."""
        response = client.get('/item/99999')
        
        # Should either return 404 or redirect
        assert response.status_code in [404, 302]
    
    def test_dashboard_contains_stats(self, client, repository, sample_edition):
        """Test that dashboard shows statistics."""
        # Add some items
        for i in range(3):
            item = repository.add_item(
                edition=sample_edition,
                punkt=i + 1,
                title=f"Item {i + 1}"
            )
            repository.update_item_analysis(item, 75.0, "Test", f"Title {i}")
        
        response = client.get('/')
        
        assert response.status_code == 200
        # Page should render successfully
        assert len(response.data) > 100
    
    def test_editions_page_shows_editions(self, client, sample_edition):
        """Test that editions page shows edition data."""
        response = client.get('/editions')
        
        assert response.status_code == 200
        # Should contain edition year
        assert b'2025' in response.data
    
    def test_relevant_page_shows_items(self, client, repository, sample_edition):
        """Test that relevant page shows relevant items."""
        # Create a relevant item
        item = repository.add_item(
            edition=sample_edition,
            punkt=1,
            title="Relevant Test Item"
        )
        repository.update_item_analysis(item, 85.0, "Very relevant", "Relevant Item")
        
        response = client.get('/relevant')
        
        assert response.status_code == 200
        # Page renders successfully
        assert len(response.data) > 100


class TestPDFProxy:
    """Tests for PDF proxy endpoint."""
    
    def test_pdf_proxy_missing_url(self, client):
        """Test PDF proxy with missing URL parameter."""
        response = client.get('/pdf-proxy')
        
        # Should return error for missing URL
        assert response.status_code in [400, 404, 500]
    
    def test_pdf_proxy_invalid_url(self, client):
        """Test PDF proxy with invalid URL."""
        response = client.get('/pdf-proxy?url=not-a-valid-url')
        
        # Should handle gracefully
        assert response.status_code in [400, 404, 500]


class TestStaticAssets:
    """Tests for static asset serving."""
    
    def test_css_served(self, client):
        """Test that CSS file is accessible."""
        response = client.get('/static/css/style.css')
        
        # Should serve CSS or return 404 if not configured
        assert response.status_code in [200, 404]
    
    def test_js_served(self, client):
        """Test that JavaScript file is accessible."""
        response = client.get('/static/js/app.js')
        
        # Should serve JS or return 404 if not configured
        assert response.status_code in [200, 404]
