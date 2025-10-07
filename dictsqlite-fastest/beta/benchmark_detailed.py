"""Detailed benchmark: Optimization-specific tests for v1, v2, and v3

Tests specific optimization features of each version:
- v1: Memory budget, cache efficiency, ThreadPoolExecutor
- v2: Batching, aiosqlite performance 
- v3: Connection pool scaling, prefetch patterns, adaptive batching
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Tuple, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta as AsyncV1
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncV2
from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3 as AsyncV3


async def test_v1_cache_efficiency(db_path: str):
    """Test v1's cache efficiency with repeated reads."""
    print("\n" + "="*70)
    print("v1: Cache Efficiency Test")
    print("="*70)
    
    async with AsyncV1(db_path, memory_budget_mb=64) as db:
        # Populate data
        print("Populating 1000 items...")
        for i in range(1000):
            await db.aset(f'cache_key_{i}', f'value_{i}')
        
        # First pass - cold cache
        print("First pass (cold cache)...")
        start = time.time()
        for i in range(500):
            await db.aget(f'cache_key_{i}')
        cold_time = time.time() - start
        cold_ops = 500 / cold_time
        
        # Second pass - warm cache
        print("Second pass (warm cache)...")
        start = time.time()
        for i in range(500):
            await db.aget(f'cache_key_{i}')
        warm_time = time.time() - start
        warm_ops = 500 / warm_time
        
        improvement = ((warm_ops / cold_ops) - 1) * 100
        print(f"\nResults:")
        print(f"  Cold cache: {cold_time:.3f}s ({cold_ops:.0f} ops/sec)")
        print(f"  Warm cache: {warm_time:.3f}s ({warm_ops:.0f} ops/sec)")
        print(f"  Cache improvement: {improvement:.1f}%")


async def test_v2_batching_efficiency(db_path: str):
    """Test v2's batching efficiency."""
    print("\n" + "="*70)
    print("v2: Batching Efficiency Test")
    print("="*70)
    
    async with AsyncV2(db_path) as db:
        # Test single writes
        print("Single writes (500 items)...")
        start = time.time()
        for i in range(500):
            await db.aset(f'single_{i}', f'value_{i}')
        single_time = time.time() - start
        single_ops = 500 / single_time
        
        # Test bulk insert
        print("Bulk insert (500 items)...")
        bulk_data = {f'bulk_{i}': f'value_{i}' for i in range(500)}
        start = time.time()
        await db.abulk_insert(bulk_data)
        bulk_time = time.time() - start
        bulk_ops = 500 / bulk_time
        
        improvement = ((bulk_ops / single_ops) - 1) * 100
        print(f"\nResults:")
        print(f"  Single writes: {single_time:.3f}s ({single_ops:.0f} ops/sec)")
        print(f"  Bulk insert:   {bulk_time:.3f}s ({bulk_ops:.0f} ops/sec)")
        print(f"  Batch improvement: {improvement:.1f}%")


async def test_v3_connection_pool_scaling(db_path: str):
    """Test v3's connection pool auto-scaling."""
    print("\n" + "="*70)
    print("v3: Connection Pool Scaling Test")
    print("="*70)
    
    async with AsyncV3(
        db_path,
        pool_min_size=2,
        pool_max_size=8,
        pool_auto_scale=True,
        enable_prefetch=False,
        adaptive_batch=False,
        extended_stats=True
    ) as db:
        # Populate data
        print("Populating 500 items...")
        for i in range(500):
            await db.aset(f'pool_key_{i}', f'value_{i}')
        
        # Low concurrency
        print("Low concurrency (2 concurrent tasks)...")
        async def read_batch(start_idx, count):
            for i in range(start_idx, start_idx + count):
                await db.aget(f'pool_key_{i % 500}')
        
        start = time.time()
        await asyncio.gather(
            read_batch(0, 100),
            read_batch(100, 100)
        )
        low_time = time.time() - start
        
        stats_low = db.get_stats()
        pool_low = stats_low.get('pool', {})
        
        # High concurrency
        print("High concurrency (8 concurrent tasks)...")
        start = time.time()
        tasks = [read_batch(i * 50, 50) for i in range(8)]
        await asyncio.gather(*tasks)
        high_time = time.time() - start
        
        stats_high = db.get_stats()
        pool_high = stats_high.get('pool', {})
        
        print(f"\nResults:")
        print(f"  Low concurrency:  {low_time:.3f}s")
        print(f"    Pool connections: {pool_low.get('active_connections', 0)}")
        print(f"  High concurrency: {high_time:.3f}s")
        print(f"    Pool connections: {pool_high.get('peak_connections', 0)}")
        print(f"    Pool scaled up: {pool_high.get('scaled_up', 0)} times")


async def test_v3_prefetch_patterns(db_path: str):
    """Test v3's prefetch pattern detection."""
    print("\n" + "="*70)
    print("v3: Prefetch Pattern Detection Test")
    print("="*70)
    
    async with AsyncV3(
        db_path,
        pool_min_size=2,
        pool_max_size=4,
        enable_prefetch=True,
        adaptive_batch=False,
        extended_stats=True
    ) as db:
        # Populate sequential data
        print("Populating 1000 items...")
        for i in range(1000):
            await db.aset(f'seq_key_{i}', f'value_{i}')
        
        # Sequential access pattern (should trigger prefetch)
        print("Sequential access pattern (0-199)...")
        start = time.time()
        for i in range(200):
            await db.aget(f'seq_key_{i}')
        seq_time = time.time() - start
        seq_ops = 200 / seq_time
        
        stats_seq = db.get_stats()
        prefetch_seq = stats_seq.get('prefetch', {})
        
        # Random access pattern (should not benefit from prefetch)
        print("Random access pattern (random 200 items)...")
        import random
        random_indices = random.sample(range(200, 1000), 200)
        
        start = time.time()
        for i in random_indices:
            await db.aget(f'seq_key_{i}')
        random_time = time.time() - start
        random_ops = 200 / random_time
        
        stats_random = db.get_stats()
        prefetch_random = stats_random.get('prefetch', {})
        
        print(f"\nResults:")
        print(f"  Sequential access: {seq_time:.3f}s ({seq_ops:.0f} ops/sec)")
        print(f"    Prefetch hits: {prefetch_seq.get('prefetch_hits', 0)}")
        print(f"    Patterns detected: {prefetch_seq.get('patterns_detected', 0)}")
        print(f"  Random access:     {random_time:.3f}s ({random_ops:.0f} ops/sec)")
        print(f"    Prefetch hits: {prefetch_random.get('prefetch_hits', 0)}")


async def test_concurrent_stress(db_path_v1: str, db_path_v2: str, db_path_v3: str):
    """Stress test with high concurrency for all versions."""
    print("\n" + "="*70)
    print("Concurrent Stress Test (All Versions)")
    print("="*70)
    
    async def stress_test(db, version_name: str, count: int, concurrency: int):
        print(f"\n{version_name}: {count} ops with {concurrency} concurrent tasks...")
        
        # Populate
        for i in range(count):
            await db.aset(f'stress_{i}', f'data_{i}')
        
        # Concurrent reads
        async def read_batch(start_idx, batch_size):
            for i in range(start_idx, start_idx + batch_size):
                await db.aget(f'stress_{i % count}')
        
        batch_size = count // concurrency
        tasks = [read_batch(i * batch_size, batch_size) for i in range(concurrency)]
        
        start = time.time()
        await asyncio.gather(*tasks)
        elapsed = time.time() - start
        ops_per_sec = count / elapsed
        
        print(f"  Time: {elapsed:.3f}s, Throughput: {ops_per_sec:.0f} ops/sec")
        return ops_per_sec
    
    # Test all versions
    async with AsyncV1(db_path_v1, memory_budget_mb=128) as db_v1:
        v1_ops = await stress_test(db_v1, "v1", 1000, 16)
    
    async with AsyncV2(db_path_v2) as db_v2:
        v2_ops = await stress_test(db_v2, "v2", 1000, 16)
    
    async with AsyncV3(
        db_path_v3,
        pool_min_size=4,
        pool_max_size=16,
        pool_auto_scale=True,
        enable_prefetch=True,
        adaptive_batch=True
    ) as db_v3:
        v3_ops = await stress_test(db_v3, "v3", 1000, 16)
    
    print(f"\nComparison:")
    print(f"  v1: {v1_ops:.0f} ops/sec (baseline)")
    print(f"  v2: {v2_ops:.0f} ops/sec ({v2_ops/v1_ops:.2f}x)")
    print(f"  v3: {v3_ops:.0f} ops/sec ({v3_ops/v1_ops:.2f}x)")


async def main():
    """Run detailed benchmarks."""
    print("=" * 70)
    print("DictSQLite-Fastest: Detailed Optimization Benchmarks")
    print("=" * 70)
    
    # Create temp files
    temp_files = []
    for i in range(6):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f'_test{i}.db')
        temp_files.append(tmp.name)
        tmp.close()
    
    try:
        # v1 tests
        await test_v1_cache_efficiency(temp_files[0])
        
        # v2 tests
        await test_v2_batching_efficiency(temp_files[1])
        
        # v3 tests
        await test_v3_connection_pool_scaling(temp_files[2])
        await test_v3_prefetch_patterns(temp_files[3])
        
        # Stress test
        await test_concurrent_stress(temp_files[4], temp_files[5], temp_files[5])
        
        print("\n" + "="*70)
        print("✅ All detailed benchmarks completed!")
        print("="*70)
        
    finally:
        # Cleanup
        for path in temp_files:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
