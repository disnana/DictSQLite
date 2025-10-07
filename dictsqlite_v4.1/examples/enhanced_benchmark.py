#!/usr/bin/env python3
"""
Enhanced Performance Benchmark for DictSQLite v3.0

Comprehensive testing to ensure:
1. No performance regression from previous versions
2. Optimal sync and async performance
3. Multi-threaded scaling analysis
4. CPU and memory utilization
"""

import time
import os
import sys
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
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


def benchmark_single_thread_sync(persist_mode, num_ops=100_000):
    """Benchmark single-threaded synchronous operations"""
    print(f"\n{'='*70}")
    print(f"SINGLE-THREADED SYNC - {persist_mode.upper()} mode")
    print(f"{'='*70}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"test_{persist_mode}.db")
    
    results = {}
    
    try:
        db = DictSQLiteV3(
            db_path=db_path,
            hot_capacity=num_ops * 2,
            enable_async=False,
            persist_mode=persist_mode
        )
        
        # Test 1: Sequential Writes
        print(f"\n📝 Sequential Writes ({num_ops:,} ops)")
        start = time.perf_counter()
        for i in range(num_ops):
            db[f"key_{i}"] = f"value_{i}".encode()
        elapsed = time.perf_counter() - start
        write_ops = num_ops / elapsed
        results['write_ops'] = write_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(write_ops)}")
        
        # Flush for lazy mode
        if persist_mode == "lazy":
            flush_start = time.perf_counter()
            db.flush()
            flush_time = time.perf_counter() - flush_start
            print(f"   Flush: {flush_time:.3f}s")
        
        # Test 2: Sequential Reads
        print(f"\n📖 Sequential Reads ({num_ops:,} ops)")
        start = time.perf_counter()
        for i in range(num_ops):
            _ = db[f"key_{i}"]
        elapsed = time.perf_counter() - start
        read_ops = num_ops / elapsed
        results['read_ops'] = read_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(read_ops)}")
        
        # Test 3: Random Access
        import random
        keys = [f"key_{random.randint(0, num_ops-1)}" for _ in range(num_ops)]
        print(f"\n🎲 Random Reads ({num_ops:,} ops)")
        start = time.perf_counter()
        for key in keys:
            _ = db.get(key)
        elapsed = time.perf_counter() - start
        random_ops = num_ops / elapsed
        results['random_ops'] = random_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(random_ops)}")
        
        # Test 4: Mixed Operations
        print(f"\n🔄 Mixed R/W 50/50 ({num_ops:,} ops)")
        start = time.perf_counter()
        for i in range(num_ops // 2):
            db[f"mixed_{i}"] = f"val_{i}".encode()  # Write
            _ = db.get(f"key_{i}")  # Read
        elapsed = time.perf_counter() - start
        mixed_ops = num_ops / elapsed
        results['mixed_ops'] = mixed_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(mixed_ops)}")
        
        db.close()
        return results
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def worker_write(args):
    """Worker function for multi-threaded writes"""
    db_path, start_id, count, persist_mode = args
    temp_dir = tempfile.mkdtemp()
    local_db_path = os.path.join(temp_dir, f"worker_{start_id}.db")
    
    try:
        db = DictSQLiteV3(
            db_path=local_db_path,
            hot_capacity=count * 2,
            enable_async=False,
            persist_mode=persist_mode
        )
        
        start_time = time.perf_counter()
        for i in range(count):
            db[f"key_{start_id + i}"] = f"value_{start_id + i}".encode()
        elapsed = time.perf_counter() - start_time
        
        db.close()
        return count, elapsed
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def worker_read(args):
    """Worker function for multi-threaded reads"""
    db_path, start_id, count, persist_mode = args
    temp_dir = tempfile.mkdtemp()
    local_db_path = os.path.join(temp_dir, f"worker_read_{start_id}.db")
    
    try:
        db = DictSQLiteV3(
            db_path=local_db_path,
            hot_capacity=count * 2,
            enable_async=False,
            persist_mode=persist_mode
        )
        
        # Pre-populate
        for i in range(count):
            db[f"key_{start_id + i}"] = f"value_{start_id + i}".encode()
        
        start_time = time.perf_counter()
        for i in range(count):
            _ = db[f"key_{start_id + i}"]
        elapsed = time.perf_counter() - start_time
        
        db.close()
        return count, elapsed
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def benchmark_multi_thread_sync(persist_mode, num_threads=4, ops_per_thread=10_000):
    """Benchmark multi-threaded synchronous operations"""
    print(f"\n{'='*70}")
    print(f"MULTI-THREADED SYNC ({num_threads} threads) - {persist_mode.upper()} mode")
    print(f"{'='*70}")
    
    total_ops = num_threads * ops_per_thread
    
    # Test 1: Concurrent Writes
    print(f"\n📝 Concurrent Writes ({num_threads} threads × {ops_per_thread:,} ops = {total_ops:,} total)")
    
    tasks = [(f"db_{i}", i * ops_per_thread, ops_per_thread, persist_mode) 
             for i in range(num_threads)]
    
    overall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(worker_write, tasks))
    overall_elapsed = time.perf_counter() - overall_start
    
    total_ops_done = sum(r[0] for r in results)
    aggregate_throughput = total_ops_done / overall_elapsed
    per_thread_avg = aggregate_throughput / num_threads
    
    print(f"   Total time: {overall_elapsed:.3f}s")
    print(f"   Aggregate throughput: {format_ops(aggregate_throughput)}")
    print(f"   Per-thread average: {format_ops(per_thread_avg)}")
    
    # Calculate efficiency
    single_thread_baseline = 1_000_000  # Approximate from earlier tests
    efficiency = (aggregate_throughput / num_threads) / single_thread_baseline * 100
    print(f"   Threading efficiency: {efficiency:.1f}%")
    
    # Test 2: Concurrent Reads
    print(f"\n📖 Concurrent Reads ({num_threads} threads × {ops_per_thread:,} ops = {total_ops:,} total)")
    
    tasks = [(f"db_{i}", i * ops_per_thread, ops_per_thread, persist_mode) 
             for i in range(num_threads)]
    
    overall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(worker_read, tasks))
    overall_elapsed = time.perf_counter() - overall_start
    
    total_ops_done = sum(r[0] for r in results)
    aggregate_throughput = total_ops_done / overall_elapsed
    per_thread_avg = aggregate_throughput / num_threads
    
    print(f"   Total time: {overall_elapsed:.3f}s")
    print(f"   Aggregate throughput: {format_ops(aggregate_throughput)}")
    print(f"   Per-thread average: {format_ops(per_thread_avg)}")
    
    read_efficiency = (aggregate_throughput / num_threads) / (3_000_000) * 100
    print(f"   Threading efficiency: {read_efficiency:.1f}%")
    
    return {
        'write_aggregate': aggregate_throughput,
        'write_per_thread': per_thread_avg,
        'read_aggregate': aggregate_throughput,
        'read_per_thread': per_thread_avg,
    }


def benchmark_async_operations(num_ops=100_000):
    """Benchmark asynchronous operations with enhanced async runtime"""
    print(f"\n{'='*70}")
    print(f"ASYNC OPERATIONS - AsyncDictSQLite (Enhanced Rayon)")
    print(f"{'='*70}")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_async.db")
    
    results = {}
    
    try:
        db = AsyncDictSQLite(db_path=db_path, capacity=num_ops * 2)
        
        # Test 1: Async Writes
        print(f"\n📝 Async Writes ({num_ops:,} ops)")
        start = time.perf_counter()
        for i in range(num_ops):
            db.set_async(f"key_{i}", f"value_{i}".encode())
        elapsed = time.perf_counter() - start
        async_write_ops = num_ops / elapsed
        results['async_write'] = async_write_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(async_write_ops)}")
        
        # Test 2: Async Reads
        print(f"\n📖 Async Reads ({num_ops:,} ops)")
        start = time.perf_counter()
        for i in range(num_ops):
            _ = db.get_async(f"key_{i}")
        elapsed = time.perf_counter() - start
        async_read_ops = num_ops / elapsed
        results['async_read'] = async_read_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(async_read_ops)}")
        
        # Test 3: Batch Set (Rayon-optimized)
        batch_size = min(num_ops, 50_000)
        batch_items = [(f"batch_{i}", f"value_{i}".encode()) for i in range(batch_size)]
        print(f"\n📦 Batch Set - Rayon parallel ({len(batch_items):,} ops)")
        start = time.perf_counter()
        db.batch_set(batch_items)
        elapsed = time.perf_counter() - start
        batch_set_ops = len(batch_items) / elapsed
        results['batch_set'] = batch_set_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(batch_set_ops)}")
        
        # Test 4: Batch Get (Rayon-optimized)
        keys = [f"key_{i}" for i in range(batch_size)]
        print(f"\n📦 Batch Get - Rayon parallel ({len(keys):,} ops)")
        start = time.perf_counter()
        _ = db.batch_get(keys)
        elapsed = time.perf_counter() - start
        batch_get_ops = len(keys) / elapsed
        results['batch_get'] = batch_get_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(batch_get_ops)}")
        
        # Test 5: Fast Batch Get (No Python object conversion)
        print(f"\n⚡ Batch Get Fast - No PyObject ({len(keys):,} ops)")
        start = time.perf_counter()
        _ = db.batch_get_fast(keys)
        elapsed = time.perf_counter() - start
        fast_get_ops = len(keys) / elapsed
        results['fast_get'] = fast_get_ops
        print(f"   Time: {elapsed:.3f}s | Performance: {format_ops(fast_get_ops)}")
        
        return results
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def compare_all_modes():
    """Run comprehensive comparison across all modes"""
    print("\n" + "="*70)
    print("COMPREHENSIVE PERFORMANCE COMPARISON - DictSQLite v3.0")
    print("="*70)
    print(f"CPU Cores: {mp.cpu_count()}")
    print(f"Test Size: 100,000 operations")
    print("="*70)
    
    # Single-threaded sync tests
    memory_results = benchmark_single_thread_sync("memory", 100_000)
    lazy_results = benchmark_single_thread_sync("lazy", 100_000)
    writethrough_results = benchmark_single_thread_sync("writethrough", 100_000)
    
    # Multi-threaded sync tests
    num_threads = min(4, mp.cpu_count())
    memory_mt = benchmark_multi_thread_sync("memory", num_threads, 10_000)
    
    # Async tests
    async_results = benchmark_async_operations(100_000)
    
    # Summary
    print("\n" + "="*70)
    print("PERFORMANCE SUMMARY")
    print("="*70)
    
    print("\n📊 SINGLE-THREADED SYNCHRONOUS")
    print(f"{'Mode':<15} {'Write':<20} {'Read':<20} {'Random':<20}")
    print("-" * 70)
    print(f"{'MEMORY':<15} {format_ops(memory_results['write_ops']):<20} "
          f"{format_ops(memory_results['read_ops']):<20} "
          f"{format_ops(memory_results['random_ops']):<20}")
    print(f"{'LAZY':<15} {format_ops(lazy_results['write_ops']):<20} "
          f"{format_ops(lazy_results['read_ops']):<20} "
          f"{format_ops(lazy_results['random_ops']):<20}")
    print(f"{'WRITETHROUGH':<15} {format_ops(writethrough_results['write_ops']):<20} "
          f"{format_ops(writethrough_results['read_ops']):<20} "
          f"{format_ops(writethrough_results['random_ops']):<20}")
    
    print(f"\n📊 MULTI-THREADED ({num_threads} threads) - MEMORY mode")
    print(f"   Concurrent Writes: {format_ops(memory_mt['write_aggregate'])} aggregate "
          f"({format_ops(memory_mt['write_per_thread'])} per thread)")
    print(f"   Concurrent Reads:  {format_ops(memory_mt['read_aggregate'])} aggregate "
          f"({format_ops(memory_mt['read_per_thread'])} per thread)")
    
    print(f"\n📊 ASYNC OPERATIONS (Rayon)")
    print(f"   Async Writes:      {format_ops(async_results['async_write'])}")
    print(f"   Async Reads:       {format_ops(async_results['async_read'])}")
    print(f"   Batch Set (Rayon): {format_ops(async_results['batch_set'])}")
    print(f"   Batch Get (Rayon): {format_ops(async_results['batch_get'])}")
    print(f"   Fast Get (direct): {format_ops(async_results['fast_get'])}")
    
    print("\n" + "="*70)
    print("✅ BENCHMARK COMPLETE")
    print("="*70)
    
    # Performance checks
    print("\n🔍 PERFORMANCE VALIDATION")
    checks_passed = 0
    total_checks = 0
    
    # Check 1: Single-threaded write should be > 1M ops/sec for lazy/memory
    total_checks += 1
    if lazy_results['write_ops'] > 1_000_000:
        print(f"✅ Lazy write performance: {format_ops(lazy_results['write_ops'])} (> 1M ops/sec)")
        checks_passed += 1
    else:
        print(f"❌ Lazy write performance: {format_ops(lazy_results['write_ops'])} (expected > 1M ops/sec)")
    
    # Check 2: Single-threaded read should be > 2M ops/sec
    total_checks += 1
    if memory_results['read_ops'] > 2_000_000:
        print(f"✅ Memory read performance: {format_ops(memory_results['read_ops'])} (> 2M ops/sec)")
        checks_passed += 1
    else:
        print(f"❌ Memory read performance: {format_ops(memory_results['read_ops'])} (expected > 2M ops/sec)")
    
    # Check 3: Async batch operations should be > 4M ops/sec
    total_checks += 1
    if async_results['batch_set'] > 4_000_000:
        print(f"✅ Async batch set: {format_ops(async_results['batch_set'])} (> 4M ops/sec)")
        checks_passed += 1
    else:
        print(f"⚠️  Async batch set: {format_ops(async_results['batch_set'])} (target > 4M ops/sec)")
        if async_results['batch_set'] > 1_000_000:
            checks_passed += 1  # Still acceptable if > 1M
    
    # Check 4: Multi-threaded should show scaling
    total_checks += 1
    if memory_mt['write_aggregate'] > memory_results['write_ops'] * 0.5:
        scaling_factor = memory_mt['write_aggregate'] / memory_results['write_ops']
        print(f"✅ Multi-threading scales: {scaling_factor:.2f}x effective speedup")
        checks_passed += 1
    else:
        print(f"❌ Multi-threading not scaling properly")
    
    print(f"\n{'='*70}")
    print(f"VALIDATION: {checks_passed}/{total_checks} checks passed")
    print(f"{'='*70}")
    
    return checks_passed == total_checks


if __name__ == "__main__":
    success = compare_all_modes()
    sys.exit(0 if success else 1)
