#!/usr/bin/env python3
"""
Comprehensive Benchmark for DictSQLite v4.1
Measures ops/s for all major operations including basic, pickle, bulk, and encryption
"""
import tempfile
import os
import sys
import time
import pickle
import statistics
from typing import Dict, List, Tuple

try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
except ImportError:
    print("Error: dictsqlite module not found. Please build with 'maturin develop'")
    sys.exit(1)


class ComprehensiveBenchmark:
    """Comprehensive benchmark suite measuring ops/s"""
    
    def __init__(self, iterations: int = 5, warmup: int = 1):
        self.iterations = iterations
        self.warmup = warmup
        self.results: Dict[str, Dict[str, float]] = {}
    
    def measure_ops(self, name: str, operation_count: int, func, *args, **kwargs) -> Tuple[float, float]:
        """Measure operations per second with warmup"""
        # Warmup
        for _ in range(self.warmup):
            func(*args, **kwargs)
        
        # Actual measurement
        times = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        stdev_time = statistics.stdev(times) if len(times) > 1 else 0
        ops_per_sec = operation_count / avg_time
        
        self.results[name] = {
            'ops': operation_count,
            'avg_time': avg_time,
            'stdev_time': stdev_time,
            'ops_per_sec': ops_per_sec,
            'times': times
        }
        
        return ops_per_sec, stdev_time
    
    def print_results(self):
        """Print benchmark results in a formatted table"""
        print("\n" + "="*100)
        print("COMPREHENSIVE BENCHMARK RESULTS - DictSQLite v4.1")
        print("="*100)
        print(f"{'Operation':<50} {'Ops/sec':>15} {'Time (ms)':>15} {'Std Dev':>15}")
        print("-"*100)
        
        for name, data in self.results.items():
            ops_per_sec = data['ops_per_sec']
            avg_time_ms = data['avg_time'] * 1000
            stdev_ms = data['stdev_time'] * 1000
            print(f"{name:<50} {ops_per_sec:>15,.0f} {avg_time_ms:>15.2f} {stdev_ms:>15.2f}")
        
        print("="*100)


def benchmark_basic_operations():
    """Benchmark basic set/get/delete operations"""
    print("\n" + "="*100)
    print("BENCHMARK 1: Basic Operations")
    print("="*100)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        bench = ComprehensiveBenchmark(iterations=5)
        db = DictSQLiteV4(db_path, hot_capacity=100000, persist_mode="lazy")
        
        # 1. Single Set Operation
        count = 10000
        def single_set():
            for i in range(count):
                db[f"basic_set_{i}"] = f"value_{i}".encode()
        
        ops, _ = bench.measure_ops("Basic: Single Set (10K items)", count, single_set)
        print(f"  Single Set: {ops:,.0f} ops/sec")
        
        # 2. Single Get Operation
        def single_get():
            for i in range(count):
                _ = db[f"basic_set_{i}"]
        
        ops, _ = bench.measure_ops("Basic: Single Get (10K items)", count, single_get)
        print(f"  Single Get: {ops:,.0f} ops/sec")
        
        # 3. Contains Check
        def contains_check():
            for i in range(count):
                _ = f"basic_set_{i}" in db
        
        ops, _ = bench.measure_ops("Basic: Contains Check (10K items)", count, contains_check)
        print(f"  Contains: {ops:,.0f} ops/sec")
        
        # 4. Delete Operation
        def delete_op():
            for i in range(count // 2):  # Delete half
                del db[f"basic_set_{i}"]
        
        ops, _ = bench.measure_ops("Basic: Delete (5K items)", count // 2, delete_op)
        print(f"  Delete: {ops:,.0f} ops/sec")
        
        # 5. Keys iteration
        db.clear()
        for i in range(1000):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        def keys_iteration():
            _ = db.keys()
        
        ops, _ = bench.measure_ops("Basic: keys() (1K items)", 1, keys_iteration)
        print(f"  keys(): {ops:,.0f} ops/sec")
        
        # 6. Items iteration
        def items_iteration():
            _ = db.items()
        
        ops, _ = bench.measure_ops("Basic: items() (1K items)", 1, items_iteration)
        print(f"  items(): {ops:,.0f} ops/sec")
        
        db.close()
        return bench
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def benchmark_bulk_operations():
    """Benchmark bulk insert and batch operations"""
    print("\n" + "="*100)
    print("BENCHMARK 2: Bulk Operations")
    print("="*100)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        bench = ComprehensiveBenchmark(iterations=5)
        db = DictSQLiteV4(db_path, hot_capacity=100000, persist_mode="lazy")
        
        # 1. Bulk Insert (update method)
        count = 50000
        items = {f"bulk_{i}": f"value_{i}".encode() for i in range(count)}
        
        def bulk_insert():
            db.update(items)
        
        ops, _ = bench.measure_ops("Bulk: update() (50K items)", count, bulk_insert)
        print(f"  Bulk Insert: {ops:,.0f} ops/sec")
        
        db.clear()
        
        # 2. Batch Get
        for i in range(10000):
            db[f"batch_get_{i}"] = f"value_{i}".encode()
        
        def batch_get():
            for i in range(10000):
                _ = db[f"batch_get_{i}"]
        
        ops, _ = bench.measure_ops("Bulk: Batch Get (10K items)", 10000, batch_get)
        print(f"  Batch Get: {ops:,.0f} ops/sec")
        
        # 3. pop() operations
        db.clear()
        for i in range(5000):
            db[f"pop_{i}"] = f"value_{i}".encode()
        
        def batch_pop():
            for i in range(5000):
                _ = db.pop(f"pop_{i}", None)
        
        ops, _ = bench.measure_ops("Bulk: pop() (5K items)", 5000, batch_pop)
        print(f"  Batch pop(): {ops:,.0f} ops/sec")
        
        # 4. setdefault() operations
        db.clear()
        def setdefault_ops():
            for i in range(5000):
                db.setdefault(f"setdef_{i}", f"default_{i}".encode())
        
        ops, _ = bench.measure_ops("Bulk: setdefault() (5K items)", 5000, setdefault_ops)
        print(f"  setdefault(): {ops:,.0f} ops/sec")
        
        db.close()
        return bench
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def benchmark_pickle_operations():
    """Benchmark pickle serialization operations"""
    print("\n" + "="*100)
    print("BENCHMARK 3: Pickle Operations")
    print("="*100)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        bench = ComprehensiveBenchmark(iterations=5)
        db = DictSQLiteV4(db_path, hot_capacity=50000, persist_mode="lazy")
        
        # 1. Simple objects
        count = 5000
        simple_objs = [{"id": i, "name": f"item_{i}", "value": i * 100} for i in range(count)]
        
        def pickle_simple_write():
            for i, obj in enumerate(simple_objs):
                db[f"pickle_simple_{i}"] = pickle.dumps(obj)
        
        ops, _ = bench.measure_ops("Pickle: Write Simple Objects (5K dicts)", count, pickle_simple_write)
        print(f"  Simple Write: {ops:,.0f} ops/sec")
        
        def pickle_simple_read():
            for i in range(count):
                data = db[f"pickle_simple_{i}"]
                _ = pickle.loads(data)  # nosec B301
        
        ops, _ = bench.measure_ops("Pickle: Read Simple Objects (5K dicts)", count, pickle_simple_read)
        print(f"  Simple Read: {ops:,.0f} ops/sec")
        
        # 2. Complex nested objects
        db.clear()
        count = 1000
        complex_objs = [
            {
                "id": i,
                "data": {
                    "nested": {
                        "values": list(range(10)),
                        "strings": [f"str_{j}" for j in range(10)]
                    }
                },
                "metadata": {"created": time.time(), "index": i}
            }
            for i in range(count)
        ]
        
        def pickle_complex_write():
            for i, obj in enumerate(complex_objs):
                db[f"pickle_complex_{i}"] = pickle.dumps(obj)
        
        ops, _ = bench.measure_ops("Pickle: Write Complex Objects (1K nested)", count, pickle_complex_write)
        print(f"  Complex Write: {ops:,.0f} ops/sec")
        
        def pickle_complex_read():
            for i in range(count):
                data = db[f"pickle_complex_{i}"]
                _ = pickle.loads(data)  # nosec B301
        
        ops, _ = bench.measure_ops("Pickle: Read Complex Objects (1K nested)", count, pickle_complex_read)
        print(f"  Complex Read: {ops:,.0f} ops/sec")
        
        # 3. Large binary data
        db.clear()
        count = 500
        large_data = [os.urandom(10240) for _ in range(count)]  # 10KB each
        
        def pickle_large_write():
            for i, data in enumerate(large_data):
                db[f"pickle_large_{i}"] = pickle.dumps(data)
        
        ops, _ = bench.measure_ops("Pickle: Write Large Binary (500 x 10KB)", count, pickle_large_write)
        print(f"  Large Write: {ops:,.0f} ops/sec")
        
        def pickle_large_read():
            for i in range(count):
                data = db[f"pickle_large_{i}"]
                _ = pickle.loads(data)  # nosec B301
        
        ops, _ = bench.measure_ops("Pickle: Read Large Binary (500 x 10KB)", count, pickle_large_read)
        print(f"  Large Read: {ops:,.0f} ops/sec")
        
        db.close()
        return bench
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def benchmark_encryption_operations():
    """Benchmark operations with encryption enabled"""
    print("\n" + "="*100)
    print("BENCHMARK 4: Encryption Operations (AES-256-GCM)")
    print("="*100)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        bench = ComprehensiveBenchmark(iterations=5)
        db = DictSQLiteV4(
            db_path, 
            hot_capacity=50000, 
            persist_mode="lazy",
            encryption_password="benchmark_password_12345678"  # nosec B106
        )
        
        # 1. Encrypted Set
        count = 10000
        def encrypted_set():
            for i in range(count):
                db[f"enc_set_{i}"] = f"encrypted_value_{i}".encode()
        
        ops, _ = bench.measure_ops("Encryption: Set (10K items)", count, encrypted_set)
        print(f"  Encrypted Set: {ops:,.0f} ops/sec")
        
        # 2. Encrypted Get
        def encrypted_get():
            for i in range(count):
                _ = db[f"enc_set_{i}"]
        
        ops, _ = bench.measure_ops("Encryption: Get (10K items)", count, encrypted_get)
        print(f"  Encrypted Get: {ops:,.0f} ops/sec")
        
        # 3. Encrypted Bulk Insert
        db.clear()
        count = 20000
        items = {f"enc_bulk_{i}": f"encrypted_bulk_{i}".encode() for i in range(count)}
        
        def encrypted_bulk():
            db.update(items)
        
        ops, _ = bench.measure_ops("Encryption: Bulk Insert (20K items)", count, encrypted_bulk)
        print(f"  Encrypted Bulk: {ops:,.0f} ops/sec")
        
        # 4. Encrypted Pickle
        db.clear()
        count = 2000
        objs = [{"id": i, "data": f"object_{i}", "values": list(range(5))} for i in range(count)]
        
        def encrypted_pickle_write():
            for i, obj in enumerate(objs):
                db[f"enc_pickle_{i}"] = pickle.dumps(obj)
        
        ops, _ = bench.measure_ops("Encryption: Pickle Write (2K objects)", count, encrypted_pickle_write)
        print(f"  Encrypted Pickle Write: {ops:,.0f} ops/sec")
        
        def encrypted_pickle_read():
            for i in range(count):
                data = db[f"enc_pickle_{i}"]
                _ = pickle.loads(data)  # nosec B301
        
        ops, _ = bench.measure_ops("Encryption: Pickle Read (2K objects)", count, encrypted_pickle_read)
        print(f"  Encrypted Pickle Read: {ops:,.0f} ops/sec")
        
        db.close()
        return bench
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def benchmark_persistence_modes():
    """Benchmark different persistence modes"""
    print("\n" + "="*100)
    print("BENCHMARK 5: Persistence Modes")
    print("="*100)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        bench = ComprehensiveBenchmark(iterations=5)
        
        # 1. Memory Mode
        print("\n  Testing MEMORY mode...")
        db = DictSQLiteV4(db_path, hot_capacity=20000, persist_mode="memory")
        count = 10000
        
        def memory_write():
            for i in range(count):
                db[f"mem_{i}"] = f"value_{i}".encode()
        
        ops, _ = bench.measure_ops("Persistence: Memory Mode Write (10K)", count, memory_write)
        print(f"    Memory Write: {ops:,.0f} ops/sec")
        db.close()
        
        # 2. Lazy Mode
        os.unlink(db_path)
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        print("\n  Testing LAZY mode...")
        db = DictSQLiteV4(db_path, hot_capacity=20000, persist_mode="lazy")
        
        def lazy_write():
            for i in range(count):
                db[f"lazy_{i}"] = f"value_{i}".encode()
        
        ops, _ = bench.measure_ops("Persistence: Lazy Mode Write (10K)", count, lazy_write)
        print(f"    Lazy Write: {ops:,.0f} ops/sec")
        
        def lazy_flush():
            db.flush()
        
        ops, _ = bench.measure_ops("Persistence: Lazy Mode Flush", 1, lazy_flush)
        print(f"    Lazy Flush: {ops:,.0f} ops/sec")
        db.close()
        
        # 3. WriteThrough Mode
        os.unlink(db_path)
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        print("\n  Testing WRITETHROUGH mode...")
        db = DictSQLiteV4(db_path, hot_capacity=20000, persist_mode="writethrough")
        
        count = 1000  # Smaller count for writethrough
        def writethrough_write():
            for i in range(count):
                db[f"wt_{i}"] = f"value_{i}".encode()
        
        ops, _ = bench.measure_ops("Persistence: WriteThrough Write (1K)", count, writethrough_write)
        print(f"    WriteThrough Write: {ops:,.0f} ops/sec")
        db.close()
        
        return bench
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def benchmark_lru_eviction():
    """Benchmark LRU eviction performance"""
    print("\n" + "="*100)
    print("BENCHMARK 6: LRU Eviction")
    print("="*100)
    
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        bench = ComprehensiveBenchmark(iterations=5)
        
        # Test with small capacity to trigger evictions
        capacity = 1000
        write_count = 5000
        
        db = DictSQLiteV4(db_path, hot_capacity=capacity, persist_mode="lazy")
        
        def lru_eviction_test():
            for i in range(write_count):
                db[f"lru_{i}"] = f"value_{i}".encode()
        
        ops, _ = bench.measure_ops(f"LRU: Eviction Test (cap={capacity}, writes={write_count})", write_count, lru_eviction_test)
        print(f"  LRU with Eviction: {ops:,.0f} ops/sec")
        
        # Test read after eviction
        def lru_read_evicted():
            for i in range(write_count):
                try:
                    _ = db[f"lru_{i}"]
                except KeyError:
                    pass
        
        ops, _ = bench.measure_ops("LRU: Read After Eviction (5K items)", write_count, lru_read_evicted)
        print(f"  Read After Eviction: {ops:,.0f} ops/sec")
        
        db.close()
        return bench
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


def run_all_benchmarks():
    """Run all comprehensive benchmarks"""
    print("\n" + "="*100)
    print("DICTSQLITE V4.1 - COMPREHENSIVE BENCHMARK SUITE")
    print("="*100)
    print(f"Iterations per test: 5")
    print(f"Warmup runs: 1")
    print("="*100)
    
    all_results = {}
    
    # Run all benchmarks
    bench1 = benchmark_basic_operations()
    all_results.update(bench1.results)
    
    bench2 = benchmark_bulk_operations()
    all_results.update(bench2.results)
    
    bench3 = benchmark_pickle_operations()
    all_results.update(bench3.results)
    
    bench4 = benchmark_encryption_operations()
    all_results.update(bench4.results)
    
    bench5 = benchmark_persistence_modes()
    all_results.update(bench5.results)
    
    bench6 = benchmark_lru_eviction()
    all_results.update(bench6.results)
    
    # Print consolidated results
    print("\n" + "="*100)
    print("CONSOLIDATED RESULTS - ALL BENCHMARKS")
    print("="*100)
    print(f"{'Operation':<55} {'Ops/sec':>15} {'Time (ms)':>15} {'Std Dev':>10}")
    print("-"*100)
    
    for name, data in all_results.items():
        ops_per_sec = data['ops_per_sec']
        avg_time_ms = data['avg_time'] * 1000
        stdev_ms = data['stdev_time'] * 1000
        print(f"{name:<55} {ops_per_sec:>15,.0f} {avg_time_ms:>15.2f} {stdev_ms:>10.2f}")
    
    print("="*100)
    
    # Print summary statistics
    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100)
    
    all_ops = [data['ops_per_sec'] for data in all_results.values()]
    print(f"Total benchmarks run: {len(all_results)}")
    print(f"Average ops/sec: {statistics.mean(all_ops):,.0f}")
    print(f"Median ops/sec: {statistics.median(all_ops):,.0f}")
    print(f"Max ops/sec: {max(all_ops):,.0f}")
    print(f"Min ops/sec: {min(all_ops):,.0f}")
    
    # Top 5 fastest operations
    print("\nTop 5 Fastest Operations:")
    sorted_ops = sorted(all_results.items(), key=lambda x: x[1]['ops_per_sec'], reverse=True)
    for i, (name, data) in enumerate(sorted_ops[:5], 1):
        print(f"  {i}. {name}: {data['ops_per_sec']:,.0f} ops/sec")
    
    print("\n" + "="*100)
    print("Benchmark completed successfully!")
    print("="*100)


if __name__ == "__main__":
    run_all_benchmarks()
