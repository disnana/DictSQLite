"""
v4 Step 1 Tests: Basic Structure and Fast Python Dict Cache

Tests verify:
1. Fast dict-based cache lookup
2. Basic CRUD operations  
3. No performance regression vs v3
4. Cache hit/miss tracking
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent))

# Import both v3 and v4 for comparison
from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3
from dictsqlite_fastest_beta_v4_step1 import AsyncDictSQLiteFastestBetaV4


def cleanup_db_files(db_path):
    """データベースファイルとWALファイルをクリーンアップ - 高速版"""
    # 性能比較テストのため、待機なしの高速クリーンアップ
    for ext in ['', '-wal', '-shm']:
        try:
            file_path = db_path + ext
            if os.path.exists(file_path):
                os.unlink(file_path)
        except (FileNotFoundError, PermissionError):
            # Windows環境でPermissionErrorが発生する可能性があるが無視
            pass
        except Exception:
            pass


@pytest_asyncio.fixture
async def v4_db():
    """Create a temporary v4 database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    db = AsyncDictSQLiteFastestBetaV4(db_path)
    await db._ensure_initialized()
    
    yield db
    
    await db.aclose()
    cleanup_db_files(db_path)


@pytest_asyncio.fixture
async def v3_db():
    """Create a temporary v3 database for comparison"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    db = AsyncDictSQLiteFastestBetaV3(db_path)
    await db._ensure_initialized()
    
    yield db
    
    await db.aclose()
    cleanup_db_files(db_path)


@pytest.mark.asyncio
async def test_basic_crud(v4_db):
    """Test 1: Basic CRUD operations work correctly"""
    # Create
    await v4_db.aset('key1', 'value1')
    await v4_db.aset('key2', {'nested': 'value'})
    
    # Read
    val1 = await v4_db.aget('key1')
    assert val1 == 'value1', f"Expected 'value1', got {val1}"
    
    val2 = await v4_db.aget('key2')
    assert val2 == {'nested': 'value'}, f"Expected dict, got {val2}"
    
    # Update
    await v4_db.aset('key1', 'updated_value')
    val1_updated = await v4_db.aget('key1')
    assert val1_updated == 'updated_value', f"Expected 'updated_value', got {val1_updated}"
    
    # Delete
    await v4_db.adelete('key1')
    val1_deleted = await v4_db.aget('key1')
    assert val1_deleted is None, f"Expected None after delete, got {val1_deleted}"
    
    print("✓ Test 1: Basic CRUD operations passed")


@pytest.mark.asyncio
async def test_fast_cache_lookup(v4_db):
    """Test 2: Fast dict-based cache provides speedup"""
    # Populate data
    test_data = {f'key_{i}': f'value_{i}' for i in range(100)}
    await v4_db.abulk_insert(test_data)
    
    # First read - will populate cache
    start = time.time()
    for i in range(100):
        await v4_db.aget(f'key_{i}')
    first_read_time = time.time() - start
    
    # Second read - should be from cache
    start = time.time()
    for i in range(100):
        await v4_db.aget(f'key_{i}')
    second_read_time = time.time() - start
    
    print(f"  First read: {first_read_time:.4f}s")
    print(f"  Second read (cached): {second_read_time:.4f}s")
    if first_read_time > 0:
        print(f"  Speedup: {first_read_time / second_read_time:.2f}x")
    
    # Both reads should be fast (< 1 second for 100 items)
    assert first_read_time < 1.0, "First read should be fast"
    assert second_read_time < 1.0, "Second read should be fast"
    
    print("✓ Test 2: Fast cache lookup passed")


@pytest.mark.asyncio
async def test_cache_stats(v4_db):
    """Test 3: Cache statistics are tracked"""
    # Set some data
    await v4_db.aset('test_key', 'test_value')
    
    # Read multiple times
    for _ in range(5):
        await v4_db.aget('test_key')
    
    # Get stats
    stats = v4_db.get_stats()
    
    # Verify cache stats exist
    assert 'cache' in stats, "Cache stats should be present"
    assert 'hit_rate' in stats['cache'], "Hit rate should be tracked"
    
    print(f"  Cache stats: {stats['cache']}")
    print("✓ Test 3: Cache stats tracking passed")


@pytest.mark.asyncio
async def test_no_regression_vs_v3(v3_db, v4_db):
    """Test 4: v4 performance is not worse than v3"""
    test_data = {f'key_{i}': f'value_{i}' for i in range(200)}
    
    # Test v3
    await v3_db.abulk_insert(test_data)
    start = time.time()
    for i in range(200):
        await v3_db.aget(f'key_{i}')
    v3_time = time.time() - start
    
    # Test v4
    await v4_db.abulk_insert(test_data)
    start = time.time()
    for i in range(200):
        await v4_db.aget(f'key_{i}')
    v4_time = time.time() - start
    
    print(f"  v3 time: {v3_time:.4f}s")
    print(f"  v4 time: {v4_time:.4f}s")
    print(f"  v4 vs v3: {v4_time / v3_time:.2f}x")
    
    # v4 should not be significantly slower (allow 20% tolerance)
    assert v4_time < v3_time * 1.2, f"v4 should not be >20% slower than v3"
    
    print("✓ Test 4: No regression vs v3 passed")


@pytest.mark.asyncio
async def test_bulk_operations(v4_db):
    """Test 5: Bulk operations work correctly"""
    # Bulk insert
    bulk_data = {f'bulk_{i}': f'value_{i}' for i in range(50)}
    await v4_db.abulk_insert(bulk_data)
    
    # Verify all inserted
    for i in range(50):
        val = await v4_db.aget(f'bulk_{i}')
        assert val == f'value_{i}', f"Bulk insert failed for bulk_{i}"
    
    # Count
    count = await v4_db.alen()
    assert count == 50, f"Expected 50 items, got {count}"
    
    print("✓ Test 5: Bulk operations passed")


@pytest.mark.asyncio
async def test_concurrent_access(v4_db):
    """Test 6: Concurrent operations don't cause errors"""
    # Prepare data
    await v4_db.abulk_insert({f'key_{i}': f'value_{i}' for i in range(50)})
    
    # Concurrent reads
    async def read_many():
        tasks = [v4_db.aget(f'key_{i}') for i in range(50)]
        results = await asyncio.gather(*tasks)
        return results
    
    results = await read_many()
    
    # Verify all results
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"
    assert all(r is not None for r in results), "All keys should exist"
    
    print("✓ Test 6: Concurrent access passed")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
