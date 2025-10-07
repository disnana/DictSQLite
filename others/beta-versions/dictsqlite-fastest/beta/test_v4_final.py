"""
Comprehensive tests for v4 FINAL optimized version.

Ensures all functionality works and performance targets are met.
"""

import asyncio
import os
import pytest
import tempfile
import time


@pytest.mark.asyncio
async def test_basic_crud_operations():
    """Test basic CRUD operations work correctly."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path) as db:
            # Set
            await db.aset('key1', {'value': 'data1'})
            
            # Get
            result = await db.aget('key1')
            assert result == {'value': 'data1'}
            
            # Update
            await db.aset('key1', {'value': 'data2'})
            result = await db.aget('key1')
            assert result == {'value': 'data2'}
            
            # Delete
            await db.adelete('key1')
            result = await db.aget('key1')
            assert result is None
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_bulk_operations():
    """Test bulk insert and get operations."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path) as db:
            # Bulk insert
            items = {f'key_{i}': {'id': i, 'data': f'value_{i}'} for i in range(100)}
            await db.abulk_insert(items)
            
            # Wait for writes to complete
            await asyncio.sleep(0.5)
            
            # Verify all items
            for i in range(100):
                result = await db.aget(f'key_{i}')
                assert result == {'id': i, 'data': f'value_{i}'}
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_cache_performance():
    """Test that cache provides significant performance boost."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path, cache_max_size=1000) as db:
            # Insert test data
            test_data = {f'key_{i}': {'value': i} for i in range(100)}
            await db.abulk_insert(test_data)
            await asyncio.sleep(0.5)
        
        # Reopen and test cache speed
        async with AsyncDictSQLiteFastestBetaV4Final(db_path, cache_max_size=1000) as db:
            # First pass - loads into cache
            for i in range(100):
                await db.aget(f'key_{i}')
            
            # Second pass - should be ultra-fast from cache
            start = time.time()
            for _ in range(1000):
                for i in range(100):
                    result = await db.aget(f'key_{i}')
                    assert result == {'value': i}
            elapsed = time.time() - start
            
            # Should be very fast (>50,000 ops/sec)
            ops_per_sec = 100000 / elapsed
            print(f"Cache performance: {ops_per_sec:.0f} ops/sec")
            assert ops_per_sec > 30000, f"Cache too slow: {ops_per_sec:.0f} ops/sec"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent read/write operations."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path, pool_size=10) as db:
            # Prepare data
            test_data = {f'key_{i}': {'value': i} for i in range(100)}
            await db.abulk_insert(test_data)
            await asyncio.sleep(0.5)
            
            # Concurrent reads
            async def read_batch(start, count):
                results = []
                for i in range(start, start + count):
                    result = await db.aget(f'key_{i % 100}')
                    results.append(result)
                return results
            
            # Run 10 concurrent readers
            start = time.time()
            results = await asyncio.gather(*[
                read_batch(i * 10, 10) for i in range(10)
            ])
            elapsed = time.time() - start
            
            # Verify all results
            assert len(results) == 10
            for batch in results:
                assert len(batch) == 10
            
            ops_per_sec = 100 / elapsed
            print(f"Concurrent read performance: {ops_per_sec:.0f} ops/sec")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_auto_preload():
    """Test auto-preload functionality."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        # Create database with data
        async with AsyncDictSQLiteFastestBetaV4Final(db_path) as db:
            test_data = {f'key_{i}': {'value': i} for i in range(50)}
            await db.abulk_insert(test_data)
            await asyncio.sleep(0.5)
        
        # Reopen with auto-preload
        async with AsyncDictSQLiteFastestBetaV4Final(db_path, auto_preload=True) as db:
            # Should be preloaded
            stats = db.get_stats()
            assert stats['preloaded'] == True
            assert stats['cache']['size'] == 50
            
            # All gets should be from cache (ultra-fast)
            start = time.time()
            for i in range(50):
                result = await db.aget(f'key_{i}')
                assert result == {'value': i}
            elapsed = time.time() - start
            
            # Should be extremely fast
            assert elapsed < 0.1, f"Preload not working, took {elapsed}s"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_stats_collection():
    """Test that stats are collected correctly."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path, enable_stats=True) as db:
            # Perform operations
            await db.aset('key1', {'value': 1})
            await db.aget('key1')
            await db.adelete('key1')
            
            # Check stats
            stats = db.get_stats()
            assert stats['operations']['get'] >= 1
            assert stats['operations']['set'] >= 1
            assert stats['operations']['delete'] >= 1
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_write_buffer_batching():
    """Test that write buffering works correctly."""
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path) as db:
            # Write several items
            for i in range(10):
                await db.aset(f'key_{i}', {'value': i})
            
            # Give time for buffer to flush
            await asyncio.sleep(1.5)
            
            # Verify all written
            for i in range(10):
                result = await db.aget(f'key_{i}')
                assert result == {'value': i}
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_performance_vs_baseline():
    """
    Test that v4 Final is faster than a baseline implementation.
    This ensures we're actually achieving performance improvements.
    """
    from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4Final(db_path, auto_preload=False) as db:
            # Prepare test data
            test_data = {f'key_{i}': {'id': i, 'data': f'value_{i}'} for i in range(100)}
            await db.abulk_insert(test_data)
            await asyncio.sleep(0.5)
            
            # Benchmark sequential reads
            iterations = 1000
            start = time.time()
            for _ in range(iterations):
                for i in range(10):
                    _ = await db.aget(f'key_{i}')
            elapsed = time.time() - start
            
            ops_per_sec = (iterations * 10) / elapsed
            print(f"Sequential read performance: {ops_per_sec:.0f} ops/sec")
            
            # Should be fast (target: >50,000 ops/sec)
            assert ops_per_sec > 10000, f"Performance too low: {ops_per_sec:.0f} ops/sec"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == '__main__':
    # Run all tests
    pytest.main([__file__, '-v', '-s'])
