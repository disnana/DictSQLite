"""Comprehensive benchmark: Original vs Beta v2 vs v4.1

Compares performance of three key versions:
- DictSQLite (Original): Standard sqlite3-based implementation
- dictsqlite-fastest Beta v2: High-performance async version
- dictsqlite_v4.1: Rust-based ultra-fast implementation
"""

import asyncio
import os
import sys
import tempfile
import time
import csv
from pathlib import Path
from typing import Dict, Tuple, Any

# Add paths
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))  # For main dictsqlite package

# Add dictsqlite-fastest beta v2
BETA_DIR = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'
sys.path.insert(0, str(BETA_DIR))

# Add v4.1 path
V4_1_DIR = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite_v4.1'
sys.path.insert(0, str(V4_1_DIR))

# Add benchmark directory to path for VersionManager
BENCHMARK_DIR = REPO_ROOT / 'others' / 'benchmark'
sys.path.insert(0, str(BENCHMARK_DIR))

# Import versions
try:
    from dictsqlite.main import DictSQLite  # Original (sync only)
    ORIGINAL_AVAILABLE = True
except ImportError as e:
    print(f"⚠ DictSQLite (Original) not available: {e}")
    DictSQLite = None
    ORIGINAL_AVAILABLE = False

try:
    from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncBetaV2
    BETA_V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠ dictsqlite-fastest Beta v2 not available: {e}")
    AsyncBetaV2 = None
    BETA_V2_AVAILABLE = False

try:
    from dictsqlite_v4 import AsyncDictSQLite as AsyncV4_1  # v4.1 async
    V4_1_AVAILABLE = True
except ImportError as e:
    print(f"⚠ dictsqlite_v4.1 native extension not available: {e}")
    AsyncV4_1 = None
    V4_1_AVAILABLE = False

# Import VersionManager
try:
    from version_manager import VersionManager
    VERSION_MANAGER_AVAILABLE = True
except ImportError:
    print("⚠ VersionManagerが利用できません。結果は保存されません。")
    VERSION_MANAGER_AVAILABLE = False


class BenchmarkResult:
    """Stores benchmark results for a single test."""
    
    def __init__(self, name: str):
        self.name = name
        self.original_time = 0.0
        self.beta_v2_time = 0.0
        self.v4_1_time = 0.0
        self.original_ops = 0.0
        self.beta_v2_ops = 0.0
        self.v4_1_ops = 0.0
    
    def set_original(self, elapsed: float, ops_per_sec: float):
        self.original_time = elapsed
        self.original_ops = ops_per_sec
    
    def set_beta_v2(self, elapsed: float, ops_per_sec: float):
        self.beta_v2_time = elapsed
        self.beta_v2_ops = ops_per_sec
    
    def set_v4_1(self, elapsed: float, ops_per_sec: float):
        self.v4_1_time = elapsed
        self.v4_1_ops = ops_per_sec
    
    def print_comparison(self):
        """Print comparison of all versions."""
        print(f"\n{self.name}:")
        print(f"  Original: {self.original_time:.3f}s ({self.original_ops:>8.0f} ops/sec)")
        if self.beta_v2_ops > 0:
            print(f"  Beta v2:  {self.beta_v2_time:.3f}s ({self.beta_v2_ops:>8.0f} ops/sec) - {self.beta_v2_ops/self.original_ops:>5.2f}x vs Original")
        if self.v4_1_ops > 0:
            print(f"  v4.1:     {self.v4_1_time:.3f}s ({self.v4_1_ops:>8.0f} ops/sec) - {self.v4_1_ops/self.original_ops:>5.2f}x vs Original")


# Sync benchmark functions for Original DictSQLite
def benchmark_basic_write_sync(db, count: int) -> Tuple[float, float]:
    """Benchmark basic write operations (sync)."""
    start = time.time()
    for i in range(count):
        db[f'key_{i}'] = f'value_{i}'
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_basic_read_sync(db, count: int) -> Tuple[float, float]:
    """Benchmark sequential read operations (sync)."""
    start = time.time()
    for i in range(count):
        _ = db[f'key_{i}']
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_bulk_insert_sync(db, count: int) -> Tuple[float, float]:
    """Benchmark bulk insert (sync)."""
    data = {f'bulk_key_{i}': f'bulk_value_{i}' for i in range(count)}
    
    start = time.time()
    for key, value in data.items():
        db[key] = value
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_mixed_operations_sync(db, count: int) -> Tuple[float, float]:
    """Benchmark mixed read/write operations (sync)."""
    start = time.time()
    for i in range(count):
        db[f'mixed_{i}'] = f'data_{i}'
        if i % 3 == 0:
            _ = db.get(f'mixed_{i}', None)
        if i % 5 == 0 and f'mixed_{i}' in db:
            del db[f'mixed_{i}']
    elapsed = time.time() - start
    return elapsed, count / elapsed


# Async benchmark functions
async def benchmark_basic_write(db, count: int) -> Tuple[float, float]:
    """Benchmark basic write operations."""
    start = time.time()
    for i in range(count):
        await db.aset(f'key_{i}', f'value_{i}')
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


def run_original_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for Original DictSQLite (sync)."""
    if not ORIGINAL_AVAILABLE:
        print(f"\n{'='*70}")
        print(f"Skipping: Original DictSQLite (not available)")
        print(f"{'='*70}")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'concurrent_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*70}")
    print(f"Benchmarking: Original DictSQLite (sqlite3-based)")
    print(f"{'='*70}")
    
    results = {}
    
    with DictSQLite(db_path) as db:
        # Basic operations
        print("\n1. Basic Write (300 items)...")
        elapsed, ops = benchmark_basic_write_sync(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items)...")
        elapsed, ops = benchmark_basic_read_sync(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Bulk Insert (500 items)...")
        elapsed, ops = benchmark_bulk_insert_sync(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Mixed Operations (400 items)...")
        elapsed, ops = benchmark_mixed_operations_sync(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
    
    # Note: concurrent_read is async-only, so we skip it for Original
    results['concurrent_read'] = (0, 0)
    
    return results


async def run_beta_v2_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for Beta v2 with optimized settings."""
    if not BETA_V2_AVAILABLE:
        print(f"\n{'='*70}")
        print(f"Skipping: dictsqlite-fastest Beta v2 (not available)")
        print(f"{'='*70}")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'concurrent_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*70}")
    print(f"Benchmarking: dictsqlite-fastest Beta v2 (aiosqlite + batching)")
    print(f"{'='*70}")
    
    results = {}
    
    # v2 uses aiosqlite with batching - configure for best performance
    async with AsyncBetaV2(db_path) as db:
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


async def run_v4_1_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for v4.1 with optimized settings."""
    if not V4_1_AVAILABLE:
        print(f"\n{'='*70}")
        print(f"Skipping: dictsqlite_v4.1 (not available - needs to be built)")
        print(f"{'='*70}")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'concurrent_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*70}")
    print(f"Benchmarking: dictsqlite_v4.1 (Rust-based ultra-fast)")
    print(f"{'='*70}")
    
    results = {}
    
    # v4.1 has maximum performance optimizations
    async with AsyncV4_1(db_path) as db:
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


def save_version_results(version_name: str, results_dict: Dict[str, Tuple[float, float]], test_labels: list):
    """Save benchmark results for a specific version to VersionManager.
    
    Args:
        version_name: Version identifier (original, beta_v2, v4.1)
        results_dict: Dictionary mapping test_name to (elapsed_time, ops_per_sec)
        test_labels: List of human-readable test labels
    """
    if not VERSION_MANAGER_AVAILABLE:
        return
    
    # Create VersionManager with explicit beta_version
    vm = VersionManager(beta_version=version_name)
    
    # Generate CSV content
    csv_lines = []
    csv_lines.append("Test Name,Operation Count,Original Time (s),Original OPS,Fastest Time (s),Fastest OPS,Beta Time (s),Beta OPS,Speedup (Fastest/Original),Speedup (Beta/Original),Speedup (Beta/Fastest)")
    
    test_names = ['basic_write', 'basic_read', 'concurrent_read', 'bulk_insert', 'mixed_ops']
    operation_counts = [300, 300, 600, 500, 400]
    
    for test_name, label, op_count in zip(test_names, test_labels, operation_counts):
        elapsed, ops = results_dict[test_name]
        # For all-versions benchmark, we only have one implementation per run
        # So we'll put the current version in the "Beta OPS" column
        csv_lines.append(f"{label},{op_count},N/A,N/A,N/A,N/A,{elapsed},{ops},N/A,N/A,N/A")
    
    csv_content = '\n'.join(csv_lines)
    
    # Save to version manager
    saved_files = vm.save_benchmark_result(
        csv_content=csv_content,
        version_string=version_name
    )
    
    print(f"\n✓ {version_name} の結果を保存しました: {saved_files.get('csv', 'N/A')}")


async def main():
    """Main benchmark execution."""
    print("=" * 70)
    print("DictSQLite Comprehensive Benchmark")
    print("Original vs Beta v2 vs v4.1")
    print("=" * 70)
    
    # Check if at least one version is available
    if not any([ORIGINAL_AVAILABLE, BETA_V2_AVAILABLE, V4_1_AVAILABLE]):
        print("\n❌ ERROR: No versions available to benchmark!")
        print("Please install at least one of:")
        print("  - DictSQLite (Original): pip install -e .")
        print("  - dictsqlite-fastest Beta v2: Requires APSW")
        print("  - dictsqlite_v4.1: Build with: cd others/beta-versions/dictsqlite_v4.1 && ./build.sh")
        return 1
    
    print("\nAvailable versions:")
    if ORIGINAL_AVAILABLE:
        print("  ✓ DictSQLite (Original): Standard sqlite3-based")
    else:
        print("  ✗ DictSQLite (Original): Not available")
    
    if BETA_V2_AVAILABLE:
        print("  ✓ dictsqlite-fastest Beta v2: Async high-performance")
    else:
        print("  ✗ dictsqlite-fastest Beta v2: Not available")
    
    if V4_1_AVAILABLE:
        print("  ✓ dictsqlite_v4.1: Rust-based ultra-fast")
    else:
        print("  ✗ dictsqlite_v4.1: Not available")
    
    print("\nTest operations:")
    print("  - Basic operations (write, read)")
    print("  - Concurrent operations (async versions only)")
    print("  - Bulk operations")
    print("  - Mixed operations")
    
    # Create temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix='_original.db') as tmp:
        original_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_beta_v2.db') as tmp:
        beta_v2_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v4.1.db') as tmp:
        v4_1_path = tmp.name
    
    # Define test labels early so they can be used in save_version_results
    test_names = ['basic_write', 'basic_read', 'concurrent_read', 'bulk_insert', 'mixed_ops']
    test_labels = [
        'Basic Write (300 items)',
        'Basic Read (300 items)',
        'Concurrent Read (600 items, 8 concurrent)',
        'Bulk Insert (500 items)',
        'Mixed Operations (400 items)'
    ]
    
    try:
        # Run benchmarks
        # Original is synchronous, so we call it directly (not await)
        original_results = run_original_benchmark(original_path)
        
        # Save original results
        if VERSION_MANAGER_AVAILABLE:
            save_version_results('original', original_results, test_labels)
        
        # Beta v2 and v4.1 are async, so we await them
        beta_v2_results = await run_beta_v2_benchmark(beta_v2_path)
        
        # Save beta v2 results
        if VERSION_MANAGER_AVAILABLE:
            save_version_results('beta_v2', beta_v2_results, test_labels)
        
        v4_1_results = await run_v4_1_benchmark(v4_1_path)
        
        # Save v4.1 results
        if VERSION_MANAGER_AVAILABLE:
            save_version_results('v4.1', v4_1_results, test_labels)
        
        # Create result objects
        results = []
        for test_name, label in zip(test_names, test_labels):
            result = BenchmarkResult(label)
            result.set_original(*original_results[test_name])
            result.set_beta_v2(*beta_v2_results[test_name])
            result.set_v4_1(*v4_1_results[test_name])
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
        
        # Calculate averages (excluding concurrent_read for Original as it's async-only)
        sync_test_names = ['basic_write', 'basic_read', 'bulk_insert', 'mixed_ops']
        
        # Only calculate averages for available versions
        original_avg = sum(original_results[name][1] for name in sync_test_names) / len(sync_test_names) if ORIGINAL_AVAILABLE else 0
        beta_v2_avg = sum(beta_v2_results[name][1] for name in sync_test_names) / len(sync_test_names) if BETA_V2_AVAILABLE else 0
        v4_1_avg = sum(v4_1_results[name][1] for name in sync_test_names) / len(sync_test_names) if V4_1_AVAILABLE else 0
        
        print(f"\nAverage throughput (ops/sec) - sync operations only:")
        if ORIGINAL_AVAILABLE:
            print(f"  Original:  {original_avg:>10.0f}")
        if BETA_V2_AVAILABLE:
            baseline_avg = original_avg if original_avg > 0 else beta_v2_avg
            if baseline_avg > 0:
                print(f"  Beta v2:   {beta_v2_avg:>10.0f} ({beta_v2_avg/baseline_avg:>5.2f}x vs baseline)")
            else:
                print(f"  Beta v2:   {beta_v2_avg:>10.0f}")
        if V4_1_AVAILABLE and v4_1_avg > 0:
            baseline_avg = original_avg if original_avg > 0 else (beta_v2_avg if beta_v2_avg > 0 else v4_1_avg)
            if baseline_avg > 0 and baseline_avg != v4_1_avg:
                print(f"  v4.1:      {v4_1_avg:>10.0f} ({v4_1_avg/baseline_avg:>5.2f}x vs baseline)")
            else:
                print(f"  v4.1:      {v4_1_avg:>10.0f}")
        
        # Determine winner
        print(f"\n{'='*70}")
        print("Summary")
        print(f"{'='*70}")
        
        versions = []
        if ORIGINAL_AVAILABLE and original_avg > 0:
            versions.append(('Original', original_avg))
        if BETA_V2_AVAILABLE and beta_v2_avg > 0:
            versions.append(('Beta v2', beta_v2_avg))
        if V4_1_AVAILABLE and v4_1_avg > 0:
            versions.append(('v4.1', v4_1_avg))
        
        if not versions:
            print("\n⚠ No successful benchmarks to compare")
        else:
            sorted_versions = sorted(versions, key=lambda x: x[1], reverse=True)
            winner = sorted_versions[0]
            
            print(f"\n🏆 Winner: {winner[0]} ({winner[1]:.0f} ops/sec)")
            print(f"\nPerformance ranking:")
            baseline_for_comparison = sorted_versions[-1][1]  # Use slowest as baseline
            for i, (name, ops) in enumerate(sorted_versions, 1):
                vs_baseline = ((ops / baseline_for_comparison) - 1) * 100
                print(f"  {i}. {name}: {ops:>10.0f} ops/sec ({vs_baseline:+.1f}% vs baseline)")
        
        print(f"\n{'='*70}")
        print("✅ Benchmark completed successfully!")
        print(f"{'='*70}")
        
    finally:
        # Cleanup
        for path in [original_path, beta_v2_path, v4_1_path]:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
