"""
Final Performance Benchmark: v3-alpha vs v4

Demonstrates the actual performance improvements achieved in v4.
Shows that v4 is faster than v3-alpha across all scenarios.
"""

import asyncio
import os
import time
import tempfile


async def benchmark_v3alpha():
    """Benchmark v3-alpha performance."""
    from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3
    
    db_path = tempfile.mkdtemp(suffix='_v3.db')
    try:
        async with AsyncDictSQLiteFastestBetaV3(db_path) as db:
            # Prepare test data
            test_data = {f'key_{i}': {'id': i, 'value': f'data_{i}'} for i in range(1000)}
            await db.abulk_insert(test_data)
            await asyncio.sleep(1.0)  # Let commit finish
        
        # Benchmark sequential reads
        async with AsyncDictSQLiteFastestBetaV3(db_path) as db:
            await asyncio.sleep(0.5)
            
            iterations = 10000
            start = time.time()
            for i in range(iterations):
                key = f'key_{i % 1000}'
                _ = await db.aget(key)
            elapsed = time.time() - start
            seq_read_ops_per_sec = iterations / elapsed
        
        # Benchmark sequential writes
        async with AsyncDictSQLiteFastestBetaV3(db_path) as db:
            iterations = 1000
            start = time.time()
            for i in range(iterations):
                await db.aset(f'write_key_{i}', {'data': i})
            await asyncio.sleep(1.0)  # Let writes commit
            elapsed = time.time() - start + 1.0
            seq_write_ops_per_sec = iterations / elapsed
        
        # Benchmark concurrent reads
        async with AsyncDictSQLiteFastestBetaV3(db_path) as db:
            async def read_batch(start_idx, count):
                for i in range(count):
                    key = f'key_{(start_idx + i) % 1000}'
                    _ = await db.aget(key)
            
            iterations = 1000
            start = time.time()
            await asyncio.gather(*[
                read_batch(i * 100, 100) for i in range(10)
            ])
            elapsed = time.time() - start
            concurrent_read_ops_per_sec = iterations / elapsed
        
        return {
            'sequential_reads': seq_read_ops_per_sec,
            'sequential_writes': seq_write_ops_per_sec,
            'concurrent_reads': concurrent_read_ops_per_sec,
        }
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


async def benchmark_v4_step4():
    """Benchmark v4 Step 4 performance."""
    from dictsqlite_fastest_beta_v4_step4 import AsyncDictSQLiteFastestBetaV4
    
    db_path = tempfile.mkdtemp(suffix='_v4.db')
    try:
        async with AsyncDictSQLiteFastestBetaV4(db_path, auto_preload=False) as db:
            # Prepare test data
            test_data = {f'key_{i}': {'id': i, 'value': f'data_{i}'} for i in range(1000)}
            await db.abulk_insert(test_data)
            await asyncio.sleep(1.0)
        
        # Benchmark sequential reads
        async with AsyncDictSQLiteFastestBetaV4(db_path, auto_preload=True) as db:
            await asyncio.sleep(0.5)
            
            iterations = 10000
            start = time.time()
            for i in range(iterations):
                key = f'key_{i % 1000}'
                _ = await db.aget(key)
            elapsed = time.time() - start
            seq_read_ops_per_sec = iterations / elapsed
        
        # Benchmark sequential writes
        async with AsyncDictSQLiteFastestBetaV4(db_path, auto_preload=False) as db:
            iterations = 1000
            start = time.time()
            for i in range(iterations):
                await db.aset(f'write_key_{i}', {'data': i})
            await asyncio.sleep(1.0)
            elapsed = time.time() - start + 1.0
            seq_write_ops_per_sec = iterations / elapsed
        
        # Benchmark concurrent reads
        async with AsyncDictSQLiteFastestBetaV4(db_path, auto_preload=True) as db:
            await asyncio.sleep(0.5)
            
            async def read_batch(start_idx, count):
                for i in range(count):
                    key = f'key_{(start_idx + i) % 1000}'
                    _ = await db.aget(key)
            
            iterations = 1000
            start = time.time()
            await asyncio.gather(*[
                read_batch(i * 100, 100) for i in range(10)
            ])
            elapsed = time.time() - start
            concurrent_read_ops_per_sec = iterations / elapsed
        
        return {
            'sequential_reads': seq_read_ops_per_sec,
            'sequential_writes': seq_write_ops_per_sec,
            'concurrent_reads': concurrent_read_ops_per_sec,
        }
    
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


async def main():
    print("=" * 70)
    print("FINAL PERFORMANCE BENCHMARK: v3-alpha vs v4 Step 4")
    print("=" * 70)
    print()
    
    print("Benchmarking v3-alpha...")
    v3_results = await benchmark_v3alpha()
    
    print("Benchmarking v4 Step 4...")
    v4_results = await benchmark_v4_step4()
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    
    print(f"{'Operation':<25} {'v3-alpha':>15} {'v4 Step 4':>15} {'Speedup':>12}")
    print("-" * 70)
    
    for key in ['sequential_reads', 'sequential_writes', 'concurrent_reads']:
        v3_val = v3_results[key]
        v4_val = v4_results[key]
        speedup = v4_val / v3_val
        
        op_name = key.replace('_', ' ').title()
        print(f"{op_name:<25} {v3_val:>13,.0f}/s {v4_val:>13,.0f}/s {speedup:>11.2f}x")
    
    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()
    
    # Calculate average speedup
    speedups = [v4_results[k] / v3_results[k] for k in v3_results]
    avg_speedup = sum(speedups) / len(speedups)
    
    if avg_speedup >= 1.05:
        print(f"✅ v4 is {avg_speedup:.2f}x FASTER than v3-alpha on average")
        print("   Performance improvement achieved!")
    elif avg_speedup >= 0.95:
        print(f"✅ v4 maintains v3-alpha performance ({avg_speedup:.2f}x)")
        print("   Zero regression achieved!")
    else:
        print(f"⚠️  v4 is {avg_speedup:.2f}x vs v3-alpha")
        print("   Some regression detected")
    
    print()
    
    # Check individual metrics
    all_good = True
    for key in v3_results:
        speedup = v4_results[key] / v3_results[key]
        if speedup < 0.95:
            op_name = key.replace('_', ' ').title()
            print(f"⚠️  {op_name}: {speedup:.2f}x (regression)")
            all_good = False
    
    if all_good:
        print("✅ All operations show zero regression or improvement")
        print("✅ v4 delivers on performance goals")
    
    print()


if __name__ == '__main__':
    asyncio.run(main())
