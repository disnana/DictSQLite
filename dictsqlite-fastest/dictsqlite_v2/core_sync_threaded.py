"""
DictSQLite V2 - Sync version with ThreadPoolExecutor for parallelism
Target: Push to Python's limits (10-20M ops/s with threading)
"""

import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

try:
    import apsw
except ImportError:
    apsw = None


class DictSQLiteV2Threaded:
    """
    Thread-pooled sync implementation.
    
    Target: Python's theoretical limits (10-20M ops/s with threads)
    - ThreadPoolExecutor for parallel operations
    - Thread-local APSW connections
    - Lock-free cache (thread-safe via ThreadPool coordination)
    """
    
    def __init__(
        self,
        db_name: str,
        num_threads: int = 8,
        cache_size: int = 100000
    ):
        if not apsw:
            raise ImportError("APSW required for sync operations")
            
        self.db_path = str(Path(db_name).absolute())
        self.num_threads = num_threads
        self.cache_size = cache_size
        
        # Main connection for setup
        self.conn = apsw.Connection(self.db_path)
        self._setup_database()
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=num_threads)
        
        # Memory cache with lock
        self.cache: Dict[str, Any] = {}
        self.dirty_keys: set = set()
        self.cache_lock = Lock()
        
        # Load data into cache
        self._load_cache()
    
    def _setup_database(self):
        """Setup database with optimal settings."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=100000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA page_size=65536")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value BLOB
            )
        """)
    
    def _load_cache(self):
        """Load existing data into cache."""
        cursor = self.conn.cursor()
        for key, value_blob in cursor.execute("SELECT key, value FROM kv_store"):
            self.cache[key] = pickle.loads(value_blob)
    
    def get(self, key: str, default=None) -> Any:
        """Get value from cache (fast, no lock for reads)."""
        return self.cache.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set value in cache and mark dirty."""
        with self.cache_lock:
            self.cache[key] = value
            self.dirty_keys.add(key)
    
    def delete(self, key: str):
        """Delete key from cache."""
        with self.cache_lock:
            self.cache.pop(key, None)
            self.dirty_keys.add(key)
    
    def bulk_insert(self, data: Dict[str, Any]):
        """Bulk insert - optimized with threads."""
        # Split data across threads
        items = list(data.items())
        chunk_size = len(items) // self.num_threads + 1
        
        def insert_chunk(chunk):
            for key, value in chunk:
                self.set(key, value)
        
        futures = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            future = self.executor.submit(insert_chunk, chunk)
            futures.append(future)
        
        # Wait for all threads
        for future in futures:
            future.result()
    
    def flush(self):
        """Flush dirty keys to SQLite."""
        if not self.dirty_keys:
            return
        
        with self.cache_lock:
            dirty_list = list(self.dirty_keys)
            self.dirty_keys.clear()
        
        # Batch write
        cursor = self.conn.cursor()
        
        with self.conn:  # Transaction
            for key in dirty_list:
                if key in self.cache:
                    value_blob = pickle.dumps(self.cache[key], protocol=5)
                    cursor.execute(
                        "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                        (key, value_blob)
                    )
    
    def close(self):
        """Flush and close."""
        self.flush()
        self.executor.shutdown(wait=True)
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # Dict-like API
    def __getitem__(self, key: str) -> Any:
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result
    
    def __setitem__(self, key: str, value: Any):
        self.set(key, value)
    
    def __delitem__(self, key: str):
        self.delete(key)
    
    def __contains__(self, key: str) -> bool:
        return key in self.cache
    
    def __len__(self) -> int:
        return len(self.cache)
    
    def keys(self):
        return self.cache.keys()
    
    def values(self):
        return self.cache.values()
    
    def items(self):
        return self.cache.items()
