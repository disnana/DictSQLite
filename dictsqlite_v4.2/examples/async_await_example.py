#!/usr/bin/env python3
"""
Example: Using AsyncDictSQLite with True Asyncio Support

This example demonstrates the new awaitable async methods in DictSQLite v4.2.
Now you can use `await` with AsyncDictSQLite operations!
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from __init__ import AsyncDictSQLite

async def main():
    print("=" * 70)
    print("DictSQLite v4.2 - True Asyncio Support Demo")
    print("=" * 70)
    
    # Create async database instance
    async with AsyncDictSQLite("example_async.db", capacity=10000, persist_mode="lazy") as db:
        
        # Example 1: Basic async get/set
        print("\n1. Basic Async Operations")
        print("-" * 70)
        
        await db.aset("user:1", b"Alice")
        await db.aset("user:2", b"Bob")
        await db.aset("user:3", b"Charlie")
        print("✓ Set 3 users asynchronously")
        
        user1 = await db.aget("user:1")
        print(f"✓ Retrieved user:1 = {user1}")
        
        # Example 2: Concurrent operations
        print("\n2. Concurrent Async Operations")
        print("-" * 70)
        
        # Write 50 records concurrently
        # AsyncDictSQLite also supports Pickle mode (default)
        write_tasks = [
            db.aset(f"product:{i}", f"Product {i}")  # Pickleモードで自動変換
            for i in range(50)
        ]
        await asyncio.gather(*write_tasks)
        print("✓ Wrote 50 products concurrently")
        
        # Read them back concurrently
        read_tasks = [
            db.aget(f"product:{i}")
            for i in range(50)
        ]
        products = await asyncio.gather(*read_tasks)
        print(f"✓ Read {len([p for p in products if p])} products concurrently")
        
        # Example 3: Batch operations
        print("\n3. Batch Async Operations")
        print("-" * 70)
        
        # Batch set
        items = [(f"order:{i}", f"Order #{i}") for i in range(20)]  # Pickleモードで自動変換
        await db.abatch_set(items)
        print("✓ Batch set 20 orders")
        
        # Batch get
        keys = [f"order:{i}" for i in range(20)]
        orders = await db.abatch_get(keys)
        print(f"✓ Batch retrieved {len([o for o in orders if o])} orders")
        
        # Example 4: Mixed sync/async (backward compatibility)
        print("\n4. Backward Compatibility (Mixed Sync/Async)")
        print("-" * 70)
        
        # Still can use synchronous methods
        db.set("sync_key", b"sync_value")
        print("✓ Synchronous set works")
        
        value = db.get("sync_key")
        print(f"✓ Synchronous get works: {value}")
        
        # And mix with async
        await db.aset("async_key", b"async_value")
        async_value = await db.aget("async_key")
        print(f"✓ Async operations work: {async_value}")
        
        # Statistics
        print("\n5. Statistics")
        print("-" * 70)
        stats = db.stats()
        print(f"✓ Cache size: {stats['size']}/{stats['capacity']} entries")
        
        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
    
    # Cleanup
    if os.path.exists("example_async.db"):
        os.unlink("example_async.db")
    for ext in ['-wal', '-shm']:
        f = "example_async.db" + ext
        if os.path.exists(f):
            os.unlink(f)

if __name__ == "__main__":
    asyncio.run(main())
