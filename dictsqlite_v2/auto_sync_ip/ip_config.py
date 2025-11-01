"""
Configuration for IP-based synchronization.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IPSyncConfig:
    """Configuration for IP-based auto-sync system"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8765
    
    # Connection settings
    max_connections: int = 100
    connection_timeout: float = 30.0
    heartbeat_interval: float = 5.0
    
    # Sync settings
    sync_interval: float = 2.0
    batch_size: int = 1000
    compression_enabled: bool = True
    
    # Recovery settings
    enable_auto_recovery: bool = True
    recovery_check_interval: float = 10.0
    max_recovery_retries: int = 5
    recovery_retry_delay: float = 5.0
    
    # Peer nodes (for client mode)
    peer_addresses: List[str] = field(default_factory=list)
    
    # Security (future enhancement)
    enable_auth: bool = False
    auth_token: Optional[str] = None
    
    # Node identification
    node_id: Optional[str] = None
    
    # Performance
    use_msgpack: bool = True
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    
    def validate(self) -> bool:
        """Validate configuration"""
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        if self.max_connections < 1:
            raise ValueError("max_connections must be positive")
        if self.sync_interval <= 0:
            raise ValueError("sync_interval must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive")
        return True
