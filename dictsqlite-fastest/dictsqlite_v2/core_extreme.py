"""
DictSQLite V2 - Extreme Performance Edition
Target: 100M+ ops/s for bulk operations

Architecture:
- Lock-free for single-threaded bulk operations
- APSW with prepared statements and transaction batching
- Minimal serialization overhead
- Optimized for sequential bulk reads/writes
"""

import apsw
import pickle
import os
from typing import Any, Dict, Iterator, Optional
from pathlib import Path


class DictSQLiteV2Extreme:
    """Ultra-optimized for bulk sequential operations - 100M+ ops/s target"""
    
    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        **kwargs
    ):
        self.db_name = db_name
        self.table_name = table_name
        
        # In-memory cache (no locks for single-threaded bulk ops)
        self._cache: Dict[str, Any] = {}
        self._dirty = False
        
        # APSW connection
        self._conn = None
        self._init_db()
        
        # Load existing data into cache
        self._load_all()
    
    def _init_db(self):
        """Initialize APSW database"""
        db_path = Path(self.db_name)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = apsw.Connection(str(db_path))
        cursor = self._conn.cursor()
        
        # Extreme performance settings
        cursor.execute("PRAGMA journal_mode=OFF")  # No journaling for max speed
        cursor.execute("PRAGMA synchronous=OFF")   # No fsync
        cursor.execute("PRAGMA cache_size=100000") # Large cache
        cursor.execute("PRAGMA page_size=65536")   # Large pages
        cursor.execute("PRAGMA temp_store=MEMORY") # Temp tables in memory
        
        # Create table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT PRIMARY KEY,
                value BLOB
            )
        """)
    
    def _load_all(self):
        """Load all data into memory cache"""
        cursor = self._conn.cursor()
        for key, value_blob in cursor.execute(
            f"SELECT key, value FROM {self.table_name}"
        ):
            self._cache[key] = pickle.loads(value_blob)
    
    def _sync_to_disk(self):
        """Sync all dirty data to disk in one transaction"""
        if not self._dirty:
            return
        
        cursor = self._conn.cursor()
        cursor.execute("BEGIN")
        
        # Prepare statement for reuse
        stmt = f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)"
        
        # Batch insert all cache items
        data = [(k, pickle.dumps(v, protocol=5)) for k, v in self._cache.items()]
        cursor.executemany(stmt, data)
        
        cursor.execute("COMMIT")
        self._dirty = False
    
    # Dict-like interface
    def __getitem__(self, key: str) -> Any:
        """Get item - pure memory access"""
        return self._cache[key]
    
    def __setitem__(self, key: str, value: Any):
        """Set item - pure memory write"""
        self._cache[key] = value
        self._dirty = True
    
    def __delitem__(self, key: str):
        """Delete item"""
        del self._cache[key]
        self._dirty = True
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists"""
        return key in self._cache
    
    def __len__(self) -> int:
        """Get number of items"""
        return len(self._cache)
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over keys"""
        return iter(self._cache)
    
    def keys(self):
        """Get keys view"""
        return self._cache.keys()
    
    def values(self):
        """Get values view"""
        return self._cache.values()
    
    def items(self):
        """Get items view"""
        return self._cache.items()
    
    def get(self, key: str, default=None) -> Any:
        """Get with default"""
        return self._cache.get(key, default)
    
    def bulk_insert(self, data: Dict[str, Any]):
        """Bulk insert - optimized for massive throughput"""
        self._cache.update(data)
        self._dirty = True
    
    def update_many(self, data: Dict[str, Any]):
        """Alias for bulk_insert"""
        self.bulk_insert(data)
    
    def close(self):
        """Close and sync to disk"""
        self._sync_to_disk()
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def __del__(self):
        if self._conn:
            try:
                self.close()
            except:
                pass
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'version': '2.0.0-extreme',
            'cache_size': len(self._cache),
            'dirty': self._dirty
        }


# Alias for compatibility
DictSQLiteV2 = DictSQLiteV2Extreme
