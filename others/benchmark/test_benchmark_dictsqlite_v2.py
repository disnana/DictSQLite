"""Benchmark test for dictsqlite_v2 (Rust extension).

This module provides isolated benchmark tests for dictsqlite_v2,
the high-performance Rust extension version.
"""

import sys
import time
import tempfile
import os
import subprocess
from pathlib import Path
from typing import Dict, Tuple

# Add repository root to path
REPO_ROOT = Path(__file__).parent.parent.parent


def check_dictsqlite_v2_installed() -> bool:
    """Check if dictsqlite_v2 is properly installed."""
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'from dictsqlite import DictSQLiteV4; print("OK")'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and "OK" in result.stdout
    except Exception:
        return False


# Try to import dictsqlite_v2
try:
    # Filter out local dictsqlite from path to get installed version
    original_path = sys.path.copy()
    sys.path = [p for p in sys.path if 'dictsqlite' not in p.lower() or 'site-packages' in p]
    
    from dictsqlite import DictSQLiteV4
    
    sys.path = original_path
    AVAILABLE = True
    print("✅ dictsqlite_v2 (DictSQLiteV4) loaded successfully")
    
except Exception as e:
    print(f"⚠️ dictsqlite_v2 not available: {e}")
    print(f"   Checking installation...")
    if check_dictsqlite_v2_installed():
        print(f"   ℹ️  dictsqlite_v2 is installed but import failed due to path issues")
        print(f"   ℹ️  Try running from a different directory or use subprocess")
    DictSQLiteV4 = None
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
    """Run all benchmarks for dictsqlite_v2.
    
    Returns:
        Dictionary mapping test name to (elapsed_time, ops_per_sec)
    """
    if not AVAILABLE:
        print("⏭️  Skipping dictsqlite_v2 (not available)")
        return {
            'basic_write': (0, 0),
            'basic_read': (0, 0),
            'bulk_insert': (0, 0),
            'mixed_ops': (0, 0)
        }
    
    print(f"\n{'='*80}")
    print(f"🔬 Benchmarking: dictsqlite_v2版 (Rust Extension v2.0.6)")
    print(f"{'='*80}")
    
    results = {}
    
    # Use lazy persist mode for optimal performance
    db = DictSQLiteV4(db_path, persist_mode='lazy')
    
    try:
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
    
    finally:
        if hasattr(db, 'close'):
            db.close()
    
    return results


if __name__ == "__main__":
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='_v2.db') as tmp:
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
