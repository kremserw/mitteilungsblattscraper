"""Integration tests for task manager."""

import time
import threading

import pytest

from src.api.services.task_manager import TaskManager, get_task_manager


class TestTaskManager:
    """Tests for TaskManager class."""
    
    @pytest.fixture
    def task_manager(self):
        """Provide a fresh TaskManager instance."""
        return TaskManager()
    
    def test_initial_state(self, task_manager):
        """Test task manager initial state."""
        assert task_manager.is_running is False
        status = task_manager.status
        assert status['running'] is False
        assert status['task'] is None
        assert status['logs'] == []
        assert status['error'] is None
    
    def test_add_log(self, task_manager):
        """Test adding log messages."""
        task_manager.add_log("Test message 1")
        task_manager.add_log("Test message 2")
        
        status = task_manager.status
        assert len(status['logs']) == 2
        assert "Test message 1" in status['logs'][0]
        assert "Test message 2" in status['logs'][1]
    
    def test_add_log_with_timestamp(self, task_manager):
        """Test that logs include timestamps."""
        task_manager.add_log("Test message")
        
        log = task_manager.status['logs'][0]
        assert "[" in log  # Timestamp in brackets
    
    def test_clear_logs(self, task_manager):
        """Test clearing logs."""
        task_manager.add_log("Message 1")
        task_manager.add_log("Message 2")
        task_manager.clear_logs()
        
        assert task_manager.status['logs'] == []
    
    def test_set_progress(self, task_manager):
        """Test setting progress."""
        task_manager.set_progress(5, 10)
        
        status = task_manager.status
        assert status['progress'] == 5
        assert status['total'] == 10
    
    def test_start_task_success(self, task_manager):
        """Test starting a task successfully."""
        completed = threading.Event()
        
        def test_task():
            time.sleep(0.1)
            completed.set()
        
        started = task_manager.start_task("test", test_task)
        
        assert started is True
        assert task_manager.is_running is True
        
        # Wait for task to complete
        completed.wait(timeout=2)
        time.sleep(0.1)  # Allow task cleanup
        
        assert task_manager.is_running is False
    
    def test_start_task_concurrent_blocked(self, task_manager):
        """Test that concurrent tasks are blocked."""
        def slow_task():
            time.sleep(0.5)
        
        # Start first task
        started1 = task_manager.start_task("task1", slow_task)
        assert started1 is True
        
        # Try to start second task - should be blocked
        started2 = task_manager.start_task("task2", slow_task)
        assert started2 is False
    
    def test_task_with_exception(self, task_manager):
        """Test that task exceptions are handled."""
        def failing_task():
            raise ValueError("Task failed!")
        
        task_manager.start_task("failing", failing_task)
        
        # Wait for task to complete
        time.sleep(0.2)
        
        status = task_manager.status
        assert status['running'] is False
        assert status['error'] is not None
        assert "Task failed" in status['error']
    
    def test_task_with_logging(self, task_manager):
        """Test that tasks can log during execution."""
        def logging_task(tm):
            tm.add_log("Step 1")
            time.sleep(0.05)
            tm.add_log("Step 2")
        
        task_manager.start_task("logging", logging_task, task_manager)
        
        # Wait for task to complete
        time.sleep(0.2)
        
        logs = task_manager.status['logs']
        assert any("Step 1" in log for log in logs)
        assert any("Step 2" in log for log in logs)


class TestTaskManagerSingleton:
    """Tests for task manager singleton."""
    
    def test_get_task_manager_returns_same_instance(self):
        """Test that get_task_manager returns the same instance."""
        tm1 = get_task_manager()
        tm2 = get_task_manager()
        
        assert tm1 is tm2
