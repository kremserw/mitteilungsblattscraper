"""Comprehensive tests for the task manager."""

import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from src.api.services.task_manager import TaskManager, get_task_manager


class TestTaskManagerStatus:
    """Tests for task manager status reporting."""
    
    @pytest.fixture
    def tm(self):
        """Fresh task manager for each test."""
        task_manager = TaskManager()
        task_manager.clear_logs()
        task_manager._running = False
        task_manager._task_name = None
        task_manager._error = None
        task_manager._progress = 0
        task_manager._total = 0
        return task_manager
    
    def test_status_returns_dict(self, tm):
        """Test that status returns a dictionary."""
        status = tm.status
        
        assert isinstance(status, dict)
        assert 'running' in status
        assert 'task' in status
        assert 'logs' in status
        assert 'error' in status
    
    def test_status_tracks_task_name(self, tm):
        """Test that status tracks current task name."""
        def quick_task():
            time.sleep(0.1)
        
        tm.start_task("test_task_name", quick_task)
        
        status = tm.status
        assert status['task'] == "test_task_name"
        
        time.sleep(0.2)
    
    def test_status_tracks_progress(self, tm):
        """Test progress tracking in status."""
        tm.set_progress(5, 10)
        
        status = tm.status
        assert status['progress'] == 5
        assert status['total'] == 10
    
    def test_status_tracks_error(self, tm):
        """Test error tracking in status."""
        def failing_task():
            raise ValueError("Test error message")
        
        tm.start_task("fail", failing_task)
        time.sleep(0.2)
        
        status = tm.status
        assert status['error'] is not None
        assert "Test error message" in status['error']
    
    def test_logs_are_timestamped(self, tm):
        """Test that logs include timestamps."""
        tm.add_log("Test message")
        
        logs = tm.status['logs']
        assert len(logs) == 1
        # Should have timestamp in brackets
        assert "[" in logs[0]
        assert "Test message" in logs[0]
    
    def test_logs_limited(self, tm):
        """Test that logs are limited in size."""
        # Add many logs
        for i in range(200):
            tm.add_log(f"Log message {i}")
        
        logs = tm.status['logs']
        # Should be capped
        assert len(logs) <= 150  # Approximate max


class TestTaskManagerExecution:
    """Tests for task execution."""
    
    @pytest.fixture
    def tm(self):
        """Fresh task manager for each test."""
        task_manager = TaskManager()
        task_manager.clear_logs()
        task_manager._running = False
        return task_manager
    
    def test_task_with_arguments(self, tm):
        """Test running task with arguments."""
        results = []
        
        def task_with_args(a, b, c=None):
            results.append((a, b, c))
        
        tm.start_task("args", task_with_args, "first", "second", c="third")
        time.sleep(0.1)
        
        assert results == [("first", "second", "third")]
    
    def test_task_completion_clears_running(self, tm):
        """Test that task completion clears running state."""
        def quick():
            pass
        
        tm.start_task("quick", quick)
        time.sleep(0.1)
        
        assert tm.is_running is False
    
    def test_concurrent_task_rejection(self, tm):
        """Test that concurrent tasks are rejected."""
        def slow():
            time.sleep(0.5)
        
        started1 = tm.start_task("slow1", slow)
        started2 = tm.start_task("slow2", slow)
        
        assert started1 is True
        assert started2 is False
        
        time.sleep(0.6)


class TestTaskRunnerIntegration:
    """Integration tests for task runner functions."""
    
    def test_run_scan_task_exists(self):
        """Verify run_scan_task function exists."""
        from src.api.services.task_manager import run_scan_task
        
        import inspect
        sig = inspect.signature(run_scan_task)
        params = list(sig.parameters.keys())
        
        # Should accept task_manager, repository, config
        assert len(params) >= 3
    
    def test_run_scrape_task_exists(self):
        """Verify run_scrape_task function exists."""
        from src.api.services.task_manager import run_scrape_task
        
        import inspect
        sig = inspect.signature(run_scrape_task)
        params = list(sig.parameters.keys())
        
        assert len(params) >= 3
    
    def test_run_analyze_task_exists(self):
        """Verify run_analyze_task function exists."""
        from src.api.services.task_manager import run_analyze_task
        
        import inspect
        sig = inspect.signature(run_analyze_task)
        params = list(sig.parameters.keys())
        
        assert len(params) >= 3
    
    def test_run_sync_all_task_exists(self):
        """Verify run_sync_all_task function exists."""
        from src.api.services.task_manager import run_sync_all_task
        
        import inspect
        sig = inspect.signature(run_sync_all_task)
        params = list(sig.parameters.keys())
        
        # Should accept config and task_manager at minimum
        assert len(params) >= 2


class TestTaskManagerSingleton:
    """Tests for singleton behavior."""
    
    def test_get_task_manager_singleton(self):
        """Test that get_task_manager returns same instance."""
        tm1 = get_task_manager()
        tm2 = get_task_manager()
        
        assert tm1 is tm2
    
    def test_singleton_preserves_state(self):
        """Test that singleton preserves state between calls."""
        tm1 = get_task_manager()
        tm1.add_log("Singleton test message")
        
        tm2 = get_task_manager()
        logs = tm2.status['logs']
        
        assert any("Singleton test message" in log for log in logs)
