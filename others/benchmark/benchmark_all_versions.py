"""Comprehensive benchmark: Original vs dictsqlite_v2 vs dictsqlite-fastest beta v2

Compares performance of three key versions with optimized sync/async tests:
- DictSQLite (Original): Standard sqlite3-based implementation (dictsqlite/)
- dictsqlite_v2: High-performance Rust extension version 2.0.6 (dictsqlite_v2/dictsqlite/)
- dictsqlite-fastest beta v2: APSW-based async high-performance version
"""

import asyncio
import os
import sys
import tempfile
import time
import csv
import importlib.util
from pathlib import Path
from typing import Dict, Tuple, Any

# Add paths
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))  # For main dictsqlite package

# Add dictsqlite_v2 path
V2_DIR = REPO_ROOT / 'dictsqlite_v2' / 'dictsqlite' / 'python'
sys.path.insert(0, str(V2_DIR))

# Add dictsqlite-fastest beta v2 path
BETA_V2_DIR = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'
sys.path.insert(0, str(BETA_V2_DIR))

# Add benchmark directory to path for VersionManager
BENCHMARK_DIR = REPO_ROOT / 'others' / 'benchmark'
sys.path.insert(0, str(BENCHMARK_DIR))

# Import graph generation libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠ matplotlib not available. Graphs will not be generated.")

# Import versions
try:
    from dictsqlite.main import DictSQLite  # Original (sync only)
    ORIGINAL_AVAILABLE = True
except ImportError as e:
    print(f"⚠ DictSQLite (Original) not available: {e}")
    DictSQLite = None
    ORIGINAL_AVAILABLE = False

try:
    # Import dictsqlite_v2 (Rust extension version 2.0.6)
    import dictsqlite as dictsqlite_v2_module
    from dictsqlite import DictSQLite as DictSQLiteV2_Sync
    from dictsqlite import AsyncDictSQLite as DictSQLiteV2_Async
    V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠ dictsqlite_v2 not available: {e}")
    DictSQLiteV2_Sync = None
    DictSQLiteV2_Async = None
    V2_AVAILABLE = False

try:
    # Import dictsqlite-fastest beta v2
    from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncBetaV2
    BETA_V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠ dictsqlite-fastest beta v2 not available: {e}")
    AsyncBetaV2 = None
    BETA_V2_AVAILABLE = False

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
        self.v2_time = 0.0
        self.beta_v2_time = 0.0
        self.original_ops = 0.0
        self.v2_ops = 0.0
        self.beta_v2_ops = 0.0
    
    def set_original(self, elapsed: float, ops_per_sec: float):
        self.original_time = elapsed
        self.original_ops = ops_per_sec
    
    def set_v2(self, elapsed: float, ops_per_sec: float):
        self.v2_time = elapsed
        self.v2_ops = ops_per_sec
    
    def set_beta_v2(self, elapsed: float, ops_per_sec: float):
        self.beta_v2_time = elapsed
        self.beta_v2_ops = ops_per_sec
    
    def print_comparison(self):
        """Print comparison of all versions."""
        print(f"\n{self.name}:")
        if self.original_ops > 0:
            print(f"  Original:        {self.original_time:.3f}s ({self.original_ops:>8.0f} ops/sec)")
        if self.v2_ops > 0:
            if self.original_ops > 0:
                print(f"  dictsqlite_v2:   {self.v2_time:.3f}s ({self.v2_ops:>8.0f} ops/sec) - {self.v2_ops/self.original_ops:>5.2f}x vs Original")
            else:
                print(f"  dictsqlite_v2:   {self.v2_time:.3f}s ({self.v2_ops:>8.0f} ops/sec)")
        if self.beta_v2_ops > 0:
            if self.original_ops > 0:
                print(f"  Beta v2:         {self.beta_v2_time:.3f}s ({self.beta_v2_ops:>8.0f} ops/sec) - {self.beta_v2_ops/self.original_ops:>5.2f}x vs Original")
            else:
                print(f"  Beta v2:         {self.beta_v2_time:.3f}s ({self.beta_v2_ops:>8.0f} ops/sec)")


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


# Async benchmark functions for Beta v2 (with aset/aget/abulk_insert methods)
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


# V4.1-specific benchmark functions (uses set/get/batch_set, not async methods)
async def benchmark_v2_basic_write(db, count: int) -> Tuple[float, float]:
    """Benchmark basic write operations for dictsqlite_v2 (async)."""
    start = time.time()
    for i in range(count):
        await db.aset(f'key_{i}', f'value_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_v2_basic_read(db, count: int) -> Tuple[float, float]:
    """Benchmark sequential read operations for dictsqlite_v2 (async)."""
    start = time.time()
    for i in range(count):
        await db.aget(f'key_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_v2_bulk_insert(db, count: int) -> Tuple[float, float]:
    """Benchmark bulk insert for dictsqlite_v2 (async)."""
    # dictsqlite_v2 may not have batch_set, use sequential async inserts
    start = time.time()
    for i in range(count):
        await db.aset(f'bulk_key_{i}', f'bulk_value_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_v2_mixed_operations(db, count: int) -> Tuple[float, float]:
    """Benchmark mixed read/write operations for dictsqlite_v2."""
    start = time.time()
    for i in range(count):
        await db.aset(f'mixed_{i}', f'data_{i}')
        if i % 3 == 0:
            await db.aget(f'mixed_{i}')
    elapsed = time.time() - start
    return elapsed, count / elapsed


async def benchmark_v2_concurrent_read(db, count: int) -> Tuple[float, float]:
    """Benchmark concurrent read operations for dictsqlite_v2."""
    # Pre-populate data
    for i in range(count):
        await db.aset(f'concurrent_{i}', f'value_{i}')
    
    # Concurrent reads
    start = time.time()
    tasks = []
    for i in range(count):
        tasks.append(db.aget(f'concurrent_{i}'))
    
    await asyncio.gather(*tasks)
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


async def run_v2_benchmark(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run benchmark for dictsqlite_v2 with optimized sync/async tests."""
    if not V2_AVAILABLE:
        print(f"\n{'='*70}")
        print(f"Skipping: dictsqlite_v2 (not available - needs to be built)")
        print(f"{'='*70}")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'concurrent_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*70}")
    print(f"Benchmarking: dictsqlite_v2 (Rust extension v2.0.6 - sync/async support)")
    print(f"{'='*70}")
    
    results = {}
    
    # Use async version of dictsqlite_v2
    db = DictSQLiteV2_Async(db_path)
    try:
        # Basic operations
        print("\n1. Basic Write (300 items) [async]...")
        elapsed, ops = await benchmark_v2_basic_write(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items) [async]...")
        elapsed, ops = await benchmark_v2_basic_read(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Concurrent Read (600 items, 8 concurrent) [async]...")
        elapsed, ops = await benchmark_v2_concurrent_read(db, 600)
        results['concurrent_read'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Bulk Insert (500 items) [async]...")
        elapsed, ops = await benchmark_v2_bulk_insert(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("5. Mixed Operations (400 items) [async]...")
        elapsed, ops = await benchmark_v2_mixed_operations(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   {elapsed:.3f}s, {ops:.0f} ops/sec")
    finally:
        # Cleanup if the class has a close method
        if hasattr(db, 'close'):
            if asyncio.iscoroutinefunction(db.close):
                await db.close()
            else:
                db.close()
    
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


def generate_comparison_graphs(original_results: Dict[str, Tuple[float, float]], 
                               beta_v2_results: Dict[str, Tuple[float, float]], 
                               v2_results: Dict[str, Tuple[float, float]],
                               test_labels: list,
                               output_dir: Path = None):
    """Generate comparison graphs for all versions.
    
    Args:
        original_results: Original version results
        beta_v2_results: Beta v2 version results
        v2_results: dictsqlite_v2 version results
        test_labels: List of test labels
        output_dir: Output directory for graphs (default: results/graphs)
    """
    if not MATPLOTLIB_AVAILABLE:
        print("\n⚠ Matplotlib not available. Skipping graph generation.")
        return
    
    if output_dir is None:
        output_dir = BENCHMARK_DIR / "results" / "graphs"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup Japanese fonts
    try:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Noto Sans CJK JP']
    except Exception:
        pass
    
    # Prepare data
    test_names = ['basic_write', 'basic_read', 'concurrent_read', 'bulk_insert', 'mixed_ops']
    short_labels = ['Write', 'Read', 'Concurrent\nRead', 'Bulk\nInsert', 'Mixed\nOps']
    
    # Extract OPS data
    original_ops = [original_results[name][1] if ORIGINAL_AVAILABLE else 0 for name in test_names]
    beta_v2_ops = [beta_v2_results[name][1] if BETA_V2_AVAILABLE else 0 for name in test_names]
    v2_ops = [v2_results[name][1] if V2_AVAILABLE else 0 for name in test_names]
    
    # Graph 1: Bar chart comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = range(len(test_names))
    width = 0.25
    
    if ORIGINAL_AVAILABLE:
        ax.bar([i - width for i in x], original_ops, width, label='Original版', alpha=0.8)
    if BETA_V2_AVAILABLE:
        ax.bar(x, beta_v2_ops, width, label='Beta v2版', alpha=0.8)
    if V2_AVAILABLE:
        ax.bar([i + width for i in x], v2_ops, width, label='dictsqlite_v2版', alpha=0.8)
    
    ax.set_xlabel('Test Type', fontsize=12)
    ax.set_ylabel('Operations per Second (ops/sec)', fontsize=12)
    ax.set_title('DictSQLite Version Comparison - All Benchmarks', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels, fontsize=10)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    graph_path = output_dir / "version_comparison_bar.png"
    plt.savefig(graph_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved bar chart: {graph_path}")
    
    # Graph 2: Speedup comparison (relative to Original or slowest)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Calculate speedups
    speedups = []
    labels_for_speedup = []
    
    for i, test_name in enumerate(test_names):
        # Find baseline - use the smallest non-zero value
        available_ops = []
        if ORIGINAL_AVAILABLE and original_ops[i] > 0:
            available_ops.append(original_ops[i])
        if BETA_V2_AVAILABLE and beta_v2_ops[i] > 0:
            available_ops.append(beta_v2_ops[i])
        if V2_AVAILABLE and v2_ops[i] > 0:
            available_ops.append(v2_ops[i])
        
        if not available_ops:
            continue
            
        baseline = min(available_ops)
        
        test_speedups = []
        if ORIGINAL_AVAILABLE and original_ops[i] > 0:
            test_speedups.append(original_ops[i] / baseline)
        if BETA_V2_AVAILABLE and beta_v2_ops[i] > 0:
            test_speedups.append(beta_v2_ops[i] / baseline)
        if V2_AVAILABLE and v2_ops[i] > 0:
            test_speedups.append(v2_ops[i] / baseline)
        
        if test_speedups:
            speedups.append(test_speedups)
            labels_for_speedup.append(short_labels[i])
    
    if speedups:
        x_speedup = range(len(labels_for_speedup))
        version_labels = []
        if ORIGINAL_AVAILABLE:
            version_labels.append('Original版')
        if BETA_V2_AVAILABLE:
            version_labels.append('Beta v2版')
        if V2_AVAILABLE:
            version_labels.append('dictsqlite_v2版')
        
        # Plot each version's speedups across tests
        for version_idx, version_label in enumerate(version_labels):
            version_speedups = []
            for test_speedup_list in speedups:
                # Get speedup for this version from this test
                if version_idx < len(test_speedup_list):
                    version_speedups.append(test_speedup_list[version_idx])
                else:
                    version_speedups.append(0)
            ax.plot(x_speedup, version_speedups, marker='o', linewidth=2, markersize=8, label=version_label)
        
        ax.set_xlabel('Test Type', fontsize=12)
        ax.set_ylabel('Speedup (relative to baseline)', fontsize=12)
        ax.set_title('DictSQLite Version Speedup Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x_speedup)
        ax.set_xticklabels(labels_for_speedup, fontsize=10)
        ax.legend(fontsize=11)
        ax.grid(alpha=0.3)
        ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        plt.tight_layout()
        graph_path = output_dir / "version_comparison_speedup.png"
        plt.savefig(graph_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved speedup chart: {graph_path}")
    
    print(f"\n✅ Graphs saved to: {output_dir}")
    print(f"   - version_comparison_bar.png")
    print(f"   - version_comparison_speedup.png")


async def main():
    """Main benchmark execution."""
    print("=" * 70)
    print("DictSQLite Comprehensive Benchmark")
    print("Original vs Beta v2 vs v4.1")
    print("=" * 70)
    
    # Version mapping table
    print("\n" + "=" * 70)
    print("バージョンマッピング (Version Mapping)")
    print("=" * 70)
    print("\n以下の3つのバージョンを比較します:")
    print("\n  1. Original版 (DictSQLite Original)")
    print("     - ソースコード: dictsqlite/")
    print("     - 実装: 標準sqlite3ベース")
    print("     - 特徴: Python標準ライブラリのみ使用")
    print("\n  2. dictsqlite_v2版 (dictsqlite_v2)")
    print("     - ソースコード: dictsqlite_v2/dictsqlite/")
    print("     - 実装: Rust拡張（バージョン 2.0.6）")
    print("     - 特徴: 同期・非同期両対応の高性能Rust実装")
    print("\n  3. Beta v2版 (dictsqlite-fastest Beta v2)")
    print("     - ソースコード: others/beta-versions/dictsqlite-fastest/beta/")
    print("     - 実装: APSWベース（非同期高性能版）")
    print("     - 特徴: メモリ最適化、LRUキャッシュ")
    print("\n" + "=" * 70)
    
    # Check if at least one version is available
    if not any([ORIGINAL_AVAILABLE, V2_AVAILABLE, BETA_V2_AVAILABLE]):
        print("\n❌ ERROR: No versions available to benchmark!")
        print("Please install at least one of:")
        print("  - DictSQLite (Original): pip install -e .")
        print("  - dictsqlite_v2: Build with: cd dictsqlite_v2/dictsqlite && maturin develop")
        print("  - dictsqlite-fastest Beta v2: Requires APSW")
        return 1
    
    print("\nAvailable versions:")
    if ORIGINAL_AVAILABLE:
        print("  ✓ DictSQLite (Original版): Standard sqlite3-based")
    else:
        print("  ✗ DictSQLite (Original版): Not available")
    
    if V2_AVAILABLE:
        print("  ✓ dictsqlite_v2 (dictsqlite_v2版): Rust extension v2.0.6 with sync/async support")
    else:
        print("  ✗ dictsqlite_v2 (dictsqlite_v2版): Not available")
    
    if BETA_V2_AVAILABLE:
        print("  ✓ dictsqlite-fastest Beta v2 (Beta v2版): Async high-performance")
    else:
        print("  ✗ dictsqlite-fastest Beta v2 (Beta v2版): Not available")
    
    print("\nTest operations:")
    print("  - Sync operations: Basic write/read, bulk insert")
    print("  - Async operations: Concurrent read, async write/read (where supported)")
    print("  - Mixed operations: Combined sync/async workloads")
    
    # Create temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix='_original.db') as tmp:
        original_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v2.db') as tmp:
        v2_path = tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='_beta_v2.db') as tmp:
        beta_v2_path = tmp.name
    
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
        # Run benchmarks with individual error handling
        # Original is synchronous, so we call it directly (not await)
        try:
            original_results = run_original_benchmark(original_path)
            
            # Save original results
            if VERSION_MANAGER_AVAILABLE and ORIGINAL_AVAILABLE:
                save_version_results('original', original_results, test_labels)
        except Exception as e:
            print(f"\n❌ Error running Original benchmark: {e}")
            import traceback
            traceback.print_exc()
            original_results = {
                'basic_write': (0, 0),
                'basic_read': (0, 0),
                'concurrent_read': (0, 0),
                'bulk_insert': (0, 0),
                'mixed_ops': (0, 0)
            }
        
        # Beta v2 and dictsqlite_v2 are async, so we await them
        try:
            beta_v2_results = await run_beta_v2_benchmark(beta_v2_path)
            
            # Save beta v2 results
            if VERSION_MANAGER_AVAILABLE and BETA_V2_AVAILABLE:
                save_version_results('beta_v2', beta_v2_results, test_labels)
        except Exception as e:
            print(f"\n❌ Error running Beta v2 benchmark: {e}")
            import traceback
            traceback.print_exc()
            beta_v2_results = {
                'basic_write': (0, 0),
                'basic_read': (0, 0),
                'concurrent_read': (0, 0),
                'bulk_insert': (0, 0),
                'mixed_ops': (0, 0)
            }
        
        try:
            v2_results = await run_v2_benchmark(v2_path)
            
            # Save dictsqlite_v2 results
            if VERSION_MANAGER_AVAILABLE and V2_AVAILABLE:
                save_version_results('v2', v2_results, test_labels)
        except Exception as e:
            print(f"\n❌ Error running dictsqlite_v2 benchmark: {e}")
            import traceback
            traceback.print_exc()
            v2_results = {
                'basic_write': (0, 0),
                'basic_read': (0, 0),
                'concurrent_read': (0, 0),
                'bulk_insert': (0, 0),
                'mixed_ops': (0, 0)
            }
        
        # Create result objects
        results = []
        for test_name, label in zip(test_names, test_labels):
            result = BenchmarkResult(label)
            result.set_original(*original_results[test_name])
            result.set_beta_v2(*beta_v2_results[test_name])
            result.set_v2(*v2_results[test_name])
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
        v2_avg = sum(v2_results[name][1] for name in sync_test_names) / len(sync_test_names) if V2_AVAILABLE else 0
        beta_v2_avg = sum(beta_v2_results[name][1] for name in sync_test_names) / len(sync_test_names) if BETA_V2_AVAILABLE else 0
        
        print(f"\nAverage throughput (ops/sec) - sync operations only:")
        if ORIGINAL_AVAILABLE:
            print(f"  Original:        {original_avg:>10.0f}")
        if V2_AVAILABLE and v2_avg > 0:
            baseline_avg = original_avg if original_avg > 0 else v2_avg
            if baseline_avg > 0 and baseline_avg != v2_avg:
                print(f"  dictsqlite_v2:   {v2_avg:>10.0f} ({v2_avg/baseline_avg:>5.2f}x vs baseline)")
            else:
                print(f"  dictsqlite_v2:   {v2_avg:>10.0f}")
        if BETA_V2_AVAILABLE:
            baseline_avg = original_avg if original_avg > 0 else (v2_avg if v2_avg > 0 else beta_v2_avg)
            if baseline_avg > 0:
                print(f"  Beta v2:         {beta_v2_avg:>10.0f} ({beta_v2_avg/baseline_avg:>5.2f}x vs baseline)")
            else:
                print(f"  Beta v2:         {beta_v2_avg:>10.0f}")
        
        # Determine winner
        print(f"\n{'='*70}")
        print("Summary")
        print(f"{'='*70}")
        
        versions = []
        if ORIGINAL_AVAILABLE and original_avg > 0:
            versions.append(('Original', original_avg))
        if V2_AVAILABLE and v2_avg > 0:
            versions.append(('dictsqlite_v2', v2_avg))
        if BETA_V2_AVAILABLE and beta_v2_avg > 0:
            versions.append(('Beta v2', beta_v2_avg))
        
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
        
        # Generate comparison graphs
        print(f"\n{'='*70}")
        print("Generating comparison graphs...")
        print(f"{'='*70}")
        try:
            generate_comparison_graphs(
                original_results, 
                beta_v2_results, 
                v2_results, 
                test_labels
            )
        except Exception as e:
            print(f"\n⚠ Error generating graphs: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n{'='*70}")
        print("✅ Benchmark completed successfully!")
        print(f"{'='*70}")
        
    finally:
        # Cleanup
        for path in [original_path, v2_path, beta_v2_path]:
            if os.path.exists(path):
                os.unlink(path)
    
    return 0


if __name__ == "__main__":
    # Clean up any cached bytecode to ensure we're running the latest version
    import pathlib
    pycache_dir = pathlib.Path(__file__).parent / '__pycache__'
    if pycache_dir.exists():
        import shutil
        try:
            shutil.rmtree(pycache_dir)
        except:
            pass
    
    sys.exit(asyncio.run(main()))
