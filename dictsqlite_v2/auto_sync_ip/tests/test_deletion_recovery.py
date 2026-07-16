"""
Test for deletion synchronization during recovery.

This test verifies that deleted items are properly handled during
recovery and don't incorrectly reappear.
"""

import pytest
import asyncio
import sys
import os

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
class TestDeletionRecovery:
    """Test deletion synchronization during recovery"""
    
    async def test_deletion_not_restored_on_recovery(self):
        """
        Test that deleted items are not restored during recovery.
        
        Scenario:
        1. Node A and Node B both have key1
        2. Node A deletes key1
        3. Connection is lost before sync
        4. Node B requests missing data for recovery
        5. Node B should receive the deletion and remove key1
        """
        db_server = MockDB()
        db_client = MockDB()
        
        # Both have the same initial data
        db_server["key1"] = "value1"
        db_client["key1"] = "value1"
        
        config_server = IPSyncConfig(port=8780)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8780")
        await client.connect()
        
        # Start client receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Server deletes key1
        del db_server["key1"]
        server.track_change("key1", None, "delete")
        
        # Wait a moment for tracking
        await asyncio.sleep(0.1)
        
        # Client requests missing data (recovery scenario)
        await client.request_missing_data()
        
        # Wait for data to be received
        await asyncio.sleep(0.3)
        
        # Verify that key1 was deleted on client too
        assert "key1" not in db_client, "Deleted key should not exist on client after recovery"
        
        # Verify change log shows deletion
        assert "key1" in client.change_log
        assert client.change_log["key1"]["operation"] == "delete"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
    
    async def test_deletion_wins_over_old_data(self):
        """
        Test that a deletion with newer timestamp wins over old data.
        
        Scenario:
        1. Node A has key1 with timestamp T1
        2. Node B deletes key1 with timestamp T2 (T2 > T1)
        3. Node A requests recovery
        4. Node A should receive deletion and remove key1
        """
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8781)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8781")
        await client.connect()
        
        # Start receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Client has old data
        db_client["key1"] = "old_value"
        client.track_change("key1", "old_value")
        await asyncio.sleep(0.05)
        
        # Server also had it but deletes it (newer timestamp)
        await asyncio.sleep(0.05)
        db_server["key1"] = "temp"  # Add it first
        server.track_change("key1", "temp")
        del db_server["key1"]  # Then delete
        server.track_change("key1", None, "delete")
        
        # Client requests recovery
        await client.request_missing_data()
        
        # Wait for sync
        await asyncio.sleep(0.3)
        
        # Deletion should win
        assert "key1" not in db_client, "Newer deletion should override old data"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
    
    async def test_recovery_includes_both_additions_and_deletions(self):
        """
        Test that recovery correctly handles both additions and deletions.
        
        Scenario:
        1. Server has key1, key2, and deleted key3
        2. Client is empty and requests recovery
        3. Client should get key1, key2, and deletion of key3
        """
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8782)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Server has data
        db_server["key1"] = "value1"
        server.track_change("key1", "value1")
        
        db_server["key2"] = "value2"
        server.track_change("key2", "value2")
        
        # Server had key3 but deleted it
        server.track_change("key3", None, "delete")
        
        # Client starts empty but might have had key3 before
        db_client["key3"] = "old_value3"
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8782")
        await client.connect()
        
        # Start receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Client requests recovery
        await client.request_missing_data()
        
        # Wait for sync
        await asyncio.sleep(0.3)
        
        # Verify results
        assert "key1" in db_client
        assert db_client["key1"] == "value1"
        
        assert "key2" in db_client
        assert db_client["key2"] == "value2"
        
        assert "key3" not in db_client, "Deleted key3 should not exist"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
