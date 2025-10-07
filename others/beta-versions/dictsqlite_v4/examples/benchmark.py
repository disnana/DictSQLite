#!/usr/bin/env python3
"""
DictSQLite v3.0 Example and Benchmark

Demonstrates the ultra-high performance capabilities of v3.0
"""

import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dictsqlite_v3 import DictSQLiteV3, AsyncDictSQLite, is_native_available
except ImportError:
    print("❌ DictSQLite v3.0 not built yet!")
    print("\nPlease build it first:")
    print("  cd dictsqlite_v3")
    print("  maturin develop --release")
    sys.exit(1)


def format_ops(ops):
    """Format operations per second"""
    if ops >= 1_000_000:
        return f"{ops/1_000_000:.1f}M ops/sec"
    elif ops >= 1_000:
        return f"{ops/1_000:.1f}K ops/sec"
    else:
        return f"{ops:.0f} ops/sec"


def benchmark_sequential_writes():
    """Benchmark sequential writes"""
    print("\n📊 Sequential Write Benchmark")
    print("-" * 60)
    
    db = DictSQLiteV3(":memory:", hot_capacity=1_000_000, enable_async=False)
    
    num_ops = 100_000
    start = time.perf_counter()
    
    for i in range(num_ops):
        db[f"key_{i}"] = f"value_{i}"
    
    elapsed = time.perf_counter() - start
    ops_per_sec = num_ops / elapsed
    
    print(f"Operations: {num_ops:,}")
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    
    return ops_per_sec


def benchmark_sequential_reads():
    """Benchmark sequential reads"""
    print("\n📊 Sequential Read Benchmark")
    print("-" * 60)
    
    # Pre-populate
    db = DictSQLiteV3(":memory:", hot_capacity=1_000_000, enable_async=False)
    num_ops = 100_000
    
    for i in range(num_ops):
        db[f"key_{i}"] = f"value_{i}"
    
    # Benchmark reads
    start = time.perf_counter()
    
    for i in range(num_ops):
        _ = db[f"key_{i}"]
    
    elapsed = time.perf_counter() - start
    ops_per_sec = num_ops / elapsed
    
    print(f"Operations: {num_ops:,}")
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    
    return ops_per_sec


def benchmark_bulk_insert():
    """Benchmark bulk insert"""
    print("\n📊 Bulk Insert Benchmark")
    print("-" * 60)
    
    db = DictSQLiteV3(":memory:", hot_capacity=1_000_000, enable_async=False)
    
    num_ops = 100_000
    items = {f"key_{i}": f"value_{i}" for i in range(num_ops)}
    
    start = time.perf_counter()
    db.bulk_insert(items)
    elapsed = time.perf_counter() - start
    
    ops_per_sec = num_ops / elapsed
    
    print(f"Operations: {num_ops:,}")
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    
    return ops_per_sec


def benchmark_mixed_operations():
    """Benchmark mixed read/write operations"""
    print("\n📊 Mixed Operations Benchmark (50% read, 50% write)")
    print("-" * 60)
    
    db = DictSQLiteV3(":memory:", hot_capacity=1_000_000, enable_async=False)
    
    num_ops = 50_000
    start = time.perf_counter()
    
    for i in range(num_ops):
        db[f"key_{i}"] = f"value_{i}"
        _ = db.get(f"key_{i % 1000}", None)
    
    elapsed = time.perf_counter() - start
    total_ops = num_ops * 2  # write + read
    ops_per_sec = total_ops / elapsed
    
    print(f"Operations: {total_ops:,}")
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    
    return ops_per_sec


def benchmark_concurrent():
    """Benchmark concurrent access"""
    print("\n📊 Concurrent Access Benchmark")
    print("-" * 60)
    
    import threading
    
    db = DictSQLiteV3(":memory:", hot_capacity=1_000_000, enable_async=True)
    
    num_threads = 8
    ops_per_thread = 10_000
    
    def worker(thread_id):
        for i in range(ops_per_thread):
            key = f"key_{thread_id}_{i}"
            value = f"value_{thread_id}_{i}"
            db[key] = value
            _ = db.get(key, None)
    
    start = time.perf_counter()
    
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    elapsed = time.perf_counter() - start
    total_ops = num_threads * ops_per_thread * 2  # write + read
    ops_per_sec = total_ops / elapsed
    
    print(f"Threads: {num_threads}")
    print(f"Operations: {total_ops:,}")
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    
    return ops_per_sec


def main():
    """Main benchmark runner"""
    print("=" * 60)
    print("DictSQLite v3.0 Performance Benchmark")
    print("=" * 60)
    
    if not is_native_available():
        print("❌ Native extension not available!")
        return 1
    
    print("\n✅ Native Rust extension loaded")
    print("🎯 Target: 100M+ ops/sec")
    
    # Run benchmarks
    results = {}
    results['sequential_write'] = benchmark_sequential_writes()
    results['sequential_read'] = benchmark_sequential_reads()
    results['bulk_insert'] = benchmark_bulk_insert()
    results['mixed_ops'] = benchmark_mixed_operations()
    results['concurrent'] = benchmark_concurrent()
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 Benchmark Summary")
    print("=" * 60)
    
    for name, ops in results.items():
        status = "✅" if ops >= 1_000_000 else "⚠️"
        print(f"{status} {name:20s}: {format_ops(ops)}")
    
    # Check if target achieved
    max_ops = max(results.values())
    print(f"\n🏆 Peak Performance: {format_ops(max_ops)}")
    
    if max_ops >= 100_000_000:
        print("🎉 TARGET ACHIEVED: 100M+ ops/sec!")
    elif max_ops >= 10_000_000:
        print("✅ Excellent: 10M+ ops/sec achieved")
    elif max_ops >= 1_000_000:
        print("👍 Good: 1M+ ops/sec achieved")
    else:
        print("⚠️ Below target - check build configuration")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
