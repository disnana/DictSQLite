"""
Comprehensive integration tests for IP-based auto-sync system

Tests all aspects of the WebSocket-based synchronization including:
- Cross-network synchronization
- Multi-master scenarios
- Automatic recovery
- Deletion handling
- Performance under load
"""

import pytest
import asyncio
import tempfile
import time
import sys
from pathlib import Path

# Add auto_sync_ip to path
auto_sync_ip_path = Path(__file__).parent.parent
if str(auto_sync_ip_path) not in sys.path:
    sys.path.insert(0, str(auto_sync_ip_path))

from ip_config import IPSyncConfig
from sync_server import SyncServer
from sync_client import SyncClient
from ip_sync_manager import IPSyncManager
from recovery import AutoRecovery


class TestIPSyncComprehensive:
    """Comprehensive tests for IP-based synchronization"""
    
    @pytest.mark.asyncio
    async def test_basic_network_sync(self):
        """Test basic synchronization over network"""
        db_server = {}
        db_client = {}
        
        config_server = IPSyncConfig(host="127.0.0.1", port=18765)
        config_client = IPSyncConfig(
            host="127.0.0.1",
            port=18766,
            peer_addresses=["ws://127.0.0.1:18765"]
        )
        
        server = SyncServer(db_server, config_server)
        client = SyncClient(db_client, config_client)
        
        # Start server
        await server.start()
        
        try:
            # Connect client
            await client.connect()
            
            # Add data on server
            db_server["test_key"] = "test_value"
            server.track_change("test_key", "test_value")
            
            # Wait for sync
            await asyncio.sleep(0.3)
            
            # Verify sync
            assert db_client.get("test_key") == "test_value"
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_bidirectional_network_sync(self):
        """Test bidirectional synchronization"""
        db1 = {}
        db2 = {}
        
        config1 = IPSyncConfig(
            host="127.0.0.1",
            port=18770,
            peer_addresses=["ws://127.0.0.1:18771"]
        )
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18771,
            peer_addresses=["ws://127.0.0.1:18770"]
        )
        
        manager1 = IPSyncManager(db1, config1)
        manager2 = IPSyncManager(db2, config2)
        
        await manager1.start(enable_server=True, connect_to_peers=True)
        await manager2.start(enable_server=True, connect_to_peers=True)
        
        try:
            # Wait for connections
            await asyncio.sleep(0.3)
            
            # Add data on both sides
            db1["from_db1"] = "value1"
            manager1.track_change("from_db1", "value1")
            
            db2["from_db2"] = "value2"
            manager2.track_change("from_db2", "value2")
            
            # Wait for sync
            await asyncio.sleep(0.5)
            
            # Both should have both keys
            assert db1.get("from_db2") == "value2"
            assert db2.get("from_db1") == "value1"
        finally:
            await manager1.stop()
            await manager2.stop()
    
    @pytest.mark.asyncio
    async def test_three_node_mesh(self):
        """Test 3-node mesh topology"""
        db1, db2, db3 = {}, {}, {}
        
        config1 = IPSyncConfig(
            host="127.0.0.1",
            port=18780,
            peer_addresses=["ws://127.0.0.1:18781", "ws://127.0.0.1:18782"]
        )
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18781,
            peer_addresses=["ws://127.0.0.1:18780", "ws://127.0.0.1:18782"]
        )
        config3 = IPSyncConfig(
            host="127.0.0.1",
            port=18782,
            peer_addresses=["ws://127.0.0.1:18780", "ws://127.0.0.1:18781"]
        )
        
        mgr1 = IPSyncManager(db1, config1)
        mgr2 = IPSyncManager(db2, config2)
        mgr3 = IPSyncManager(db3, config3)
        
        await mgr1.start(enable_server=True, connect_to_peers=True)
        await mgr2.start(enable_server=True, connect_to_peers=True)
        await mgr3.start(enable_server=True, connect_to_peers=True)
        
        try:
            # Wait for all connections
            await asyncio.sleep(0.5)
            
            # Add data on each node
            db1["node1_data"] = "data1"
            mgr1.track_change("node1_data", "data1")
            
            db2["node2_data"] = "data2"
            mgr2.track_change("node2_data", "data2")
            
            db3["node3_data"] = "data3"
            mgr3.track_change("node3_data", "data3")
            
            # Wait for propagation
            await asyncio.sleep(1.0)
            
            # All nodes should have all data
            for db in [db1, db2, db3]:
                assert db.get("node1_data") == "data1"
                assert db.get("node2_data") == "data2"
                assert db.get("node3_data") == "data3"
        finally:
            await mgr1.stop()
            await mgr2.stop()
            await mgr3.stop()
    
    @pytest.mark.asyncio
    async def test_automatic_reconnection(self):
        """Test automatic reconnection after disconnection"""
        db_server = {}
        db_client = {}
        
        config_server = IPSyncConfig(host="127.0.0.1", port=18790)
        config_client = IPSyncConfig(
            host="127.0.0.1",
            port=18791,
            peer_addresses=["ws://127.0.0.1:18790"],
            enable_auto_recovery=True,
            recovery_retry_interval=0.5
        )
        
        manager_server = IPSyncManager(db_server, config_server)
        manager_client = IPSyncManager(db_client, config_client)
        
        await manager_server.start(enable_server=True)
        await manager_client.start(enable_server=False, connect_to_peers=True)
        
        try:
            # Wait for connection
            await asyncio.sleep(0.3)
            
            # Add data
            db_server["test"] = "value"
            manager_server.track_change("test", "value")
            
            await asyncio.sleep(0.3)
            assert db_client.get("test") == "value"
            
            # Simulate disconnection by stopping server
            await manager_server.stop()
            
            # Wait a bit
            await asyncio.sleep(0.3)
            
            # Restart server
            await manager_server.start(enable_server=True)
            
            # Wait for reconnection
            await asyncio.sleep(1.0)
            
            # Add new data
            db_server["after_reconnect"] = "new_value"
            manager_server.track_change("after_reconnect", "new_value")
            
            await asyncio.sleep(0.5)
            
            # Should sync again
            assert db_client.get("after_reconnect") == "new_value"
        finally:
            await manager_client.stop()
            await manager_server.stop()
    
    @pytest.mark.asyncio
    async def test_large_dataset_network_sync(self):
        """Test syncing large datasets over network"""
        db1 = {}
        db2 = {}
        
        config1 = IPSyncConfig(
            host="127.0.0.1",
            port=18800,
            batch_size=100
        )
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18801,
            peer_addresses=["ws://127.0.0.1:18800"],
            batch_size=100
        )
        
        mgr1 = IPSyncManager(db1, config1)
        mgr2 = IPSyncManager(db2, config2)
        
        await mgr1.start(enable_server=True)
        await mgr2.start(enable_server=False, connect_to_peers=True)
        
        try:
            # Wait for connection
            await asyncio.sleep(0.3)
            
            # Add 500 items
            for i in range(500):
                key = f"key_{i}"
                value = f"value_{i}"
                db1[key] = value
                mgr1.track_change(key, value)
            
            # Wait for sync
            await asyncio.sleep(2.0)
            
            # Verify all synced
            assert len(db2) == 500
            for i in range(500):
                assert db2.get(f"key_{i}") == f"value_{i}"
        finally:
            await mgr1.stop()
            await mgr2.stop()
    
    @pytest.mark.asyncio
    async def test_deletion_propagation(self):
        """Test that deletions propagate correctly"""
        db1 = {"to_delete": "value", "to_keep": "keep"}
        db2 = {}
        
        config1 = IPSyncConfig(host="127.0.0.1", port=18810)
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18811,
            peer_addresses=["ws://127.0.0.1:18810"]
        )
        
        mgr1 = IPSyncManager(db1, config1)
        mgr2 = IPSyncManager(db2, config2)
        
        await mgr1.start(enable_server=True)
        await mgr2.start(enable_server=False, connect_to_peers=True)
        
        try:
            # Wait for connection
            await asyncio.sleep(0.3)
            
            # Sync initial data
            mgr1.track_change("to_delete", "value")
            mgr1.track_change("to_keep", "keep")
            
            await asyncio.sleep(0.5)
            assert db2.get("to_delete") == "value"
            assert db2.get("to_keep") == "keep"
            
            # Delete item
            del db1["to_delete"]
            mgr1.track_change("to_delete", None)
            
            # Wait for sync
            await asyncio.sleep(0.5)
            
            # Verify deletion propagated
            assert "to_delete" not in db2
            assert db2.get("to_keep") == "keep"
        finally:
            await mgr1.stop()
            await mgr2.stop()
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_timestamps(self):
        """Test timestamp-based conflict resolution"""
        db1 = {}
        db2 = {}
        
        config1 = IPSyncConfig(
            host="127.0.0.1",
            port=18820,
            peer_addresses=["ws://127.0.0.1:18821"]
        )
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18821,
            peer_addresses=["ws://127.0.0.1:18820"]
        )
        
        mgr1 = IPSyncManager(db1, config1)
        mgr2 = IPSyncManager(db2, config2)
        
        await mgr1.start(enable_server=True, connect_to_peers=True)
        await mgr2.start(enable_server=True, connect_to_peers=True)
        
        try:
            # Wait for connections
            await asyncio.sleep(0.3)
            
            # Both nodes update same key with different values
            db1["conflict_key"] = "value_from_db1"
            mgr1.track_change("conflict_key", "value_from_db1")
            
            await asyncio.sleep(0.05)  # Small delay
            
            db2["conflict_key"] = "value_from_db2"
            mgr2.track_change("conflict_key", "value_from_db2")
            
            # Wait for sync
            await asyncio.sleep(1.0)
            
            # Last write should win (db2's value)
            assert db1.get("conflict_key") == "value_from_db2"
            assert db2.get("conflict_key") == "value_from_db2"
        finally:
            await mgr1.stop()
            await mgr2.stop()
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self):
        """Test that statistics are collected properly"""
        db1 = {}
        db2 = {}
        
        config1 = IPSyncConfig(host="127.0.0.1", port=18830)
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18831,
            peer_addresses=["ws://127.0.0.1:18830"]
        )
        
        mgr1 = IPSyncManager(db1, config1)
        mgr2 = IPSyncManager(db2, config2)
        
        await mgr1.start(enable_server=True)
        await mgr2.start(enable_server=False, connect_to_peers=True)
        
        try:
            # Wait for connection
            await asyncio.sleep(0.3)
            
            # Make some changes
            for i in range(10):
                db1[f"key{i}"] = f"value{i}"
                mgr1.track_change(f"key{i}", f"value{i}")
            
            # Wait for sync
            await asyncio.sleep(0.5)
            
            # Check stats
            stats1 = mgr1.get_stats()
            stats2 = mgr2.get_stats()
            
            assert "changes_sent" in stats1
            assert "changes_received" in stats2
            assert stats2["changes_received"] >= 10
        finally:
            await mgr1.stop()
            await mgr2.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_missing_data(self):
        """Test recovery of missing data when node comes online"""
        db1 = {}
        db2 = {}
        
        config1 = IPSyncConfig(host="127.0.0.1", port=18840)
        config2 = IPSyncConfig(
            host="127.0.0.1",
            port=18841,
            peer_addresses=["ws://127.0.0.1:18840"],
            enable_auto_recovery=True
        )
        
        mgr1 = IPSyncManager(db1, config1)
        
        # Start only server first
        await mgr1.start(enable_server=True)
        
        try:
            # Add data while client is offline
            for i in range(20):
                db1[f"offline_key_{i}"] = f"offline_value_{i}"
                mgr1.track_change(f"offline_key_{i}", f"offline_value_{i}")
            
            # Now start client
            mgr2 = IPSyncManager(db2, config2)
            await mgr2.start(enable_server=False, connect_to_peers=True)
            
            # Wait for connection and recovery
            await asyncio.sleep(1.5)
            
            # Client should have recovered all missing data
            assert len(db2) == 20
            for i in range(20):
                assert db2.get(f"offline_key_{i}") == f"offline_value_{i}"
            
            await mgr2.stop()
        finally:
            await mgr1.stop()


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @pytest.mark.asyncio
    async def test_distributed_cache_scenario(self):
        """Simulate a distributed cache across data centers"""
        cache_dc1 = {}
        cache_dc2 = {}
        cache_dc3 = {}
        
        config_dc1 = IPSyncConfig(
            host="127.0.0.1",
            port=18850,
            peer_addresses=["ws://127.0.0.1:18851", "ws://127.0.0.1:18852"],
            sync_interval=0.2
        )
        config_dc2 = IPSyncConfig(
            host="127.0.0.1",
            port=18851,
            peer_addresses=["ws://127.0.0.1:18850", "ws://127.0.0.1:18852"],
            sync_interval=0.2
        )
        config_dc3 = IPSyncConfig(
            host="127.0.0.1",
            port=18852,
            peer_addresses=["ws://127.0.0.1:18850", "ws://127.0.0.1:18851"],
            sync_interval=0.2
        )
        
        mgr_dc1 = IPSyncManager(cache_dc1, config_dc1)
        mgr_dc2 = IPSyncManager(cache_dc2, config_dc2)
        mgr_dc3 = IPSyncManager(cache_dc3, config_dc3)
        
        await mgr_dc1.start(enable_server=True, connect_to_peers=True)
        await mgr_dc2.start(enable_server=True, connect_to_peers=True)
        await mgr_dc3.start(enable_server=True, connect_to_peers=True)
        
        try:
            # Wait for mesh to form
            await asyncio.sleep(0.5)
            
            # Each DC caches different API responses
            cache_dc1["api_user_123"] = {"name": "Alice", "age": 30}
            mgr_dc1.track_change("api_user_123", cache_dc1["api_user_123"])
            
            cache_dc2["api_product_456"] = {"name": "Widget", "price": 9.99}
            mgr_dc2.track_change("api_product_456", cache_dc2["api_product_456"])
            
            cache_dc3["api_order_789"] = {"items": [1, 2, 3], "total": 99.99}
            mgr_dc3.track_change("api_order_789", cache_dc3["api_order_789"])
            
            # Wait for propagation
            await asyncio.sleep(1.0)
            
            # All DCs should have all cached data
            for cache in [cache_dc1, cache_dc2, cache_dc3]:
                assert "api_user_123" in cache
                assert "api_product_456" in cache
                assert "api_order_789" in cache
                assert cache["api_user_123"]["name"] == "Alice"
                assert cache["api_product_456"]["price"] == 9.99
                assert cache["api_order_789"]["total"] == 99.99
        finally:
            await mgr_dc1.stop()
            await mgr_dc2.stop()
            await mgr_dc3.stop()
    
    @pytest.mark.asyncio
    async def test_session_store_scenario(self):
        """Simulate distributed session storage"""
        sessions_web1 = {}
        sessions_web2 = {}
        
        config_web1 = IPSyncConfig(
            host="127.0.0.1",
            port=18860,
            peer_addresses=["ws://127.0.0.1:18861"],
            sync_interval=0.1
        )
        config_web2 = IPSyncConfig(
            host="127.0.0.1",
            port=18861,
            peer_addresses=["ws://127.0.0.1:18860"],
            sync_interval=0.1
        )
        
        mgr_web1 = IPSyncManager(sessions_web1, config_web1)
        mgr_web2 = IPSyncManager(sessions_web2, config_web2)
        
        await mgr_web1.start(enable_server=True, connect_to_peers=True)
        await mgr_web2.start(enable_server=True, connect_to_peers=True)
        
        try:
            # Wait for connection
            await asyncio.sleep(0.3)
            
            # User logs in on web1
            session_id = "sess_xyz789"
            sessions_web1[session_id] = {
                "user_id": "user456",
                "logged_in": True,
                "login_time": time.time()
            }
            mgr_web1.track_change(session_id, sessions_web1[session_id])
            
            # Wait for replication
            await asyncio.sleep(0.3)
            
            # Session should be available on web2
            assert session_id in sessions_web2
            assert sessions_web2[session_id]["user_id"] == "user456"
            assert sessions_web2[session_id]["logged_in"] is True
            
            # User makes request to web2, updates session
            sessions_web2[session_id]["last_activity"] = time.time()
            sessions_web2[session_id]["page_views"] = 5
            mgr_web2.track_change(session_id, sessions_web2[session_id])
            
            # Wait for sync back
            await asyncio.sleep(0.3)
            
            # web1 should have updated session
            assert "last_activity" in sessions_web1[session_id]
            assert sessions_web1[session_id]["page_views"] == 5
        finally:
            await mgr_web1.stop()
            await mgr_web2.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
