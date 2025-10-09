#!/usr/bin/env python3
"""
DictSQLite v4.2 Comprehensive Performance Test Suite

This suite tests v4.2 optimizations across multiple dimensions:
- Async vs Sync operations
- With/without encryption
- With/without safe pickle
- Different buffer sizes
- Different persist modes
- Various operation patterns

The tests are designed to validate the expected performance improvements:
- Async write buffering: 300x speedup
- Sync WriteThrough batching: 43x speedup
- Batch read optimization: 5-10x speedup
"""

import tempfile
import os
import sys
import time
import statistics
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
except ImportError:
    print("❌ Error: dictsqlite module not found.")
    print("Please build with: maturin develop --release")
    sys.exit(1)


def cleanup_db_files(db_path):
    """
    データベースファイルとWALファイルをクリーンアップ
    性能テスト用: 待機なしの高速クリーンアップ
    """
    # 性能テストでは待機を入れない（測定結果に影響するため）
    for ext in ['', '-wal', '-shm']:
        try:
            file_path = db_path + ext
            if os.path.exists(file_path):
                os.unlink(file_path)
        except (FileNotFoundError, PermissionError):
            # Windows環境でPermissionErrorが発生する可能性があるが、
            # 性能測定に影響しないよう待機せず無視
            pass
        except Exception:
            # その他のエラーも無視
            pass


class PerformanceTestSuite:
    """Comprehensive performance test suite for v4.2"""
    
    def __init__(self, iterations: int = 3, output_json: bool = True, output_filename: str = "performance_results.json"):
        self.iterations = iterations
        self.output_json = output_json
        self.output_filename = output_filename
        self.results: Dict[str, Any] = {
            'version': '4.2.0',
            'timestamp': datetime.now().isoformat(),
            'iterations': iterations,
            'tests': {}
        }
    
    def measure(self, name: str, func, *args, **kwargs) -> Tuple[float, Any]:
        """Measure execution time of a function"""
        times = []
        result = None
        for i in range(self.iterations):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        avg_time = statistics.mean(times)
        stdev = statistics.stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)
        
        self.results['tests'][name] = {
            'avg_time': avg_time,
            'stdev': stdev,
            'min_time': min_time,
            'max_time': max_time,
            'iterations': times
        }
        
        return avg_time, result
    
    def format_ops(self, ops_per_sec: float) -> str:
        """Format operations per second"""
        if ops_per_sec >= 1_000_000:
            return f"{ops_per_sec/1_000_000:.2f}M ops/sec"
        elif ops_per_sec >= 1_000:
            return f"{ops_per_sec/1_000:.2f}K ops/sec"
        else:
            return f"{ops_per_sec:.0f} ops/sec"
    
    def print_result(self, name: str, count: int, avg_time: float):
        """Print formatted test result"""
        ops_per_sec = count / avg_time if avg_time > 0 else 0
        test_data = self.results['tests'][name]
        
        print(f"\n📊 {name}")
        print(f"   Count: {count:,} operations")
        print(f"   Time: {avg_time:.3f}s (±{test_data['stdev']:.3f}s)")
        print(f"   Range: {test_data['min_time']:.3f}s - {test_data['max_time']:.3f}s")
        print(f"   Throughput: {self.format_ops(ops_per_sec)}")
    
    def test_async_write_buffering(self):
        """Test 1: Async write buffering optimization (300x speedup)"""
        print("\n" + "="*80)
        print("TEST 1: 非同期書き込みバッファリング（300倍高速化の検証）")
        print("="*80)
        
        count = 1000
        results = {}
        
        # Test different buffer sizes
        for buffer_size in [1, 10, 50, 100, 200]:
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                db = AsyncDictSQLite(db_path, capacity=10000, 
                                    persist_mode="writethrough", 
                                    buffer_size=buffer_size)
                
                def write_test():
                    for i in range(count):
                        db.set_async(f"key_{i}", f"value_{i}".encode())
                    db.flush()
                
                avg_time, _ = self.measure(
                    f"async_write_buffer_{buffer_size}", 
                    write_test
                )
                
                self.print_result(f"async_write_buffer_{buffer_size}", count, avg_time)
                results[buffer_size] = count / avg_time
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
        
        # Show improvement
        baseline = results.get(1, 0)
        if baseline > 0:
            print(f"\n💡 バッファサイズによる改善:")
            for size, ops in results.items():
                improvement = ops / baseline
                print(f"   buffer_size={size}: {improvement:.1f}x faster than buffer_size=1")
    
    def test_sync_writethrough_batching(self):
        """Test 2: Sync WriteThrough batching (43x speedup)"""
        print("\n" + "="*80)
        print("TEST 2: 同期WriteThrough バッチ書き込み（43倍高速化の検証）")
        print("="*80)
        
        count = 1000
        results = {}
        
        for buffer_size in [1, 50, 100, 200]:
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                db = DictSQLiteV4(db_path, hot_capacity=10000,
                                 persist_mode="writethrough",
                                 buffer_size=buffer_size)
                
                def write_test():
                    for i in range(count):
                        db[f"key_{i}"] = f"value_{i}".encode()
                    db.flush()
                
                avg_time, _ = self.measure(
                    f"sync_writethrough_buffer_{buffer_size}",
                    write_test
                )
                
                self.print_result(f"sync_writethrough_buffer_{buffer_size}", count, avg_time)
                results[buffer_size] = count / avg_time
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
        
        # Show improvement
        baseline = results.get(1, 0)
        if baseline > 0:
            print(f"\n💡 バッファサイズによる改善:")
            for size, ops in results.items():
                improvement = ops / baseline
                print(f"   buffer_size={size}: {improvement:.1f}x faster than buffer_size=1")
    
    def test_persist_modes_comparison(self):
        """Test 3: Compare all persist modes"""
        print("\n" + "="*80)
        print("TEST 3: Persist モード比較（Memory/Lazy/WriteThrough）")
        print("="*80)
        
        count = 1000
        results = {}
        
        for mode in ['memory', 'lazy', 'writethrough']:
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                db = DictSQLiteV4(db_path, hot_capacity=10000,
                                 persist_mode=mode,
                                 buffer_size=100)
                
                def write_test():
                    for i in range(count):
                        db[f"key_{i}"] = f"value_{i}".encode()
                    if mode in ['lazy', 'writethrough']:
                        db.flush()
                
                avg_time, _ = self.measure(f"persist_mode_{mode}", write_test)
                self.print_result(f"persist_mode_{mode}", count, avg_time)
                results[mode] = count / avg_time
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
        
        print(f"\n💡 モード比較:")
        for mode, ops in sorted(results.items(), key=lambda x: x[1], reverse=True):
            print(f"   {mode.upper()}: {self.format_ops(ops)}")
    
    def test_encryption_overhead(self):
        """Test 4: Encryption overhead"""
        print("\n" + "="*80)
        print("TEST 4: 暗号化オーバーヘッド（AES-256-GCM）")
        print("="*80)
        
        count = 500
        results = {}
        
        for encrypted in [False, True]:
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                password = "test_password_12345" if encrypted else None
                db = DictSQLiteV4(db_path, hot_capacity=10000,
                                 persist_mode="lazy",
                                 encryption_password=password,
                                 buffer_size=100)
                
                def write_test():
                    for i in range(count):
                        db[f"key_{i}"] = f"value_{i}".encode()
                    db.flush()
                
                def read_test():
                    for i in range(count):
                        _ = db.get(f"key_{i}")
                
                # Write test
                write_time, _ = self.measure(
                    f"encryption_{encrypted}_write",
                    write_test
                )
                self.print_result(f"encryption_{encrypted}_write", count, write_time)
                
                # Read test
                read_time, _ = self.measure(
                    f"encryption_{encrypted}_read",
                    read_test
                )
                self.print_result(f"encryption_{encrypted}_read", count, read_time)
                
                results[encrypted] = {
                    'write': count / write_time,
                    'read': count / read_time
                }
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
        
        # Calculate overhead
        if False in results and True in results:
            write_overhead = (results[True]['write'] / results[False]['write'] - 1) * 100
            read_overhead = (results[True]['read'] / results[False]['read'] - 1) * 100
            print(f"\n💡 暗号化オーバーヘッド:")
            print(f"   Write: {abs(write_overhead):.1f}% {'slower' if write_overhead < 0 else 'faster'}")
            print(f"   Read: {abs(read_overhead):.1f}% {'slower' if read_overhead < 0 else 'faster'}")
    
    def test_safe_pickle_overhead(self):
        """Test 5: Safe pickle validation overhead"""
        print("\n" + "="*80)
        print("TEST 5: Safe Pickle検証オーバーヘッド")
        print("="*80)
        
        count = 500
        results = {}
        
        for safe_pickle in [False, True]:
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                db = DictSQLiteV4(db_path, hot_capacity=10000,
                                 persist_mode="lazy",
                                 enable_safe_pickle=safe_pickle,
                                 buffer_size=100)
                
                def write_test():
                    for i in range(count):
                        db[f"key_{i}"] = f"value_{i}".encode()
                    db.flush()
                
                avg_time, _ = self.measure(
                    f"safe_pickle_{safe_pickle}",
                    write_test
                )
                self.print_result(f"safe_pickle_{safe_pickle}", count, avg_time)
                results[safe_pickle] = count / avg_time
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
        
        # Calculate overhead
        if False in results and True in results:
            overhead = (results[True] / results[False] - 1) * 100
            print(f"\n💡 Safe Pickle オーバーヘッド:")
            print(f"   {abs(overhead):.1f}% {'slower' if overhead < 0 else 'faster'}")
    
    def test_batch_operations(self):
        """Test 6: Batch operations performance"""
        print("\n" + "="*80)
        print("TEST 6: バッチ操作パフォーマンス")
        print("="*80)
        
        count = 1000
        
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        try:
            db = AsyncDictSQLite(db_path, capacity=10000,
                                persist_mode="lazy",
                                buffer_size=100)
            
            # Prepare data
            for i in range(count):
                db.set_async(f"key_{i}", f"value_{i}".encode())
            db.flush()
            
            # Batch get test
            keys = [f"key_{i}" for i in range(count)]
            
            def batch_get_test():
                return db.batch_get(keys)
            
            avg_time, _ = self.measure("async_batch_get", batch_get_test)
            self.print_result("async_batch_get", count, avg_time)
            
            # Batch set test
            items = [(f"batch_key_{i}", f"batch_value_{i}".encode()) for i in range(count)]
            
            def batch_set_test():
                db.batch_set(items)
                db.flush()
            
            avg_time, _ = self.measure("async_batch_set", batch_set_test)
            self.print_result("async_batch_set", count, avg_time)
            
            db.close()
            
        finally:
            for ext in ['', '-wal', '-shm']:
                try:
                    os.unlink(db_path + ext)
                except FileNotFoundError:
                    pass
    
    def test_mixed_operations(self):
        """Test 7: Mixed read/write patterns"""
        print("\n" + "="*80)
        print("TEST 7: 混合読み書きパターン")
        print("="*80)
        
        count = 1000
        patterns = {
            'read_heavy': (0.8, 0.2),  # 80% read, 20% write
            'write_heavy': (0.2, 0.8),  # 20% read, 80% write
            'balanced': (0.5, 0.5),     # 50% read, 50% write
        }
        
        for pattern_name, (read_ratio, write_ratio) in patterns.items():
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                db = DictSQLiteV4(db_path, hot_capacity=10000,
                                 persist_mode="lazy",
                                 buffer_size=100)
                
                # Pre-populate
                for i in range(count // 2):
                    db[f"key_{i}"] = f"value_{i}".encode()
                
                def mixed_test():
                    import random
                    for i in range(count):
                        if random.random() < read_ratio:
                            # Read operation
                            _ = db.get(f"key_{i % (count // 2)}", None)
                        else:
                            # Write operation
                            db[f"key_{i}"] = f"new_value_{i}".encode()
                    db.flush()
                
                avg_time, _ = self.measure(f"mixed_{pattern_name}", mixed_test)
                self.print_result(f"mixed_{pattern_name}", count, avg_time)
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
    
    def test_combined_features(self):
        """Test 8: All features combined"""
        print("\n" + "="*80)
        print("TEST 8: 全機能組み合わせテスト")
        print("="*80)
        
        count = 500
        combinations = [
            ('baseline', {}),
            ('encryption', {'encryption_password': 'test_password_12345'}),
            ('safe_pickle', {'enable_safe_pickle': True}),
            ('both', {'encryption_password': 'test_password_12345', 'enable_safe_pickle': True}),
        ]
        
        results = {}
        
        for name, kwargs in combinations:
            fd, db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            
            try:
                db = DictSQLiteV4(db_path, hot_capacity=10000,
                                 persist_mode="lazy",
                                 buffer_size=100,
                                 **kwargs)
                
                def combined_test():
                    for i in range(count):
                        db[f"key_{i}"] = f"value_{i}".encode()
                    db.flush()
                    for i in range(count):
                        _ = db[f"key_{i}"]
                
                avg_time, _ = self.measure(f"combined_{name}", combined_test)
                self.print_result(f"combined_{name}", count * 2, avg_time)
                results[name] = (count * 2) / avg_time
                
                db.close()
                
            finally:
                cleanup_db_files(db_path)
        
        # Show comparison
        baseline = results.get('baseline', 0)
        if baseline > 0:
            print(f"\n💡 機能別のパフォーマンス比較:")
            for name, ops in results.items():
                ratio = ops / baseline
                print(f"   {name}: {self.format_ops(ops)} ({ratio:.2f}x vs baseline)")
    
    def save_results(self):
        """Save results to JSON file"""
        if self.output_json:
            with open(self.output_filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n📄 Results saved to: {self.output_filename}")
    
    def run_all(self):
        """Run all performance tests"""
        print("\n" + "="*80)
        print("DictSQLite v4.2 包括的パフォーマンステスト")
        print("="*80)
        print(f"Iterations per test: {self.iterations}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        tests = [
            self.test_async_write_buffering,
            self.test_sync_writethrough_batching,
            self.test_persist_modes_comparison,
            self.test_encryption_overhead,
            self.test_safe_pickle_overhead,
            self.test_batch_operations,
            self.test_mixed_operations,
            self.test_combined_features,
        ]
        
        for i, test in enumerate(tests, 1):
            try:
                test()
            except Exception as e:
                print(f"\n❌ Test {i} failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print("\n" + "="*80)
        print("テストサマリー")
        print("="*80)
        print(f"Total tests: {len(self.results['tests'])}")
        print(f"Total time: {sum(t['avg_time'] for t in self.results['tests'].values()):.2f}s")
        
        self.save_results()
        
        print("\n✅ All performance tests completed!")
        return 0


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DictSQLite v4.2 Comprehensive Performance Test Suite"
    )
    parser.add_argument(
        '--iterations', '-i',
        type=int,
        default=3,
        help='Number of iterations per test (default: 3)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='performance_results.json',
        help='Output JSON file (default: performance_results.json)'
    )
    parser.add_argument(
        '--no-json',
        action='store_true',
        help='Disable JSON output'
    )
    
    args = parser.parse_args()
    
    suite = PerformanceTestSuite(
        iterations=args.iterations,
        output_json=not args.no_json,
        output_filename=args.output
    )
    
    return suite.run_all()


if __name__ == "__main__":
    sys.exit(main())
