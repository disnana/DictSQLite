"""
Comprehensive tests for DictSQLite v3.0

Tests for:
- API compatibility with v1
- Context manager support
- Performance benchmarks
- All dict-like operations
"""

import pytest
import tempfile
import os
import time
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dictsqlite_v3 import DictSQLiteV3, AsyncDictSQLite, is_native_available
    NATIVE_AVAILABLE = is_native_available()
except ImportError:
    NATIVE_AVAILABLE = False
    DictSQLiteV3 = None
    AsyncDictSQLite = None


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native extension not built")
class TestDictSQLiteV3Compatibility:
    """Test v1 API compatibility"""
    
    def setup_method(self):
        """Create temporary database for each test"""
        self.db_file = tempfile.mktemp(suffix='.db')
    
    def teardown_method(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_file):
            os.unlink(self.db_file)
    
    def test_basic_crud(self):
        """Test basic create, read, update, delete operations"""
        db = DictSQLiteV3(self.db_file)
        
        # Create
        db['key1'] = b'value1'
        assert db['key1'] == b'value1'
        
        # Update
        db['key1'] = b'value2'
        assert db['key1'] == b'value2'
        
        # Delete
        del db['key1']
        assert 'key1' not in db
        
        # KeyError on missing key
        with pytest.raises(KeyError):
            _ = db['nonexistent']
        
        db.close()
    
    def test_dict_methods(self):
        """Test dict-like methods"""
        db = DictSQLiteV3(self.db_file)
        
        # get with default
        assert db.get('missing', 'default') == 'default'
        
        # setdefault
        result = db.setdefault('new_key', b'new_value')
        assert result == b'new_value'
        assert db['new_key'] == b'new_value'
        
        # update
        db.update({'k1': b'v1', 'k2': b'v2'})
        assert db['k1'] == b'v1'
        assert db['k2'] == b'v2'
        
        # update with kwargs
        db.update(k3=b'v3', k4=b'v4')
        assert db['k3'] == b'v3'
        
        # pop
        value = db.pop('k1')
        assert value == b'v1'
        assert 'k1' not in db
        
        # pop with default
        assert db.pop('missing', 'default') == 'default'
        
        db.close()
    
    def test_iteration(self):
        """Test iteration over keys, values, items"""
        db = DictSQLiteV3(self.db_file)
        
        # Add some data
        data = {f'key{i}': f'value{i}'.encode() for i in range(10)}
        db.bulk_insert(data)
        
        # Test keys()
        keys = list(db.keys())
        assert len(keys) == 10
        assert all(k in keys for k in data.keys())
        
        # Test values()
        values = db.values()
        assert len(values) == 10
        
        # Test items()
        items = db.items()
        assert len(items) == 10
        
        # Test __iter__
        iter_keys = list(db)
        assert set(iter_keys) == set(keys)
        
        # Test __len__
        assert len(db) == 10
        
        # Test __contains__
        assert 'key0' in db
        assert 'nonexistent' not in db
        
        db.close()
    
    def test_context_manager(self):
        """Test with statement support"""
        # Write data using context manager
        with DictSQLiteV3(self.db_file) as db:
            db['test_key'] = b'test_value'
            assert db['test_key'] == b'test_value'
        
        # Verify data persists after context exit
        with DictSQLiteV3(self.db_file) as db:
            assert db['test_key'] == b'test_value'
    
    def test_bulk_operations(self):
        """Test bulk insert for performance"""
        db = DictSQLiteV3(self.db_file)
        
        # Bulk insert
        items = {f'bulk{i}': f'value{i}'.encode() for i in range(1000)}
        db.bulk_insert(items)
        
        # Verify all items
        assert len(db) == 1000
        assert db['bulk0'] == b'value0'
        assert db['bulk999'] == b'value999'
        
        db.close()
    
    def test_clear(self):
        """Test clear operation"""
        db = DictSQLiteV3(self.db_file)
        
        # Add data
        db.update({f'k{i}': f'v{i}'.encode() for i in range(100)})
        assert len(db) == 100
        
        # Clear
        db.clear()
        assert len(db) == 0
        
        db.close()
    
    def test_stats(self):
        """Test statistics reporting"""
        db = DictSQLiteV3(self.db_file)
        
        # Add some data
        for i in range(100):
            db[f'key{i}'] = f'value{i}'.encode()
        
        # Get stats
        stats = db.stats()
        assert 'hot_tier_size' in stats
        assert stats['hot_tier_size'] == 100
        
        db.close()


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native extension not built")
class TestDictSQLiteV3Performance:
    """Performance tests"""
    
    def setup_method(self):
        """Create temporary database for each test"""
        self.db_file = tempfile.mktemp(suffix='.db')
    
    def teardown_method(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_file):
            os.unlink(self.db_file)
    
    def test_write_performance(self):
        """Test write performance - should be > 1M ops/sec"""
        db = DictSQLiteV3(self.db_file, hot_capacity=100000)
        
        num_ops = 10000
        start = time.perf_counter()
        
        for i in range(num_ops):
            db[f'key{i}'] = f'value{i}'.encode()
        
        elapsed = time.perf_counter() - start
        ops_per_sec = num_ops / elapsed
        
        print(f"\nWrite performance: {ops_per_sec:,.0f} ops/sec")
        
        # Should be much faster than v1 (which is ~1K ops/sec)
        assert ops_per_sec > 100_000, f"Write performance too low: {ops_per_sec:,.0f} ops/sec"
        
        db.close()
    
    def test_read_performance(self):
        """Test read performance - should be > 1M ops/sec"""
        db = DictSQLiteV3(self.db_file, hot_capacity=100000)
        
        # Pre-populate
        num_ops = 10000
        for i in range(num_ops):
            db[f'key{i}'] = f'value{i}'.encode()
        
        # Measure reads
        start = time.perf_counter()
        
        for i in range(num_ops):
            _ = db[f'key{i}']
        
        elapsed = time.perf_counter() - start
        ops_per_sec = num_ops / elapsed
        
        print(f"\nRead performance: {ops_per_sec:,.0f} ops/sec")
        
        # Should be much faster than v1
        assert ops_per_sec > 100_000, f"Read performance too low: {ops_per_sec:,.0f} ops/sec"
        
        db.close()
    
    def test_bulk_insert_performance(self):
        """Test bulk insert performance"""
        db = DictSQLiteV3(self.db_file, hot_capacity=100000)
        
        num_ops = 10000
        items = {f'key{i}': f'value{i}'.encode() for i in range(num_ops)}
        
        start = time.perf_counter()
        db.bulk_insert(items)
        elapsed = time.perf_counter() - start
        
        ops_per_sec = num_ops / elapsed
        
        print(f"\nBulk insert performance: {ops_per_sec:,.0f} ops/sec")
        
        # Bulk should be even faster
        assert ops_per_sec > 100_000, f"Bulk insert too low: {ops_per_sec:,.0f} ops/sec"
        
        db.close()


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native extension not built")
class TestAsyncDictSQLite:
    """Test async version"""
    
    def setup_method(self):
        """Create temporary database for each test"""
        self.db_file = tempfile.mktemp(suffix='.db')
    
    def teardown_method(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_file):
            os.unlink(self.db_file)
    
    def test_async_basic_operations(self):
        """Test async basic operations"""
        db = AsyncDictSQLite(self.db_file)
        
        # Set
        db.set('key1', b'value1')
        
        # Get
        value = db.get('key1')
        assert value == b'value1'
        
        # Stats
        stats = db.stats()
        assert stats['size'] == 1
    
    def test_async_batch_operations(self):
        """Test async batch operations"""
        db = AsyncDictSQLite(self.db_file)
        
        # Batch set
        items = [(f'key{i}', f'value{i}'.encode()) for i in range(100)]
        db.batch_set(items)
        
        # Batch get
        keys = [f'key{i}' for i in range(100)]
        values = db.batch_get(keys)
        
        assert len(values) == 100
        assert values[0] == b'value0'


@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native extension not built")
def test_native_available():
    """Test that native extension is detected"""
    assert is_native_available() == True


@pytest.mark.skipif(NATIVE_AVAILABLE, reason="Only test when native not available")
def test_fallback_error():
    """Test error when native extension not available"""
    with pytest.raises(RuntimeError, match="native extension not available"):
        db = DictSQLiteV3(":memory:")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
