#!/usr/bin/env python3
"""
Concurrent performance demonstration for AsyncDictSQLiteFastestBeta.

This test demonstrates that async is FASTER than sync for concurrent operations.
"""
import asyncio
import tempfile
import os
import sys
import time
from statistics import mean

sys.path.insert(0, os.path.dirname(__file__))
from dictsqlite_fastest_beta import AsyncDictSQLiteFastestBeta, DictSQLiteFastestBeta


def test_sync_concurrent_simulation(iterations=3):
    """Simulate concurrent operations with sync (must be sequential)."""
    print("\n=== Sync Version (Sequential, simulating concurrent requests) ===")
    results = []
    
    for run in range(iterations):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_sync.db')
        
        try:
            with DictSQLiteFastestBeta(db_path) as db:
                count = 100
                start = time.perf_counter()
                
                # Must execute sequentially (no true concurrency)
                for i in range(count):
                    db[f'key_{i}'] = f'value_{i}'
                
                elapsed = time.perf_counter() - start
                ops = count / elapsed
                results.append(ops)
                print(f"  Run {run + 1}: {ops:,.0f} ops/s ({elapsed:.3f}s for {count} operations)")
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
    
    avg = mean(results)
    print(f"\n  Average: {avg:,.0f} ops/s")
    return avg


async def test_async_concurrent_real(iterations=3):
    """Test async version with TRUE concurrent operations."""
    print("\n=== Async Version (TRUE concurrent execution) ===")
    results = []
    
    for run in range(iterations):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_async.db')
        
        try:
            async with AsyncDictSQLiteFastestBeta(db_path, max_connections=10) as db:
                count = 100
                start = time.perf_counter()
                
                # Execute truly concurrently
                tasks = [db.aset(f'key_{i}', f'value_{i}') for i in range(count)]
                await asyncio.gather(*tasks)
                
                elapsed = time.perf_counter() - start
                ops = count / elapsed
                results.append(ops)
                print(f"  Run {run + 1}: {ops:,.0f} ops/s ({elapsed:.3f}s for {count} operations)")
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
    
    avg = mean(results)
    print(f"\n  Average: {avg:,.0f} ops/s")
    return avg


async def test_async_concurrent_reads(iterations=3):
    """Test async version with concurrent read operations."""
    print("\n=== Async Version (Concurrent READS - cache hits) ===")
    results = []
    
    for run in range(iterations):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_async.db')
        
        try:
            async with AsyncDictSQLiteFastestBeta(db_path, max_connections=10) as db:
                # Prepare data
                for i in range(100):
                    await db.aset(f'key_{i}', f'value_{i}')
                
                # Now test concurrent reads (mostly from cache)
                count = 1000
                start = time.perf_counter()
                
                tasks = [db.aget(f'key_{i % 100}') for i in range(count)]
                results_data = await asyncio.gather(*tasks)
                
                elapsed = time.perf_counter() - start
                ops = count / elapsed
                results.append(ops)
                print(f"  Run {run + 1}: {ops:,.0f} ops/s ({elapsed:.3f}s for {count} operations)")
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
    
    avg = mean(results)
    print(f"\n  Average: {avg:,.0f} ops/s")
    return avg


def test_sync_concurrent_reads_simulation(iterations=3):
    """Simulate concurrent reads with sync (must be sequential)."""
    print("\n=== Sync Version (Sequential READS, simulating concurrent requests) ===")
    results = []
    
    for run in range(iterations):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_sync.db')
        
        try:
            with DictSQLiteFastestBeta(db_path) as db:
                # Prepare data
                for i in range(100):
                    db[f'key_{i}'] = f'value_{i}'
                
                # Sequential reads
                count = 1000
                start = time.perf_counter()
                
                for i in range(count):
                    _ = db[f'key_{i % 100}']
                
                elapsed = time.perf_counter() - start
                ops = count / elapsed
                results.append(ops)
                print(f"  Run {run + 1}: {ops:,.0f} ops/s ({elapsed:.3f}s for {count} operations)")
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
    
    avg = mean(results)
    print(f"\n  Average: {avg:,.0f} ops/s")
    return avg


async def test_async_bulk_operations(iterations=3):
    """Test async bulk operations."""
    print("\n=== Async Version (Bulk Operations) ===")
    results = []
    
    for run in range(iterations):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_async.db')
        
        try:
            async with AsyncDictSQLiteFastestBeta(db_path) as db:
                count = 1000
                bulk_data = {f'key_{i}': f'value_{i}' for i in range(count)}
                
                start = time.perf_counter()
                await db.abulk_insert(bulk_data)
                elapsed = time.perf_counter() - start
                
                ops = count / elapsed
                results.append(ops)
                print(f"  Run {run + 1}: {ops:,.0f} ops/s ({elapsed:.3f}s for {count} operations)")
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
    
    avg = mean(results)
    print(f"\n  Average: {avg:,.0f} ops/s")
    return avg


def test_sync_bulk_operations(iterations=3):
    """Test sync bulk operations."""
    print("\n=== Sync Version (Bulk Operations) ===")
    results = []
    
    for run in range(iterations):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_sync.db')
        
        try:
            with DictSQLiteFastestBeta(db_path) as db:
                count = 1000
                bulk_data = {f'key_{i}': f'value_{i}' for i in range(count)}
                
                start = time.perf_counter()
                db.bulk_insert(bulk_data)
                elapsed = time.perf_counter() - start
                
                ops = count / elapsed
                results.append(ops)
                print(f"  Run {run + 1}: {ops:,.0f} ops/s ({elapsed:.3f}s for {count} operations)")
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
    
    avg = mean(results)
    print(f"\n  Average: {avg:,.0f} ops/s")
    return avg


async def main():
    """Run all performance comparisons."""
    print("=" * 80)
    print("ASYNC vs SYNC PERFORMANCE COMPARISON")
    print("Demonstrating where Async EXCELS")
    print("=" * 80)
    
    # Test 1: Concurrent writes
    print("\n" + "=" * 80)
    print("TEST 1: Concurrent Write Operations (100 operations)")
    print("=" * 80)
    sync_write_ops = test_sync_concurrent_simulation(iterations=3)
    async_write_ops = await test_async_concurrent_real(iterations=3)
    
    print(f"\n📊 Results:")
    print(f"  Sync (sequential):  {sync_write_ops:>10,.0f} ops/s")
    print(f"  Async (concurrent): {async_write_ops:>10,.0f} ops/s")
    speedup = async_write_ops / sync_write_ops
    if speedup > 1:
        print(f"  ✅ Async is {speedup:.2f}x FASTER for concurrent writes")
    else:
        print(f"  ⚠️  Async is {1/speedup:.2f}x slower (overhead from async machinery)")
    
    # Test 2: Concurrent reads (cached)
    print("\n" + "=" * 80)
    print("TEST 2: Concurrent Read Operations (1000 reads, mostly cached)")
    print("=" * 80)
    sync_read_ops = test_sync_concurrent_reads_simulation(iterations=3)
    async_read_ops = await test_async_concurrent_reads(iterations=3)
    
    print(f"\n📊 Results:")
    print(f"  Sync (sequential):  {sync_read_ops:>10,.0f} ops/s")
    print(f"  Async (concurrent): {async_read_ops:>10,.0f} ops/s")
    speedup = async_read_ops / sync_read_ops
    if speedup > 1:
        print(f"  ✅ Async is {speedup:.2f}x FASTER for concurrent reads")
    else:
        print(f"  ⚠️  Async is {1/speedup:.2f}x slower")
    
    # Test 3: Bulk operations
    print("\n" + "=" * 80)
    print("TEST 3: Bulk Operations (1000 items)")
    print("=" * 80)
    sync_bulk_ops = test_sync_bulk_operations(iterations=3)
    async_bulk_ops = await test_async_bulk_operations(iterations=3)
    
    print(f"\n📊 Results:")
    print(f"  Sync:  {sync_bulk_ops:>10,.0f} ops/s")
    print(f"  Async: {async_bulk_ops:>10,.0f} ops/s")
    ratio = async_bulk_ops / sync_bulk_ops
    if ratio > 0.8:
        print(f"  ✅ Async maintains {ratio*100:.1f}% of sync performance ({(1-ratio)*100:.1f}% overhead)")
    else:
        print(f"  ⚠️  Async is {1/ratio:.2f}x slower")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Key Findings:")
    print()
    
    if async_write_ops > sync_write_ops:
        print(f"  1. ✅ Async concurrent writes: {speedup:.2f}x faster than sync")
        print(f"     - Async can process multiple requests simultaneously")
        print(f"     - Sync must process requests one at a time")
    
    if async_read_ops > sync_read_ops:
        print(f"  2. ✅ Async concurrent reads: Much faster with caching")
        print(f"     - Cache hits are nearly instantaneous")
        print(f"     - Parallel execution maximizes throughput")
    
    if async_bulk_ops > sync_bulk_ops * 0.8:
        print(f"  3. ✅ Async bulk operations: Comparable to sync")
        print(f"     - Only ~{(1-ratio)*100:.0f}% overhead for async benefits")
    
    print()
    print("When to use Async:")
    print("  • Web applications with concurrent requests")
    print("  • Real-time APIs serving multiple clients")
    print("  • Applications needing high responsiveness")
    print("  • Workloads with mixed read/write operations")
    print()
    print("When to use Sync:")
    print("  • Batch processing with sequential operations")
    print("  • Simple scripts without concurrency needs")
    print("  • Maximum throughput for single-threaded work")
    print()


if __name__ == '__main__':
    asyncio.run(main())
