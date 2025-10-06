#!/usr/bin/env python3
"""Benchmark ultra-fast implementation to verify 1M+ ops/s."""

import sys
import os
import time
import tempfile
from pathlib import Path

# Add path
sys.path.insert(0, str(Path(__file__).parent))

from core_ultra import UltraFastDictSQLiteV2


def benchmark_ultra():
    """Benchmark the ultra-fast implementation."""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        print("=" * 70)
        print("Ultra-Fast DictSQLite v2.0 Benchmark")
        print("=" * 70)
        
        with UltraFastDictSQLiteV2(db_path, sync_interval=10.0) as db:
            # Warm up
            for i in range(1000):
                db[f'warmup_{i}'] = f'value_{i}'
            
            # Write benchmark
            print("\n[1] Write Performance Test (100K operations)")
            start = time.perf_counter()
            for i in range(100000):
                db[f'key_{i}'] = f'value_{i}'
            duration = time.perf_counter() - start
            write_ops = 100000 / duration
            print(f"   Duration: {duration:.3f}s")
            print(f"   Throughput: {write_ops:,.0f} ops/s")
            print(f"   Target: 1,000,000 ops/s")
            print(f"   Status: {'✅ PASS' if write_ops >= 1000000 else '❌ FAIL'}")
            
            # Read benchmark
            print("\n[2] Read Performance Test (100K operations)")
            start = time.perf_counter()
            for i in range(100000):
                _ = db[f'key_{i % 10000}']
            duration = time.perf_counter() - start
            read_ops = 100000 / duration
            print(f"   Duration: {duration:.3f}s")
            print(f"   Throughput: {read_ops:,.0f} ops/s")
            print(f"   Target: 1,000,000 ops/s")
            print(f"   Status: {'✅ PASS' if read_ops >= 1000000 else '❌ FAIL'}")
            
            # Bulk write benchmark
            print("\n[3] Bulk Write Performance Test (100K operations)")
            bulk_data = {f'bulk_{i}': f'value_{i}' for i in range(100000)}
            start = time.perf_counter()
            db.bulk_insert(bulk_data)
            duration = time.perf_counter() - start
            bulk_ops = 100000 / duration
            print(f"   Duration: {duration:.3f}s")
            print(f"   Throughput: {bulk_ops:,.0f} ops/s")
            print(f"   Target: 2,000,000 ops/s")
            print(f"   Status: {'✅ PASS' if bulk_ops >= 2000000 else '❌ FAIL'}")
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Write ops/s:  {write_ops:>12,.0f}  (target: 1,000,000)")
            print(f"Read ops/s:   {read_ops:>12,.0f}  (target: 1,000,000)")
            print(f"Bulk ops/s:   {bulk_ops:>12,.0f}  (target: 2,000,000)")
            
            write_pass = write_ops >= 1000000
            read_pass = read_ops >= 1000000
            bulk_pass = bulk_ops >= 2000000
            
            all_pass = write_pass and read_pass and bulk_pass
            print(f"\nOverall: {'✅ ALL TARGETS ACHIEVED' if all_pass else '❌ TARGETS NOT MET'}")
            
            # Sync to disk
            print("\nSyncing to disk...")
            db.sync()
            print("Sync complete.")
    
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
            os.unlink(db_path + '-wal')
            os.unlink(db_path + '-shm')
        except:
            pass


if __name__ == '__main__':
    benchmark_ultra()
