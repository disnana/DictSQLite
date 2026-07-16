"""
Tests for the SyncNode class.
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_node import SyncNode


class MockDB(dict):
    """Mock database for testing"""
    def __init__(self):
        super().__init__()
    
    def close(self):
        pass


class TestSyncNode:
    """Test cases for SyncNode"""
    
    def test_node_initialization(self):
        """Test node initialization"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        assert node.node_id == "test_node"
        assert node.table_name == "main"
        assert node.db is db
    
    def test_auto_generated_node_id(self):
        """Test auto-generated node ID"""
        db = MockDB()
        node = SyncNode(db)
        
        assert node.node_id.startswith("node_")
        assert len(node.node_id) > 5
    
    def test_track_change(self):
        """Test tracking changes"""
        db = MockDB()
        node = SyncNode(db)
        
        node.track_change("key1", "value1")
        
        assert "key1" in node._change_log
        assert node._change_log["key1"]["value"] == "value1"
        assert node._change_log["key1"]["operation"] == "set"
        assert node._change_log["key1"]["synced"] is False
    
    def test_track_multiple_changes(self):
        """Test tracking multiple changes"""
        db = MockDB()
        node = SyncNode(db)
        
        node.track_change("key1", "value1")
        node.track_change("key2", "value2")
        node.track_change("key3", "value3")
        
        assert len(node._change_log) == 3
    
    def test_get_unsynced_changes(self):
        """Test getting unsynced changes"""
        db = MockDB()
        node = SyncNode(db)
        
        node.track_change("key1", "value1")
        node.track_change("key2", "value2")
        
        unsynced = node.get_unsynced_changes()
        
        assert len(unsynced) == 2
        assert "key1" in unsynced
        assert "key2" in unsynced
    
    def test_mark_synced(self):
        """Test marking changes as synced"""
        db = MockDB()
        node = SyncNode(db)
        
        node.track_change("key1", "value1")
        node.track_change("key2", "value2")
        
        node.mark_synced(["key1"])
        
        unsynced = node.get_unsynced_changes()
        assert len(unsynced) == 1
        assert "key2" in unsynced
        assert "key1" not in unsynced
    
    def test_get_changes_since(self):
        """Test getting changes since a timestamp"""
        db = MockDB()
        node = SyncNode(db)
        
        # First change
        node.track_change("key1", "value1")
        time.sleep(0.1)
        
        # Record timestamp
        cutoff_time = time.time()
        time.sleep(0.1)
        
        # Second change
        node.track_change("key2", "value2")
        
        changes = node.get_changes_since(cutoff_time)
        
        assert len(changes) == 1
        assert "key2" in changes
        assert "key1" not in changes
    
    def test_apply_remote_change_no_conflict(self):
        """Test applying remote change with no conflict"""
        db = MockDB()
        node = SyncNode(db)
        
        success, conflict = node.apply_remote_change(
            "key1",
            "remote_value",
            time.time(),
            "remote_node"
        )
        
        assert success is True
        assert conflict is None
        assert db["key1"] == "remote_value"
    
    def test_apply_remote_change_with_conflict(self):
        """Test applying remote change with conflict"""
        db = MockDB()
        node = SyncNode(db)
        
        # Create a local change
        node.track_change("key1", "local_value")
        
        # Try to apply remote change
        success, conflict = node.apply_remote_change(
            "key1",
            "remote_value",
            time.time(),
            "remote_node"
        )
        
        assert success is False
        assert conflict is not None
        assert conflict["value"] == "local_value"
    
    def test_apply_remote_delete(self):
        """Test applying remote delete operation"""
        db = MockDB()
        node = SyncNode(db)
        
        # Add a key first
        db["key1"] = "value1"
        
        # Apply remote delete (value=None means delete)
        success, conflict = node.apply_remote_change(
            "key1",
            None,
            time.time(),
            "remote_node"
        )
        
        assert success is True
        assert "key1" not in db
    
    def test_get_all_data(self):
        """Test getting all data"""
        db = MockDB()
        node = SyncNode(db)
        
        db["key1"] = "value1"
        db["key2"] = "value2"
        
        data = node.get_all_data()
        
        assert len(data) == 2
        assert data["key1"] == "value1"
        assert data["key2"] == "value2"
    
    def test_get_metadata(self):
        """Test getting node metadata"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        node.track_change("key1", "value1")
        node.track_change("key2", "value2")
        
        metadata = node.get_metadata()
        
        assert metadata["node_id"] == "test_node"
        assert metadata["table_name"] == "main"
        assert metadata["change_count"] == 2
        assert metadata["unsynced_count"] == 2
        assert metadata["peer_count"] == 0
    
    def test_add_peer(self):
        """Test adding a peer"""
        db = MockDB()
        node = SyncNode(db)
        
        node.add_peer("peer1")
        
        assert "peer1" in node.peer_nodes
        assert "peer1" in node.peer_last_sync
        assert node.peer_last_sync["peer1"] == 0.0
    
    def test_remove_peer(self):
        """Test removing a peer"""
        db = MockDB()
        node = SyncNode(db)
        
        node.add_peer("peer1")
        node.remove_peer("peer1")
        
        assert "peer1" not in node.peer_nodes
        assert "peer1" not in node.peer_last_sync
    
    def test_update_peer_sync_time(self):
        """Test updating peer sync time"""
        db = MockDB()
        node = SyncNode(db)
        
        node.add_peer("peer1")
        
        sync_time = time.time()
        node.update_peer_sync_time("peer1", sync_time)
        
        assert node.peer_last_sync["peer1"] == sync_time
    
    def test_serialize_deserialize_changes(self):
        """Test serialization and deserialization of changes"""
        db = MockDB()
        node = SyncNode(db)
        
        changes = {
            "key1": {
                "value": "value1",
                "timestamp": 1000.0,
                "operation": "set",
                "node_id": "node1",
                "synced": False
            }
        }
        
        # Serialize
        serialized = node.serialize_changes(changes)
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = node.deserialize_changes(serialized)
        assert deserialized == changes
