"""
Tests for the SyncConfig class.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SyncConfig, SyncMode


class TestSyncConfig:
    """Test cases for SyncConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = SyncConfig()
        
        assert config.sync_interval == 5.0
        assert config.sync_mode == SyncMode.BIDIRECTIONAL
        assert config.enable_multi_master is True
        assert config.conflict_strategy == "last_write_wins"
        assert config.enable_auto_recovery is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = SyncConfig(
            sync_interval=10.0,
            sync_mode=SyncMode.PUSH,
            enable_multi_master=False,
            conflict_strategy="first_write_wins",
            enable_auto_recovery=False
        )
        
        assert config.sync_interval == 10.0
        assert config.sync_mode == SyncMode.PUSH
        assert config.enable_multi_master is False
        assert config.conflict_strategy == "first_write_wins"
        assert config.enable_auto_recovery is False
    
    def test_validate_valid_config(self):
        """Test validation of valid config"""
        config = SyncConfig()
        assert config.validate() is True
    
    def test_validate_invalid_sync_interval(self):
        """Test validation with invalid sync interval"""
        config = SyncConfig(sync_interval=-1.0)
        
        with pytest.raises(ValueError, match="sync_interval must be positive"):
            config.validate()
    
    def test_validate_invalid_recovery_interval(self):
        """Test validation with invalid recovery interval"""
        config = SyncConfig(recovery_retry_interval=-1.0)
        
        with pytest.raises(ValueError, match="recovery_retry_interval must be positive"):
            config.validate()
    
    def test_validate_invalid_max_retries(self):
        """Test validation with invalid max retries"""
        config = SyncConfig(max_recovery_retries=-1)
        
        with pytest.raises(ValueError, match="max_recovery_retries must be non-negative"):
            config.validate()
    
    def test_validate_invalid_batch_size(self):
        """Test validation with invalid batch size"""
        config = SyncConfig(batch_size=0)
        
        with pytest.raises(ValueError, match="batch_size must be positive"):
            config.validate()
    
    def test_sync_modes(self):
        """Test different sync modes"""
        assert SyncMode.PUSH.value == "push"
        assert SyncMode.PULL.value == "pull"
        assert SyncMode.BIDIRECTIONAL.value == "bidirectional"
    
    def test_peer_nodes_list(self):
        """Test peer nodes list"""
        config = SyncConfig(peer_nodes=["node1", "node2", "node3"])
        
        assert len(config.peer_nodes) == 3
        assert "node1" in config.peer_nodes
        assert "node2" in config.peer_nodes
        assert "node3" in config.peer_nodes
    
    def test_performance_settings(self):
        """Test performance-related settings"""
        config = SyncConfig(
            batch_size=200,
            compression_enabled=False
        )
        
        assert config.batch_size == 200
        assert config.compression_enabled is False
    
    def test_network_settings(self):
        """Test network-related settings"""
        config = SyncConfig(
            connection_timeout=60.0,
            max_concurrent_syncs=10
        )
        
        assert config.connection_timeout == 60.0
        assert config.max_concurrent_syncs == 10
    
    def test_logging_settings(self):
        """Test logging-related settings"""
        config = SyncConfig(
            log_level="DEBUG",
            enable_sync_log=False
        )
        
        assert config.log_level == "DEBUG"
        assert config.enable_sync_log is False
