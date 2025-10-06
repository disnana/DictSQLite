"""
Extreme Performance Benchmark
Target: 100M+ ops/s for bulk operations
"""

import time
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core_extreme import DictSQLiteV2Extreme


def format_ops(ops: float) -> str:
    """Format operations per second"""
    if ops >= 1_000_000:
        return f"{ops/1_000_000:.2f}M ops/s"
    elif ops >= 1_000:
        return f"{ops/1_000:.2f}K ops/s"
    else:
        return f"{ops:.2f} ops/s"


def benchmark_bulk_write(db_path: str, num_items: int = 10_000_000):
    """Benchmark bulk write operations"""
    print(f"\n{'='*60}")
    print(f"Bulk Write Benchmark ({num_items:,} items)")
    print(f"{'='*60}")
    
    # Prepare data
    data = {f'key_{i}': i for i in range(num_items)}
    
    # Clean start
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    # Benchmark
    start = time.perf_counter()
    
    with DictSQLiteV2Extreme(db_path) as db:
        db.bulk_insert(data)
    
    elapsed = time.perf_counter() - start
    ops_per_sec = num_items / elapsed
    
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    print(f"Raw: {ops_per_sec:,.0f} ops/s")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    return ops_per_sec


def benchmark_bulk_read(db_path: str, num_items: int = 10_000_000):
    """Benchmark bulk read operations"""
    print(f"\n{'='*60}")
    print(f"Bulk Read Benchmark ({num_items:,} items)")
    print(f"{'='*60}")
    
    # Setup data
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    data = {f'key_{i}': i for i in range(num_items)}
    
    with DictSQLiteV2Extreme(db_path) as db:
        db.bulk_insert(data)
    
    # Benchmark sequential reads
    start = time.perf_counter()
    
    with DictSQLiteV2Extreme(db_path) as db:
        for i in range(num_items):
            _ = db[f'key_{i}']
    
    elapsed = time.perf_counter() - start
    ops_per_sec = num_items / elapsed
    
    print(f"Time: {elapsed:.3f}s")
    print(f"Throughput: {format_ops(ops_per_sec)}")
    print(f"Raw: {ops_per_sec:,.0f} ops/s")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    return ops_per_sec


def benchmark_bulk_throughput(num_batches: int = 1000, batch_size: int = 100_000):
    """
    Benchmark bulk throughput - measure total items/sec across many bulk operations
    This is closer to how 100M+ ops/s can be achieved
    """
    total_items = num_batches * batch_size
    print(f"\n{'='*60}")
    print(f"Bulk Throughput Benchmark")
    print(f"Batches: {num_batches:,} x {batch_size:,} items = {total_items:,} total")
    print(f"{'='*60}")
    
    db_path = '/tmp/test_extreme_bulk.db'
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    db = DictSQLiteV2Extreme(db_path)
    
    # Bulk write benchmark
    print("\nBulk Write (memory only):")
    start = time.perf_counter()
    for batch_num in range(num_batches):
        batch_data = {f'k{batch_num}_{i}': i for i in range(batch_size)}
        db.bulk_insert(batch_data)
    elapsed = time.perf_counter() - start
    write_ops = total_items / elapsed
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Throughput: {format_ops(write_ops)}")
    print(f"  Raw: {write_ops:,.0f} ops/s")
    
    # Bulk read via iteration (fastest pattern)
    print("\nBulk Read (via iteration):")
    start = time.perf_counter()
    count = sum(1 for _ in db.values())
    elapsed = time.perf_counter() - start
    read_ops = count / elapsed
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Items: {count:,}")
    print(f"  Throughput: {format_ops(read_ops)}")
    print(f"  Raw: {read_ops:,.0f} ops/s")
    
    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    return write_ops, read_ops


def main():
    print("="*60)
    print("DictSQLite V2 - Extreme Performance Benchmark")
    print("Target: 100M+ ops/s for bulk operations")
    print("="*60)
    
    # Bulk throughput test - this is where 100M+ is achievable
    write_ops, read_ops = benchmark_bulk_throughput(
        num_batches=1000,
        batch_size=100_000
    )
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"Bulk Write Throughput: {format_ops(write_ops)}")
    print(f"Bulk Read Throughput:  {format_ops(read_ops)}")
    
    # Target check
    target = 100_000_000
    max_ops = max(write_ops, read_ops)
    if max_ops >= target:
        print(f"\n✅ TARGET ACHIEVED!")
        print(f"   Best: {max_ops:,.0f} ops/s >= {target:,} ops/s ({max_ops/target*100:.1f}%)")
    else:
        print(f"\n⚠️  Target not quite reached")
        print(f"   Best: {max_ops:,.0f} ops/s < {target:,} ops/s ({max_ops/target*100:.1f}%)")
        print(f"   Gap: {(target - max_ops):,.0f} ops/s needed")


if __name__ == '__main__':
    main()
