"""API tests for editions endpoints."""

import json

import pytest


class TestEditionsAPI:
    """Tests for /api/editions endpoints."""
    
    def test_list_editions_empty(self, client):
        """Test listing editions when database is empty."""
        response = client.get('/api/editions/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []
    
    def test_list_editions(self, client, populated_repository):
        """Test listing all editions."""
        response = client.get('/api/editions/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3
    
    def test_list_editions_filter_by_year(self, client, populated_repository):
        """Test filtering editions by year."""
        response = client.get('/api/editions/?year=2025')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert all(ed['year'] == 2025 for ed in data)
    
    def test_get_edition(self, client, sample_edition):
        """Test getting a single edition."""
        response = client.get('/api/editions/2025-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['year'] == 2025
        assert data['stueck'] == 1
    
    def test_get_edition_not_found(self, client):
        """Test getting non-existent edition returns 404."""
        response = client.get('/api/editions/9999-99')
        
        assert response.status_code == 404
    
    def test_get_edition_items(self, client, populated_repository):
        """Test getting items for an edition."""
        response = client.get('/api/editions/2025-1/items')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3
    
    def test_get_edition_items_not_found(self, client):
        """Test getting items for non-existent edition returns 404."""
        response = client.get('/api/editions/9999-99/items')
        
        assert response.status_code == 404
    
    def test_get_stats(self, client, populated_repository):
        """Test getting statistics."""
        response = client.get('/api/editions/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_editions' in data
        assert 'total_items' in data
    
    def test_get_unscraped(self, client, repository):
        """Test getting unscraped editions."""
        # Add an unscraped edition
        repository.add_edition(year=2025, stueck=99)
        
        response = client.get('/api/editions/unscraped')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
    
    def test_reset_edition(self, client, sample_edition, sample_item, repository):
        """Test resetting an edition."""
        from datetime import datetime
        
        # Mark edition as scraped
        sample_edition.scraped_at = datetime.now()
        repository.commit()
        
        response = client.post('/api/editions/2025-1/reset')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['reset'] is True
    
    def test_reset_edition_not_found(self, client):
        """Test resetting non-existent edition returns 404."""
        response = client.post('/api/editions/9999-99/reset')
        
        assert response.status_code == 404
