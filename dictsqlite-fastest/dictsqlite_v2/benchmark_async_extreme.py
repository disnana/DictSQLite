"""
Benchmark for extreme async performance.
Target: 100M+ ops/s with multiprocessing
"""

import asyncio
import time
import random
from core_async_extreme import AsyncDictSQLiteV2Extreme


async def benchmark_random_access(num_operations: int = 1000000):
    """Benchmark random access operations."""
    print(f"\n{'='*80}")
    print(f"Extreme Async Benchmark - Random Access")
    print(f"{'='*80}")
    print(f"Operations: {num_operations:,}")
    print(f"Pattern: Random keys, various data")
    print()
    
    db_path = "/tmp/bench_async_extreme.db"
    
    async with AsyncDictSQLiteV2Extreme(db_path, num_workers=8) as db:
        # Prepare varied data
        print("Preparing test data...")
        test_data = {}
        for i in range(num_operations):
            key = f"key_{random.randint(0, num_operations)}"
            value = {
                'id': i,
                'data': f"value_{i}" * random.randint(1, 5),
                'nested': {'field': random.random()}
            }
            test_data[key] = value
        
        # Benchmark write
        print(f"\n1. Testing WRITE performance (random access)...")
        start = time.perf_counter()
        
        # Concurrent writes
        await db.bulk_set(test_data)
        
        write_duration = time.perf_counter() - start
        write_ops = num_operations / write_duration
        
        print(f"   Duration: {write_duration:.3f}s")
        print(f"   Throughput: {write_ops:,.0f} ops/s")
        print(f"   Target: 100,000,000 ops/s")
        print(f"   Achievement: {(write_ops / 100_000_000) * 100:.1f}%")
        
        # Benchmark read
        print(f"\n2. Testing READ performance (random access)...")
        keys_to_read = random.sample(list(test_data.keys()), min(num_operations, len(test_data)))
        
        start = time.perf_counter()
        
        # Concurrent reads
        results = await db.bulk_get(keys_to_read)
        
        read_duration = time.perf_counter() - start
        read_ops = len(keys_to_read) / read_duration
        
        print(f"   Duration: {read_duration:.3f}s")
        print(f"   Throughput: {read_ops:,.0f} ops/s")
        print(f"   Target: 100,000,000 ops/s")
        print(f"   Achievement: {(read_ops / 100_000_000) * 100:.1f}%")
        
        # Mixed operations
        print(f"\n3. Testing MIXED operations (random access)...")
        start = time.perf_counter()
        
        tasks = []
        for i in range(num_operations // 2):
            # Half writes, half reads
            if i % 2 == 0:
                key = f"mixed_key_{random.randint(0, num_operations)}"
                value = {'mixed': i}
                tasks.append(db.set(key, value))
            else:
                key = random.choice(list(test_data.keys()))
                tasks.append(db.get(key))
        
        await asyncio.gather(*tasks)
        
        mixed_duration = time.perf_counter() - start
        mixed_ops = (num_operations // 2) / mixed_duration
        
        print(f"   Duration: {mixed_duration:.3f}s")
        print(f"   Throughput: {mixed_ops:,.0f} ops/s")
        print(f"   Target: 100,000,000 ops/s")
        print(f"   Achievement: {(mixed_ops / 100_000_000) * 100:.1f}%")
        
        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY - Extreme Async Performance")
        print(f"{'='*80}")
        print(f"Write:  {write_ops:>15,.0f} ops/s  ({(write_ops / 100_000_000) * 100:>5.1f}% of 100M target)")
        print(f"Read:   {read_ops:>15,.0f} ops/s  ({(read_ops / 100_000_000) * 100:>5.1f}% of 100M target)")
        print(f"Mixed:  {mixed_ops:>15,.0f} ops/s  ({(mixed_ops / 100_000_000) * 100:>5.1f}% of 100M target)")
        print()
        
        if write_ops >= 100_000_000 and read_ops >= 100_000_000:
            print("✅ TARGET ACHIEVED: 100M+ ops/s!")
        else:
            print(f"⚠️  Target not yet reached. Current max: {max(write_ops, read_ops):,.0f} ops/s")
        print(f"{'='*80}\n")


async def benchmark_concurrent_operations(num_concurrent: int = 10000):
    """Benchmark highly concurrent operations."""
    print(f"\n{'='*80}")
    print(f"Extreme Async Benchmark - Concurrent Operations")
    print(f"{'='*80}")
    print(f"Concurrent operations: {num_concurrent:,}")
    print()
    
    db_path = "/tmp/bench_async_concurrent.db"
    
    async with AsyncDictSQLiteV2Extreme(db_path, num_workers=8) as db:
        print("Testing concurrent writes...")
        start = time.perf_counter()
        
        # Launch all operations concurrently
        tasks = []
        for i in range(num_concurrent):
            key = f"concurrent_key_{i}"
            value = {'data': f"value_{i}"}
            tasks.append(db.set(key, value))
        
        await asyncio.gather(*tasks)
        
        duration = time.perf_counter() - start
        ops_per_sec = num_concurrent / duration
        
        print(f"   Duration: {duration:.3f}s")
        print(f"   Throughput: {ops_per_sec:,.0f} ops/s")
        print(f"   Concurrency achieved: {num_concurrent:,} simultaneous operations")
        print()


if __name__ == "__main__":
    print("DictSQLite V2 - Extreme Async Performance Benchmark")
    print("Target: 100M+ ops/s through multiprocessing\n")
    
    # Run benchmarks
    asyncio.run(benchmark_random_access(1000000))
    asyncio.run(benchmark_concurrent_operations(10000))
