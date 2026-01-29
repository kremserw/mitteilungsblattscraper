"""API tests for settings endpoints."""

import json

import pytest


class TestSettingsAPI:
    """Tests for /api/settings endpoints."""
    
    def test_get_role(self, client, test_config):
        """Test getting role description."""
        response = client.get('/api/settings/role')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'role_description' in data
        assert data['role_description'] == test_config['role_description']
    
    def test_update_role_put(self, client):
        """Test updating role description with PUT."""
        new_role = "Updated test role description"
        
        response = client.put(
            '/api/settings/role',
            data=json.dumps({'role_description': new_role}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['saved'] is True
    
    def test_update_role_post(self, client):
        """Test updating role description with POST."""
        new_role = "Another updated role"
        
        response = client.post(
            '/api/settings/role',
            data=json.dumps({'role_description': new_role}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['saved'] is True
    
    def test_get_stats(self, client, repository, sample_edition):
        """Test getting database statistics."""
        # Add some items to the sample edition to have meaningful stats
        for i in range(3):
            repository.add_item(edition=sample_edition, punkt=i+1, title=f"Item {i+1}")
        
        response = client.get('/api/settings/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_editions' in data
        assert 'total_items' in data
        assert data['total_editions'] >= 1
        assert data['total_items'] >= 3
