"""
Configuration module for the auto-sync system.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class SyncMode(Enum):
    """Synchronization modes"""
    PUSH = "push"  # Push changes to other nodes
    PULL = "pull"  # Pull changes from other nodes
    BIDIRECTIONAL = "bidirectional"  # Both push and pull


@dataclass
class SyncConfig:
    """Configuration for auto-sync system"""
    
    # Synchronization settings
    sync_interval: float = 5.0  # seconds
    sync_mode: SyncMode = SyncMode.BIDIRECTIONAL
    
    # Multi-master settings
    enable_multi_master: bool = True
    node_id: Optional[str] = None  # Unique identifier for this node
    
    # Conflict resolution
    conflict_strategy: str = "last_write_wins"  # Options: last_write_wins, first_write_wins, manual
    
    # Recovery settings
    enable_auto_recovery: bool = True
    recovery_retry_interval: float = 10.0  # seconds
    max_recovery_retries: int = 3
    
    # Network settings
    connection_timeout: float = 30.0  # seconds
    max_concurrent_syncs: int = 5
    
    # Peer nodes
    peer_nodes: List[str] = field(default_factory=list)
    
    # Logging
    log_level: str = "INFO"
    enable_sync_log: bool = True
    
    # Performance
    batch_size: int = 100  # Number of items to sync in one batch
    compression_enabled: bool = True
    
    def validate(self) -> bool:
        """Validate configuration"""
        if self.sync_interval <= 0:
            raise ValueError("sync_interval must be positive")
        if self.recovery_retry_interval <= 0:
            raise ValueError("recovery_retry_interval must be positive")
        if self.max_recovery_retries < 0:
            raise ValueError("max_recovery_retries must be non-negative")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        return True
