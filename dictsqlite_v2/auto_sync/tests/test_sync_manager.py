"""
Tests for the SyncManager class.
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_manager import SyncManager
from sync_node import SyncNode
from config import SyncConfig, SyncMode


class MockDB(dict):
    """Mock database for testing"""
    def close(self):
        pass


class TestSyncManager:
    """Test cases for SyncManager"""
    
    def test_initialization(self):
        """Test sync manager initialization"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        config = SyncConfig()
        
        manager = SyncManager(node, config)
        
        assert manager.local_node is node
        assert manager.config is config
        assert manager._running is False
    
    def test_add_peer(self):
        """Test adding a peer node"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        manager = SyncManager(node1, SyncConfig())
        manager.add_peer(node2)
        
        assert node2.node_id in manager.peer_nodes
        assert node2.node_id in node1.peer_nodes
    
    def test_remove_peer(self):
        """Test removing a peer node"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        manager = SyncManager(node1, SyncConfig())
        manager.add_peer(node2)
        manager.remove_peer(node2.node_id)
        
        assert node2.node_id not in manager.peer_nodes
        assert node2.node_id not in node1.peer_nodes
    
    def test_start_stop(self):
        """Test starting and stopping sync manager"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        config = SyncConfig(sync_interval=1.0)
        
        manager = SyncManager(node, config)
        
        manager.start()
        assert manager._running is True
        
        time.sleep(0.1)
        
        manager.stop()
        assert manager._running is False
    
    def test_force_sync(self):
        """Test forcing immediate sync"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        manager = SyncManager(node1, SyncConfig())
        manager.add_peer(node2)
        
        # Add some changes
        db1["key1"] = "value1"
        node1.track_change("key1", "value1")
        
        # Force sync
        manager.force_sync()
        
        # Check stats
        stats = manager.get_stats()
        assert stats['total_syncs'] > 0
    
    def test_get_stats(self):
        """Test getting sync statistics"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        manager = SyncManager(node, SyncConfig())
        
        stats = manager.get_stats()
        
        assert 'total_syncs' in stats
        assert 'successful_syncs' in stats
        assert 'failed_syncs' in stats
        assert 'conflicts_resolved' in stats
        assert 'items_synced' in stats
        assert 'peer_count' in stats
        assert 'local_node_id' in stats
        assert stats['local_node_id'] == "test_node"
    
    def test_get_node_info(self):
        """Test getting node information"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        manager = SyncManager(node, SyncConfig())
        
        info = manager.get_node_info()
        
        assert info['node_id'] == "test_node"
        assert 'table_name' in info
        assert 'change_count' in info
    
    def test_sync_with_peer_push(self):
        """Test syncing with peer in PUSH mode"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.PUSH)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Add data to node1
        db1["key1"] = "value1"
        node1.track_change("key1", "value1")
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Check that data was pushed to node2
        assert db2.get("key1") == "value1"
    
    def test_sync_with_peer_pull(self):
        """Test syncing with peer in PULL mode"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.PULL)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Add data to node2
        db2["key1"] = "value1"
        node2.track_change("key1", "value1")
        
        # Sync (pull from node2)
        manager.sync_with_peer(node2)
        
        # Check that data was pulled to node1
        assert db1.get("key1") == "value1"
    
    def test_sync_with_peer_bidirectional(self):
        """Test syncing with peer in BIDIRECTIONAL mode"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.BIDIRECTIONAL)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Add different data to both nodes
        db1["key1"] = "value1"
        node1.track_change("key1", "value1")
        
        db2["key2"] = "value2"
        node2.track_change("key2", "value2")
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Both nodes should have both keys
        assert db1.get("key1") == "value1"
        assert db2.get("key2") == "value2"
    
    def test_auto_recovery_enabled(self):
        """Test that auto recovery is enabled when configured"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        config = SyncConfig(enable_auto_recovery=True)
        
        manager = SyncManager(node, config)
        manager.start()
        
        assert manager.recovery_manager._running is True
        
        manager.stop()
    
    def test_auto_recovery_disabled(self):
        """Test that auto recovery can be disabled"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        config = SyncConfig(enable_auto_recovery=False)
        
        manager = SyncManager(node, config)
        manager.start()
        
        assert manager.recovery_manager._running is False
        
        manager.stop()
    
    def test_close(self):
        """Test closing sync manager"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        manager = SyncManager(node, SyncConfig())
        
        manager.start()
        time.sleep(0.1)
        
        manager.close()
        
        assert manager._running is False
