"""
Comprehensive CRUD operation tests for the auto-sync system.

Tests all Create, Read, Update, Delete operations in various scenarios.
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


class TestCRUDOperations:
    """Comprehensive CRUD operation tests"""
    
    def test_create_single_item(self):
        """Test creating a single item"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Create
        db["key1"] = "value1"
        node.track_change("key1", "value1")
        
        # Verify
        assert "key1" in db
        assert db["key1"] == "value1"
        assert len(node.get_unsynced_changes()) == 1
    
    def test_create_multiple_items(self):
        """Test creating multiple items"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Create multiple
        for i in range(10):
            key = f"key{i}"
            value = f"value{i}"
            db[key] = value
            node.track_change(key, value)
        
        # Verify
        assert len(db) == 10
        assert len(node.get_unsynced_changes()) == 10
    
    def test_read_existing_item(self):
        """Test reading an existing item"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        db["key1"] = "value1"
        
        # Read
        value = db.get("key1")
        assert value == "value1"
    
    def test_read_nonexistent_item(self):
        """Test reading a non-existent item"""
        db = MockDB()
        
        # Read non-existent
        value = db.get("nonexistent")
        assert value is None
    
    def test_update_existing_item(self):
        """Test updating an existing item"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Create
        db["key1"] = "value1"
        node.track_change("key1", "value1")
        
        # Update
        db["key1"] = "updated_value"
        node.track_change("key1", "updated_value")
        
        # Verify
        assert db["key1"] == "updated_value"
        changes = node.get_unsynced_changes()
        assert changes["key1"]["value"] == "updated_value"
    
    def test_update_multiple_times(self):
        """Test updating the same item multiple times"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Create
        db["key1"] = "value1"
        node.track_change("key1", "value1")
        
        # Update multiple times
        for i in range(5):
            db["key1"] = f"value{i}"
            node.track_change("key1", f"value{i}")
        
        # Verify last value
        assert db["key1"] == "value4"
    
    def test_delete_existing_item(self):
        """Test deleting an existing item"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Create
        db["key1"] = "value1"
        node.track_change("key1", "value1")
        
        # Delete
        del db["key1"]
        node.track_change("key1", None, "delete")
        
        # Verify
        assert "key1" not in db
        changes = node.get_unsynced_changes()
        assert changes["key1"]["operation"] == "delete"
    
    def test_delete_nonexistent_item(self):
        """Test deleting a non-existent item"""
        db = MockDB()
        
        # Try to delete non-existent (should raise KeyError)
        with pytest.raises(KeyError):
            del db["nonexistent"]
    
    def test_crud_cycle(self):
        """Test complete CRUD cycle"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Create
        db["key1"] = "value1"
        node.track_change("key1", "value1")
        assert db["key1"] == "value1"
        
        # Read
        value = db.get("key1")
        assert value == "value1"
        
        # Update
        db["key1"] = "updated_value"
        node.track_change("key1", "updated_value")
        assert db["key1"] == "updated_value"
        
        # Delete
        del db["key1"]
        node.track_change("key1", None, "delete")
        assert "key1" not in db


class TestSyncedCRUDOperations:
    """Test CRUD operations across synced nodes"""
    
    def test_create_syncs_to_peer(self):
        """Test that creating an item syncs to peer"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.PUSH)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Create on node1
        db1["key1"] = "value1"
        node1.track_change("key1", "value1")
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Verify on node2
        assert db2.get("key1") == "value1"
    
    def test_update_syncs_to_peer(self):
        """Test that updating an item syncs to peer"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.PUSH)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Create on both
        db1["key1"] = "value1"
        db2["key1"] = "value1"
        
        # Update on node1
        db1["key1"] = "updated_value"
        node1.track_change("key1", "updated_value")
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Verify update on node2
        assert db2.get("key1") == "updated_value"
    
    def test_delete_syncs_to_peer(self):
        """Test that deleting an item syncs to peer"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.PUSH)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Create on both
        db1["key1"] = "value1"
        db2["key1"] = "value1"
        
        # Delete on node1
        del db1["key1"]
        node1.track_change("key1", None, "delete")
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Verify deletion on node2
        assert "key1" not in db2
    
    def test_bidirectional_crud_sync(self):
        """Test bidirectional CRUD synchronization"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.BIDIRECTIONAL)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Create on node1
        db1["key1"] = "value1"
        node1.track_change("key1", "value1")
        
        # Create on node2
        db2["key2"] = "value2"
        node2.track_change("key2", "value2")
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Verify both nodes have both keys
        assert db1.get("key1") == "value1"
        assert db1.get("key2") == "value2"
        assert db2.get("key1") == "value1"
        assert db2.get("key2") == "value2"
    
    def test_multiple_crud_operations_sync(self):
        """Test syncing multiple CRUD operations"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(sync_mode=SyncMode.PUSH)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Multiple operations on node1
        db1["key1"] = "value1"
        node1.track_change("key1", "value1")
        
        db1["key2"] = "value2"
        node1.track_change("key2", "value2")
        
        db1["key1"] = "updated_value1"
        node1.track_change("key1", "updated_value1")
        
        db1["key3"] = "value3"
        node1.track_change("key3", "value3")
        
        del db1["key2"]
        node1.track_change("key2", None, "delete")
        
        # Sync all
        manager.sync_with_peer(node2)
        
        # Verify final state on node2
        assert db2.get("key1") == "updated_value1"
        assert "key2" not in db2
        assert db2.get("key3") == "value3"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_database_sync(self):
        """Test syncing with empty database"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig()
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Sync empty databases
        manager.sync_with_peer(node2)
        
        assert len(db1) == 0
        assert len(db2) == 0
    
    def test_large_batch_sync(self):
        """Test syncing a large batch of items"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        config = SyncConfig(batch_size=50)
        manager = SyncManager(node1, config)
        manager.add_peer(node2)
        
        # Create 100 items
        for i in range(100):
            key = f"key{i}"
            value = f"value{i}"
            db1[key] = value
            node1.track_change(key, value)
        
        # Sync
        manager.sync_with_peer(node2)
        
        # Verify all items synced
        assert len(db2) == 100
        for i in range(100):
            assert db2.get(f"key{i}") == f"value{i}"
    
    def test_special_characters_in_keys(self):
        """Test handling of special characters in keys"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        special_keys = [
            "key with spaces",
            "key:with:colons",
            "key/with/slashes",
            "key@with#special$chars",
            "日本語キー",
            "emoji_key_🎉"
        ]
        
        for key in special_keys:
            db[key] = f"value_for_{key}"
            node.track_change(key, f"value_for_{key}")
        
        # Verify all stored
        assert len(db) == len(special_keys)
        for key in special_keys:
            assert key in db
    
    def test_special_values(self):
        """Test handling of special values"""
        db = MockDB()
        node = SyncNode(db, node_id="test_node")
        
        # Test various types
        test_values = [
            ("int_key", 42),
            ("float_key", 3.14),
            ("bool_key", True),
            ("none_key", None),
            ("list_key", [1, 2, 3]),
            ("dict_key", {"nested": "dict"}),
            ("tuple_key", (1, 2, 3)),
            ("empty_string", ""),
            ("unicode_key", "こんにちは世界"),
        ]
        
        for key, value in test_values:
            db[key] = value
            node.track_change(key, value)
        
        # Verify all stored correctly
        for key, value in test_values:
            assert db[key] == value
    
    def test_concurrent_modifications(self):
        """Test handling of concurrent modifications"""
        db1 = MockDB()
        db2 = MockDB()
        node1 = SyncNode(db1, node_id="node1")
        node2 = SyncNode(db2, node_id="node2")
        
        # Both modify the same key
        db1["shared_key"] = "value_from_node1"
        node1.track_change("shared_key", "value_from_node1")
        
        time.sleep(0.01)  # Ensure different timestamp
        
        db2["shared_key"] = "value_from_node2"
        node2.track_change("shared_key", "value_from_node2")
        
        # Try to apply node2's change to node1
        success, conflict = node1.apply_remote_change(
            "shared_key",
            "value_from_node2",
            time.time(),
            "node2"
        )
        
        # Should detect conflict
        assert success is False
        assert conflict is not None
