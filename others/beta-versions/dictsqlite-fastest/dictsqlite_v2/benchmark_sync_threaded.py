"""
Benchmark for sync threaded performance.
Target: Python's limits (10-20M ops/s with threading)
"""

import time
import random
from core_sync_threaded import DictSQLiteV2Threaded


def benchmark_sync_threaded(num_operations: int = 1000000):
    """Benchmark threaded sync operations."""
    print(f"\n{'='*80}")
    print(f"Sync Threaded Benchmark")
    print(f"{'='*80}")
    print(f"Operations: {num_operations:,}")
    print(f"Threads: 8")
    print()
    
    db_path = "/tmp/bench_sync_threaded.db"
    
    with DictSQLiteV2Threaded(db_path, num_threads=8) as db:
        # Prepare data
        print("Preparing test data...")
        test_data = {}
        for i in range(num_operations):
            key = f"key_{random.randint(0, num_operations)}"
            value = {
                'id': i,
                'data': f"value_{i}",
                'nested': {'field': random.random()}
            }
            test_data[key] = value
        
        # Benchmark write
        print(f"\n1. Testing WRITE performance (threaded)...")
        start = time.perf_counter()
        
        db.bulk_insert(test_data)
        
        write_duration = time.perf_counter() - start
        write_ops = num_operations / write_duration
        
        print(f"   Duration: {write_duration:.3f}s")
        print(f"   Throughput: {write_ops:,.0f} ops/s")
        print(f"   Target: 10,000,000 ops/s (Python limit with threads)")
        print(f"   Achievement: {(write_ops / 10_000_000) * 100:.1f}%")
        
        # Benchmark read
        print(f"\n2. Testing READ performance (threaded)...")
        keys_to_read = random.sample(list(test_data.keys()), min(num_operations, len(test_data)))
        
        start = time.perf_counter()
        
        for key in keys_to_read:
            _ = db.get(key)
        
        read_duration = time.perf_counter() - start
        read_ops = len(keys_to_read) / read_duration
        
        print(f"   Duration: {read_duration:.3f}s")
        print(f"   Throughput: {read_ops:,.0f} ops/s")
        print(f"   Target: 10,000,000 ops/s")
        print(f"   Achievement: {(read_ops / 10_000_000) * 100:.1f}%")
        
        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY - Sync Threaded Performance")
        print(f"{'='*80}")
        print(f"Write:  {write_ops:>15,.0f} ops/s")
        print(f"Read:   {read_ops:>15,.0f} ops/s")
        print()
        
        if write_ops >= 10_000_000 or read_ops >= 10_000_000:
            print("✅ Python limits reached!")
        else:
            print(f"⚠️  Current max: {max(write_ops, read_ops):,.0f} ops/s")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    print("DictSQLite V2 - Sync Threaded Performance Benchmark")
    print("Target: 10-20M ops/s (Python limits with threading)\n")
    
    benchmark_sync_threaded(1000000)
