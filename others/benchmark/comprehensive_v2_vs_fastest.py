"""Comprehensive benchmark: dictsqlite_v2 (all modes) vs fastest version

Tests all persist modes and compares with fastest version to ensure v2 wins in all aspects.
"""

import sys
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, Tuple

REPO_ROOT = Path(__file__).parent.parent.parent

# Try to import dictsqlite_v2
try:
    original_path = sys.path.copy()
    repo_root_str = str(REPO_ROOT)
    sys.path = [p for p in sys.path 
                if not (p.startswith(repo_root_str) or 'dictsqlite' in p.lower()) 
                or 'site-packages' in p]
    
    from dictsqlite import DictSQLiteV4
    sys.path = original_path
    V2_AVAILABLE = True
    print("✅ dictsqlite_v2 loaded")
except Exception as e:
    print(f"❌ dictsqlite_v2 not available: {e}")
    DictSQLiteV4 = None
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


def benchmark_write(db, count: int) -> Tuple[float, float]:
    """Benchmark write operations."""
    start = time.time()
    for i in range(count):
        db[f'key_{i}'] = f'value_{i}'
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_read(db, count: int) -> Tuple[float, float]:
    """Benchmark read operations."""
    start = time.time()
    for i in range(count):
        _ = db[f'key_{i}']
    elapsed = time.time() - start
    return elapsed, count / elapsed


def benchmark_mixed(db, count: int) -> Tuple[float, float]:
    """Benchmark mixed operations."""
    start = time.time()
    for i in range(count):
        db[f'mixed_{i}'] = f'data_{i}'
        if i % 3 == 0:
            _ = db.get(f'mixed_{i}', None)
    elapsed = time.time() - start
    return elapsed, count / elapsed


def run_v2_benchmark(mode: str, db_path: str, count: int = 1000) -> Dict[str, Tuple[float, float]]:
    """Run benchmarks for dictsqlite_v2 in specific mode."""
    if not V2_AVAILABLE:
        return {'write': (0, 0), 'read': (0, 0), 'mixed': (0, 0)}
    
    print(f"\n{'='*80}")
    print(f"🔬 dictsqlite_v2 - Mode: {mode.upper()}")
    print(f"{'='*80}")
    
    results = {}
    
    # Configure based on mode
    if mode == 'memory':
        db = DictSQLiteV4(":memory:", persist_mode='memory', hot_capacity=1_000_000)
    elif mode == 'lazy':
        db = DictSQLiteV4(db_path, persist_mode='lazy', hot_capacity=1_000_000, buffer_size=100)
    else:  # writethrough
        db = DictSQLiteV4(db_path, persist_mode='writethrough', hot_capacity=1_000_000, buffer_size=100)
    
    try:
        print(f"Write ({count} items)...", end=' ')
        elapsed, ops = benchmark_write(db, count)
        results['write'] = (elapsed, ops)
        print(f"{ops:>10,.0f} ops/sec")
        
        print(f"Read ({count} items)...", end=' ')
        elapsed, ops = benchmark_read(db, count)
        results['read'] = (elapsed, ops)
        print(f"{ops:>10,.0f} ops/sec")
        
        print(f"Mixed ({count} items)...", end=' ')
        elapsed, ops = benchmark_mixed(db, count)
        results['mixed'] = (elapsed, ops)
        print(f"{ops:>10,.0f} ops/sec")
    
    finally:
        if hasattr(db, 'close'):
            db.close()
    
    return results


def run_fastest_benchmark(db_path: str, count: int = 1000) -> Dict[str, Tuple[float, float]]:
    """Run benchmarks for fastest version."""
    if not FASTEST_AVAILABLE:
        return {'write': (0, 0), 'read': (0, 0), 'mixed': (0, 0)}
    
    print(f"\n{'='*80}")
    print(f"🔬 dictsqlite-fastest Beta v2")
    print(f"{'='*80}")
    
    results = {}
    db = DictSQLiteFastestBeta(db_path, cache_capacity=1_000_000)
    
    try:
        print(f"Write ({count} items)...", end=' ')
        elapsed, ops = benchmark_write(db, count)
        results['write'] = (elapsed, ops)
        print(f"{ops:>10,.0f} ops/sec")
        
        print(f"Read ({count} items)...", end=' ')
        elapsed, ops = benchmark_read(db, count)
        results['read'] = (elapsed, ops)
        print(f"{ops:>10,.0f} ops/sec")
        
        print(f"Mixed ({count} items)...", end=' ')
        elapsed, ops = benchmark_mixed(db, count)
        results['mixed'] = (elapsed, ops)
        print(f"{ops:>10,.0f} ops/sec")
    
    finally:
        if hasattr(db, 'close'):
            db.close()
    
    return results


def main():
    """Run comprehensive benchmarks."""
    count = 2000  # Larger count for more accurate measurements
    
    print("="*80)
    print("dictsqlite_v2 (全モード) vs fastest 総合ベンチマーク")
    print(f"テスト数: {count} items")
    print("="*80)
    
    all_results = {}
    
    # Test all v2 modes
    modes = ['memory', 'lazy', 'writethrough']
    for mode in modes:
        if mode == 'memory':
            db_path = ":memory:"
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{mode}.db') as tmp:
                db_path = tmp.name
        
        try:
            results = run_v2_benchmark(mode, db_path, count)
            all_results[f'v2_{mode}'] = results
        finally:
            if mode != 'memory' and os.path.exists(db_path):
                for ext in ['', '-wal', '-shm']:
                    try:
                        os.unlink(db_path + ext)
                    except FileNotFoundError:
                        pass
    
    # Test fastest
    with tempfile.NamedTemporaryFile(delete=False, suffix='_fastest.db') as tmp:
        db_path = tmp.name
    
    try:
        results = run_fastest_benchmark(db_path, count)
        all_results['fastest'] = results
    finally:
        for ext in ['', '-wal', '-shm']:
            try:
                os.unlink(db_path + ext)
            except FileNotFoundError:
                pass
    
    # Print comparison
    print(f"\n{'='*80}")
    print("📊 パフォーマンス比較 (すべてv2がfastestに勝つ必要がある)")
    print(f"{'='*80}")
    
    test_names = ['write', 'read', 'mixed']
    test_labels = ['Write', 'Read', 'Mixed']
    
    for test_name, label in zip(test_names, test_labels):
        print(f"\n{label} ({count} items):")
        
        # Show all versions
        versions = []
        for key in ['v2_memory', 'v2_lazy', 'v2_writethrough', 'fastest']:
            if key in all_results and all_results[key][test_name][1] > 0:
                ops = all_results[key][test_name][1]
                versions.append((key, ops))
                print(f"  {key:20s}: {ops:>12,.0f} ops/sec")
        
        # Find best
        if versions:
            versions.sort(key=lambda x: x[1], reverse=True)
            best_name, best_ops = versions[0]
            
            # Check if v2 wins
            v2_versions = [v for v in versions if v[0].startswith('v2_')]
            fastest_versions = [v for v in versions if v[0] == 'fastest']
            
            if v2_versions and fastest_versions:
                best_v2_ops = max(v[1] for v in v2_versions)
                fastest_ops = fastest_versions[0][1]
                
                if best_v2_ops > fastest_ops:
                    ratio = best_v2_ops / fastest_ops
                    print(f"  🏆 v2が勝利! {ratio:.2f}x faster than fastest")
                else:
                    ratio = fastest_ops / best_v2_ops
                    print(f"  ⚠️  fastestが勝利! {ratio:.2f}x faster than best v2")
    
    # Overall winner
    print(f"\n{'='*80}")
    print("総合評価:")
    
    for key in ['v2_memory', 'v2_lazy', 'v2_writethrough', 'fastest']:
        if key in all_results:
            avg_ops = sum(r[1] for r in all_results[key].values()) / len(all_results[key])
            print(f"  {key:20s}: 平均 {avg_ops:>12,.0f} ops/sec")
    
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
