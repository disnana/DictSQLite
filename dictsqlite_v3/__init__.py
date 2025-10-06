"""
DictSQLite v3.0 Python Wrapper

High-performance wrapper providing dict-like interface
"""

try:
    from dictsqlite_v3 import DictSQLiteV3 as _NativeDictSQLiteV3
    from dictsqlite_v3 import AsyncDictSQLite as _NativeAsyncDictSQLite
    _NATIVE_AVAILABLE = True
except ImportError:
    _NATIVE_AVAILABLE = False
    _NativeDictSQLiteV3 = None
    _NativeAsyncDictSQLite = None


class DictSQLiteV3:
    """
    High-performance DictSQLite v3.0 with dict-like interface
    
    Targets 100M+ ops/sec with lock-free concurrent hashmap
    """
    
    def __init__(self, db_path, hot_capacity=1_000_000, enable_async=True):
        """
        Initialize DictSQLite v3.0
        
        Args:
            db_path: Path to database file
            hot_capacity: Maximum entries in hot tier (in-memory)
            enable_async: Enable async background flush
        """
        if not _NATIVE_AVAILABLE:
            raise RuntimeError(
                "DictSQLite v3.0 native extension not available. "
                "Please build it using: cd dictsqlite_v3 && maturin develop --release"
            )
        
        self._db = _NativeDictSQLiteV3(db_path, hot_capacity, enable_async)
    
    def __getitem__(self, key):
        """Get value by key"""
        result = self._db.get(str(key))
        if result is None:
            raise KeyError(key)
        return result
    
    def __setitem__(self, key, value):
        """Set value for key"""
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes):
            import pickle
            value = pickle.dumps(value)
        self._db.set(str(key), value)
    
    def __delitem__(self, key):
        """Delete key"""
        self._db.delete(str(key))
    
    def __contains__(self, key):
        """Check if key exists"""
        return self._db.contains(str(key))
    
    def __len__(self):
        """Get number of entries"""
        return self._db.len()
    
    def get(self, key, default=None):
        """Get value with default"""
        try:
            return self[key]
        except KeyError:
            return default
    
    def keys(self):
        """Get all keys"""
        return self._db.keys()
    
    def clear(self):
        """Clear all data"""
        self._db.clear()
    
    def bulk_insert(self, items):
        """Bulk insert items (optimized)"""
        if isinstance(items, dict):
            items = items.items()
        
        prepared = {}
        for key, value in items:
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif not isinstance(value, bytes):
                import pickle
                value = pickle.dumps(value)
            prepared[str(key)] = value
        
        self._db.bulk_insert(prepared)
    
    def stats(self):
        """Get performance statistics"""
        return self._db.stats()
    
    def flush(self):
        """Flush hot tier to storage"""
        self._db.flush()


class AsyncDictSQLite:
    """
    Async version of DictSQLite v3.0 for high-concurrency scenarios
    """
    
    def __init__(self, db_path, capacity=1_000_000):
        """
        Initialize Async DictSQLite
        
        Args:
            db_path: Path to database file
            capacity: Maximum entries
        """
        if not _NATIVE_AVAILABLE:
            raise RuntimeError(
                "DictSQLite v3.0 native extension not available. "
                "Please build it using: cd dictsqlite_v3 && maturin develop --release"
            )
        
        self._db = _NativeAsyncDictSQLite(db_path, capacity)
    
    def get(self, key):
        """Get value (async)"""
        return self._db.get_async(str(key))
    
    def set(self, key, value):
        """Set value (async)"""
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes):
            import pickle
            value = pickle.dumps(value)
        self._db.set_async(str(key), value)
    
    def batch_get(self, keys):
        """Batch get (optimized for concurrent access)"""
        return self._db.batch_get([str(k) for k in keys])
    
    def batch_set(self, items):
        """Batch set (optimized for concurrent writes)"""
        prepared = []
        for key, value in items:
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif not isinstance(value, bytes):
                import pickle
                value = pickle.dumps(value)
            prepared.append((str(key), value))
        
        self._db.batch_set(prepared)
    
    def stats(self):
        """Get cache statistics"""
        size, capacity = self._db.stats()
        return {"size": size, "capacity": capacity}


def is_native_available():
    """Check if native extension is available"""
    return _NATIVE_AVAILABLE


__all__ = [
    'DictSQLiteV3',
    'AsyncDictSQLite',
    'is_native_available',
]
