"""
Conflict resolution strategies for multi-master synchronization.
"""

from enum import Enum
from typing import Any, Dict, Optional
import time


class ConflictResolutionStrategy(Enum):
    """Conflict resolution strategies"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MANUAL = "manual"
    MERGE = "merge"


class ConflictResolver:
    """
    Handles conflicts in multi-master replication.
    
    When multiple nodes modify the same key simultaneously, conflicts can occur.
    This class provides various strategies to resolve such conflicts.
    """
    
    def __init__(self, strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS):
        """
        Initialize conflict resolver.
        
        Args:
            strategy: The conflict resolution strategy to use
        """
        self.strategy = strategy
        self.manual_resolutions: Dict[str, Any] = {}
    
    def resolve_conflict(
        self, 
        key: str, 
        local_value: Any, 
        local_timestamp: float,
        remote_value: Any, 
        remote_timestamp: float,
        local_node_id: str,
        remote_node_id: str
    ) -> tuple[Any, str]:
        """
        Resolve a conflict between local and remote values.
        
        Args:
            key: The key with conflicting values
            local_value: Value on local node
            local_timestamp: Timestamp of local modification
            remote_value: Value on remote node
            remote_timestamp: Timestamp of remote modification
            local_node_id: ID of local node
            remote_node_id: ID of remote node
            
        Returns:
            Tuple of (resolved_value, resolution_reason)
        """
        if self.strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            return self._last_write_wins(
                key, local_value, local_timestamp, remote_value, remote_timestamp
            )
        elif self.strategy == ConflictResolutionStrategy.FIRST_WRITE_WINS:
            return self._first_write_wins(
                key, local_value, local_timestamp, remote_value, remote_timestamp
            )
        elif self.strategy == ConflictResolutionStrategy.MANUAL:
            return self._manual_resolution(
                key, local_value, remote_value, local_node_id, remote_node_id
            )
        elif self.strategy == ConflictResolutionStrategy.MERGE:
            return self._merge_values(
                key, local_value, remote_value
            )
        else:
            raise ValueError(f"Unknown conflict resolution strategy: {self.strategy}")
    
    def _last_write_wins(
        self, 
        key: str,
        local_value: Any, 
        local_timestamp: float,
        remote_value: Any, 
        remote_timestamp: float
    ) -> tuple[Any, str]:
        """Last-write-wins strategy"""
        if remote_timestamp > local_timestamp:
            return remote_value, "remote_newer"
        elif local_timestamp > remote_timestamp:
            return local_value, "local_newer"
        else:
            # Same timestamp, prefer local
            return local_value, "same_timestamp_local_preferred"
    
    def _first_write_wins(
        self, 
        key: str,
        local_value: Any, 
        local_timestamp: float,
        remote_value: Any, 
        remote_timestamp: float
    ) -> tuple[Any, str]:
        """First-write-wins strategy"""
        if remote_timestamp < local_timestamp:
            return remote_value, "remote_older"
        elif local_timestamp < remote_timestamp:
            return local_value, "local_older"
        else:
            # Same timestamp, prefer local
            return local_value, "same_timestamp_local_preferred"
    
    def _manual_resolution(
        self,
        key: str,
        local_value: Any,
        remote_value: Any,
        local_node_id: str,
        remote_node_id: str
    ) -> tuple[Any, str]:
        """Manual resolution strategy - requires pre-set resolution"""
        if key in self.manual_resolutions:
            return self.manual_resolutions[key], "manual_override"
        # Default to local if no manual resolution set
        return local_value, "manual_not_set_default_local"
    
    def _merge_values(
        self,
        key: str,
        local_value: Any,
        remote_value: Any
    ) -> tuple[Any, str]:
        """
        Attempt to merge values.
        
        This is a simple merge strategy that works for certain types:
        - For lists: concatenate and deduplicate
        - For dicts: merge keys
        - For numbers: sum
        - For others: keep local
        """
        if isinstance(local_value, list) and isinstance(remote_value, list):
            # Merge lists and remove duplicates
            merged = list(set(local_value + remote_value))
            return merged, "merged_lists"
        elif isinstance(local_value, dict) and isinstance(remote_value, dict):
            # Merge dictionaries
            merged = {**local_value, **remote_value}
            return merged, "merged_dicts"
        elif isinstance(local_value, (int, float)) and isinstance(remote_value, (int, float)):
            # Sum numbers
            merged = local_value + remote_value
            return merged, "merged_numbers"
        else:
            # Can't merge, keep local
            return local_value, "merge_not_possible_kept_local"
    
    def set_manual_resolution(self, key: str, value: Any):
        """Set a manual resolution for a specific key"""
        self.manual_resolutions[key] = value
    
    def clear_manual_resolutions(self):
        """Clear all manual resolutions"""
        self.manual_resolutions.clear()
