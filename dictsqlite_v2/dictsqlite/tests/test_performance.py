#!/usr/bin/env python3
"""
Performance benchmarks for DictSQLite v4.1

This module provides comprehensive performance tests to ensure
that optimizations maintain or improve performance targets.
"""
import tempfile
import os
import sys
import time
import statistics
from typing import List, Dict, Any

try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
except ImportError:
    print("Error: dictsqlite module not found. Please build with 'maturin develop'")
    sys.exit(1)


class PerformanceBenchmark:
    """Performance benchmark suite for DictSQLite v4.1"""
    
    def __init__(self, iterations: int = 3):
        self.iterations = iterations
        self.results: Dict[str, List[float]] = {}
    
    def measure(self, name: str, func, *args, **kwargs) -> float:
        """Measure execution time of a function"""
        times = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        avg_time = statistics.mean(times)
        self.results[name] = times
        return avg_time
    
    def benchmark_sequential_writes(self, db, count: int = 1000) -> float:
        """Benchmark sequential write operations"""
        def write_sequential():
            for i in range(count):
                db[f"key_{i}"] = f"value_{i}".encode()
        
        return self.measure(f"Sequential Writes ({count})", write_sequential)
    
    def benchmark_sequential_reads(self, db, count: int = 1000) -> float:
        """Benchmark sequential read operations"""
        # Pre-populate
        for i in range(count):
            db[f"read_key_{i}"] = f"read_value_{i}".encode()
        
        def read_sequential():
            for i in range(count):
                _ = db[f"read_key_{i}"]
        
        return self.measure(f"Sequential Reads ({count})", read_sequential)
    
    def benchmark_bulk_insert(self, db, count: int = 10000) -> float:
        """Benchmark bulk insert operations"""
        items = {f"bulk_key_{i}": f"bulk_value_{i}".encode() for i in range(count)}
        
        def bulk_insert():
            db.update(items)
        
        return self.measure(f"Bulk Insert ({count})", bulk_insert)
    
    def benchmark_mixed_operations(self, db, count: int = 1000) -> float:
        """Benchmark mixed read/write operations"""
        # Pre-populate some data
        for i in range(count // 2):
            db[f"mixed_key_{i}"] = f"mixed_value_{i}".encode()
        
        def mixed_ops():
            for i in range(count):
                if i % 3 == 0:
                    db[f"mixed_key_{i}"] = f"mixed_new_value_{i}".encode()
                elif i % 3 == 1:
                    _ = db.get(f"mixed_key_{i % (count // 2)}", None)
                else:
                    db.pop(f"mixed_key_{i % (count // 4)}", None)
        
        return self.measure(f"Mixed Operations ({count})", mixed_ops)
    
    def benchmark_lru_eviction(self, db, capacity: int, writes: int) -> float:
        """Benchmark LRU eviction performance"""
        def eviction_test():
            for i in range(writes):
                db[f"evict_key_{i}"] = f"evict_value_{i}".encode()
        
        return self.measure(f"LRU Eviction Test (cap={capacity}, writes={writes})", eviction_test)
    
    def benchmark_persistence_flush(self, db, count: int = 1000) -> float:
        """Benchmark flush operation performance"""
        # Pre-populate
        for i in range(count):
            db[f"flush_key_{i}"] = f"flush_value_{i}".encode()
        
        def flush_test():
            db.flush()
        
        return self.measure(f"Flush ({count} items)", flush_test)
    
    def print_results(self):
        """Print benchmark results"""
        print("\n" + "="*70)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*70)
        
        for name, times in self.results.items():
            avg = statistics.mean(times)
            stdev = statistics.stdev(times) if len(times) > 1 else 0
            min_t = min(times)
            max_t = max(times)
            
            # Calculate ops/sec for operations with counts
            ops_per_sec = None
            if "(" in name and ")" in name:
                try:
                    count_str = name.split("(")[1].split(")")[0]
                    if "=" in count_str:
                        count = int(count_str.split("=")[-1].split(",")[0])
                    else:
                        count = int(count_str)
                    ops_per_sec = count / avg
                except (ValueError, IndexError):
                    pass
            
            print(f"\n{name}:")
            print(f"  Average: {avg*1000:.2f}ms (±{stdev*1000:.2f}ms)")
            print(f"  Range: {min_t*1000:.2f}ms - {max_t*1000:.2f}ms")
            if ops_per_sec:
                print(f"  Throughput: {ops_per_sec:,.0f} ops/sec")
        
        print("\n" + "="*70)


def test_sync_performance():
    """Test synchronous DictSQLiteV4 performance"""
    print("\n" + "="*70)
    print("TEST: Synchronous Performance (DictSQLiteV4)")
    print("="*70)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        benchmark = PerformanceBenchmark(iterations=3)
        
        # Test LAZY mode (fastest for our use case)
        print("\n[Mode: LAZY - Recommended for high performance]")
        db = DictSQLiteV4(db_path, hot_capacity=10000, persist_mode="lazy")
        
        # Run benchmarks
        benchmark.benchmark_sequential_writes(db, 1000)
        benchmark.benchmark_sequential_reads(db, 1000)
        benchmark.benchmark_bulk_insert(db, 5000)
        benchmark.benchmark_mixed_operations(db, 1000)
        benchmark.benchmark_persistence_flush(db, 1000)
        
        db.close()
        
        # Test with LRU eviction
        print("\n[LRU Eviction Performance]")
        os.unlink(db_path)
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        db = DictSQLiteV4(db_path, hot_capacity=100, persist_mode="lazy")
        benchmark.benchmark_lru_eviction(db, 100, 500)  # Trigger evictions
        db.close()
        
        benchmark.print_results()
        
        # Performance assertions (ensure no regression)
        lazy_write_time = statistics.mean(benchmark.results["Sequential Writes (1000)"])
        lazy_read_time = statistics.mean(benchmark.results["Sequential Reads (1000)"])
        
        # These are conservative thresholds - should be much faster
        assert lazy_write_time < 1.0, f"Write performance regression: {lazy_write_time:.2f}s > 1.0s"
        assert lazy_read_time < 0.5, f"Read performance regression: {lazy_read_time:.2f}s > 0.5s"
        
        print("\n✅ Performance tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Performance test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def test_async_performance():
    """Test asynchronous AsyncDictSQLite performance"""
    print("\n" + "="*70)
    print("TEST: Asynchronous Performance (AsyncDictSQLite)")
    print("="*70)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        benchmark = PerformanceBenchmark(iterations=3)
        
        print("\n[Mode: LAZY]")
        db = AsyncDictSQLite(db_path, capacity=10000, persist_mode="lazy")
        
        # Run benchmarks
        benchmark.benchmark_sequential_writes(db, 1000)
        benchmark.benchmark_sequential_reads(db, 1000)
        
        # Async-specific: batch operations
        items = [(f"async_batch_{i}", f"async_value_{i}".encode()) for i in range(1000)]
        def batch_set():
            db.batch_set(items)
        benchmark.measure("Async Batch Set (1000)", batch_set)
        
        keys = [f"async_batch_{i}" for i in range(1000)]
        def batch_get():
            db.batch_get(keys)
        benchmark.measure("Async Batch Get (1000)", batch_get)
        
        db.close()
        
        benchmark.print_results()
        
        # Performance assertions
        async_write_time = statistics.mean(benchmark.results["Sequential Writes (1000)"])
        assert async_write_time < 1.0, f"Async write performance regression: {async_write_time:.2f}s > 1.0s"
        
        print("\n✅ Async performance tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Async performance test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def test_encryption_performance():
    """Test performance with encryption enabled"""
    print("\n" + "="*70)
    print("TEST: Encryption Performance Impact")
    print("="*70)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        benchmark_plain = PerformanceBenchmark(iterations=3)
        benchmark_encrypted = PerformanceBenchmark(iterations=3)
        
        # Test without encryption
        print("\n[Without Encryption]")
        db_plain = DictSQLiteV4(db_path, persist_mode="lazy")
        benchmark_plain.benchmark_sequential_writes(db_plain, 500)
        benchmark_plain.benchmark_sequential_reads(db_plain, 500)
        db_plain.close()
        
        os.unlink(db_path)
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        # Test with encryption
        print("\n[With Encryption]")
        db_encrypted = DictSQLiteV4(
            db_path, 
            persist_mode="lazy",
            encryption_password="test_password_12345"  # nosec B106
        )
        benchmark_encrypted.benchmark_sequential_writes(db_encrypted, 500)
        benchmark_encrypted.benchmark_sequential_reads(db_encrypted, 500)
        db_encrypted.close()
        
        # Compare results
        plain_write = statistics.mean(benchmark_plain.results["Sequential Writes (500)"])
        encrypted_write = statistics.mean(benchmark_encrypted.results["Sequential Writes (500)"])
        plain_read = statistics.mean(benchmark_plain.results["Sequential Reads (500)"])
        encrypted_read = statistics.mean(benchmark_encrypted.results["Sequential Reads (500)"])
        
        write_overhead = (encrypted_write / plain_write - 1) * 100
        read_overhead = (encrypted_read / plain_read - 1) * 100
        
        print(f"\nEncryption Overhead:")
        print(f"  Write: {write_overhead:.1f}%")
        print(f"  Read: {read_overhead:.1f}%")
        
        # Ensure encryption overhead is reasonable (< 50%)
        assert write_overhead < 50, f"Encryption write overhead too high: {write_overhead:.1f}%"
        assert read_overhead < 50, f"Encryption read overhead too high: {read_overhead:.1f}%"
        
        print("\n✅ Encryption performance test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Encryption performance test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def run_all_performance_tests():
    """Run all performance tests"""
    print("\n" + "="*70)
    print("COMPREHENSIVE PERFORMANCE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Synchronous Performance", test_sync_performance),
        ("Asynchronous Performance", test_async_performance),
        ("Encryption Performance", test_encryption_performance),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # Summary
    print("\n" + "="*70)
    print("PERFORMANCE TEST SUMMARY")
    print("="*70)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All performance tests PASSED!")
        print("No performance regressions detected.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_performance_tests())
