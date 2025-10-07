"""Comprehensive benchmark: v1 vs v2 vs v3

Compares performance of all three versions with optimized configurations.
Tests basic operations, concurrent operations, and version-specific optimizations.
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Tuple, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta as AsyncV1
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncV2
from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3 as AsyncV3


class BenchmarkResult:
    """Stores benchmark results for a single test."""
    
    def __init__(self, name: str):
        self.name = name
        self.v1_time = 0.0
        self.v2_time = 0.0
        self.v3_time = 0.0
        self.v1_ops = 0.0
        self.v2_ops = 0.0
        self.v3_ops = 0.0
    
    def set_v1(self, elapsed: float, ops_per_sec: float):
        self.v1_time = elapsed
        self.v1_ops = ops_per_sec
    
    def set_v2(self, elapsed: float, ops_per_sec: float):
        self.v2_time = elapsed
        self.v2_ops = ops_per_sec
    
    def set_v3(self, elapsed: float, ops_per_sec: float):
        self.v3_time = elapsed
        self.v3_ops = ops_per_sec
    
    def print_comparison(self):
        """Print comparison of all versions."""
        print(f"\n{self.name}:")
        print(f"  v1: {self.v1_time:.3f}s ({self.v1_ops:.0f} ops/sec)")
        print(f"  v2: {self.v2_time:.3f}s ({self.v2_ops:.0f} ops/sec) - {self.v2_ops/self.v1_ops:.2f}x vs v1")
        print(f"  v3: {self.v3_time:.3f}s ({self.v3_ops:.0f} ops/sec) - {self.v3_ops/self.v1_ops:.2f}x vs v1")


async def benchmark_basic_write(db, count: int) -> Tuple[float, float]:
    """Benchmark basic write operations."""
    start = time.time()
    for i in range(count):
        await db.aset(f'key_{i}', f'value_{i}')
    # Ensure flush
    await asyncio.sleep(0.05)
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_basic_read(db, count: int) -> Tuple[float, float]:
    """Benchmark sequential read operations."""
    start = time.time()
    for i in range(count):
        await db.aget(f'key_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_concurrent_read(db, count: int, concurrency: int) -> Tuple[float, float]:
    """Benchmark concurrent read operations."""
    async def read_batch(start_idx, batch_size):
        for i in range(start_idx, start_idx + batch_size):
            await db.aget(f'key_{i % count}')
    
    batch_size = count // concurrency
    tasks = []
    for i in range(concurrency):
        tasks.append(read_batch(i * batch_size, batch_size))
    
    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_bulk_insert(db, count: int) -> Tuple[float, float]:
    """Benchmark bulk insert."""
    data = {f'bulk_key_{i}': f'bulk_value_{i}' for i in range(count)}
    
    start = time.time()
    await db.abulk_insert(data)
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_mixed_operations(db, count: int) -> Tuple[float, float]:
    """Benchmark mixed read/write operations."""
    start = time.time()
    for i in range(count):
        await db.aset(f'mixed_{i}', f'data_{i}')
        if i % 3 == 0:
            await db.aget(f'mixed_{i}')
        if i % 5 == 0:
            await db.adelete(f'mixed_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def run_v1_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for v1 with optimized settings."""
    print(f"\n{'='*70}")
    print(f"Benchmarking: v1 (ThreadPoolExecutor)")
    print(f"{'='*70}")
    
    results = {}
    
    # v1 uses ThreadPoolExecutor, so we configure it for optimal performance
    async with AsyncV1(db_path, memory_budget_mb=128) as db:
        # Basic operations
        print("\n1. Basic Write (300 items)...")
        elapsed, ops = await benchmark_basic_write(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items)...")
        elapsed, ops = await benchmark_basic_read(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Concurrent Read (600 items, 8 concurrent)...")
        elapsed, ops = await benchmark_concurrent_read(db, 600, 8)
        results['concurrent_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Bulk Insert (500 items)...")
        elapsed, ops = await benchmark_bulk_insert(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("5. Mixed Operations (400 items)...")
        elapsed, ops = await benchmark_mixed_operations(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
    
    return results


async def run_v2_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for v2 with optimized settings."""
    print(f"\n{'='*70}")
    print(f"Benchmarking: v2 (aiosqlite + batching)")
    print(f"{'='*70}")
    
    results = {}
    
    # v2 uses aiosqlite with batching - configure for best performance
    async with AsyncV2(db_path) as db:
        # Basic operations
        print("\n1. Basic Write (300 items)...")
        elapsed, ops = await benchmark_basic_write(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items)...")
        elapsed, ops = await benchmark_basic_read(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Concurrent Read (600 items, 8 concurrent)...")
        elapsed, ops = await benchmark_concurrent_read(db, 600, 8)
        results['concurrent_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Bulk Insert (500 items)...")
        elapsed, ops = await benchmark_bulk_insert(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("5. Mixed Operations (400 items)...")
        elapsed, ops = await benchmark_mixed_operations(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
    
    return results


async def run_v3_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for v3 with optimized settings."""
    print(f"\n{'='*70}")
    print(f"Benchmarking: v3 (Dynamic pool + prefetch + adaptive batch)")
    print(f"{'='*70}")
    
    results = {}
    
    # v3 has all advanced features - configure optimally
    async with AsyncV3(
        db_path,
        pool_min_size=2,
        pool_max_size=8,
        pool_auto_scale=True,
        enable_prefetch=True,
        adaptive_batch=True,
        extended_stats=True
    ) as db:
        # Basic operations
        print("\n1. Basic Write (300 items)...")
        elapsed, ops = await benchmark_basic_write(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items)...")
        elapsed, ops = await benchmark_basic_read(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Concurrent Read (600 items, 8 concurrent)...")
        elapsed, ops = await benchmark_concurrent_read(db, 600, 8)
        results['concurrent_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Bulk Insert (500 items)...")
        elapsed, ops = await benchmark_bulk_insert(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("5. Mixed Operations (400 items)...")
        elapsed, ops = await benchmark_mixed_operations(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        # Print v3 statistics
        if hasattr(db, 'get_stats'):
            stats = db.get_stats()
            print(f"\nv3 Statistics:")
            if 'pool' in stats:
                print(f"  Pool: {stats['pool']}")
            if 'prefetch' in stats:
                print(f"  Prefetch: {stats['prefetch']}")
    
    return results


async def main():
    """Main benchmark execution."""
    print("=" * 70)
    print("DictSQLite-Fastest: v1 vs v2 vs v3 Comprehensive Benchmark")
    print("=" * 70)
    print("\nThis benchmark tests:")
    print("  - Basic operations (write, read)")
    print("  - Concurrent operations")
    print("  - Bulk operations")
    print("  - Mixed operations")
    print("\nEach version is configured with its optimal settings.")
    
    # Create temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v1.db') as tmp:
        v1_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v2.db') as tmp:
        v2_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v3.db') as tmp:
        v3_path = tmp.name
    
    try:
        # Run benchmarks
        v1_results = await run_v1_benchmark(v1_path)
        v2_results = await run_v2_benchmark(v2_path)
        v3_results = await run_v3_benchmark(v3_path)
        
        # Create result objects
        test_names = ['basic_write', 'basic_read', 'concurrent_read', 'bulk_insert', 'mixed_ops']
        test_labels = [
            'Basic Write (300 items)',
            'Basic Read (300 items)',
            'Concurrent Read (600 items, 8 concurrent)',
            'Bulk Insert (500 items)',
            'Mixed Operations (400 items)'
        ]
        
        results = []
        for test_name, label in zip(test_names, test_labels):
            result = BenchmarkResult(label)
            result.set_v1(*v1_results[test_name])
            result.set_v2(*v2_results[test_name])
            result.set_v3(*v3_results[test_name])
            results.append(result)
        
        # Print comparison summary
        print(f"\n{'='*70}")
        print("Performance Comparison Summary")
        print(f"{'='*70}")
        
        for result in results:
            result.print_comparison()
        
        # Overall statistics
        print(f"\n{'='*70}")
        print("Overall Performance")
        print(f"{'='*70}")
        
        v1_avg = sum(r.v1_ops for r in results) / len(results)
        v2_avg = sum(r.v2_ops for r in results) / len(results)
        v3_avg = sum(r.v3_ops for r in results) / len(results)
        
        print(f"\nAverage throughput (ops/sec):")
        print(f"  v1: {v1_avg:.0f}")
        print(f"  v2: {v2_avg:.0f} ({v2_avg/v1_avg:.2f}x vs v1)")
        print(f"  v3: {v3_avg:.0f} ({v3_avg/v1_avg:.2f}x vs v1)")
        
        # Determine winner
        print(f"\n{'='*70}")
        print("Summary")
        print(f"{'='*70}")
        
        if v3_avg > v2_avg and v3_avg > v1_avg:
            improvement_vs_v1 = ((v3_avg / v1_avg) - 1) * 100
            improvement_vs_v2 = ((v3_avg / v2_avg) - 1) * 100
            print(f"✓ v3 is the fastest:")
            print(f"  - {improvement_vs_v1:.1f}% faster than v1")
            print(f"  - {improvement_vs_v2:.1f}% faster than v2")
        elif v2_avg > v1_avg:
            improvement = ((v2_avg / v1_avg) - 1) * 100
            print(f"✓ v2 is faster than v1 by {improvement:.1f}%")
            if v3_avg < v2_avg:
                regression = ((v2_avg / v3_avg) - 1) * 100
                print(f"  Note: v3 is {regression:.1f}% slower than v2 with current settings")
        else:
            print(f"✓ v1 performs well as the baseline")
        
        print(f"\n{'='*70}")
        print("✅ Benchmark completed successfully!")
        print(f"{'='*70}")
        
    finally:
        # Cleanup
        for path in [v1_path, v2_path, v3_path]:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
