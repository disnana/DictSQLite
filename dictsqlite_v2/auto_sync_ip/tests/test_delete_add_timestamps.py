"""
Test for delete-then-add scenarios with timestamp management.

This test verifies that the system correctly handles cases where
data is deleted and then re-added, ensuring timestamp-based 
conflict resolution works properly.
"""

import pytest
import asyncio
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ip_config import IPSyncConfig
from sync_server import SyncServer
from sync_client import SyncClient


class MockDB(dict):
    """Mock database for testing"""
    def close(self):
        pass


@pytest.mark.asyncio
class TestDeleteThenAdd:
    """Test delete-then-add scenarios with timestamp management"""
    
    async def test_delete_then_add_newer_timestamp(self):
        """
        Test that re-adding deleted data with a newer timestamp works correctly.
        
        Scenario:
        1. Node A has key1 = "old_value" at T1
        2. Node B deletes key1 at T2 (T2 > T1)
        3. Node B re-adds key1 = "new_value" at T3 (T3 > T2)
        4. Node A syncs and should get the new value
        """
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8790)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8790")
        await client.connect()
        
        # Start receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Step 1: Client has old data
        db_client["key1"] = "old_value"
        client.track_change("key1", "old_value")
        await asyncio.sleep(0.05)
        
        # Step 2: Server deletes it
        await asyncio.sleep(0.05)
        db_server["key1"] = "temp"
        server.track_change("key1", "temp")
        del db_server["key1"]
        server.track_change("key1", None, "delete")
        await asyncio.sleep(0.05)
        
        # Step 3: Server re-adds with new value (newer timestamp)
        await asyncio.sleep(0.05)
        db_server["key1"] = "new_value"
        server.track_change("key1", "new_value", "set")
        
        # Broadcast the re-add
        changes = {"key1": server.change_log["key1"]}
        await server.broadcast_changes(changes)
        
        # Wait for sync
        await asyncio.sleep(0.3)
        
        # Client should have the new value (not deleted, not old value)
        assert "key1" in db_client
        assert db_client["key1"] == "new_value", "Re-added value should override deletion"
        
        # Verify change log shows the latest operation
        assert client.change_log["key1"]["operation"] == "set"
        assert client.change_log["key1"]["value"] == "new_value"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
    
    async def test_old_add_after_newer_delete_ignored(self):
        """
        Test that adding data with an older timestamp after deletion is ignored.
        
        Scenario:
        1. Node A deletes key1 at T2
        2. Node B has key1 = "old_value" from T1 (T1 < T2)
        3. Node B tries to sync its old data
        4. The deletion should win (newer timestamp)
        """
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8791)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8791")
        await client.connect()
        
        # Start receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Server has deletion with newer timestamp
        await asyncio.sleep(0.1)
        server.track_change("key1", None, "delete")
        
        # Client has old data with older timestamp
        # Simulate old data by manually creating a change with old timestamp
        old_timestamp = time.time() - 10  # 10 seconds ago
        db_client["key1"] = "old_value"
        client.change_log["key1"] = {
            'value': "old_value",
            'timestamp': old_timestamp,
            'operation': 'set',
            'source_node': client.node_id
        }
        
        # Client requests recovery
        await client.request_missing_data()
        
        # Wait for sync
        await asyncio.sleep(0.3)
        
        # Deletion should win (newer timestamp)
        assert "key1" not in db_client, "Newer deletion should override old data"
        assert client.change_log["key1"]["operation"] == "delete"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
    
    async def test_complex_delete_add_sequence(self):
        """
        Test a complex sequence: add -> delete -> add -> delete -> add
        
        Verifies that timestamp ordering maintains correct final state.
        """
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8792)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8792")
        await client.connect()
        
        # Start receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Sequence on server:
        # T1: Add value1
        db_server["key1"] = "value1"
        server.track_change("key1", "value1", "set")
        await asyncio.sleep(0.05)
        
        # T2: Delete
        del db_server["key1"]
        server.track_change("key1", None, "delete")
        await asyncio.sleep(0.05)
        
        # T3: Add value2
        db_server["key1"] = "value2"
        server.track_change("key1", "value2", "set")
        await asyncio.sleep(0.05)
        
        # T4: Delete
        del db_server["key1"]
        server.track_change("key1", None, "delete")
        await asyncio.sleep(0.05)
        
        # T5: Add value3 (final state)
        db_server["key1"] = "value3"
        server.track_change("key1", "value3", "set")
        
        # Client requests all data
        await client.request_missing_data()
        
        # Wait for sync
        await asyncio.sleep(0.3)
        
        # Client should have the final state
        assert "key1" in db_client
        assert db_client["key1"] == "value3", "Final re-added value should be present"
        assert client.change_log["key1"]["operation"] == "set"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
    
    async def test_concurrent_delete_and_add_timestamp_resolution(self):
        """
        Test concurrent operations on different nodes resolved by timestamp.
        
        Scenario:
        1. Node A adds key1 = "from_A" at T1
        2. Node B deletes key1 at T2 (T2 > T1)
        3. Both sync - deletion should win
        """
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8793)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8793")
        await client.connect()
        
        # Start receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Client adds data (older)
        db_client["key1"] = "from_client"
        client.track_change("key1", "from_client")
        await asyncio.sleep(0.1)
        
        # Server has deletion (newer timestamp)
        await asyncio.sleep(0.05)
        server.track_change("key1", None, "delete")
        
        # Sync both ways
        await client.sync_changes()
        await asyncio.sleep(0.1)
        await client.request_missing_data()
        await asyncio.sleep(0.3)
        
        # Both should have deletion (newer timestamp wins)
        assert "key1" not in db_client
        assert "key1" not in db_server
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
