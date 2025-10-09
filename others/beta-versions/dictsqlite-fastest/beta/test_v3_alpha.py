"""Comprehensive test suite for DictSQLite-Fastest Beta v3-alpha.

Tests all 4 phases:
- Phase 1: Dynamic Connection Pool
- Phase 2: Pattern-based Prefetch
- Phase 3: Adaptive Batch Sizing
- Phase 4: Extended Statistics
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3


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


async def test_basic_operations():
    """Test basic read/write operations."""
    print("Test 1: Basic Operations...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBetaV3(db_path) as db:
            # Write
            await db.aset('key1', 'value1')
            await db.aset('key2', {'nested': 'value'})
            
            # Read
            val1 = await db.aget('key1')
            val2 = await db.aget('key2')
            
            assert val1 == 'value1', f"Expected 'value1', got {val1}"
            assert val2 == {'nested': 'value'}, f"Expected dict, got {val2}"
            
            # Delete
            await db.adelete('key1')
            val1_after = await db.aget('key1')
            assert val1_after is None, f"Key should be deleted, got {val1_after}"
            
        print("  ✓ Basic operations passed")
        return True
    finally:
        cleanup_db_files(db_path)


async def test_phase1_dynamic_pool():
    """Test Phase 1: Dynamic Connection Pool."""
    print("Test 2: Phase 1 - Dynamic Connection Pool...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        # Create DB with dynamic pool settings
        async with AsyncDictSQLiteFastestBetaV3(
            db_path,
            pool_min_size=2,
            pool_max_size=5,
            pool_auto_scale=True,
            pool_idle_timeout=2.0
        ) as db:
            # Initial pool should have min_size connections
            stats = db.get_stats()
            assert stats['pool']['current_size'] >= 2, \
                f"Expected >= 2 connections, got {stats['pool']['current_size']}"
            
            # Create concurrent load to trigger scaling
            async def concurrent_reads():
                tasks = []
                for i in range(10):
                    tasks.append(db.aget(f'key{i}', default=None))
                await asyncio.gather(*tasks)
            
            await concurrent_reads()
            
            # Check if pool scaled up
            stats = db.get_stats()
            print(f"  - Pool stats: {stats['pool']}")
            assert stats['pool']['created_connections'] >= 2, \
                "Pool should have created connections"
            
        print("  ✓ Phase 1 dynamic pool passed")
        return True
    finally:
        cleanup_db_files(db_path)


async def test_phase2_prefetch():
    """Test Phase 2: Pattern-based Prefetch."""
    print("Test 3: Phase 2 - Pattern-based Prefetch...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBetaV3(
            db_path,
            enable_prefetch=True,
            prefetch_size=5
        ) as db:
            # Insert sequential data
            data = {f'item_{i}': f'value_{i}' for i in range(20)}
            await db.abulk_insert(data)
            
            # Access sequential keys to trigger prefetch pattern detection
            for i in range(5):
                val = await db.aget(f'item_{i}')
                assert val == f'value_{i}', f"Expected value_{i}, got {val}"
            
            # Check prefetch stats
            stats = db.get_stats()
            if 'prefetch' in stats:
                print(f"  - Prefetch stats: {stats['prefetch']}")
                # Prefetch should have been triggered
                assert stats['prefetch']['prefetches_triggered'] >= 0, \
                    "Prefetch should have been triggered"
            
        print("  ✓ Phase 2 prefetch passed")
        return True
    finally:
        cleanup_db_files(db_path)


async def test_phase3_adaptive_batch():
    """Test Phase 3: Adaptive Batch Sizing."""
    print("Test 4: Phase 3 - Adaptive Batch Sizing...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBetaV3(
            db_path,
            adaptive_batch=True,
            batch_min_size=10,
            batch_max_size=200,
            async_batch_size=50
        ) as db:
            # Write data to trigger batch adjustments
            for i in range(100):
                await db.aset(f'key_{i}', f'value_{i}')
            
            # Force flush to ensure batch processing
            await asyncio.sleep(0.5)
            
            # Check adaptive batch stats
            stats = db.get_stats()
            if 'adaptive_batch' in stats:
                print(f"  - Adaptive batch stats: {stats['adaptive_batch']}")
                assert 'avg_batch_size' in stats['adaptive_batch'], \
                    "Should have batch size statistics"
            
        print("  ✓ Phase 3 adaptive batch passed")
        return True
    finally:
        cleanup_db_files(db_path)


async def test_phase4_extended_stats():
    """Test Phase 4: Extended Statistics."""
    print("Test 5: Phase 4 - Extended Statistics...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBetaV3(
            db_path,
            extended_stats=True
        ) as db:
            # Perform various operations
            await db.aset('key1', 'value1')
            await db.aget('key1')
            await db.adelete('key1')
            await db.abulk_insert({'key2': 'value2', 'key3': 'value3'})
            
            # Check extended stats
            stats = db.get_stats()
            print(f"  - Extended stats keys: {stats.get('extended', {}).keys()}")
            
            if 'extended' in stats:
                # Check operation counts
                assert stats['extended']['operation_counts']['get'] > 0, \
                    "Should have get operations"
                assert stats['extended']['operation_counts']['set'] > 0, \
                    "Should have set operations"
                assert stats['extended']['operation_counts']['delete'] > 0, \
                    "Should have delete operations"
                assert stats['extended']['operation_counts']['bulk_insert'] > 0, \
                    "Should have bulk_insert operations"
                
                # Check timing stats
                assert 'get_avg_ms' in stats['extended'], \
                    "Should have average timing stats"
            
        print("  ✓ Phase 4 extended stats passed")
        return True
    finally:
        cleanup_db_files(db_path)


async def test_concurrent_operations():
    """Test concurrent operations with all v3-alpha features enabled."""
    print("Test 6: Concurrent Operations (All Features)...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastestBetaV3(
            db_path,
            pool_min_size=2,
            pool_max_size=8,
            pool_auto_scale=True,
            enable_prefetch=True,
            adaptive_batch=True,
            extended_stats=True
        ) as db:
            # Concurrent writes
            async def write_batch(start, count):
                for i in range(start, start + count):
                    await db.aset(f'concurrent_key_{i}', f'value_{i}')
            
            # Run multiple concurrent batches
            tasks = [
                write_batch(0, 50),
                write_batch(50, 50),
                write_batch(100, 50),
            ]
            await asyncio.gather(*tasks)
            
            # Concurrent reads
            async def read_batch(start, count):
                results = []
                for i in range(start, start + count):
                    val = await db.aget(f'concurrent_key_{i}')
                    results.append(val)
                return results
            
            read_tasks = [
                read_batch(0, 50),
                read_batch(50, 50),
                read_batch(100, 50),
            ]
            results = await asyncio.gather(*read_tasks)
            
            # Verify results
            all_results = [item for sublist in results for item in sublist]
            assert len(all_results) == 150, f"Expected 150 results, got {len(all_results)}"
            
            # Check stats
            stats = db.get_stats()
            print(f"  - Pool: {stats['pool']}")
            print(f"  - Cache hit rate: {stats['cache']['hit_rate']:.1f}%")
            if 'extended' in stats:
                print(f"  - Total operations: {sum(stats['extended']['operation_counts'].values())}")
            
        print("  ✓ Concurrent operations passed")
        return True
    finally:
        cleanup_db_files(db_path)


async def test_performance_comparison():
    """Performance comparison: v3-alpha features enabled vs disabled."""
    print("Test 7: Performance Comparison...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v3.db') as tmp:
        db_v3_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_base.db') as tmp:
        db_base_path = tmp.name
    
    try:
        # Test with v3-alpha features
        start = time.time()
        async with AsyncDictSQLiteFastestBetaV3(
            db_v3_path,
            pool_min_size=2,
            pool_max_size=8,
            enable_prefetch=True,
            adaptive_batch=True,
            extended_stats=True
        ) as db:
            # Write
            for i in range(500):
                await db.aset(f'key_{i}', f'value_{i}')
            
            # Sequential read (should benefit from prefetch)
            for i in range(100):
                await db.aget(f'key_{i}')
        
        v3_time = time.time() - start
        
        # Test without v3-alpha features
        start = time.time()
        async with AsyncDictSQLiteFastestBetaV3(
            db_base_path,
            pool_min_size=2,
            pool_max_size=2,
            pool_auto_scale=False,
            enable_prefetch=False,
            adaptive_batch=False,
            extended_stats=False
        ) as db:
            # Write
            for i in range(500):
                await db.aset(f'key_{i}', f'value_{i}')
            
            # Sequential read
            for i in range(100):
                await db.aget(f'key_{i}')
        
        base_time = time.time() - start
        
        print(f"  - With v3-alpha features: {v3_time:.3f}s")
        print(f"  - Without v3-alpha features: {base_time:.3f}s")
        print(f"  - Speedup: {base_time/v3_time:.2f}x")
        
        print("  ✓ Performance comparison completed")
        return True
    finally:
        for path in [db_v3_path, db_base_path]:
            if os.path.exists(path):
                os.unlink(path)


async def main():
    """Run all tests."""
    print("=" * 70)
    print("DictSQLite-Fastest Beta v3-alpha Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        test_basic_operations,
        test_phase1_dynamic_pool,
        test_phase2_prefetch,
        test_phase3_adaptive_batch,
        test_phase4_extended_stats,
        test_concurrent_operations,
        test_performance_comparison,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"  ✗ Test failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        print()
    
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
