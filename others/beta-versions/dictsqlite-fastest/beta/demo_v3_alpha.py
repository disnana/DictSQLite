"""Demo: DictSQLite-Fastest Beta v3-alpha

This demo shows how to use v3-alpha features effectively.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dictsqlite_fastest_beta_v3_alpha import AsyncDictSQLiteFastestBetaV3


async def demo_basic_usage():
    """Demo 1: Basic usage (same as v2)"""
    print("=" * 70)
    print("Demo 1: Basic Usage (100% compatible with v2)")
    print("=" * 70)
    
    db_path = '/tmp/demo_basic.db'
    
    async with AsyncDictSQLiteFastestBetaV3(db_path) as db:
        # Write
        await db.aset('user_1', {'name': 'Alice', 'age': 30})
        await db.aset('user_2', {'name': 'Bob', 'age': 25})
        
        # Read
        user1 = await db.aget('user_1')
        print(f"User 1: {user1}")
        
        # Bulk insert
        users = {f'user_{i}': {'name': f'User {i}', 'age': 20 + i} for i in range(3, 10)}
        await db.abulk_insert(users)
        
        # Count
        count = await db.alen()
        print(f"Total users: {count}")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    print()


async def demo_dynamic_pool():
    """Demo 2: Phase 1 - Dynamic Connection Pool"""
    print("=" * 70)
    print("Demo 2: Phase 1 - Dynamic Connection Pool")
    print("=" * 70)
    
    db_path = '/tmp/demo_pool.db'
    
    # Configure pool
    async with AsyncDictSQLiteFastestBetaV3(
        db_path,
        pool_min_size=2,
        pool_max_size=8,
        pool_auto_scale=True
    ) as db:
        # Prepare data
        data = {f'item_{i}': f'value_{i}' for i in range(100)}
        await db.abulk_insert(data)
        
        # Concurrent reads to trigger pool scaling
        async def read_many():
            tasks = [db.aget(f'item_{i}') for i in range(100)]
            await asyncio.gather(*tasks)
        
        print("Running concurrent reads...")
        await read_many()
        
        # Check pool stats
        stats = db.get_stats()
        print(f"\nPool Statistics:")
        print(f"  Created connections: {stats['pool']['created_connections']}")
        print(f"  Active connections: {stats['pool']['active_connections']}")
        print(f"  Peak connections: {stats['pool']['peak_connections']}")
        print(f"  Scaled up: {stats['pool']['scaled_up']} times")
        print(f"  Scaled down: {stats['pool']['scaled_down']} times")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    print()


async def demo_prefetch():
    """Demo 3: Phase 2 - Pattern-based Prefetch"""
    print("=" * 70)
    print("Demo 3: Phase 2 - Pattern-based Prefetch")
    print("=" * 70)
    
    db_path = '/tmp/demo_prefetch.db'
    
    async with AsyncDictSQLiteFastestBetaV3(
        db_path,
        enable_prefetch=True,
        prefetch_size=10
    ) as db:
        # Insert sequential data
        data = {f'item_{i}': {'id': i, 'data': f'data_{i}'} for i in range(100)}
        await db.abulk_insert(data)
        
        print("Accessing items sequentially...")
        
        # Access items sequentially - prefetch will kick in
        for i in range(20):
            item = await db.aget(f'item_{i}')
            if i == 0:
                print(f"  item_0: {item['id']} (DB query)")
            elif i == 5:
                print(f"  item_5: {item['id']} (prefetch cache hit!)")
        
        # Check prefetch stats
        stats = db.get_stats()
        print(f"\nPrefetch Statistics:")
        print(f"  Patterns detected: {stats['prefetch']['patterns_detected']}")
        print(f"  Prefetches triggered: {stats['prefetch']['prefetches_triggered']}")
        print(f"  Prefetch hits: {stats['prefetch']['prefetch_hits']}")
        print(f"  Hit rate: {stats['prefetch']['hit_rate']:.1f}%")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    print()


async def demo_adaptive_batch():
    """Demo 4: Phase 3 - Adaptive Batch Sizing"""
    print("=" * 70)
    print("Demo 4: Phase 3 - Adaptive Batch Sizing")
    print("=" * 70)
    
    db_path = '/tmp/demo_adaptive.db'
    
    async with AsyncDictSQLiteFastestBetaV3(
        db_path,
        adaptive_batch=True,
        batch_min_size=10,
        batch_max_size=200,
        async_batch_size=50
    ) as db:
        print("Writing data with adaptive batching...")
        
        # Write data - batch size will adapt
        for i in range(150):
            await db.aset(f'key_{i}', f'value_{i}')
        
        # Wait for final flush
        await asyncio.sleep(0.5)
        
        # Check adaptive batch stats
        stats = db.get_stats()
        print(f"\nAdaptive Batch Statistics:")
        print(f"  Total batches: {stats['adaptive_batch']['total_batches']}")
        print(f"  Average batch size: {stats['adaptive_batch']['avg_batch_size']:.1f}")
        print(f"  Average latency: {stats['adaptive_batch']['avg_latency_ms']:.2f} ms")
        print(f"  Adjustments made: {stats['adaptive_batch']['adjustments']}")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    print()


async def demo_extended_stats():
    """Demo 5: Phase 4 - Extended Statistics"""
    print("=" * 70)
    print("Demo 5: Phase 4 - Extended Statistics")
    print("=" * 70)
    
    db_path = '/tmp/demo_stats.db'
    
    async with AsyncDictSQLiteFastestBetaV3(
        db_path,
        extended_stats=True
    ) as db:
        # Perform various operations
        print("Performing various operations...")
        
        # Writes
        for i in range(50):
            await db.aset(f'key_{i}', f'value_{i}')
        
        # Reads
        for i in range(30):
            await db.aget(f'key_{i}')
        
        # Deletes
        for i in range(10):
            await db.adelete(f'key_{i}')
        
        # Bulk insert
        bulk_data = {f'bulk_{i}': f'bulk_value_{i}' for i in range(20)}
        await db.abulk_insert(bulk_data)
        
        # Check extended stats
        stats = db.get_stats()
        print(f"\nExtended Statistics:")
        print(f"  Operation counts:")
        for op, count in stats['extended']['operation_counts'].items():
            print(f"    {op}: {count}")
        
        print(f"\n  Average timings:")
        for op in ['get', 'set', 'delete', 'bulk_insert']:
            avg_key = f'{op}_avg_ms'
            p95_key = f'{op}_p95_ms'
            if avg_key in stats['extended']:
                print(f"    {op}: {stats['extended'][avg_key]:.3f} ms (p95: {stats['extended'][p95_key]:.3f} ms)")
        
        print(f"\n  Hot keys: {stats['extended']['hot_keys_count']}")
        print(f"  Avg connection wait: {stats['extended']['avg_connection_wait_ms']:.3f} ms")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    print()


async def demo_all_features():
    """Demo 6: All features enabled"""
    print("=" * 70)
    print("Demo 6: All v3-alpha Features Enabled")
    print("=" * 70)
    
    db_path = '/tmp/demo_all.db'
    
    async with AsyncDictSQLiteFastestBetaV3(
        db_path,
        pool_min_size=2,
        pool_max_size=8,
        pool_auto_scale=True,
        enable_prefetch=True,
        prefetch_size=10,
        adaptive_batch=True,
        extended_stats=True
    ) as db:
        print("Creating test dataset...")
        
        # Insert data
        data = {f'item_{i}': {'id': i, 'value': f'value_{i}'} for i in range(100)}
        await db.abulk_insert(data)
        
        print("Sequential access (triggers prefetch)...")
        for i in range(20):
            await db.aget(f'item_{i}')
        
        print("Concurrent access (triggers pool scaling)...")
        tasks = [db.aget(f'item_{i}') for i in range(50)]
        await asyncio.gather(*tasks)
        
        # Get comprehensive stats
        stats = db.get_stats()
        
        print(f"\nComprehensive Statistics:")
        print(f"\n  Cache:")
        print(f"    Hit rate: {stats['cache']['hit_rate']:.1f}%")
        print(f"    Size: {stats['cache']['size']}")
        
        print(f"\n  Connection Pool:")
        print(f"    Active: {stats['pool']['active_connections']}")
        print(f"    Peak: {stats['pool']['peak_connections']}")
        print(f"    Scaled up: {stats['pool']['scaled_up']} times")
        
        print(f"\n  Prefetch:")
        print(f"    Hit rate: {stats['prefetch']['hit_rate']:.1f}%")
        print(f"    Patterns detected: {stats['prefetch']['patterns_detected']}")
        
        print(f"\n  Operations:")
        print(f"    Total: {sum(stats['extended']['operation_counts'].values())}")
        print(f"    Hot keys: {stats['extended']['hot_keys_count']}")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    print()


async def main():
    """Run all demos."""
    print("\n")
    print("#" * 70)
    print("# DictSQLite-Fastest Beta v3-alpha - Interactive Demo")
    print("#" * 70)
    print()
    
    demos = [
        demo_basic_usage,
        demo_dynamic_pool,
        demo_prefetch,
        demo_adaptive_batch,
        demo_extended_stats,
        demo_all_features,
    ]
    
    for demo in demos:
        try:
            await demo()
        except Exception as e:
            print(f"Error in demo: {e}")
            import traceback
            traceback.print_exc()
    
    print("#" * 70)
    print("# All demos completed!")
    print("#" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
