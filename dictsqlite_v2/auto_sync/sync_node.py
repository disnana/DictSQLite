"""
Sync node representation for multi-master synchronization.
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional, Set
from threading import Lock
import pickle


logger = logging.getLogger(__name__)


class SyncNode:
    """
    Represents a node in the multi-master synchronization system.
    
    Each node maintains:
    - A local database instance
    - Metadata about changes (timestamps, versions)
    - Connection state with peer nodes
    """
    
    def __init__(
        self, 
        db_instance: Any,
        node_id: Optional[str] = None,
        table_name: str = "main"
    ):
        """
        Initialize a sync node.
        
        Args:
            db_instance: The DictSQLite database instance
            node_id: Unique identifier for this node (auto-generated if not provided)
            table_name: Table name to synchronize
        """
        self.db = db_instance
        self.node_id = node_id or self._generate_node_id()
        self.table_name = table_name
        
        # Change tracking
        self._change_log: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        # Peer tracking
        self.peer_nodes: Set[str] = set()
        self.peer_last_sync: Dict[str, float] = {}
        
        # Initialize metadata table
        self._init_metadata()
        
        logger.info(f"SyncNode initialized with ID: {self.node_id}")
    
    def _generate_node_id(self) -> str:
        """Generate a unique node ID"""
        return f"node_{uuid.uuid4().hex[:8]}"
    
    def _init_metadata(self):
        """Initialize metadata tracking for synchronization"""
        # Create a metadata table to track changes
        # This is a simplified version - in production, you'd use a proper metadata schema
        self._metadata_table = f"{self.table_name}_sync_metadata"
    
    def track_change(self, key: str, value: Any, operation: str = "set"):
        """
        Track a change made to the database.
        
        Args:
            key: The key that was changed
            value: The new value
            operation: Type of operation (set, delete)
        """
        with self._lock:
            timestamp = time.time()
            self._change_log[key] = {
                'value': value,
                'timestamp': timestamp,
                'operation': operation,
                'node_id': self.node_id,
                'synced': False
            }
    
    def get_changes_since(self, timestamp: float) -> Dict[str, Dict[str, Any]]:
        """
        Get all changes since a specific timestamp.
        
        Args:
            timestamp: Get changes after this timestamp
            
        Returns:
            Dictionary of changes
        """
        with self._lock:
            return {
                key: change 
                for key, change in self._change_log.items()
                if change['timestamp'] > timestamp
            }
    
    def get_unsynced_changes(self) -> Dict[str, Dict[str, Any]]:
        """Get all changes that haven't been synced yet"""
        with self._lock:
            return {
                key: change 
                for key, change in self._change_log.items()
                if not change['synced']
            }
    
    def mark_synced(self, keys: list[str]):
        """Mark specific keys as synced"""
        with self._lock:
            for key in keys:
                if key in self._change_log:
                    self._change_log[key]['synced'] = True
    
    def apply_remote_change(self, key: str, value: Any, timestamp: float, remote_node_id: str):
        """
        Apply a change received from a remote node.
        
        Args:
            key: The key to update
            value: The new value
            timestamp: Timestamp of the change
            remote_node_id: ID of the node that made the change
        """
        with self._lock:
            # Check if we have a local change for this key
            local_change = self._change_log.get(key)
            
            if local_change:
                # There's a potential conflict - let the conflict resolver handle it
                return False, local_change
            
            # No conflict, apply the change
            if value is None:
                # Delete operation
                if key in self.db:
                    del self.db[key]
            else:
                self.db[key] = value
            
            # Track this as a synced change
            self._change_log[key] = {
                'value': value,
                'timestamp': timestamp,
                'operation': 'set' if value is not None else 'delete',
                'node_id': remote_node_id,
                'synced': True
            }
            
            return True, None
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all data from the database"""
        try:
            # Try to get all items from the database
            if hasattr(self.db, 'items'):
                return dict(self.db.items())
            elif hasattr(self.db, 'keys'):
                return {key: self.db[key] for key in self.db.keys()}
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting all data: {e}")
            return {}
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get node metadata"""
        return {
            'node_id': self.node_id,
            'table_name': self.table_name,
            'change_count': len(self._change_log),
            'unsynced_count': len(self.get_unsynced_changes()),
            'peer_count': len(self.peer_nodes)
        }
    
    def add_peer(self, peer_node_id: str):
        """Add a peer node"""
        self.peer_nodes.add(peer_node_id)
        self.peer_last_sync[peer_node_id] = 0.0
    
    def remove_peer(self, peer_node_id: str):
        """Remove a peer node"""
        self.peer_nodes.discard(peer_node_id)
        if peer_node_id in self.peer_last_sync:
            del self.peer_last_sync[peer_node_id]
    
    def update_peer_sync_time(self, peer_node_id: str, sync_time: float):
        """Update the last sync time for a peer"""
        self.peer_last_sync[peer_node_id] = sync_time
    
    def serialize_changes(self, changes: Dict[str, Dict[str, Any]]) -> bytes:
        """Serialize changes for transmission"""
        return pickle.dumps(changes)
    
    def deserialize_changes(self, data: bytes) -> Dict[str, Dict[str, Any]]:
        """Deserialize changes received from another node"""
        return pickle.loads(data)
    
    def close(self):
        """Close the sync node"""
        logger.info(f"SyncNode {self.node_id} closing")
        # Clean up resources if needed
