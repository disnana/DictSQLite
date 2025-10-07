#!/usr/bin/env python3
"""
Comprehensive Performance Benchmark for DictSQLite v3.0

Tests:
1. Synchronous operations with different persist_modes
2. Asynchronous operations leveraging Tokio
3. Multi-threaded concurrent access
4. Memory vs CPU utilization
5. Comparison: Memory vs Lazy vs WriteThrough modes
"""

import time
import os
import sys
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dictsqlite_v3 import DictSQLiteV3, AsyncDictSQLite
    print("✅ Successfully imported dictsqlite_v3")
except ImportError as e:
    print(f"❌ Failed to import dictsqlite_v3: {e}")
    print("Please build the extension first: cd dictsqlite_v3 && ./build.sh")
    sys.exit(1)


def format_ops(ops):
    """Format operations per second"""
    if ops >= 1_000_000:
        return f"{ops/1_000_000:.2f}M ops/sec"
    elif ops >= 1_000:
        return f"{ops/1_000:.2f}K ops/sec"
    else:
        return f"{ops:.2f} ops/sec"


def benchmark_sync_mode(persist_mode, num_ops=100_000):
    """Benchmark synchronous operations for a given persist mode"""
    print(f"\n{'='*60}")
    print(f"Synchronous Benchmark - {persist_mode.upper()} mode")
    print(f"{'='*60}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"test_{persist_mode}.db")
    
    try:
        # Create database
        db = DictSQLiteV3(
            db_path=db_path,
            hot_capacity=num_ops,
            enable_async=False,
            persist_mode=persist_mode
        )
        
        # Test 1: Sequential Writes
        print(f"\n📝 Test 1: Sequential Writes ({num_ops:,} operations)")
        start = time.perf_counter()
        for i in range(num_ops):
            db[f"key_{i}"] = f"value_{i}".encode()
        elapsed = time.perf_counter() - start
        write_ops = num_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(write_ops)}")
        
        # Flush for lazy mode
        if persist_mode == "lazy":
            print(f"\n💾 Flushing to disk...")
            flush_start = time.perf_counter()
            db.flush()
            flush_time = time.perf_counter() - flush_start
            print(f"   Flush time: {flush_time:.3f}s")
        
        # Test 2: Sequential Reads
        print(f"\n📖 Test 2: Sequential Reads ({num_ops:,} operations)")
        start = time.perf_counter()
        for i in range(num_ops):
            _ = db[f"key_{i}"]
        elapsed = time.perf_counter() - start
        read_ops = num_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(read_ops)}")
        
        # Test 3: Random Reads
        import random
        keys = [f"key_{random.randint(0, num_ops-1)}" for _ in range(num_ops)]
        print(f"\n🎲 Test 3: Random Reads ({num_ops:,} operations)")
        start = time.perf_counter()
        for key in keys:
            _ = db.get(key)
        elapsed = time.perf_counter() - start
        random_read_ops = num_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(random_read_ops)}")
        
        # Test 4: Bulk Operations
        bulk_data = {f"bulk_{i}": f"value_{i}".encode() for i in range(min(num_ops, 50000))}
        print(f"\n📦 Test 4: Bulk Insert ({len(bulk_data):,} operations)")
        start = time.perf_counter()
        db.bulk_insert(bulk_data)
        elapsed = time.perf_counter() - start
        bulk_ops = len(bulk_data) / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(bulk_ops)}")
        
        # Test 5: Mixed Operations
        print(f"\n🔄 Test 5: Mixed Read/Write ({num_ops:,} operations)")
        start = time.perf_counter()
        for i in range(num_ops // 2):
            db[f"mixed_{i}"] = f"val_{i}".encode()  # Write
            _ = db.get(f"key_{i}")  # Read
        elapsed = time.perf_counter() - start
        mixed_ops = num_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(mixed_ops)}")
        
        db.close()
        
        return {
            'mode': persist_mode,
            'write_ops': write_ops,
            'read_ops': read_ops,
            'random_read_ops': random_read_ops,
            'bulk_ops': bulk_ops,
            'mixed_ops': mixed_ops,
        }
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def benchmark_async_mode(num_ops=100_000):
    """Benchmark asynchronous operations"""
    print(f"\n{'='*60}")
    print(f"Asynchronous Benchmark - AsyncDictSQLite")
    print(f"{'='*60}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_async.db")
    
    try:
        # Create async database
        db = AsyncDictSQLite(db_path=db_path, capacity=num_ops)
        
        # Test 1: Async Writes
        print(f"\n📝 Test 1: Async Writes ({num_ops:,} operations)")
        start = time.perf_counter()
        for i in range(num_ops):
            db.set_async(f"key_{i}", f"value_{i}".encode())
        elapsed = time.perf_counter() - start
        write_ops = num_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(write_ops)}")
        
        # Test 2: Async Reads
        print(f"\n📖 Test 2: Async Reads ({num_ops:,} operations)")
        start = time.perf_counter()
        for i in range(num_ops):
            _ = db.get_async(f"key_{i}")
        elapsed = time.perf_counter() - start
        read_ops = num_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(read_ops)}")
        
        # Test 3: Batch Operations
        keys = [f"key_{i}" for i in range(min(num_ops, 10000))]
        print(f"\n📦 Test 3: Batch Get ({len(keys):,} operations)")
        start = time.perf_counter()
        _ = db.batch_get(keys)
        elapsed = time.perf_counter() - start
        batch_ops = len(keys) / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(batch_ops)}")
        
        # Test 4: Batch Set
        items = [(f"batch_{i}", f"value_{i}".encode()) for i in range(min(num_ops, 10000))]
        print(f"\n📦 Test 4: Batch Set ({len(items):,} operations)")
        start = time.perf_counter()
        db.batch_set(items)
        elapsed = time.perf_counter() - start
        batch_set_ops = len(items) / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Performance: {format_ops(batch_set_ops)}")
        
        return {
            'write_ops': write_ops,
            'read_ops': read_ops,
            'batch_get_ops': batch_ops,
            'batch_set_ops': batch_set_ops,
        }
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def benchmark_concurrent_access(persist_mode, num_threads=8, ops_per_thread=10000):
    """Benchmark concurrent access using multiple threads"""
    print(f"\n{'='*60}")
    print(f"Concurrent Benchmark - {num_threads} threads - {persist_mode.upper()} mode")
    print(f"{'='*60}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"test_concurrent_{persist_mode}.db")
    
    try:
        # Create database
        db = DictSQLiteV3(
            db_path=db_path,
            hot_capacity=num_threads * ops_per_thread,
            enable_async=True,
            persist_mode=persist_mode
        )
        
        def worker_write(thread_id):
            """Worker function for write operations"""
            for i in range(ops_per_thread):
                db[f"thread_{thread_id}_key_{i}"] = f"value_{i}".encode()
        
        def worker_read(thread_id):
            """Worker function for read operations"""
            for i in range(ops_per_thread):
                _ = db.get(f"thread_{thread_id}_key_{i}")
        
        # Test 1: Concurrent Writes
        print(f"\n📝 Test 1: Concurrent Writes ({num_threads} threads × {ops_per_thread:,} ops)")
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_write, i) for i in range(num_threads)]
            for future in futures:
                future.result()
        elapsed = time.perf_counter() - start
        total_ops = num_threads * ops_per_thread
        concurrent_write_ops = total_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Total operations: {total_ops:,}")
        print(f"   Performance: {format_ops(concurrent_write_ops)}")
        print(f"   Per-thread: {format_ops(concurrent_write_ops / num_threads)}")
        
        # Test 2: Concurrent Reads
        print(f"\n📖 Test 2: Concurrent Reads ({num_threads} threads × {ops_per_thread:,} ops)")
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_read, i) for i in range(num_threads)]
            for future in futures:
                future.result()
        elapsed = time.perf_counter() - start
        concurrent_read_ops = total_ops / elapsed
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Total operations: {total_ops:,}")
        print(f"   Performance: {format_ops(concurrent_read_ops)}")
        print(f"   Per-thread: {format_ops(concurrent_read_ops / num_threads)}")
        
        db.close()
        
        return {
            'mode': persist_mode,
            'threads': num_threads,
            'concurrent_write_ops': concurrent_write_ops,
            'concurrent_read_ops': concurrent_read_ops,
        }
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def print_summary(results):
    """Print summary of all benchmarks"""
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    # Sync modes comparison
    print("\n📊 Synchronous Modes Comparison:")
    print(f"{'Mode':<15} {'Writes':<20} {'Reads':<20} {'Random Reads':<20}")
    print("-" * 75)
    for result in results['sync']:
        print(f"{result['mode'].upper():<15} "
              f"{format_ops(result['write_ops']):<20} "
              f"{format_ops(result['read_ops']):<20} "
              f"{format_ops(result['random_read_ops']):<20}")
    
    # Async performance
    if 'async' in results:
        async_result = results['async']
        print("\n⚡ Asynchronous Performance:")
        print(f"  Writes:     {format_ops(async_result['write_ops'])}")
        print(f"  Reads:      {format_ops(async_result['read_ops'])}")
        print(f"  Batch Get:  {format_ops(async_result['batch_get_ops'])}")
        print(f"  Batch Set:  {format_ops(async_result['batch_set_ops'])}")
    
    # Concurrent performance
    if 'concurrent' in results:
        print("\n🔀 Concurrent Performance:")
        for result in results['concurrent']:
            print(f"\n  {result['mode'].upper()} mode ({result['threads']} threads):")
            print(f"    Writes: {format_ops(result['concurrent_write_ops'])}")
            print(f"    Reads:  {format_ops(result['concurrent_read_ops'])}")
    
    # Performance rankings
    print("\n🏆 TOP PERFORMERS:")
    all_sync_writes = [(r['mode'], r['write_ops']) for r in results['sync']]
    all_sync_writes.sort(key=lambda x: x[1], reverse=True)
    print(f"\n  Fastest Writes: {all_sync_writes[0][0].upper()} - {format_ops(all_sync_writes[0][1])}")
    
    all_sync_reads = [(r['mode'], r['read_ops']) for r in results['sync']]
    all_sync_reads.sort(key=lambda x: x[1], reverse=True)
    print(f"  Fastest Reads:  {all_sync_reads[0][0].upper()} - {format_ops(all_sync_reads[0][1])}")
    
    # Speedup comparison
    if len(all_sync_writes) > 1:
        speedup = all_sync_writes[0][1] / all_sync_writes[-1][1]
        print(f"\n  💡 {all_sync_writes[0][0].upper()} is {speedup:.1f}x faster than {all_sync_writes[-1][0].upper()} for writes")


def main():
    """Run comprehensive benchmarks"""
    print("="*60)
    print("DictSQLite v3.0 - Comprehensive Performance Benchmark")
    print("="*60)
    print(f"CPU Cores: {mp.cpu_count()}")
    
    results = {
        'sync': [],
        'concurrent': []
    }
    
    # Test all persist modes
    modes = ['memory', 'lazy', 'writethrough']
    num_ops = 100_000
    
    print(f"\n🎯 Running benchmarks with {num_ops:,} operations each...")
    
    # Synchronous benchmarks
    for mode in modes:
        result = benchmark_sync_mode(mode, num_ops=num_ops)
        results['sync'].append(result)
    
    # Asynchronous benchmark
    results['async'] = benchmark_async_mode(num_ops=num_ops)
    
    # Concurrent benchmarks (test with memory and writethrough)
    for mode in ['memory', 'writethrough']:
        result = benchmark_concurrent_access(mode, num_threads=8, ops_per_thread=10000)
        results['concurrent'].append(result)
    
    # Print summary
    print_summary(results)
    
    print(f"\n{'='*60}")
    print("✅ Benchmark completed successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
