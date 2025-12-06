"""Comprehensive benchmark: dictsqlite_v2 all modes with detailed tests

This script provides:
1. All 3 persist modes (memory, lazy, writethrough) individually tested
2. Synchronous operations for each mode
3. Async operations for each mode
4. Memory profiling for each mode
5. Detailed comparison with fastest version
"""

import sys
import time
import tempfile
import os
import asyncio
import tracemalloc
from pathlib import Path
from typing import Dict, Tuple, List
import json

REPO_ROOT = Path(__file__).parent.parent.parent

# Try to import dictsqlite_v2 (sync + async)
try:
    original_path = sys.path.copy()
    repo_root_str = str(REPO_ROOT)
    sys.path = [p for p in sys.path 
                if not (p.startswith(repo_root_str) or 'dictsqlite' in p.lower()) 
                or 'site-packages' in p]
    
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
    sys.path = original_path
    V2_AVAILABLE = True
    print("✅ dictsqlite_v2 (sync + async) loaded")
except Exception as e:
    print(f"❌ dictsqlite_v2 not available: {e}")
    DictSQLiteV4 = None
    AsyncDictSQLite = None
    V2_AVAILABLE = False

# Try to import fastest
try:
    sys.path.insert(0, str(REPO_ROOT / "others" / "beta-versions" / "dictsqlite-fastest" / "beta"))
    from dictsqlite_fastest_beta_v2 import DictSQLiteFastestBeta
    FASTEST_AVAILABLE = True
    print("✅ fastest beta v2 loaded")
except Exception as e:
    print(f"⚠️  fastest not available: {e}")
    DictSQLiteFastestBeta = None
    FASTEST_AVAILABLE = False


class BenchmarkResults:
    """Store comprehensive benchmark results"""
    
    def __init__(self):
        self.results = {}
    
    def add(self, category: str, test_name: str, elapsed: float, ops: float, memory_mb: float = 0):
        """Add a benchmark result"""
        if category not in self.results:
            self.results[category] = []
        self.results[category].append({
            'test': test_name,
            'elapsed': elapsed,
            'ops_per_sec': ops,
            'memory_mb': memory_mb
        })
    
    def print_category(self, category: str):
        """Print results for a category"""
        if category not in self.results:
            return
        
        print(f"\n{'='*80}")
        print(f"📊 {category}")
        print(f"{'='*80}")
        
        for result in self.results[category]:
            print(f"  {result['test']:30s}: {result['ops_per_sec']:>12,.0f} ops/sec "
                  f"({result['elapsed']:.3f}s, {result['memory_mb']:.1f} MB)")
    
    def get_average(self, category: str) -> float:
        """Get average ops/sec for a category"""
        if category not in self.results:
            return 0
        ops_values = [r['ops_per_sec'] for r in self.results[category] if r['ops_per_sec'] > 0]
        return sum(ops_values) / len(ops_values) if ops_values else 0
    
    def save_json(self, filename: str):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)


def benchmark_sync_write(db, count: int, label: str = "Write") -> Tuple[float, float, float]:
    """Benchmark synchronous write operations with memory tracking"""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        db[f'{label}_key_{i}'] = f'{label}_value_{i}'
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


def benchmark_sync_read(db, count: int, label: str = "Read") -> Tuple[float, float, float]:
    """Benchmark synchronous read operations with memory tracking"""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        _ = db.get(f'{label}_key_{i}', None)
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


def benchmark_sync_mixed(db, count: int, label: str = "Mixed") -> Tuple[float, float, float]:
    """Benchmark synchronous mixed operations with memory tracking"""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        db[f'{label}_{i}'] = f'data_{i}'
        if i % 3 == 0:
            _ = db.get(f'{label}_{i}', None)
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


async def benchmark_async_write(db, count: int, label: str = "AsyncWrite") -> Tuple[float, float, float]:
    """Benchmark async write operations with memory tracking"""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        await db.aset(f'{label}_key_{i}', f'{label}_value_{i}')
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


async def benchmark_async_read(db, count: int, label: str = "AsyncRead") -> Tuple[float, float, float]:
    """Benchmark async read operations with memory tracking"""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        _ = await db.aget(f'{label}_key_{i}')
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


async def benchmark_async_concurrent(db, count: int, concurrency: int = 10) -> Tuple[float, float, float]:
    """Benchmark concurrent async operations with memory tracking"""
    tracemalloc.start()
    
    async def write_batch(start_idx: int, batch_size: int):
        for i in range(start_idx, start_idx + batch_size):
            await db.aset(f'concurrent_key_{i}', f'concurrent_value_{i}')
    
    start = time.time()
    batch_size = count // concurrency
    tasks = [write_batch(i * batch_size, batch_size) for i in range(concurrency)]
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


def run_sync_benchmarks(mode: str, db_path: str, count: int = 1000) -> BenchmarkResults:
    """Run all synchronous benchmarks for a specific mode"""
    print(f"\n{'='*80}")
    print(f"🔬 Synchronous Benchmarks: dictsqlite_v2 - Mode: {mode.upper()}")
    print(f"{'='*80}")
    
    results = BenchmarkResults()
    
    # Configure based on mode
    if mode == 'memory':
        db = DictSQLiteV4(":memory:", persist_mode='memory', hot_capacity=1_000_000)
    elif mode == 'lazy':
        db = DictSQLiteV4(db_path, persist_mode='lazy', hot_capacity=1_000_000, buffer_size=100)
    else:  # writethrough
        db = DictSQLiteV4(db_path, persist_mode='writethrough', hot_capacity=1_000_000, buffer_size=100)
    
    try:
        # Test 1: Write
        print(f"  Running: Write ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_write(db, count, f"sync_{mode}_write")
        results.add(f"v2_{mode}_sync", "Write", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        # Test 2: Read
        print(f"  Running: Read ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_read(db, count, f"sync_{mode}_write")
        results.add(f"v2_{mode}_sync", "Read", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        # Test 3: Mixed
        print(f"  Running: Mixed ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_mixed(db, count, f"sync_{mode}_mixed")
        results.add(f"v2_{mode}_sync", "Mixed", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        # Test 4: Update existing
        print(f"  Running: Update ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_write(db, count, f"sync_{mode}_write")
        results.add(f"v2_{mode}_sync", "Update", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
    finally:
        if hasattr(db, 'close'):
            db.close()
    
    return results


async def run_async_benchmarks(mode: str, db_path: str, count: int = 500) -> BenchmarkResults:
    """Run all asynchronous benchmarks for a specific mode"""
    print(f"\n{'='*80}")
    print(f"🔬 Asynchronous Benchmarks: dictsqlite_v2 - Mode: {mode.upper()}")
    print(f"{'='*80}")
    
    results = BenchmarkResults()
    
    # Configure based on mode
    if mode == 'memory':
        db = AsyncDictSQLite(":memory:", persist_mode='memory', capacity=1_000_000)
    elif mode == 'lazy':
        db = AsyncDictSQLite(db_path, persist_mode='lazy', capacity=1_000_000)
    else:  # writethrough
        db = AsyncDictSQLite(db_path, persist_mode='writethrough', capacity=1_000_000)
    
    try:
        # Test 1: Async Write
        print(f"  Running: Async Write ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = await benchmark_async_write(db, count, f"async_{mode}_write")
        results.add(f"v2_{mode}_async", "Async Write", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        # Test 2: Async Read
        print(f"  Running: Async Read ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = await benchmark_async_read(db, count, f"async_{mode}_write")
        results.add(f"v2_{mode}_async", "Async Read", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        # Test 3: Concurrent Write
        print(f"  Running: Concurrent Write ({count*2} items, 10 concurrent)...", end=' ', flush=True)
        elapsed, ops, mem = await benchmark_async_concurrent(db, count * 2, 10)
        results.add(f"v2_{mode}_async", "Concurrent Write", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
    finally:
        await db.aclose()
    
    return results


def run_fastest_benchmarks(db_path: str, count: int = 1000) -> BenchmarkResults:
    """Run benchmarks for fastest version"""
    if not FASTEST_AVAILABLE:
        return BenchmarkResults()
    
    print(f"\n{'='*80}")
    print(f"🔬 Benchmarks: dictsqlite-fastest Beta v2")
    print(f"{'='*80}")
    
    results = BenchmarkResults()
    db = DictSQLiteFastestBeta(db_path, cache_capacity=1_000_000)
    
    try:
        print(f"  Running: Write ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_write(db, count, "fastest_write")
        results.add("fastest", "Write", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        print(f"  Running: Read ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_read(db, count, "fastest_write")
        results.add("fastest", "Read", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
        
        print(f"  Running: Mixed ({count} items)...", end=' ', flush=True)
        elapsed, ops, mem = benchmark_sync_mixed(db, count, "fastest_mixed")
        results.add("fastest", "Mixed", elapsed, ops, mem)
        print(f"✓ {ops:,.0f} ops/sec")
    
    finally:
        if hasattr(db, 'close'):
            db.close()
    
    return results


async def main():
    """Main function to run all comprehensive benchmarks"""
    print("="*80)
    print("dictsqlite_v2 全モード総合ベンチマーク")
    print("Comprehensive Benchmark - All Modes + Sync/Async")
    print("="*80)
    
    if not V2_AVAILABLE:
        print("\n❌ dictsqlite_v2 not available. Exiting.")
        return
    
    count_sync = 2000  # Number of items for sync tests
    count_async = 1000  # Number of items for async tests
    
    all_results = BenchmarkResults()
    
    # Test all 3 modes: memory, lazy, writethrough
    modes = ['memory', 'lazy', 'writethrough']
    
    for mode in modes:
        # Create temp database for each mode (except memory)
        if mode == 'memory':
            db_path_sync = ":memory:"
            db_path_async = ":memory:"
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{mode}_sync.db') as tmp:
                db_path_sync = tmp.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{mode}_async.db') as tmp:
                db_path_async = tmp.name
        
        try:
            # Run synchronous benchmarks
            sync_results = run_sync_benchmarks(mode, db_path_sync, count_sync)
            for category, tests in sync_results.results.items():
                for test in tests:
                    all_results.add(category, test['test'], test['elapsed'], test['ops_per_sec'], test['memory_mb'])
            
            # Run asynchronous benchmarks
            async_results = await run_async_benchmarks(mode, db_path_async, count_async)
            for category, tests in async_results.results.items():
                for test in tests:
                    all_results.add(category, test['test'], test['elapsed'], test['ops_per_sec'], test['memory_mb'])
            
        finally:
            # Cleanup
            if mode != 'memory':
                for path in [db_path_sync, db_path_async]:
                    for ext in ['', '-wal', '-shm']:
                        try:
                            os.unlink(path + ext)
                        except FileNotFoundError:
                            pass
    
    # Test fastest version
    if FASTEST_AVAILABLE:
        with tempfile.NamedTemporaryFile(delete=False, suffix='_fastest.db') as tmp:
            db_path_fastest = tmp.name
        
        try:
            fastest_results = run_fastest_benchmarks(db_path_fastest, count_sync)
            for category, tests in fastest_results.results.items():
                for test in tests:
                    all_results.add(category, test['test'], test['elapsed'], test['ops_per_sec'], test['memory_mb'])
        finally:
            for ext in ['', '-wal', '-shm']:
                try:
                    os.unlink(db_path_fastest + ext)
                except FileNotFoundError:
                    pass
    
    # Print all results
    print(f"\n\n{'='*80}")
    print("📊 総合結果サマリー (Comprehensive Results Summary)")
    print(f"{'='*80}")
    
    for category in sorted(all_results.results.keys()):
        all_results.print_category(category)
    
    # Calculate and print averages
    print(f"\n{'='*80}")
    print("📈 平均パフォーマンス (Average Performance)")
    print(f"{'='*80}\n")
    
    for category in sorted(all_results.results.keys()):
        avg = all_results.get_average(category)
        if avg > 0:
            print(f"  {category:30s}: {avg:>12,.0f} ops/sec")
    
    # Save results to JSON
    results_dir = Path(__file__).parent / "results" / "v2_modes"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "comprehensive_all_modes.json"
    all_results.save_json(str(json_path))
    print(f"\n✅ Results saved to: {json_path}")
    
    # Print comparison
    print(f"\n{'='*80}")
    print("🏆 最速モード比較 (Best Mode Comparison)")
    print(f"{'='*80}\n")
    
    mode_categories = [cat for cat in all_results.results.keys() if cat.startswith('v2_')]
    mode_avgs = [(cat, all_results.get_average(cat)) for cat in mode_categories]
    mode_avgs.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (cat, avg) in enumerate(mode_avgs, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
        print(f"{medal} {rank}. {cat:30s}: {avg:>12,.0f} ops/sec")
    
    if FASTEST_AVAILABLE:
        fastest_avg = all_results.get_average("fastest")
        print(f"\n   fastest (reference)         : {fastest_avg:>12,.0f} ops/sec")


if __name__ == "__main__":
    asyncio.run(main())
