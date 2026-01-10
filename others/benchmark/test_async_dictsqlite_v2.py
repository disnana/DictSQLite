"""Async benchmark test for dictsqlite_v2 (Rust extension).

This module provides async benchmark tests for dictsqlite_v2,
testing the AsyncDictSQLite implementation.
"""

import sys
import time
import asyncio
import tempfile
import os
import tracemalloc
from pathlib import Path
from typing import Dict, Tuple

# Add repository root to path
REPO_ROOT = Path(__file__).parent.parent.parent

# Try to import dictsqlite_v2 async
try:
    # Filter out paths that could contain the local dictsqlite package
    original_path = sys.path.copy()
    repo_root_str = str(REPO_ROOT)
    
    # Remove repository root and any paths inside it (except site-packages)
    sys.path = [p for p in sys.path 
                if not (p.startswith(repo_root_str) or 'dictsqlite' in p.lower()) 
                or 'site-packages' in p]
    
    from dictsqlite import AsyncDictSQLite
    
    sys.path = original_path
    AVAILABLE = True
    print("✅ AsyncDictSQLite loaded successfully")
    
except Exception as e:
    print(f"⚠️  AsyncDictSQLite not available: {e}")
    AsyncDictSQLite = None
    AVAILABLE = False


async def benchmark_async_write(db, count: int) -> Tuple[float, float, float]:
    """Benchmark async write operations with memory tracking."""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        await db.aset(f'async_key_{i}', f'async_value_{i}')
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Return (elapsed_time, ops_per_sec, peak_memory_mb)
    return elapsed, count / elapsed, peak / (1024 * 1024)


async def benchmark_async_read(db, count: int) -> Tuple[float, float, float]:
    """Benchmark async sequential read operations with memory tracking."""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        _ = await db.aget(f'async_key_{i}')
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


# Number of keys written in async_write benchmark (used by concurrent read)
ASYNC_WRITE_COUNT = 500


async def benchmark_async_concurrent_read(db, count: int, concurrency: int = 10) -> Tuple[float, float, float]:
    """Benchmark concurrent async read operations with memory tracking."""
    tracemalloc.start()
    
    async def read_batch(start_idx: int, batch_size: int):
        for i in range(start_idx, min(start_idx + batch_size, count)):
            if i < ASYNC_WRITE_COUNT:  # Only read keys that were written
                try:
                    _ = await db.aget(f'async_key_{i}')
                except KeyError:
                    pass  # Key might not exist yet
    
    start = time.time()
    batch_size = count // concurrency
    tasks = [read_batch(i * batch_size, batch_size) for i in range(concurrency)]
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Only count successful reads
    actual_count = min(count, ASYNC_WRITE_COUNT)
    return elapsed, actual_count / elapsed, peak / (1024 * 1024)


async def benchmark_async_mixed(db, count: int) -> Tuple[float, float, float]:
    """Benchmark mixed async read/write operations with memory tracking."""
    tracemalloc.start()
    start = time.time()
    
    for i in range(count):
        await db.aset(f'async_mixed_{i}', f'data_{i}')
        if i % 3 == 0:
            _ = await db.aget(f'async_mixed_{i}')
    
    elapsed = time.time() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return elapsed, count / elapsed, peak / (1024 * 1024)


async def run_benchmarks(db_path: str) -> Dict[str, Tuple[float, float, float]]:
    """Run all async benchmarks for dictsqlite_v2.
    
    Returns:
        Dictionary mapping test name to (elapsed_time, ops_per_sec, peak_memory_mb)
    """
    if not AVAILABLE:
        print("⏭️  Skipping AsyncDictSQLite (not available)")
        return {
            'async_write': (0, 0, 0),
            'async_read': (0, 0, 0),
            'async_concurrent_read': (0, 0, 0),
            'async_mixed': (0, 0, 0)
        }
    
    print(f"\n{'='*80}")
    print(f"🔬 Async Benchmarking: dictsqlite_v2版 (AsyncDictSQLite)")
    print(f"{'='*80}")
    
    results = {}
    
    # Use lazy persist mode for optimal performance
    db = AsyncDictSQLite(db_path, persist_mode='lazy', capacity=1_000_000)
    
    try:
        print("\n1. Async Write (500 items)...")
        elapsed, ops, mem = await benchmark_async_write(db, ASYNC_WRITE_COUNT)
        results['async_write'] = (elapsed, ops, mem)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec, {mem:.2f} MB peak")
        
        print("2. Async Read (500 items)...")
        elapsed, ops, mem = await benchmark_async_read(db, ASYNC_WRITE_COUNT)
        results['async_read'] = (elapsed, ops, mem)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec, {mem:.2f} MB peak")
        
        print("3. Async Concurrent Read (1000 items, 10 concurrent)...")
        elapsed, ops, mem = await benchmark_async_concurrent_read(db, 1000, 10)
        results['async_concurrent_read'] = (elapsed, ops, mem)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec, {mem:.2f} MB peak")
        
        print("4. Async Mixed Operations (400 items)...")
        elapsed, ops, mem = await benchmark_async_mixed(db, 400)
        results['async_mixed'] = (elapsed, ops, mem)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec, {mem:.2f} MB peak")
    
    finally:
        await db.aclose()
    
    return results


async def main():
    """Main async function"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='_async_v2.db') as tmp:
        db_path = tmp.name
    
    try:
        results = await run_benchmarks(db_path)
        
        print(f"\n{'='*80}")
        print("✅ Async Benchmark completed")
        print(f"{'='*80}")
        
        for test_name, (elapsed, ops, mem) in results.items():
            if ops > 0:
                print(f"{test_name}: {elapsed:.3f}s, {ops:.0f} ops/sec, {mem:.2f} MB peak")
    
    finally:
        # Cleanup database files
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
