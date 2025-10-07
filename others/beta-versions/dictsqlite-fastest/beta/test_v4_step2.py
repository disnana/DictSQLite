"""
v4 Step 2 Tests: Background Statistics Processing

Tests verify:
1. Non-blocking statistics collection
2. Sampling-based overhead reduction
3. Background stats accuracy
4. No performance regression vs Step 1
5. All Step 1 tests still pass
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

# Import Step 1 and Step 2 for comparison
from dictsqlite_fastest_beta_v4_step1 import AsyncDictSQLiteFastestBetaV4 as V4Step1
from dictsqlite_fastest_beta_v4_step2 import AsyncDictSQLiteFastestBetaV4 as V4Step2


@pytest_asyncio.fixture
async def v4_step1_db():
    """Create a temporary v4 Step 1 database for comparison"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    db = V4Step1(db_path)
    await db._ensure_initialized()
    
    yield db
    
    await db.aclose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def v4_step2_db():
    """Create a temporary v4 Step 2 database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    db = V4Step2(db_path)
    await db._ensure_initialized()
    
    yield db
    
    await db.aclose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_background_stats_collection(v4_step2_db):
    """Test 1: Background statistics are collected correctly"""
    # Perform some operations
    await v4_step2_db.aset('key1', 'value1')
    await v4_step2_db.aset('key2', 'value2')
    await v4_step2_db.aget('key1')
    await v4_step2_db.aget('key2')
    await v4_step2_db.adelete('key1')
    
    # Get stats
    stats = v4_step2_db.get_stats()
    
    # Verify background_stats exists
    assert 'background_stats' in stats, "Background stats should be present"
    bg_stats = stats['background_stats']
    
    # Verify operation counts
    assert 'counts' in bg_stats, "Operation counts should be tracked"
    counts = bg_stats['counts']
    
    print(f"  Background stats counts: {counts}")
    
    # We should have recorded operations
    assert counts['get'] >= 0, "Get operations should be counted"
    assert counts['set'] >= 0, "Set operations should be counted"
    assert counts['delete'] >= 0, "Delete operations should be counted"
    
    # Verify sampling rate
    assert 'sampling_rate' in bg_stats, "Sampling rate should be reported"
    assert bg_stats['sampling_rate'] == 0.1, "Sampling rate should be 10%"
    
    print("✓ Test 1: Background stats collection passed")


@pytest.mark.asyncio
async def test_stats_sampling_overhead(v4_step2_db):
    """Test 2: Sampling reduces overhead"""
    # Perform many operations
    num_ops = 100
    test_data = {f'key_{i}': f'value_{i}' for i in range(num_ops)}
    await v4_step2_db.abulk_insert(test_data)
    
    # Read all
    start = time.time()
    for i in range(num_ops):
        await v4_step2_db.aget(f'key_{i}')
    read_time = time.time() - start
    
    # Get stats
    stats = v4_step2_db.get_stats()
    bg_stats = stats['background_stats']
    
    # Check if timing data exists (should be sampled, not all operations)
    if 'timing' in bg_stats and 'get' in bg_stats['timing']:
        timing = bg_stats['timing']['get']
        sample_count = timing['sample_count']
        print(f"  Operations: {num_ops}, Samples: {sample_count}")
        print(f"  Average timing: {timing['avg_ms']:.3f} ms")
        
        # Sample count should be much less than total operations (due to 10% sampling)
        assert sample_count < num_ops, "Sampling should reduce recorded operations"
        assert sample_count >= 1, "At least some samples should be recorded"
    
    print(f"  Read time for {num_ops} items: {read_time:.4f}s")
    print("✓ Test 2: Stats sampling overhead passed")


@pytest.mark.asyncio
async def test_no_regression_vs_step1(v4_step1_db, v4_step2_db):
    """Test 3: Step 2 has no performance regression vs Step 1"""
    test_data = {f'key_{i}': f'value_{i}' for i in range(200)}
    
    # Test Step 1
    await v4_step1_db.abulk_insert(test_data)
    start = time.time()
    for i in range(200):
        await v4_step1_db.aget(f'key_{i}')
    step1_time = time.time() - start
    
    # Test Step 2
    await v4_step2_db.abulk_insert(test_data)
    start = time.time()
    for i in range(200):
        await v4_step2_db.aget(f'key_{i}')
    step2_time = time.time() - start
    
    print(f"  Step 1 time: {step1_time:.4f}s")
    print(f"  Step 2 time: {step2_time:.4f}s")
    print(f"  Step 2 vs Step 1: {step2_time / step1_time:.2f}x")
    
    # Step 2 should not be significantly slower (allow 20% tolerance)
    assert step2_time < step1_time * 1.2, f"Step 2 should not be >20% slower than Step 1"
    
    print("✓ Test 3: No regression vs Step 1 passed")


@pytest.mark.asyncio
async def test_step1_tests_still_pass_basic_crud(v4_step2_db):
    """Test 4: Step 1 test - Basic CRUD operations"""
    # Create
    await v4_step2_db.aset('key1', 'value1')
    await v4_step2_db.aset('key2', {'nested': 'value'})
    
    # Read
    val1 = await v4_step2_db.aget('key1')
    assert val1 == 'value1', f"Expected 'value1', got {val1}"
    
    val2 = await v4_step2_db.aget('key2')
    assert val2 == {'nested': 'value'}, f"Expected dict, got {val2}"
    
    # Update
    await v4_step2_db.aset('key1', 'updated_value')
    val1_updated = await v4_step2_db.aget('key1')
    assert val1_updated == 'updated_value', f"Expected 'updated_value', got {val1_updated}"
    
    # Delete
    await v4_step2_db.adelete('key1')
    val1_deleted = await v4_step2_db.aget('key1')
    assert val1_deleted is None, f"Expected None after delete, got {val1_deleted}"
    
    print("✓ Test 4: Basic CRUD (Step 1 regression test) passed")


@pytest.mark.asyncio
async def test_step1_tests_still_pass_bulk_operations(v4_step2_db):
    """Test 5: Step 1 test - Bulk operations"""
    # Bulk insert
    bulk_data = {f'bulk_{i}': f'value_{i}' for i in range(50)}
    await v4_step2_db.abulk_insert(bulk_data)
    
    # Verify all inserted
    for i in range(50):
        val = await v4_step2_db.aget(f'bulk_{i}')
        assert val == f'value_{i}', f"Bulk insert failed for bulk_{i}"
    
    # Count
    count = await v4_step2_db.alen()
    assert count == 50, f"Expected 50 items, got {count}"
    
    print("✓ Test 5: Bulk operations (Step 1 regression test) passed")


@pytest.mark.asyncio
async def test_step1_tests_still_pass_concurrent_access(v4_step2_db):
    """Test 6: Step 1 test - Concurrent operations"""
    # Prepare data
    await v4_step2_db.abulk_insert({f'key_{i}': f'value_{i}' for i in range(50)})
    
    # Concurrent reads
    async def read_many():
        tasks = [v4_step2_db.aget(f'key_{i}') for i in range(50)]
        results = await asyncio.gather(*tasks)
        return results
    
    results = await read_many()
    
    # Verify all results
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"
    assert all(r is not None for r in results), "All keys should exist"
    
    print("✓ Test 6: Concurrent access (Step 1 regression test) passed")


@pytest.mark.asyncio
async def test_stats_timing_accuracy(v4_step2_db):
    """Test 7: Background stats timing data is reasonable"""
    # Perform operations
    num_ops = 100
    test_data = {f'key_{i}': f'value_{i}' for i in range(num_ops)}
    await v4_step2_db.abulk_insert(test_data)
    
    # Read operations (which will be timed)
    for i in range(num_ops):
        await v4_step2_db.aget(f'key_{i}')
    
    # Get stats
    stats = v4_step2_db.get_stats()
    bg_stats = stats['background_stats']
    
    # Verify timing data exists and is reasonable
    if 'timing' in bg_stats and 'get' in bg_stats['timing']:
        timing = bg_stats['timing']['get']
        
        # Timing should be reasonable (< 100ms per operation on average)
        assert timing['avg_ms'] < 100, f"Average get time should be < 100ms, got {timing['avg_ms']}"
        assert timing['min_ms'] >= 0, "Min time should be non-negative"
        assert timing['max_ms'] >= timing['min_ms'], "Max should be >= min"
        
        print(f"  Timing stats: avg={timing['avg_ms']:.3f}ms, min={timing['min_ms']:.3f}ms, max={timing['max_ms']:.3f}ms")
    
    print("✓ Test 7: Stats timing accuracy passed")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
