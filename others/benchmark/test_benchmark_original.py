"""Benchmark test for DictSQLite Original version.

This module provides isolated benchmark tests for the original sqlite3-based
DictSQLite implementation.
"""

import sys
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, Tuple

# Add repository root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Import Original version directly from source
try:
    import importlib.util
    import importlib.machinery
    
    original_main_path = str(REPO_ROOT / 'dictsqlite' / 'main.py')
    loader = importlib.machinery.SourceFileLoader('dictsqlite_original_main', original_main_path)
    spec = importlib.util.spec_from_loader('dictsqlite_original_main', loader)
    dictsqlite_original = importlib.util.module_from_spec(spec)
    
    original_syspath = sys.path.copy()
    sys.path.insert(0, str(REPO_ROOT))
    try:
        loader.exec_module(dictsqlite_original)
    finally:
        sys.path = original_syspath
    
    DictSQLite = dictsqlite_original.DictSQLite
    AVAILABLE = True
except Exception as e:
    print(f"❌ Failed to import Original DictSQLite: {e}")
    DictSQLite = None
    AVAILABLE = False


def benchmark_basic_write(db, count: int) -> Tuple[float, float]:
    """Benchmark basic write operations."""
    start = time.time()
    for i in range(count):
        db[f'key_{i}'] = f'value_{i}'
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_basic_read(db, count: int) -> Tuple[float, float]:
    """Benchmark sequential read operations."""
    start = time.time()
    for i in range(count):
        _ = db[f'key_{i}']
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_bulk_insert(db, count: int) -> Tuple[float, float]:
    """Benchmark bulk insert."""
    start = time.time()
    for i in range(count):
        db[f'bulk_key_{i}'] = f'bulk_value_{i}'
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_mixed_operations(db, count: int) -> Tuple[float, float]:
    """Benchmark mixed read/write operations."""
    start = time.time()
    for i in range(count):
        db[f'mixed_{i}'] = f'data_{i}'
        if i % 3 == 0:
            _ = db.get(f'mixed_{i}', None)
    elapsed = time.time() - start
    return elapsed, count / elapsed


def run_benchmarks(db_path: str) -> Dict[str, Tuple[float, float]]:
    """Run all benchmarks for Original DictSQLite.
    
    Returns:
        Dictionary mapping test name to (elapsed_time, ops_per_sec)
    """
    if not AVAILABLE:
        print("⏭️  Skipping Original version (not available)")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*80}")
    print(f"🔬 Benchmarking: Original版 (sqlite3-based)")
    print(f"{'='*80}")
    
    results = {}
    
    with DictSQLite(db_path) as db:
        print("\n1. Basic Write (300 items)...")
        elapsed, ops = benchmark_basic_write(db, 300)
        results['basic_write'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("2. Basic Read (300 items)...")
        elapsed, ops = benchmark_basic_read(db, 300)
        results['basic_read'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("3. Bulk Insert (500 items)...")
        elapsed, ops = benchmark_bulk_insert(db, 500)
        results['bulk_insert'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
        
        print("4. Mixed Operations (400 items)...")
        elapsed, ops = benchmark_mixed_operations(db, 400)
        results['mixed_ops'] = (elapsed, ops)
        print(f"   ⏱️  {elapsed:.3f}s, {ops:.0f} ops/sec")
    
    return results


if __name__ == "__main__":
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='_original.db') as tmp:
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
