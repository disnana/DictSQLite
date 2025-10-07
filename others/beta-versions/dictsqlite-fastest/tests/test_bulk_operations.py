"""Test suite for bulk operations and performance benchmarks."""

import pytest
import tempfile
import os
import asyncio
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest


@pytest.fixture()
def db_path():
    """Provide a temporary database file path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestBulkOperations:
    """Test bulk operations functionality."""

    def test_bulk_insert_basic(self, db_path):
        """Test basic bulk insert functionality."""
        with DictSQLiteFastest(db_path) as db:
            # Test with dictionary
            data = {f'key_{i}': f'value_{i}' for i in range(100)}
            db.bulk_insert(data)
            
            # Verify all items were inserted
            for key, expected_value in data.items():
                assert db[key] == expected_value

    def test_bulk_insert_list_of_tuples(self, db_path):
        """Test bulk insert with list of tuples."""
        with DictSQLiteFastest(db_path) as db:
            data = [(f'key_{i}', f'value_{i}') for i in range(50)]
            db.bulk_insert(data)
            
            # Verify all items were inserted
            for key, expected_value in data:
                assert db[key] == expected_value

    def test_bulk_get(self, db_path):
        """Test bulk get functionality."""
        with DictSQLiteFastest(db_path) as db:
            # Setup test data
            test_data = {f'test_key_{i}': {'id': i, 'data': f'item_{i}'} for i in range(100)}
            db.bulk_insert(test_data)
            
            # Test bulk get
            keys_to_get = [f'test_key_{i}' for i in range(0, 100, 10)]
            results = db.bulk_get(keys_to_get)
            
            # Verify results
            assert len(results) == len(keys_to_get)
            for key in keys_to_get:
                assert key in results
                assert results[key] == test_data[key]

    def test_bulk_get_nonexistent_keys(self, db_path):
        """Test bulk get with some nonexistent keys."""
        with DictSQLiteFastest(db_path) as db:
            # Setup some data
            test_data = {f'exists_{i}': f'value_{i}' for i in range(10)}
            db.bulk_insert(test_data)
            
            # Mix of existing and non-existing keys
            keys_to_get = ['exists_1', 'nonexistent_1', 'exists_5', 'nonexistent_2']
            results = db.bulk_get(keys_to_get)
            
            # Should only return existing keys
            assert len(results) == 2
            assert 'exists_1' in results
            assert 'exists_5' in results
            assert 'nonexistent_1' not in results
            assert 'nonexistent_2' not in results

    def test_bulk_delete(self, db_path):
        """Test bulk delete functionality."""
        with DictSQLiteFastest(db_path) as db:
            # Setup test data
            test_data = {f'del_key_{i}': f'value_{i}' for i in range(50)}
            db.bulk_insert(test_data)
            
            # Delete half the keys
            keys_to_delete = [f'del_key_{i}' for i in range(0, 50, 2)]
            db.bulk_delete(keys_to_delete)
            
            # Verify deletions
            for key in keys_to_delete:
                assert key not in db
            
            # Verify remaining keys still exist
            remaining_keys = [f'del_key_{i}' for i in range(1, 50, 2)]
            for key in remaining_keys:
                assert key in db

    def test_bulk_operations_empty(self, db_path):
        """Test bulk operations with empty inputs."""
        with DictSQLiteFastest(db_path) as db:
            # Empty operations should not fail
            db.bulk_insert({})
            db.bulk_insert([])
            
            results = db.bulk_get([])
            assert results == {}
            
            db.bulk_delete([])
            # Should not raise any errors

    def test_bulk_operations_json_mode(self, db_path):
        """Test bulk operations with JSON storage mode."""
        with DictSQLiteFastest(db_path, storage_mode='json') as db:
            test_data = {f'json_key_{i}': {'id': i, 'list': [1, 2, 3]} for i in range(20)}
            
            db.bulk_insert(test_data)
            
            keys = list(test_data.keys())[:10]
            results = db.bulk_get(keys)
            
            for key in keys:
                assert results[key] == test_data[key]


class TestAsyncBulkOperations:
    """Test async bulk operations."""

    @pytest.mark.asyncio
    async def test_async_bulk_insert(self, db_path):
        """Test async bulk insert."""
        db = AsyncDictSQLiteFastest(db_path)
        
        try:
            data = {f'async_key_{i}': f'async_value_{i}' for i in range(100)}
            await db.abulk_insert(data)
            
            # Verify with sync get
            sync_db = DictSQLiteFastest(db_path)
            for key, expected_value in data.items():
                assert sync_db[key] == expected_value
            sync_db.close()
            
        finally:
            await db.aclose()

    @pytest.mark.asyncio
    async def test_async_bulk_get(self, db_path):
        """Test async bulk get."""
        # Setup data with sync DB
        with DictSQLiteFastest(db_path) as sync_db:
            test_data = {f'async_get_{i}': {'value': i} for i in range(50)}
            sync_db.bulk_insert(test_data)
        
        # Test async bulk get
        db = AsyncDictSQLiteFastest(db_path)
        try:
            keys = [f'async_get_{i}' for i in range(0, 50, 5)]
            results = await db.abulk_get(keys)
            
            assert len(results) == len(keys)
            for key in keys:
                assert key in results
                assert results[key] == test_data[key]
        finally:
            await db.aclose()

    @pytest.mark.asyncio
    async def test_async_bulk_delete(self, db_path):
        """Test async bulk delete."""
        # Setup data
        with DictSQLiteFastest(db_path) as sync_db:
            test_data = {f'async_del_{i}': f'value_{i}' for i in range(30)}
            sync_db.bulk_insert(test_data)
        
        # Test async bulk delete
        db = AsyncDictSQLiteFastest(db_path)
        try:
            keys_to_delete = [f'async_del_{i}' for i in range(0, 30, 3)]
            await db.abulk_delete(keys_to_delete)
            
            # Verify with sync DB
            with DictSQLiteFastest(db_path) as verify_db:
                for key in keys_to_delete:
                    assert key not in verify_db
        finally:
            await db.aclose()


class TestBenchmarkIntegration:
    """Benchmark tests using pytest-benchmark."""

    def test_benchmark_bulk_insert_vs_individual(self, benchmark, db_path):
        """Benchmark bulk insert vs individual inserts."""
        test_data = {f'bench_key_{i}': f'bench_value_{i}' for i in range(1000)}
        
        def bulk_insert_func():
            with DictSQLiteFastest(db_path) as db:
                db.bulk_insert(test_data)
        
        # Benchmark bulk insert
        benchmark(bulk_insert_func)

    def test_benchmark_bulk_get_vs_individual(self, benchmark, db_path):
        """Benchmark bulk get vs individual gets."""
        # Setup data
        with DictSQLiteFastest(db_path) as db:
            test_data = {f'get_key_{i}': f'get_value_{i}' for i in range(1000)}
            db.bulk_insert(test_data)
        
        keys_to_get = [f'get_key_{i}' for i in range(0, 1000, 10)]
        
        def bulk_get_func():
            with DictSQLiteFastest(db_path) as db:
                return db.bulk_get(keys_to_get)
        
        # Benchmark bulk get
        result = benchmark(bulk_get_func)
        assert len(result) == len(keys_to_get)

    def test_benchmark_async_bulk_operations(self, benchmark, db_path):
        """Benchmark async bulk operations."""
        test_data = {f'async_bench_{i}': {'id': i, 'data': f'item_{i}'} for i in range(500)}
        
        async def async_bulk_operations():
            db = AsyncDictSQLiteFastest(db_path, max_connections=3)
            try:
                await db.abulk_insert(test_data)
                
                keys = [f'async_bench_{i}' for i in range(0, 500, 5)]
                results = await db.abulk_get(keys)
                
                await db.abulk_delete(keys[:50])
                
                return len(results)
            finally:
                await db.aclose()
        
        # Wrap async function for benchmark
        def sync_wrapper():
            return asyncio.run(async_bulk_operations())
        
        # Benchmark async operations
        result = benchmark(sync_wrapper)
        assert result == 100  # Should get 100 items (every 5th from 500)


class TestPerformanceOptimizations:
    """Test configurable performance optimizations."""

    def test_custom_cache_size(self, db_path):
        """Test custom cache size configuration."""
        with DictSQLiteFastest(db_path, cache_size=-128000) as db:  # 128MB cache
            # Test that database works with custom cache size
            test_data = {f'cache_key_{i}': f'cache_value_{i}' for i in range(100)}
            db.bulk_insert(test_data)
            
            results = db.bulk_get(list(test_data.keys())[:50])
            assert len(results) == 50

    def test_custom_mmap_size(self, db_path):
        """Test custom mmap size configuration."""
        with DictSQLiteFastest(db_path, mmap_size=134217728) as db:  # 128MB mmap
            # Test that database works with custom mmap size
            db['mmap_test'] = 'mmap_value'
            assert db['mmap_test'] == 'mmap_value'

    def test_custom_wal_autocheckpoint(self, db_path):
        """Test custom WAL autocheckpoint configuration."""
        with DictSQLiteFastest(db_path, wal_autocheckpoint=500) as db:
            # Test that database works with custom checkpoint interval
            test_data = {f'wal_key_{i}': f'wal_value_{i}' for i in range(100)}
            db.bulk_insert(test_data)
            
            assert len(db.bulk_get(list(test_data.keys()))) == 100