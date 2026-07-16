"""
Main synchronization manager for multi-master replication.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from threading import Thread, Event, Lock

# Support both relative and absolute imports
try:
    from .sync_node import SyncNode
    from .conflict_resolver import ConflictResolver, ConflictResolutionStrategy
    from .recovery_manager import RecoveryManager, RecoveryState
    from .config import SyncConfig, SyncMode
except ImportError:
    from sync_node import SyncNode
    from conflict_resolver import ConflictResolver, ConflictResolutionStrategy
    from recovery_manager import RecoveryManager, RecoveryState
    from config import SyncConfig, SyncMode


logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages synchronization between multiple DictSQLite database instances.
    
    Features:
    - Automatic synchronization based on configured interval
    - Multi-master replication support
    - Conflict resolution
    - Automatic recovery from failures
    - Peer discovery and management
    """
    
    def __init__(
        self,
        local_node: SyncNode,
        config: Optional[SyncConfig] = None
    ):
        """
        Initialize sync manager.
        
        Args:
            local_node: The local SyncNode to manage
            config: Synchronization configuration
        """
        self.local_node = local_node
        self.config = config or SyncConfig()
        self.config.validate()
        
        # Peer nodes
        self.peer_nodes: Dict[str, SyncNode] = {}
        self._peer_lock = Lock()
        
        # Conflict resolution
        strategy = ConflictResolutionStrategy[self.config.conflict_strategy.upper()]
        self.conflict_resolver = ConflictResolver(strategy)
        
        # Recovery manager
        self.recovery_manager = RecoveryManager(
            max_retries=self.config.max_recovery_retries,
            retry_interval=self.config.recovery_retry_interval
        )
        
        # Add recovery callback
        self.recovery_manager.add_recovery_callback(self._handle_recovery)
        
        # Synchronization state
        self._running = False
        self._sync_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Statistics
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'conflicts_resolved': 0,
            'items_synced': 0,
            'last_sync_time': 0.0
        }
        self._stats_lock = Lock()
        
        logger.info(f"SyncManager initialized for node {local_node.node_id}")
    
    def add_peer(self, peer_node: SyncNode):
        """
        Add a peer node for synchronization.
        
        Args:
            peer_node: SyncNode representing the peer
        """
        with self._peer_lock:
            self.peer_nodes[peer_node.node_id] = peer_node
            self.local_node.add_peer(peer_node.node_id)
            peer_node.add_peer(self.local_node.node_id)
        
        logger.info(f"Peer node added: {peer_node.node_id}")
    
    def remove_peer(self, peer_node_id: str):
        """
        Remove a peer node.
        
        Args:
            peer_node_id: ID of the peer to remove
        """
        with self._peer_lock:
            if peer_node_id in self.peer_nodes:
                del self.peer_nodes[peer_node_id]
                self.local_node.remove_peer(peer_node_id)
        
        logger.info(f"Peer node removed: {peer_node_id}")
    
    def start(self):
        """Start automatic synchronization"""
        if self._running:
            logger.warning("SyncManager already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        # Start recovery monitoring if enabled
        if self.config.enable_auto_recovery:
            self.recovery_manager.start_monitoring()
        
        # Start sync thread
        self._sync_thread = Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        
        logger.info("SyncManager started")
    
    def stop(self):
        """Stop automatic synchronization"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        # Stop recovery manager
        if self.config.enable_auto_recovery:
            self.recovery_manager.stop_monitoring()
        
        # Wait for sync thread to finish
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)
        
        logger.info("SyncManager stopped")
    
    def _sync_loop(self):
        """Main synchronization loop"""
        while self._running and not self._stop_event.is_set():
            try:
                self.sync_all_peers()
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                if self.config.enable_auto_recovery:
                    self.recovery_manager.record_failure("sync_loop", e)
            
            # Wait for next sync interval
            self._stop_event.wait(self.config.sync_interval)
    
    def sync_all_peers(self):
        """Synchronize with all peer nodes"""
        with self._peer_lock:
            peers = list(self.peer_nodes.values())
        
        for peer in peers:
            try:
                self.sync_with_peer(peer)
            except Exception as e:
                logger.error(f"Failed to sync with peer {peer.node_id}: {e}")
                if self.config.enable_auto_recovery:
                    self.recovery_manager.record_failure(
                        f"sync_peer_{peer.node_id}", 
                        e,
                        {'peer_id': peer.node_id}
                    )
    
    def sync_with_peer(self, peer_node: SyncNode):
        """
        Synchronize with a specific peer node.
        
        Args:
            peer_node: The peer node to sync with
        """
        with self._stats_lock:
            self.stats['total_syncs'] += 1
        
        try:
            # Determine sync mode
            if self.config.sync_mode in [SyncMode.PUSH, SyncMode.BIDIRECTIONAL]:
                self._push_changes_to_peer(peer_node)
            
            if self.config.sync_mode in [SyncMode.PULL, SyncMode.BIDIRECTIONAL]:
                self._pull_changes_from_peer(peer_node)
            
            # Update sync time
            sync_time = time.time()
            self.local_node.update_peer_sync_time(peer_node.node_id, sync_time)
            
            with self._stats_lock:
                self.stats['successful_syncs'] += 1
                self.stats['last_sync_time'] = sync_time
            
            logger.debug(f"Successfully synced with peer {peer_node.node_id}")
            
        except Exception as e:
            with self._stats_lock:
                self.stats['failed_syncs'] += 1
            raise
    
    def _push_changes_to_peer(self, peer_node: SyncNode):
        """Push local changes to a peer node"""
        # Get unsynced changes
        changes = self.local_node.get_unsynced_changes()
        
        if not changes:
            return
        
        # Apply changes to peer in batches
        keys_to_mark_synced = []
        items_synced = 0
        
        for key, change in changes.items():
            try:
                success, conflict = peer_node.apply_remote_change(
                    key,
                    change['value'],
                    change['timestamp'],
                    self.local_node.node_id
                )
                
                if success:
                    keys_to_mark_synced.append(key)
                    items_synced += 1
                elif conflict:
                    # Handle conflict
                    self._handle_conflict(key, change, conflict, peer_node)
                
            except Exception as e:
                logger.error(f"Failed to push change for key {key}: {e}")
        
        # Mark as synced
        if keys_to_mark_synced:
            self.local_node.mark_synced(keys_to_mark_synced)
            
            with self._stats_lock:
                self.stats['items_synced'] += items_synced
    
    def _pull_changes_from_peer(self, peer_node: SyncNode):
        """Pull changes from a peer node"""
        # Get last sync time for this peer
        last_sync = self.local_node.peer_last_sync.get(peer_node.node_id, 0.0)
        
        # Get changes since last sync
        changes = peer_node.get_changes_since(last_sync)
        
        if not changes:
            return
        
        items_synced = 0
        
        for key, change in changes.items():
            try:
                success, conflict = self.local_node.apply_remote_change(
                    key,
                    change['value'],
                    change['timestamp'],
                    peer_node.node_id
                )
                
                if success:
                    items_synced += 1
                elif conflict:
                    # Handle conflict
                    self._handle_conflict(key, change, conflict, peer_node)
                
            except Exception as e:
                logger.error(f"Failed to pull change for key {key}: {e}")
        
        if items_synced > 0:
            with self._stats_lock:
                self.stats['items_synced'] += items_synced
    
    def _handle_conflict(
        self, 
        key: str, 
        remote_change: Dict[str, Any],
        local_change: Dict[str, Any],
        peer_node: SyncNode
    ):
        """
        Handle a synchronization conflict.
        
        Args:
            key: The key with conflicting values
            remote_change: Change from remote node
            local_change: Change from local node
            peer_node: The peer node involved in the conflict
        """
        try:
            resolved_value, reason = self.conflict_resolver.resolve_conflict(
                key,
                local_change['value'],
                local_change['timestamp'],
                remote_change['value'],
                remote_change['timestamp'],
                self.local_node.node_id,
                peer_node.node_id
            )
            
            # Apply resolved value
            self.local_node.db[key] = resolved_value
            
            # Track conflict resolution
            self.local_node.track_change(key, resolved_value, "conflict_resolved")
            
            with self._stats_lock:
                self.stats['conflicts_resolved'] += 1
            
            logger.info(f"Conflict resolved for key {key}: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict for key {key}: {e}")
            if self.config.enable_auto_recovery:
                self.recovery_manager.record_failure(
                    "conflict_resolution",
                    e,
                    {'key': key, 'peer_id': peer_node.node_id}
                )
    
    def _handle_recovery(self, component: str, error: Exception):
        """
        Handle recovery callback.
        
        Args:
            component: Component being recovered
            error: The error that triggered recovery
        """
        logger.info(f"Handling recovery for {component}")
        
        # Attempt to restart sync if it was the sync loop
        if component == "sync_loop" and not self._running:
            try:
                self.start()
                logger.info("Sync loop restarted successfully")
            except Exception as e:
                logger.error(f"Failed to restart sync loop: {e}")
                raise
    
    def force_sync(self):
        """Force an immediate synchronization with all peers"""
        logger.info("Forcing immediate sync")
        self.sync_all_peers()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        with self._stats_lock:
            stats = self.stats.copy()
        
        # Add additional stats
        stats['peer_count'] = len(self.peer_nodes)
        stats['local_node_id'] = self.local_node.node_id
        stats['recovery_state'] = self.recovery_manager.get_state().value
        stats['is_running'] = self._running
        
        return stats
    
    def get_node_info(self) -> Dict[str, Any]:
        """Get information about the local node"""
        return self.local_node.get_metadata()
    
    def close(self):
        """Close the sync manager and clean up resources"""
        logger.info("Closing SyncManager")
        self.stop()
        self.local_node.close()
