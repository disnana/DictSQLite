"""
Tests for the auto-sync conflict resolver.
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conflict_resolver import ConflictResolver, ConflictResolutionStrategy


class TestConflictResolver:
    """Test cases for ConflictResolver"""
    
    def test_last_write_wins_remote_newer(self):
        """Test last-write-wins when remote is newer"""
        resolver = ConflictResolver(ConflictResolutionStrategy.LAST_WRITE_WINS)
        
        local_value = "local"
        remote_value = "remote"
        local_timestamp = 1000.0
        remote_timestamp = 2000.0
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            local_timestamp,
            remote_value,
            remote_timestamp,
            "node1",
            "node2"
        )
        
        assert resolved == "remote"
        assert reason == "remote_newer"
    
    def test_last_write_wins_local_newer(self):
        """Test last-write-wins when local is newer"""
        resolver = ConflictResolver(ConflictResolutionStrategy.LAST_WRITE_WINS)
        
        local_value = "local"
        remote_value = "remote"
        local_timestamp = 2000.0
        remote_timestamp = 1000.0
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            local_timestamp,
            remote_value,
            remote_timestamp,
            "node1",
            "node2"
        )
        
        assert resolved == "local"
        assert reason == "local_newer"
    
    def test_last_write_wins_same_timestamp(self):
        """Test last-write-wins when timestamps are the same"""
        resolver = ConflictResolver(ConflictResolutionStrategy.LAST_WRITE_WINS)
        
        local_value = "local"
        remote_value = "remote"
        timestamp = 1000.0
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            timestamp,
            remote_value,
            timestamp,
            "node1",
            "node2"
        )
        
        assert resolved == "local"
        assert reason == "same_timestamp_local_preferred"
    
    def test_first_write_wins_remote_older(self):
        """Test first-write-wins when remote is older"""
        resolver = ConflictResolver(ConflictResolutionStrategy.FIRST_WRITE_WINS)
        
        local_value = "local"
        remote_value = "remote"
        local_timestamp = 2000.0
        remote_timestamp = 1000.0
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            local_timestamp,
            remote_value,
            remote_timestamp,
            "node1",
            "node2"
        )
        
        assert resolved == "remote"
        assert reason == "remote_older"
    
    def test_first_write_wins_local_older(self):
        """Test first-write-wins when local is older"""
        resolver = ConflictResolver(ConflictResolutionStrategy.FIRST_WRITE_WINS)
        
        local_value = "local"
        remote_value = "remote"
        local_timestamp = 1000.0
        remote_timestamp = 2000.0
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            local_timestamp,
            remote_value,
            remote_timestamp,
            "node1",
            "node2"
        )
        
        assert resolved == "local"
        assert reason == "local_older"
    
    def test_manual_resolution_with_override(self):
        """Test manual resolution with a pre-set value"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MANUAL)
        
        # Set manual resolution
        resolver.set_manual_resolution("test_key", "manual_value")
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            "local",
            1000.0,
            "remote",
            2000.0,
            "node1",
            "node2"
        )
        
        assert resolved == "manual_value"
        assert reason == "manual_override"
    
    def test_manual_resolution_without_override(self):
        """Test manual resolution without a pre-set value"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MANUAL)
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            "local",
            1000.0,
            "remote",
            2000.0,
            "node1",
            "node2"
        )
        
        assert resolved == "local"
        assert reason == "manual_not_set_default_local"
    
    def test_merge_lists(self):
        """Test merging of lists"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MERGE)
        
        local_value = [1, 2, 3]
        remote_value = [3, 4, 5]
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            1000.0,
            remote_value,
            2000.0,
            "node1",
            "node2"
        )
        
        assert set(resolved) == {1, 2, 3, 4, 5}
        assert reason == "merged_lists"
    
    def test_merge_dicts(self):
        """Test merging of dictionaries"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MERGE)
        
        local_value = {"a": 1, "b": 2}
        remote_value = {"b": 3, "c": 4}
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            1000.0,
            remote_value,
            2000.0,
            "node1",
            "node2"
        )
        
        # Remote values should override local for duplicate keys
        assert resolved == {"a": 1, "b": 3, "c": 4}
        assert reason == "merged_dicts"
    
    def test_merge_numbers(self):
        """Test merging of numbers"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MERGE)
        
        local_value = 10
        remote_value = 20
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            1000.0,
            remote_value,
            2000.0,
            "node1",
            "node2"
        )
        
        assert resolved == 30
        assert reason == "merged_numbers"
    
    def test_merge_incompatible_types(self):
        """Test merge when types are incompatible"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MERGE)
        
        local_value = "string"
        remote_value = 123
        
        resolved, reason = resolver.resolve_conflict(
            "test_key",
            local_value,
            1000.0,
            remote_value,
            2000.0,
            "node1",
            "node2"
        )
        
        assert resolved == "string"
        assert reason == "merge_not_possible_kept_local"
    
    def test_clear_manual_resolutions(self):
        """Test clearing manual resolutions"""
        resolver = ConflictResolver(ConflictResolutionStrategy.MANUAL)
        
        resolver.set_manual_resolution("key1", "value1")
        resolver.set_manual_resolution("key2", "value2")
        
        assert len(resolver.manual_resolutions) == 2
        
        resolver.clear_manual_resolutions()
        
        assert len(resolver.manual_resolutions) == 0
