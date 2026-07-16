"""
DictSQLite v2 Auto-Sync System

Automatic synchronization system for dictsqlite_v2 with multi-master support
and automatic recovery.

Features:
- Automatic synchronization between multiple database instances
- Multi-master replication with conflict resolution
- Automatic recovery from failures
- Configurable sync intervals and conflict resolution strategies
"""

# Support both relative and absolute imports
try:
    from .sync_manager import SyncManager
    from .sync_node import SyncNode
    from .conflict_resolver import ConflictResolver, ConflictResolutionStrategy
    from .recovery_manager import RecoveryManager
    from .config import SyncConfig
except ImportError:
    from sync_manager import SyncManager
    from sync_node import SyncNode
    from conflict_resolver import ConflictResolver, ConflictResolutionStrategy
    from recovery_manager import RecoveryManager
    from config import SyncConfig

__all__ = [
    'SyncManager',
    'SyncNode',
    'ConflictResolver',
    'ConflictResolutionStrategy',
    'RecoveryManager',
    'SyncConfig',
]

__version__ = '1.0.0'
