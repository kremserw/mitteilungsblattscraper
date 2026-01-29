"""API tests for tasks endpoints."""

import json
import time

import pytest


class TestTasksAPI:
    """Tests for /api/tasks endpoints."""
    
    def test_get_status_idle(self, client):
        """Test getting status when idle."""
        response = client.get('/api/tasks/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['running'] is False
        assert 'logs' in data
        assert 'progress' in data
    
    def test_clear_logs(self, client):
        """Test clearing task logs."""
        response = client.post('/api/tasks/clear-logs')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['cleared'] is True
    
    def test_start_scan_blocked_when_running(self, client):
        """Test that starting a task while another is running returns 409."""
        # This test is tricky since we need to start one task and then try another
        # We'll use the task manager directly
        from src.api.services.task_manager import get_task_manager
        import threading
        
        task_manager = get_task_manager()
        task_manager.clear_logs()
        
        # Start a "long-running" task directly
        def slow_task():
            time.sleep(1)
        
        started = task_manager.start_task("slow", slow_task)
        assert started is True
        
        # Now try to start another task via API
        response = client.post('/api/tasks/scan')
        
        # Should be blocked
        assert response.status_code == 409
        
        # Wait for slow task to finish
        time.sleep(1.1)


class TestTasksAPIEndpoints:
    """Tests for specific task endpoints existence."""
    
    def test_scan_endpoint_exists(self, client):
        """Test that scan endpoint exists."""
        # We don't actually run the scan, just test the endpoint responds
        response = client.post('/api/tasks/scan')
        
        # Either 200 (started) or 409 (another task running)
        assert response.status_code in [200, 409]
    
    def test_scrape_endpoint_exists(self, client):
        """Test that scrape endpoint exists."""
        response = client.post('/api/tasks/scrape')
        assert response.status_code in [200, 409]
    
    def test_analyze_endpoint_exists(self, client):
        """Test that analyze endpoint exists."""
        response = client.post('/api/tasks/analyze')
        assert response.status_code in [200, 409]
    
    def test_sync_endpoint_exists(self, client):
        """Test that sync endpoint exists."""
        response = client.post('/api/tasks/sync')
        assert response.status_code in [200, 409]
