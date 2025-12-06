"""Benchmark test for dictsqlite-fastest Beta v2.

This module provides isolated benchmark tests for dictsqlite-fastest beta v2,
the APSW-based async high-performance version.
"""

import asyncio
import sys
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, Tuple

# Add repository root to path
REPO_ROOT = Path(__file__).parent.parent.parent

# Add dictsqlite-fastest beta v2 path
BETA_V2_DIR = REPO_ROOT / 'others' / 'beta-versions' / 'dictsqlite-fastest' / 'beta'
sys.path.insert(0, str(BETA_V2_DIR))

# Try to import dictsqlite-fastest beta v2
try:
    from dictsqlite_fastest_beta_v2 import AsyncDictSQLiteFastestBeta as AsyncBetaV2
    AVAILABLE = True
    print("✅ dictsqlite-fastest Beta v2 loaded successfully")
except ImportError as e:
    print(f"⚠️ dictsqlite-fastest beta v2 not available: {e}")
    AsyncBetaV2 = None
    AVAILABLE = False


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


async def run_benchmarks_async(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run all benchmarks for dictsqlite-fastest Beta v2.
    
    Returns:
        Dictionary mapping test name to (elapsed_time, ops_per_sec)
    """
    if not AVAILABLE:
        print("⏭️  Skipping fastest Beta v2 (not available)")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*80}")
    print(f"🔬 Benchmarking: Fastest Beta v2版 (APSW + Async)")
    print(f"{'='*80}")
    
    results = {}
    
    async with AsyncBetaV2(db_path) as db:
        print("\n1. Basic Write (300 items)...")
        elapsed, ops = await benchmark_basic_write(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items)...")
        elapsed, ops = await benchmark_basic_read(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Bulk Insert (500 items)...")
        elapsed, ops = await benchmark_bulk_insert(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Mixed Operations (400 items)...")
        elapsed, ops = await benchmark_mixed_operations(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
    
    return results


def run_benchmarks(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Synchronous wrapper for async benchmarks."""
    return asyncio.run(run_benchmarks_async(db_path))


if __name__ == "__main__":
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='_fastest.db') as tmp:
        db_path = tmp.name
    
    try:
        results = run_benchmarks(db_path)
        
        print(f"\n{'='*80}")
        print("✅ Benchmark completed")
        print(f"{'='*80}")
        
        for test_name, (elapsed, ops) in results.items():
            if ops > 0:
                print(f"{test_name}: {elapsed:.3f}s, {ops:.0f} ops/sec")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
