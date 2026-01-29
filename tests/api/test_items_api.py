"""API tests for items endpoints."""

import json

import pytest


class TestItemsAPI:
    """Tests for /api/items endpoints."""
    
    def test_list_items_empty(self, client):
        """Test listing items when none meet threshold."""
        response = client.get('/api/items/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []
    
    def test_list_items_with_threshold(self, client, repository, sample_edition):
        """Test listing relevant items."""
        # Create items with different scores
        for i, score in enumerate([40, 70, 90], start=1):
            item = repository.add_item(
                edition=sample_edition,
                punkt=i,
                title=f"Item {i}"
            )
            repository.update_item_analysis(item, score, "Test", f"Title {i}")
        
        response = client.get('/api/items/?threshold=60')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert all(item['relevance_score'] >= 60 for item in data)
    
    def test_list_recent_items(self, client, repository, sample_edition):
        """Test listing recent relevant items."""
        # Create analyzed items
        for i in range(5):
            item = repository.add_item(
                edition=sample_edition,
                punkt=i + 1,
                title=f"Item {i + 1}"
            )
            repository.update_item_analysis(item, 75, "Test", f"Title {i + 1}")
        
        response = client.get('/api/items/recent?limit=3')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3
    
    def test_get_item(self, client, sample_item):
        """Test getting a single item."""
        response = client.get(f'/api/items/{sample_item.id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == sample_item.id
        assert data['title'] == sample_item.title
    
    def test_get_item_not_found(self, client):
        """Test getting non-existent item returns 404."""
        response = client.get('/api/items/99999')
        
        assert response.status_code == 404
    
    def test_mark_item_read(self, client, sample_item):
        """Test marking an item as read."""
        assert sample_item.read_at is None
        
        response = client.post(f'/api/items/{sample_item.id}/read')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['marked'] is True
    
    def test_mark_item_read_already_read(self, client, sample_item, repository):
        """Test marking already-read item."""
        # First mark
        repository.mark_item_read(sample_item.id)
        
        # Second mark
        response = client.post(f'/api/items/{sample_item.id}/read')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['marked'] is False
