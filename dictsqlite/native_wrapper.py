"""
Native extension wrapper for DictSQLite.

This module provides high-performance native implementations using Rust,
with automatic fallback to pure Python implementations if the native
extension is not available.
"""

import sys
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# Try to import the native extension
_native_available = False
_NativeCache = None
_NativeSQLite = None

try:
    from dictsqlite_native import NativeCache as _NativeCache
    from dictsqlite_native import NativeSQLite as _NativeSQLite
    _native_available = True
    logger.info("Native Rust extension loaded successfully")
except ImportError as e:
    logger.debug(f"Native extension not available: {e}")
    logger.info("Using pure Python fallback implementation")


class PythonCache:
    """Pure Python LRU cache fallback implementation."""
    
    def __init__(self, capacity: int):
        from collections import OrderedDict
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key: str) -> Optional[bytes]:
        """Get value from cache."""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: bytes) -> None:
        """Put value in cache."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
    
    def len(self) -> int:
        """Get cache size."""
        return len(self.cache)


class PythonSQLite:
    """Pure Python SQLite wrapper fallback implementation."""
    
    def __init__(self, db_path: str, table_name: str):
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self.table_name = table_name
        
        # Create table if not exists
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (key TEXT PRIMARY KEY, value BLOB)"
        self.conn.execute(create_sql)
        self.conn.commit()
    
    def get(self, key: str) -> Optional[bytes]:
        """Get value from database."""
        cursor = self.conn.execute(
            f"SELECT value FROM {self.table_name} WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    
    def put(self, key: str, value: bytes) -> None:
        """Put value in database."""
        self.conn.execute(
            f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()
    
    def delete(self, key: str) -> None:
        """Delete key from database."""
        self.conn.execute(
            f"DELETE FROM {self.table_name} WHERE key = ?",
            (key,)
        )
        self.conn.commit()
    
    def bulk_insert(self, items: Dict[str, bytes]) -> None:
        """Bulk insert items."""
        cursor = self.conn.cursor()
        cursor.execute("BEGIN")
        try:
            for key, value in items.items():
                cursor.execute(
                    f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
                    (key, value)
                )
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
    
    def keys(self) -> list:
        """Get all keys."""
        cursor = self.conn.execute(f"SELECT key FROM {self.table_name}")
        return [row[0] for row in cursor.fetchall()]


def is_native_available() -> bool:
    """Check if native extension is available."""
    return _native_available


def get_cache_class():
    """Get the best available cache implementation."""
    return _NativeCache if _native_available else PythonCache


def get_sqlite_class():
    """Get the best available SQLite wrapper implementation."""
    return _NativeSQLite if _native_available else PythonSQLite


# Export convenience aliases
NativeCache = get_cache_class()
NativeSQLite = get_sqlite_class()

__all__ = [
    'is_native_available',
    'get_cache_class',
    'get_sqlite_class',
    'NativeCache',
    'NativeSQLite',
]
