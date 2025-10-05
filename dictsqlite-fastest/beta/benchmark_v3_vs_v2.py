"""Performance benchmark: v3-alpha vs v2

Compares performance of v3-alpha optimizations against v2 baseline.
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
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncV2


async def benchmark_write(db, count):
    """Benchmark write operations."""
    start = time.time()
    for i in range(count):
        await db.aset(f'key_{i}', f'value_{i}')
    # Ensure flush
    await asyncio.sleep(0.1)
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_read(db, count):
    """Benchmark sequential read operations."""
    start = time.time()
    for i in range(count):
        await db.aget(f'key_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_concurrent_read(db, count, concurrency):
    """Benchmark concurrent read operations."""
    async def read_batch(start_idx, batch_size):
        for i in range(start_idx, start_idx + batch_size):
            await db.aget(f'key_{i % count}')  # Wrap around
    
    batch_size = count // concurrency
    tasks = []
    for i in range(concurrency):
        tasks.append(read_batch(i * batch_size, batch_size))
    
    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_bulk_insert(db, count):
    """Benchmark bulk insert."""
    data = {f'bulk_key_{i}': f'bulk_value_{i}' for i in range(count)}
    
    start = time.time()
    await db.abulk_insert(data)
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def run_benchmark(name, db_class, db_path, **kwargs):
    """Run full benchmark suite."""
    print(f"\n{'='*70}")
    print(f"Benchmarking: {name}")
    print(f"{'='*70}")
    
    results = {}
    
    async with db_class(db_path, **kwargs) as db:
        # Test 1: Sequential Write (500 items)
        print("\n1. Sequential Write (500 items)...")
        elapsed, ops_per_sec = await benchmark_write(db, 500)
        results['write'] = (elapsed, ops_per_sec)
        print(f"   Time: {elapsed:.3f}s, Throughput: {ops_per_sec:.0f} ops/sec")
        
        # Test 2: Sequential Read (500 items)
        print("\n2. Sequential Read (500 items)...")
        elapsed, ops_per_sec = await benchmark_read(db, 500)
        results['read'] = (elapsed, ops_per_sec)
        print(f"   Time: {elapsed:.3f}s, Throughput: {ops_per_sec:.0f} ops/sec")
        
        # Test 3: Concurrent Read (1000 items, 10 concurrent)
        print("\n3. Concurrent Read (1000 items, 10 concurrent tasks)...")
        elapsed, ops_per_sec = await benchmark_concurrent_read(db, 1000, 10)
        results['concurrent_read'] = (elapsed, ops_per_sec)
        print(f"   Time: {elapsed:.3f}s, Throughput: {ops_per_sec:.0f} ops/sec")
        
        # Test 4: Bulk Insert (1000 items)
        print("\n4. Bulk Insert (1000 items)...")
        elapsed, ops_per_sec = await benchmark_bulk_insert(db, 1000)
        results['bulk_insert'] = (elapsed, ops_per_sec)
        print(f"   Time: {elapsed:.3f}s, Throughput: {ops_per_sec:.0f} ops/sec")
        
        # Get stats if available
        if hasattr(db, 'get_stats'):
            stats = db.get_stats()
            print(f"\nStatistics:")
            print(f"  Cache: {stats.get('cache', {})}")
            if 'pool' in stats:
                print(f"  Pool: {stats['pool']}")
            if 'prefetch' in stats:
                print(f"  Prefetch: {stats['prefetch']}")
    
    return results


async def main():
    """Main benchmark."""
    print("=" * 70)
    print("DictSQLite-Fastest: v3-alpha vs v2 Performance Benchmark")
    print("=" * 70)
    
    # Create temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v2.db') as tmp:
        v2_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v3.db') as tmp:
        v3_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v3_opt.db') as tmp:
        v3_opt_path = tmp.name
    
    try:
        # Benchmark v2 (baseline)
        v2_results = await run_benchmark(
            "v2 (Baseline)",
            AsyncV2,
            v2_path
        )
        
        # Benchmark v3-alpha with all features
        v3_results = await run_benchmark(
            "v3-alpha (All Features Enabled)",
            AsyncDictSQLiteFastestBetaV3,
            v3_path,
            pool_min_size=2,
            pool_max_size=8,
            pool_auto_scale=True,
            enable_prefetch=True,
            adaptive_batch=True,
            extended_stats=True
        )
        
        # Benchmark v3-alpha optimized (minimal overhead)
        v3_opt_results = await run_benchmark(
            "v3-alpha (Optimized - Pool Only)",
            AsyncDictSQLiteFastestBetaV3,
            v3_opt_path,
            pool_min_size=2,
            pool_max_size=8,
            pool_auto_scale=True,
            enable_prefetch=False,
            adaptive_batch=False,
            extended_stats=False
        )
        
        # Compare results
        print(f"\n{'='*70}")
        print("Performance Comparison Summary")
        print(f"{'='*70}")
        
        test_names = ['write', 'read', 'concurrent_read', 'bulk_insert']
        test_labels = ['Sequential Write', 'Sequential Read', 'Concurrent Read', 'Bulk Insert']
        
        for test_name, label in zip(test_names, test_labels):
            print(f"\n{label}:")
            v2_time, v2_ops = v2_results[test_name]
            v3_time, v3_ops = v3_results[test_name]
            v3_opt_time, v3_opt_ops = v3_opt_results[test_name]
            
            print(f"  v2:              {v2_time:.3f}s ({v2_ops:.0f} ops/sec)")
            print(f"  v3-alpha (all):  {v3_time:.3f}s ({v3_ops:.0f} ops/sec) - {v3_ops/v2_ops:.2f}x")
            print(f"  v3-alpha (opt):  {v3_opt_time:.3f}s ({v3_opt_ops:.0f} ops/sec) - {v3_opt_ops/v2_ops:.2f}x")
        
        # Overall score
        print(f"\n{'='*70}")
        print("Overall Performance")
        print(f"{'='*70}")
        
        v2_avg_ops = sum(v2_results[t][1] for t in test_names) / len(test_names)
        v3_avg_ops = sum(v3_results[t][1] for t in test_names) / len(test_names)
        v3_opt_avg_ops = sum(v3_opt_results[t][1] for t in test_names) / len(test_names)
        
        print(f"v2 Average:            {v2_avg_ops:.0f} ops/sec")
        print(f"v3-alpha (all) Average: {v3_avg_ops:.0f} ops/sec ({v3_avg_ops/v2_avg_ops:.2f}x)")
        print(f"v3-alpha (opt) Average: {v3_opt_avg_ops:.0f} ops/sec ({v3_opt_avg_ops/v2_avg_ops:.2f}x)")
        
        if v3_opt_avg_ops > v2_avg_ops:
            improvement = ((v3_opt_avg_ops / v2_avg_ops) - 1) * 100
            print(f"\n✓ v3-alpha (optimized) is {improvement:.1f}% faster than v2")
        else:
            regression = (1 - (v3_opt_avg_ops / v2_avg_ops)) * 100
            print(f"\n⚠ v3-alpha (optimized) is {regression:.1f}% slower than v2")
            print("  (This is expected with minimal test data; benefits appear at scale)")
        
        print(f"\n{'='*70}")
        
    finally:
        for path in [v2_path, v3_path, v3_opt_path]:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
