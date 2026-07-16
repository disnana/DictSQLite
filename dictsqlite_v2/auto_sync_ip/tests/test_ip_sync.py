"""
Tests for IP-based synchronization system.
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
from ip_sync_manager import IPSyncManager
from recovery import AutoRecovery


class MockDB(dict):
    """Mock database for testing"""
    def close(self):
        pass


class TestIPSyncConfig:
    """Test IP sync configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = IPSyncConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.use_msgpack is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = IPSyncConfig(
            host="127.0.0.1",
            port=9000,
            max_connections=50
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.max_connections == 50
    
    def test_validate_valid_config(self):
        """Test validation of valid config"""
        config = IPSyncConfig()
        assert config.validate() is True
    
    def test_validate_invalid_port(self):
        """Test validation with invalid port"""
        config = IPSyncConfig(port=70000)
        with pytest.raises(ValueError, match="Port must be between"):
            config.validate()
    
    def test_validate_invalid_sync_interval(self):
        """Test validation with invalid sync interval"""
        config = IPSyncConfig(sync_interval=-1.0)
        with pytest.raises(ValueError, match="sync_interval must be positive"):
            config.validate()


class TestSyncServer:
    """Test sync server functionality"""
    
    def test_server_initialization(self):
        """Test server initialization"""
        db = MockDB()
        config = IPSyncConfig()
        server = SyncServer(db, config)
        
        assert server.db is db
        assert server.config is config
        assert server.running is False
    
    def test_track_change(self):
        """Test tracking changes"""
        db = MockDB()
        config = IPSyncConfig()
        server = SyncServer(db, config)
        
        server.track_change("key1", "value1")
        
        assert "key1" in server.change_log
        assert server.change_log["key1"]["value"] == "value1"
    
    def test_get_stats(self):
        """Test getting server stats"""
        db = MockDB()
        config = IPSyncConfig()
        server = SyncServer(db, config)
        
        stats = server.get_stats()
        
        assert "node_id" in stats
        assert "active_connections" in stats
        assert stats["running"] is False


class TestSyncClient:
    """Test sync client functionality"""
    
    def test_client_initialization(self):
        """Test client initialization"""
        db = MockDB()
        config = IPSyncConfig()
        client = SyncClient(db, config, "ws://localhost:8765")
        
        assert client.db is db
        assert client.config is config
        assert client.connected is False
    
    def test_track_change(self):
        """Test tracking changes"""
        db = MockDB()
        config = IPSyncConfig()
        client = SyncClient(db, config, "ws://localhost:8765")
        
        client.track_change("key1", "value1")
        
        assert "key1" in client.change_log
        assert client.change_log["key1"]["value"] == "value1"
    
    def test_get_stats(self):
        """Test getting client stats"""
        db = MockDB()
        config = IPSyncConfig()
        client = SyncClient(db, config, "ws://localhost:8765")
        
        stats = client.get_stats()
        
        assert "node_id" in stats
        assert "connected" in stats
        assert stats["connected"] is False


class TestAutoRecovery:
    """Test auto-recovery functionality"""
    
    def test_recovery_initialization(self):
        """Test recovery initialization"""
        config = IPSyncConfig()
        recovery = AutoRecovery(config)
        
        assert recovery.config is config
        assert recovery.running is False
    
    def test_get_stats(self):
        """Test getting recovery stats"""
        config = IPSyncConfig()
        recovery = AutoRecovery(config)
        
        stats = recovery.get_stats()
        
        assert "running" in stats
        assert "recovery_attempts" in stats
        assert "total_recoveries" in stats


class TestIPSyncManager:
    """Test IP sync manager"""
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        db = MockDB()
        config = IPSyncConfig()
        manager = IPSyncManager(db, config)
        
        assert manager.db is db
        assert manager.config is config
        assert manager.running is False
    
    def test_track_change(self):
        """Test tracking changes"""
        db = MockDB()
        config = IPSyncConfig()
        manager = IPSyncManager(db, config)
        
        manager.track_change("key1", "value1")
        
        # Should track in clients (even if none connected)
        assert True  # No error thrown
    
    def test_get_stats(self):
        """Test getting manager stats"""
        db = MockDB()
        config = IPSyncConfig()
        manager = IPSyncManager(db, config)
        
        stats = manager.get_stats()
        
        assert "running" in stats
        assert "server" in stats
        assert "clients" in stats
        assert "auto_recovery" in stats


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations"""
    
    async def test_server_start_stop(self):
        """Test starting and stopping server"""
        db = MockDB()
        config = IPSyncConfig(port=8766)  # Different port to avoid conflicts
        server = SyncServer(db, config)
        
        await server.start()
        assert server.running is True
        
        await server.stop()
        assert server.running is False
    
    async def test_manager_start_stop(self):
        """Test starting and stopping manager"""
        db = MockDB()
        config = IPSyncConfig(port=8767, enable_auto_recovery=False)
        manager = IPSyncManager(db, config)
        
        await manager.start(enable_server=True, connect_to_peers=False)
        assert manager.running is True
        
        await manager.stop()
        assert manager.running is False
    
    async def test_client_server_communication(self):
        """Test basic client-server communication"""
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8768)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        
        # Wait for server to be ready
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8768")
        connected = await client.connect()
        
        assert connected is True
        assert client.connected is True
        
        # Cleanup
        await client.disconnect()
        await server.stop()
    
    async def test_change_synchronization(self):
        """Test synchronizing changes between nodes"""
        db_server = MockDB()
        db_client = MockDB()
        
        config_server = IPSyncConfig(port=8769)
        config_client = IPSyncConfig()
        
        # Start server
        server = SyncServer(db_server, config_server)
        await server.start()
        await asyncio.sleep(0.1)
        
        # Connect client
        client = SyncClient(db_client, config_client, "ws://localhost:8769")
        await client.connect()
        
        # Start client receive loop
        receive_task = asyncio.create_task(client.receive_loop())
        
        # Track change on server
        db_server["key1"] = "value1"
        server.track_change("key1", "value1")
        
        # Broadcast from server
        await server.broadcast_changes({"key1": server.change_log["key1"]})
        
        # Wait for propagation
        await asyncio.sleep(0.2)
        
        # Check client received change
        assert "key1" in db_client
        assert db_client["key1"] == "value1"
        
        # Cleanup
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await client.disconnect()
        await server.stop()
