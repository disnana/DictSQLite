"""
Tests for the RecoveryManager class.
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recovery_manager import RecoveryManager, RecoveryState


class TestRecoveryManager:
    """Test cases for RecoveryManager"""
    
    def test_initialization(self):
        """Test recovery manager initialization"""
        recovery = RecoveryManager(
            max_retries=3,
            retry_interval=1.0,
            health_check_interval=2.0
        )
        
        assert recovery.max_retries == 3
        assert recovery.retry_interval == 1.0
        assert recovery.health_check_interval == 2.0
        assert recovery.state == RecoveryState.HEALTHY
    
    def test_record_failure(self):
        """Test recording a failure"""
        recovery = RecoveryManager(max_retries=3, retry_interval=0.5)
        
        error = Exception("Test error")
        recovery.record_failure("test_component", error)
        
        history = recovery.get_failure_history()
        assert len(history) == 1
        assert history[0]["component"] == "test_component"
        assert "Test error" in history[0]["error"]
    
    def test_record_failure_with_context(self):
        """Test recording a failure with context"""
        recovery = RecoveryManager(max_retries=3, retry_interval=0.5)
        
        error = Exception("Test error")
        context = {"key": "value", "additional": "info"}
        recovery.record_failure("test_component", error, context)
        
        history = recovery.get_failure_history()
        assert history[0]["context"] == context
    
    def test_get_failure_history_limit(self):
        """Test getting limited failure history"""
        recovery = RecoveryManager(max_retries=10, retry_interval=0.1)
        
        # Record multiple failures
        for i in range(10):
            error = Exception(f"Error {i}")
            recovery.record_failure(f"component_{i}", error)
        
        # Get limited history
        history = recovery.get_failure_history(limit=5)
        assert len(history) == 5
    
    def test_clear_failure_history(self):
        """Test clearing failure history"""
        recovery = RecoveryManager(max_retries=3, retry_interval=0.5)
        
        error = Exception("Test error")
        recovery.record_failure("test_component", error)
        
        assert len(recovery.get_failure_history()) > 0
        
        recovery.clear_failure_history()
        
        assert len(recovery.get_failure_history()) == 0
        assert len(recovery.recovery_attempts) == 0
    
    def test_recovery_callback(self):
        """Test adding and invoking recovery callback"""
        recovery = RecoveryManager(max_retries=1, retry_interval=0.1)
        
        callback_invoked = []
        
        def test_callback(component, error):
            callback_invoked.append((component, str(error)))
        
        recovery.add_recovery_callback(test_callback)
        
        # Record a failure to trigger recovery
        error = Exception("Test error")
        recovery.record_failure("test_component", error)
        
        # Give time for callback to be invoked
        time.sleep(0.2)
        
        assert len(callback_invoked) > 0
    
    def test_get_state(self):
        """Test getting recovery state"""
        recovery = RecoveryManager(max_retries=3, retry_interval=0.5)
        
        state = recovery.get_state()
        assert state == RecoveryState.HEALTHY
    
    def test_reset_recovery_state(self):
        """Test resetting recovery state"""
        recovery = RecoveryManager(max_retries=1, retry_interval=0.1)
        
        # Record a failure
        error = Exception("Test error")
        recovery.record_failure("test_component", error)
        
        # Reset state
        recovery.reset_recovery_state()
        
        assert recovery.state == RecoveryState.HEALTHY
        assert len(recovery.recovery_attempts) == 0
    
    def test_get_stats(self):
        """Test getting recovery statistics"""
        recovery = RecoveryManager(max_retries=3, retry_interval=0.5)
        
        error = Exception("Test error")
        recovery.record_failure("test_component", error)
        
        stats = recovery.get_stats()
        
        assert "state" in stats
        assert "total_failures" in stats
        assert "active_recovery_attempts" in stats
        assert "monitoring_active" in stats
        assert stats["total_failures"] >= 1
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping health monitoring"""
        recovery = RecoveryManager(
            max_retries=3,
            retry_interval=0.5,
            health_check_interval=0.5
        )
        
        # Start monitoring
        recovery.start_monitoring()
        assert recovery._running is True
        
        time.sleep(0.2)
        
        # Stop monitoring
        recovery.stop_monitoring()
        assert recovery._running is False
    
    def test_monitoring_already_running(self):
        """Test starting monitoring when already running"""
        recovery = RecoveryManager(max_retries=3, retry_interval=0.5)
        
        recovery.start_monitoring()
        
        # Try to start again (should log a warning but not crash)
        recovery.start_monitoring()
        
        assert recovery._running is True
        
        recovery.stop_monitoring()
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries is exceeded"""
        recovery = RecoveryManager(max_retries=2, retry_interval=0.1)
        
        # Add a callback that always fails
        def failing_callback(component, error):
            raise Exception("Callback failed")
        
        recovery.add_recovery_callback(failing_callback)
        
        # Record failures to exceed max retries
        for i in range(3):
            error = Exception(f"Error {i}")
            recovery.record_failure("test_component", error)
            time.sleep(0.15)
        
        # Should be in FAILED state after exceeding retries
        stats = recovery.get_stats()
        assert stats["state"] in [RecoveryState.FAILED.value, RecoveryState.DEGRADED.value]
