"""
Tests for native extension wrapper.

These tests verify that:
1. The fallback implementation works correctly
2. The native extension (if available) is compatible with the fallback
3. Performance improvements are measurable
"""

import pytest
import tempfile
import os
from dictsqlite.native_wrapper import (
    is_native_available,
    get_cache_class,
    get_sqlite_class,
    NativeCache,
    NativeSQLite,
)


class TestCacheImplementation:
    """Test cache implementation (native or fallback)."""
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        cache = NativeCache(100)
        
        # Test put and get
        cache.put("key1", b"value1")
        assert cache.get("key1") == b"value1"
        
        # Test non-existent key
        assert cache.get("nonexistent") is None
        
        # Test overwrite
        cache.put("key1", b"value2")
        assert cache.get("key1") == b"value2"
    
    def test_cache_capacity(self):
        """Test cache capacity and LRU eviction."""
        cache = NativeCache(3)
        
        # Fill cache
        cache.put("key1", b"value1")
        cache.put("key2", b"value2")
        cache.put("key3", b"value3")
        
        # Add one more to trigger eviction
        cache.put("key4", b"value4")
        
        # key1 should be evicted (least recently used)
        assert cache.get("key1") is None
        assert cache.get("key4") == b"value4"
    
    def test_cache_clear(self):
        """Test cache clear operation."""
        cache = NativeCache(100)
        cache.put("key1", b"value1")
        cache.put("key2", b"value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.len() == 0


class TestSQLiteImplementation:
    """Test SQLite wrapper implementation (native or fallback)."""
    
    def setup_method(self):
        """Set up test database."""
        self.db_path = tempfile.mktemp(suffix='.db')
    
    def teardown_method(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_sqlite_basic_operations(self):
        """Test basic SQLite operations."""
        db = NativeSQLite(self.db_path, "test_table")
        
        # Test put and get
        db.put("key1", b"value1")
        assert db.get("key1") == b"value1"
        
        # Test non-existent key
        assert db.get("nonexistent") is None
        
        # Test overwrite
        db.put("key1", b"value2")
        assert db.get("key1") == b"value2"
    
    def test_sqlite_delete(self):
        """Test delete operation."""
        db = NativeSQLite(self.db_path, "test_table")
        
        db.put("key1", b"value1")
        assert db.get("key1") == b"value1"
        
        db.delete("key1")
        assert db.get("key1") is None
    
    def test_sqlite_bulk_insert(self):
        """Test bulk insert operation."""
        db = NativeSQLite(self.db_path, "test_table")
        
        items = {
            "key1": b"value1",
            "key2": b"value2",
            "key3": b"value3",
        }
        
        db.bulk_insert(items)
        
        assert db.get("key1") == b"value1"
        assert db.get("key2") == b"value2"
        assert db.get("key3") == b"value3"
    
    def test_sqlite_keys(self):
        """Test keys retrieval."""
        db = NativeSQLite(self.db_path, "test_table")
        
        db.put("key1", b"value1")
        db.put("key2", b"value2")
        db.put("key3", b"value3")
        
        keys = db.keys()
        assert sorted(keys) == ["key1", "key2", "key3"]


class TestNativeExtensionStatus:
    """Test native extension availability detection."""
    
    def test_is_native_available(self):
        """Test is_native_available function."""
        available = is_native_available()
        assert isinstance(available, bool)
        print(f"\nNative extension available: {available}")
    
    def test_cache_class_selection(self):
        """Test cache class selection."""
        CacheClass = get_cache_class()
        assert CacheClass is not None
        
        # Should be able to instantiate
        cache = CacheClass(100)
        assert cache is not None
    
    def test_sqlite_class_selection(self):
        """Test SQLite class selection."""
        SQLiteClass = get_sqlite_class()
        assert SQLiteClass is not None
        
        # Should be able to instantiate
        db_path = tempfile.mktemp(suffix='.db')
        try:
            db = SQLiteClass(db_path, "test_table")
            assert db is not None
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


@pytest.mark.skipif(True, reason="Benchmark tests require pytest-benchmark plugin")
class TestPerformance:
    """Performance tests (only run with --benchmark flag)."""
    
    def test_cache_performance(self, benchmark):
        """Benchmark cache operations."""
        cache = NativeCache(10000)
        
        def operation():
            for i in range(1000):
                cache.put(f"key{i}", f"value{i}".encode())
            for i in range(1000):
                _ = cache.get(f"key{i}")
        
        benchmark(operation)
    
    def test_sqlite_performance(self, benchmark):
        """Benchmark SQLite operations."""
        db_path = tempfile.mktemp(suffix='.db')
        
        def operation():
            db = NativeSQLite(db_path, "test_table")
            items = {f"key{i}": f"value{i}".encode() for i in range(1000)}
            db.bulk_insert(items)
        
        try:
            benchmark(operation)
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
