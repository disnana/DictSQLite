# DictSQLite v2 Auto-Sync System

An automatic synchronization system with multi-master support and automatic recovery for DictSQLite v2.

## Overview

The Auto-Sync System provides a comprehensive solution for synchronizing data across multiple DictSQLite database instances with support for multi-master replication, conflict resolution, and automatic failure recovery.

## Key Features

### 1. Automatic Synchronization
- Automatic sync at configurable intervals
- Support for push, pull, and bidirectional sync modes
- Efficient batch processing for data transfer

### 2. Multi-Master Support
- Multiple nodes can write simultaneously
- Change tracking and propagation between nodes
- Peer-to-peer architecture

### 3. Conflict Resolution
Four conflict resolution strategies are supported:
- **Last Write Wins**: Prioritizes the most recent change
- **First Write Wins**: Prioritizes the first change
- **Manual**: Allows manual conflict resolution
- **Merge**: Attempts to merge values when possible (lists, dicts, numbers)

### 4. Automatic Recovery
- Automatic failure detection
- Configurable retry logic
- Health monitoring
- Failure history tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        SyncManager                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • Automatic sync loop                                 │  │
│  │ • Peer node management                                │  │
│  │ • Statistics collection                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  SyncNode    │  │   Conflict   │  │    Recovery      │  │
│  │              │  │   Resolver   │  │    Manager       │  │
│  │ • Change     │  │              │  │                  │  │
│  │   tracking   │  │ • Strategy   │  │ • Health         │  │
│  │ • Metadata   │  │   selection  │  │   monitoring     │  │
│  │ • Peer mgmt  │  │ • Resolution │  │ • Auto recovery  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Installation

This module is provided as part of DictSQLite v2.

```python
# Import from the auto_sync directory
from dictsqlite_v2.auto_sync import SyncManager, SyncNode, SyncConfig
```

## Quick Start

### Simple 2-Node Synchronization

```python
from dictsqlite import DictSQLite
from dictsqlite_v2.auto_sync import SyncManager, SyncNode, SyncConfig

# Create database instances
db1 = DictSQLite("node1.db")
db2 = DictSQLite("node2.db")

# Create SyncNodes
node1 = SyncNode(db1, node_id="node1")
node2 = SyncNode(db2, node_id="node2")

# Create configuration
config = SyncConfig(
    sync_interval=5.0,  # Sync every 5 seconds
    enable_multi_master=True,
    conflict_strategy="last_write_wins"
)

# Create SyncManager
manager1 = SyncManager(node1, config)
manager1.add_peer(node2)

# Start synchronization
manager1.start()

# Operate on data
db1["key1"] = "value1"
node1.track_change("key1", "value1")

# After 5 seconds, db2 will also have the data
import time
time.sleep(6)
print(db2["key1"])  # "value1"

# Stop and cleanup
manager1.stop()
db1.close()
db2.close()
```

## API Reference

### SyncManager

Main class for managing synchronization.

**Methods:**
- `add_peer(peer_node)`: Add a peer node
- `remove_peer(peer_node_id)`: Remove a peer node
- `start()`: Start automatic synchronization
- `stop()`: Stop automatic synchronization
- `force_sync()`: Immediately perform synchronization
- `get_stats()`: Get synchronization statistics
- `get_node_info()`: Get node information
- `close()`: Close the manager

### SyncNode

Represents a node in the multi-master system.

**Methods:**
- `track_change(key, value, operation)`: Track a change
- `get_changes_since(timestamp)`: Get changes since a timestamp
- `get_unsynced_changes()`: Get unsynced changes
- `mark_synced(keys)`: Mark keys as synced
- `apply_remote_change(key, value, timestamp, node_id)`: Apply remote change
- `get_all_data()`: Get all data
- `get_metadata()`: Get metadata

### ConflictResolver

Handles conflicts in multi-master replication.

**Methods:**
- `resolve_conflict(...)`: Resolve a conflict
- `set_manual_resolution(key, value)`: Set manual resolution
- `clear_manual_resolutions()`: Clear manual resolutions

### RecoveryManager

Handles automatic recovery from failures.

**Methods:**
- `start_monitoring()`: Start monitoring
- `stop_monitoring()`: Stop monitoring
- `record_failure(component, error, context)`: Record a failure
- `add_recovery_callback(callback)`: Add recovery callback
- `get_state()`: Get current state
- `get_failure_history(limit)`: Get failure history
- `reset_recovery_state()`: Reset state

### SyncConfig

Configuration for the auto-sync system.

**Key Parameters:**
- `sync_interval`: Synchronization interval in seconds (default: 5.0)
- `sync_mode`: SyncMode.PUSH, PULL, or BIDIRECTIONAL (default: BIDIRECTIONAL)
- `enable_multi_master`: Enable multi-master support (default: True)
- `conflict_strategy`: Conflict resolution strategy (default: "last_write_wins")
- `enable_auto_recovery`: Enable automatic recovery (default: True)
- `recovery_retry_interval`: Retry interval for recovery (default: 10.0)
- `max_recovery_retries`: Maximum retry attempts (default: 3)
- `batch_size`: Batch size for sync operations (default: 100)

## Testing

The auto-sync system includes comprehensive test coverage:

```bash
cd dictsqlite_v2/auto_sync
python -m pytest tests/ -v
```

All 65 tests should pass, covering:
- Configuration validation
- Conflict resolution strategies
- Node operations and change tracking
- Recovery manager functionality
- Sync manager operations

## Examples

See the `examples/` directory for:
- `basic_usage.py`: Basic 2-node synchronization examples
- `multi_master_example.py`: Multi-master scenarios with 3-5 nodes

Run examples:
```bash
cd dictsqlite_v2/auto_sync/examples
python basic_usage.py
python multi_master_example.py
```

## Notes

1. **Performance**: For large datasets, adjust the `batch_size` parameter
2. **Network**: Current implementation is in-memory. For production, network communication needs to be implemented
3. **Conflicts**: Choose an appropriate conflict resolution strategy based on your use case
4. **Resources**: For many peer nodes, adjust `max_concurrent_syncs`

## Security Considerations

1. **Pickle Serialization**: The system uses Python's `pickle` module for serializing changes between nodes. This is safe when used within a trusted network, but should not be used with untrusted data sources.
2. **Trusted Peers**: Only add trusted nodes as peers in the synchronization network.
3. **Network Security**: When implementing network communication, ensure proper encryption and authentication.

## License

This module is part of the DictSQLite project and is provided under the MIT License.

## Support

For issues or questions, please visit the GitHub issues section of the DictSQLite repository.
