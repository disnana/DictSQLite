"""
DictSQLite v2 IP-based Auto-Sync System

Network-enabled synchronization system with WebSocket and msgpack for
fast, lightweight multi-master replication across different IPs.

Features:
- WebSocket-based communication for cross-IP synchronization
- msgpack for efficient binary serialization
- Multi-master support with multiple concurrent connections
- Automatic recovery and missing data synchronization
- High-performance, lightweight design
"""

try:
    from .sync_server import SyncServer
    from .sync_client import SyncClient
    from .ip_sync_manager import IPSyncManager
    from .ip_config import IPSyncConfig
    from .recovery import AutoRecovery
except ImportError:
    from sync_server import SyncServer
    from sync_client import SyncClient
    from ip_sync_manager import IPSyncManager
    from ip_config import IPSyncConfig
    from recovery import AutoRecovery

__all__ = [
    'SyncServer',
    'SyncClient',
    'IPSyncManager',
    'IPSyncConfig',
    'AutoRecovery',
]

__version__ = '1.0.0'
