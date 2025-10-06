#!/usr/bin/env python3
"""
Example demonstrating the native extension usage and performance benefits.

This example shows:
1. How to check if native extension is available
2. Basic usage (same as regular DictSQLite)
3. Performance comparison between native and pure Python
"""

import time
import tempfile
import os
from dictsqlite.native_wrapper import (
    is_native_available,
    NativeCache,
    NativeSQLite,
    PythonCache,
    PythonSQLite,
)


def benchmark_cache(cache_class, name, num_operations=10000):
    """Benchmark cache operations."""
    print(f"\n{name} Cache Benchmark:")
    print("-" * 50)
    
    cache = cache_class(1000)
    
    # Write benchmark
    start = time.perf_counter()
    for i in range(num_operations):
        cache.put(f"key{i}", f"value{i}".encode())
    write_time = time.perf_counter() - start
    write_ops = num_operations / write_time
    
    # Read benchmark
    start = time.perf_counter()
    for i in range(num_operations):
        _ = cache.get(f"key{i % 1000}")
    read_time = time.perf_counter() - start
    read_ops = num_operations / read_time
    
    print(f"  Write: {write_time:.3f}s ({write_ops:,.0f} ops/sec)")
    print(f"  Read:  {read_time:.3f}s ({read_ops:,.0f} ops/sec)")
    
    return write_ops, read_ops


def benchmark_sqlite(sqlite_class, name, num_operations=1000):
    """Benchmark SQLite operations."""
    print(f"\n{name} SQLite Benchmark:")
    print("-" * 50)
    
    db_path = tempfile.mktemp(suffix='.db')
    
    try:
        db = sqlite_class(db_path, "test_table")
        
        # Write benchmark
        start = time.perf_counter()
        for i in range(num_operations):
            db.put(f"key{i}", f"value{i}".encode())
        write_time = time.perf_counter() - start
        write_ops = num_operations / write_time
        
        # Read benchmark
        start = time.perf_counter()
        for i in range(num_operations):
            _ = db.get(f"key{i}")
        read_time = time.perf_counter() - start
        read_ops = num_operations / read_time
        
        # Bulk insert benchmark
        items = {f"bulk{i}": f"value{i}".encode() for i in range(num_operations)}
        start = time.perf_counter()
        db.bulk_insert(items)
        bulk_time = time.perf_counter() - start
        bulk_ops = num_operations / bulk_time
        
        print(f"  Write:       {write_time:.3f}s ({write_ops:,.0f} ops/sec)")
        print(f"  Read:        {read_time:.3f}s ({read_ops:,.0f} ops/sec)")
        print(f"  Bulk Insert: {bulk_time:.3f}s ({bulk_ops:,.0f} ops/sec)")
        
        return write_ops, read_ops, bulk_ops
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """Main example function."""
    print("=" * 60)
    print("DictSQLite Native Extension Example")
    print("=" * 60)
    
    # Check native extension availability
    if is_native_available():
        print("\n✅ Native Rust extension is AVAILABLE")
        print("   You're getting maximum performance! 🚀")
    else:
        print("\n⚠️  Native Rust extension is NOT available")
        print("   Using pure Python fallback")
        print("   To install native extension:")
        print("   1. Install Rust from https://rustup.rs/")
        print("   2. Run: ./build_native.sh")
    
    print("\n" + "=" * 60)
    print("Performance Comparison")
    print("=" * 60)
    
    # Benchmark cache
    print("\n📊 Cache Performance:")
    python_write, python_read = benchmark_cache(PythonCache, "Python")
    
    if is_native_available():
        native_write, native_read = benchmark_cache(NativeCache, "Native Rust")
        
        print("\n🏆 Cache Speedup:")
        print(f"  Write: {native_write / python_write:.1f}x faster")
        print(f"  Read:  {native_read / python_read:.1f}x faster")
    else:
        print("\n  (Install native extension to see speedup)")
    
    # Benchmark SQLite
    print("\n📊 SQLite Performance:")
    py_w, py_r, py_b = benchmark_sqlite(PythonSQLite, "Python")
    
    if is_native_available():
        nat_w, nat_r, nat_b = benchmark_sqlite(NativeSQLite, "Native Rust")
        
        print("\n🏆 SQLite Speedup:")
        print(f"  Write:       {nat_w / py_w:.1f}x faster")
        print(f"  Read:        {nat_r / py_r:.1f}x faster")
        print(f"  Bulk Insert: {nat_b / py_b:.1f}x faster")
    else:
        print("\n  (Install native extension to see speedup)")
    
    print("\n" + "=" * 60)
    print("Basic Usage Example")
    print("=" * 60)
    
    # Show basic usage
    print("\nUsing native-accelerated cache:")
    cache = NativeCache(100)
    cache.put("greeting", b"Hello, World!")
    print(f"  cache.get('greeting') = {cache.get('greeting')}")
    
    db_path = tempfile.mktemp(suffix='.db')
    try:
        print("\nUsing native-accelerated SQLite:")
        db = NativeSQLite(db_path, "example")
        db.put("name", b"Alice")
        db.put("age", b"30")
        print(f"  db.get('name') = {db.get('name')}")
        print(f"  db.get('age') = {db.get('age')}")
        print(f"  db.keys() = {db.keys()}")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    print("\n" + "=" * 60)
    print("✅ Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
