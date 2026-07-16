"""
Recovery manager for automatic recovery from failures.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from threading import Thread, Event
from enum import Enum


logger = logging.getLogger(__name__)


class RecoveryState(Enum):
    """Recovery states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"


class RecoveryManager:
    """
    Handles automatic recovery from synchronization failures.
    
    Features:
    - Monitors node health
    - Detects failures
    - Attempts automatic recovery
    - Maintains recovery history
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_interval: float = 10.0,
        health_check_interval: float = 5.0
    ):
        """
        Initialize recovery manager.
        
        Args:
            max_retries: Maximum number of recovery attempts
            retry_interval: Time between recovery attempts (seconds)
            health_check_interval: Time between health checks (seconds)
        """
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.health_check_interval = health_check_interval
        
        self.state = RecoveryState.HEALTHY
        self.recovery_attempts: Dict[str, int] = {}
        self.failure_history: list[Dict[str, Any]] = []
        
        # Health monitoring
        self._running = False
        self._health_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Recovery callbacks
        self._recovery_callbacks: list[Callable] = []
        
        logger.info("RecoveryManager initialized")
    
    def start_monitoring(self):
        """Start health monitoring"""
        if self._running:
            logger.warning("RecoveryManager already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._health_thread = Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
        logger.info("RecoveryManager monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        if self._health_thread:
            self._health_thread.join(timeout=5.0)
        logger.info("RecoveryManager monitoring stopped")
    
    def _health_check_loop(self):
        """Main health check loop"""
        while self._running and not self._stop_event.is_set():
            try:
                self._perform_health_check()
            except Exception as e:
                logger.error(f"Error in health check: {e}")
            
            self._stop_event.wait(self.health_check_interval)
    
    def _perform_health_check(self):
        """Perform health check on all monitored components"""
        # This is a placeholder - in a real implementation, you'd check:
        # - Database connectivity
        # - Peer node availability
        # - Sync queue health
        # - Resource utilization
        pass
    
    def record_failure(self, component: str, error: Exception, context: Dict[str, Any] = None):
        """
        Record a failure event.
        
        Args:
            component: Component that failed (e.g., "sync", "database", "network")
            error: The exception that occurred
            context: Additional context about the failure
        """
        failure = {
            'component': component,
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': time.time(),
            'context': context or {}
        }
        
        self.failure_history.append(failure)
        logger.error(f"Failure recorded for {component}: {error}")
        
        # Trigger recovery if needed
        if self.state != RecoveryState.RECOVERING:
            self._attempt_recovery(component, error)
    
    def _attempt_recovery(self, component: str, error: Exception):
        """
        Attempt to recover from a failure.
        
        Args:
            component: Component that failed
            error: The exception that occurred
        """
        # Track recovery attempts
        if component not in self.recovery_attempts:
            self.recovery_attempts[component] = 0
        
        self.recovery_attempts[component] += 1
        
        if self.recovery_attempts[component] > self.max_retries:
            logger.error(f"Max retries exceeded for {component}, marking as FAILED")
            self.state = RecoveryState.FAILED
            return
        
        logger.info(f"Attempting recovery for {component} (attempt {self.recovery_attempts[component]}/{self.max_retries})")
        self.state = RecoveryState.RECOVERING
        
        # Wait before retry
        time.sleep(self.retry_interval)
        
        # Execute recovery callbacks
        success = True
        for callback in self._recovery_callbacks:
            try:
                callback(component, error)
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")
                success = False
        
        if success:
            self.recovery_attempts[component] = 0
            self.state = RecoveryState.HEALTHY
            logger.info(f"Recovery successful for {component}")
        else:
            self.state = RecoveryState.DEGRADED
            logger.warning(f"Recovery incomplete for {component}")
    
    def add_recovery_callback(self, callback: Callable):
        """
        Add a recovery callback function.
        
        Args:
            callback: Function to call during recovery, signature: callback(component, error)
        """
        self._recovery_callbacks.append(callback)
    
    def get_state(self) -> RecoveryState:
        """Get current recovery state"""
        return self.state
    
    def get_failure_history(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get recent failure history.
        
        Args:
            limit: Maximum number of failures to return
            
        Returns:
            List of recent failures
        """
        return self.failure_history[-limit:]
    
    def clear_failure_history(self):
        """Clear failure history"""
        self.failure_history.clear()
        self.recovery_attempts.clear()
        logger.info("Failure history cleared")
    
    def reset_recovery_state(self):
        """Reset to healthy state"""
        self.state = RecoveryState.HEALTHY
        self.recovery_attempts.clear()
        logger.info("Recovery state reset to HEALTHY")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        return {
            'state': self.state.value,
            'total_failures': len(self.failure_history),
            'active_recovery_attempts': len(self.recovery_attempts),
            'recovery_attempts': dict(self.recovery_attempts),
            'monitoring_active': self._running
        }
