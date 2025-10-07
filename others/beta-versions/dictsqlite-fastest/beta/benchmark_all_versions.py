"""Comprehensive benchmark: v1 vs v2 vs v3 vs v4

Compares performance of all four versions with optimized configurations.
Tests basic operations, concurrent operations, and version-specific optimizations.
"""

import asyncio
import csv
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Tuple, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta as AsyncV1
from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncV2
from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3 as AsyncV3
from dictsqlite_fastest_beta_v4_final import AsyncDictSQLiteFastestBetaV4Final as AsyncV4


class BenchmarkResult:
    """Stores benchmark results for a single test."""
    
    def __init__(self, name: str):
        self.name = name
        self.v1_time = 0.0
        self.v2_time = 0.0
        self.v3_time = 0.0
        self.v4_time = 0.0
        self.v1_ops = 0.0
        self.v2_ops = 0.0
        self.v3_ops = 0.0
        self.v4_ops = 0.0
    
    def set_v1(self, elapsed: float, ops_per_sec: float):
        self.v1_time = elapsed
        self.v1_ops = ops_per_sec
    
    def set_v2(self, elapsed: float, ops_per_sec: float):
        self.v2_time = elapsed
        self.v2_ops = ops_per_sec
    
    def set_v3(self, elapsed: float, ops_per_sec: float):
        self.v3_time = elapsed
        self.v3_ops = ops_per_sec
    
    def set_v4(self, elapsed: float, ops_per_sec: float):
        self.v4_time = elapsed
        self.v4_ops = ops_per_sec
    
    def print_comparison(self):
        """Print comparison of all versions."""
        print(f"\n{self.name}:")
        print(f"  v1: {self.v1_time:.3f}s ({self.v1_ops:>8.0f} ops/sec)")
        print(f"  v2: {self.v2_time:.3f}s ({self.v2_ops:>8.0f} ops/sec) - {self.v2_ops/self.v1_ops:>5.2f}x vs v1")
        print(f"  v3: {self.v3_time:.3f}s ({self.v3_ops:>8.0f} ops/sec) - {self.v3_ops/self.v1_ops:>5.2f}x vs v1")
        print(f"  v4: {self.v4_time:.3f}s ({self.v4_ops:>8.0f} ops/sec) - {self.v4_ops/self.v1_ops:>5.2f}x vs v1")


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


async def run_v4_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for v4 with optimized settings."""
    print(f"\n{'='*70}")
    print(f"Benchmarking: v4 (Ultra-optimized cache + connection pool)")
    print(f"{'='*70}")
    
    results = {}
    
    # v4 has maximum performance optimizations
    async with AsyncV4(
        db_path,
        cache_max_size=10000,
        enable_stats=True,
        pool_size=8,
        auto_preload=False
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
        
        # Print v4 statistics
        if hasattr(db, '_stats') and hasattr(db._stats, 'get_stats'):
            stats = db._stats.get_stats()
            print(f"\nv4 Statistics:")
            print(f"  Operations: {stats}")
    
    return results


async def main():
    """Main benchmark execution."""
    print("=" * 70)
    print("DictSQLite-Fastest: v1 vs v2 vs v3 vs v4 Comprehensive Benchmark")
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
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v4.db') as tmp:
        v4_path = tmp.name
    
    try:
        # Run benchmarks
        v1_results = await run_v1_benchmark(v1_path)
        v2_results = await run_v2_benchmark(v2_path)
        v3_results = await run_v3_benchmark(v3_path)
        v4_results = await run_v4_benchmark(v4_path)
        
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
            result.set_v4(*v4_results[test_name])
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
        v4_avg = sum(r.v4_ops for r in results) / len(results)
        
        print(f"\nAverage throughput (ops/sec):")
        print(f"  v1: {v1_avg:>10.0f}")
        print(f"  v2: {v2_avg:>10.0f} ({v2_avg/v1_avg:>5.2f}x vs v1)")
        print(f"  v3: {v3_avg:>10.0f} ({v3_avg/v1_avg:>5.2f}x vs v1)")
        print(f"  v4: {v4_avg:>10.0f} ({v4_avg/v1_avg:>5.2f}x vs v1)")
        
        # Determine winner
        print(f"\n{'='*70}")
        print("Summary")
        print(f"{'='*70}")
        
        versions = [('v1', v1_avg), ('v2', v2_avg), ('v3', v3_avg), ('v4', v4_avg)]
        sorted_versions = sorted(versions, key=lambda x: x[1], reverse=True)
        winner = sorted_versions[0]
        
        print(f"\n🏆 Winner: {winner[0]} ({winner[1]:.0f} ops/sec)")
        print(f"\nPerformance ranking:")
        for i, (name, ops) in enumerate(sorted_versions, 1):
            vs_baseline = ((ops / v1_avg) - 1) * 100
            print(f"  {i}. {name}: {ops:>10.0f} ops/sec ({vs_baseline:+.1f}% vs v1)")
        
        # Show improvements
        print(f"\nKey improvements:")
        if v4_avg > v3_avg:
            improvement = ((v4_avg / v3_avg) - 1) * 100
            print(f"  ✓ v4 is {improvement:.1f}% faster than v3")
        if v3_avg > v2_avg:
            improvement = ((v3_avg / v2_avg) - 1) * 100
            print(f"  ✓ v3 is {improvement:.1f}% faster than v2")
        if v2_avg > v1_avg:
            improvement = ((v2_avg / v1_avg) - 1) * 100
            print(f"  ✓ v2 is {improvement:.1f}% faster than v1")
        
        print(f"\n{'='*70}")
        print("✅ Benchmark completed successfully!")
        print(f"{'='*70}")
        
        # Save results to CSV and generate graphs
        save_results_and_generate_graphs(results)
        
    finally:
        # Cleanup
        for path in [v1_path, v2_path, v3_path, v4_path]:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


def save_results_and_generate_graphs(results: List['BenchmarkResult']):
    """Save benchmark results to CSV in the expected format and generate graphs."""
    # Determine output directory
    benchmark_dir = Path(__file__).parent.parent.parent.parent / 'benchmark'
    results_dir = benchmark_dir / 'results' / 'versions' / 'all'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = results_dir / 'benchmark.csv'
    
    print(f"\n{'='*70}")
    print(f"Saving results to: {csv_path}")
    print(f"{'='*70}")
    
    # Write CSV in Long format (compatible with generate_graphs.py)
    csv_rows = []
    for result in results:
        # Add rows for each version
        csv_rows.append({
            'Version': 'original',
            'Test': result.name,
            'OPS': result.v1_ops,
            'Duration(s)': result.v1_time,
            'Result': '成功'
        })
        csv_rows.append({
            'Version': 'fastest',
            'Test': result.name,
            'OPS': result.v2_ops,
            'Duration(s)': result.v2_time,
            'Result': '成功'
        })
        csv_rows.append({
            'Version': 'beta',
            'Test': result.name,
            'OPS': result.v4_ops,  # Use v4 as beta
            'Duration(s)': result.v4_time,
            'Result': '成功'
        })
    
    # Write CSV file
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if csv_rows:
            writer = csv.DictWriter(f, fieldnames=['Version', 'Test', 'OPS', 'Duration(s)', 'Result'])
            writer.writeheader()
            writer.writerows(csv_rows)
    
    print(f"✓ CSV saved: {csv_path}")
    
    # Generate graphs
    try:
        print(f"\nGenerating graphs...")
        sys.path.insert(0, str(benchmark_dir))
        from generate_graphs import BenchmarkGraphGenerator
        
        generator = BenchmarkGraphGenerator(csv_path, version_type='all')
        generator.generate_all_graphs()
        
        print(f"✓ Graphs generated successfully")
    except Exception as e:
        print(f"⚠ Graph generation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
