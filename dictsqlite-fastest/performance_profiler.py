#!/usr/bin/env python3
"""
DictSQLite-Fastest Performance Profiler
高度なパフォーマンス分析とボトルネック特定ツール
"""

import asyncio
import cProfile
import pstats
import time
import memory_profiler
import psutil
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add dictsqlite-fastest to path
sys.path.insert(0, os.path.dirname(__file__))

from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest

class PerformanceProfiler:
    """高度なパフォーマンスプロファイラー"""
    
    def __init__(self):
        self.results = {}
        
    def profile_cpu(self, func, *args, **kwargs):
        """CPU使用率プロファイル"""
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        return result, stats
    
    def profile_memory(self, func, *args, **kwargs):
        """メモリ使用量プロファイル"""
        # メモリプロファイリング
        import tracemalloc
        tracemalloc.start()
        
        # 実行前メモリ使用量
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # 関数実行
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # 実行後メモリ使用量
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_diff = memory_after - memory_before
        
        # tracemalloc統計
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return result, {
            'execution_time': end_time - start_time,
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_diff': memory_diff,
            'tracemalloc_current': current / 1024 / 1024,  # MB
            'tracemalloc_peak': peak / 1024 / 1024  # MB
        }
    
    def benchmark_sync_operations(self, db_path='/tmp/profile_sync.db'):
        """同期操作のベンチマーク"""
        print("🔍 同期操作プロファイリング開始")
        
        # 基本操作テスト
        test_sizes = [100, 500, 1000, 5000]
        operations = ['insert', 'read', 'bulk_insert', 'bulk_read']
        
        results = {}
        
        for size in test_sizes:
            print(f"  📊 テストサイズ: {size}")
            results[size] = {}
            
            # 挿入テスト
            def insert_test():
                with DictSQLiteFastest(f"{db_path}_{size}_insert") as db:
                    for i in range(size):
                        db[f'key_{i}'] = f'value_{i}' * 10  # より大きなデータ
            
            result, memory_stats = self.profile_memory(insert_test)
            results[size]['insert'] = memory_stats
            print(f"    挿入: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
            
            # 読み取りテスト（データをプリロード）
            with DictSQLiteFastest(f"{db_path}_{size}_read") as db:
                for i in range(size):
                    db[f'key_{i}'] = f'value_{i}' * 10
            
            def read_test():
                with DictSQLiteFastest(f"{db_path}_{size}_read") as db:
                    for i in range(size):
                        _ = db[f'key_{i}']
            
            result, memory_stats = self.profile_memory(read_test)
            results[size]['read'] = memory_stats
            print(f"    読み取り: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
            
            # バルク挿入テスト
            def bulk_insert_test():
                with DictSQLiteFastest(f"{db_path}_{size}_bulk_insert") as db:
                    data = {f'key_{i}': f'value_{i}' * 10 for i in range(size)}
                    if hasattr(db, 'bulk_insert_apsw_optimized'):
                        db.bulk_insert_apsw_optimized(data)
                    else:
                        db.bulk_insert_optimized(data)
            
            result, memory_stats = self.profile_memory(bulk_insert_test)
            results[size]['bulk_insert'] = memory_stats
            print(f"    バルク挿入: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
            
            # バルク読み取りテスト
            with DictSQLiteFastest(f"{db_path}_{size}_bulk_read") as db:
                data = {f'key_{i}': f'value_{i}' * 10 for i in range(size)}
                db.bulk_insert_optimized(data)
            
            def bulk_read_test():
                with DictSQLiteFastest(f"{db_path}_{size}_bulk_read") as db:
                    keys = [f'key_{i}' for i in range(size)]
                    if hasattr(db, 'bulk_get_apsw_optimized'):
                        _ = db.bulk_get_apsw_optimized(keys)
                    else:
                        _ = db.bulk_get(keys)
            
            result, memory_stats = self.profile_memory(bulk_read_test)
            results[size]['bulk_read'] = memory_stats
            print(f"    バルク読み取り: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
        
        return results
    
    async def benchmark_async_operations(self, db_path='/tmp/profile_async.db'):
        """非同期操作のベンチマーク"""
        print("🔍 非同期操作プロファイリング開始")
        
        async def async_insert_test(size):
            async with AsyncDictSQLiteFastest(f"{db_path}_{size}_async_insert") as db:
                tasks = [db.aset(f'key_{i}', f'value_{i}' * 10) for i in range(size)]
                await asyncio.gather(*tasks)
        
        async def async_read_test(size):
            # データをプリロード
            async with AsyncDictSQLiteFastest(f"{db_path}_{size}_async_read") as db:
                await db.abulk_insert({f'key_{i}': f'value_{i}' * 10 for i in range(size)})
            
            async with AsyncDictSQLiteFastest(f"{db_path}_{size}_async_read") as db:
                tasks = [db.aget(f'key_{i}') for i in range(size)]
                await asyncio.gather(*tasks)
        
        async def async_bulk_test(size):
            async with AsyncDictSQLiteFastest(f"{db_path}_{size}_async_bulk") as db:
                data = {f'key_{i}': f'value_{i}' * 10 for i in range(size)}
                await db.abulk_insert(data)
                keys = list(data.keys())
                await db.abulk_get(keys)
        
        test_sizes = [100, 500, 1000, 2000]
        results = {}
        
        for size in test_sizes:
            print(f"  📊 非同期テストサイズ: {size}")
            results[size] = {}
            
            # 非同期挿入テスト
            result, memory_stats = self.profile_memory(
                lambda: asyncio.run(async_insert_test(size))
            )
            results[size]['async_insert'] = memory_stats
            print(f"    非同期挿入: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
            
            # 非同期読み取りテスト
            result, memory_stats = self.profile_memory(
                lambda: asyncio.run(async_read_test(size))
            )
            results[size]['async_read'] = memory_stats
            print(f"    非同期読み取り: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
            
            # 非同期バルクテスト
            result, memory_stats = self.profile_memory(
                lambda: asyncio.run(async_bulk_test(size))
            )
            results[size]['async_bulk'] = memory_stats
            print(f"    非同期バルク: {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
        
        return results
    
    def benchmark_concurrency(self, db_path='/tmp/profile_concurrent.db'):
        """並行性のベンチマーク"""
        print("🔍 並行性プロファイリング開始")
        
        def concurrent_worker(worker_id, operations_per_worker, db_path):
            db_file = f"{db_path}_worker_{worker_id}.db"
            with DictSQLiteFastest(db_file) as db:
                for i in range(operations_per_worker):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}" * 10
                    db[key] = value
                    retrieved = db[key]
                    assert retrieved == value
            return f"Worker {worker_id} completed"
        
        thread_counts = [1, 2, 4, 8]
        operations_per_worker = 250
        results = {}
        
        for thread_count in thread_counts:
            print(f"  📊 スレッド数: {thread_count}")
            
            def concurrent_test():
                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    futures = [
                        executor.submit(concurrent_worker, i, operations_per_worker, db_path)
                        for i in range(thread_count)
                    ]
                    results_list = []
                    for future in as_completed(futures):
                        results_list.append(future.result())
                    return results_list
            
            result, memory_stats = self.profile_memory(concurrent_test)
            results[thread_count] = memory_stats
            print(f"    並行実行({thread_count}スレッド): {memory_stats['execution_time']:.4f}s, メモリ増加: {memory_stats['memory_diff']:.2f}MB")
            
            # スループット計算
            total_operations = thread_count * operations_per_worker * 2  # read + write
            throughput = total_operations / memory_stats['execution_time']
            print(f"    スループット: {throughput:.0f} ops/sec")
        
        return results
    
    def generate_report(self, sync_results, async_results, concurrent_results):
        """包括的なパフォーマンスレポートを生成"""
        print("\n" + "="*80)
        print("📈 DICTSQLITE-FASTEST パフォーマンス分析レポート")
        print("="*80)
        
        # 同期操作分析
        print("\n🔄 同期操作分析:")
        for size, operations in sync_results.items():
            print(f"\n  データサイズ: {size}")
            for op_name, stats in operations.items():
                ops_per_sec = size / stats['execution_time'] if stats['execution_time'] > 0 else 0
                print(f"    {op_name:15}: {stats['execution_time']:6.4f}s ({ops_per_sec:8.0f} ops/sec) メモリ: {stats['memory_diff']:+6.2f}MB")
        
        # 非同期操作分析
        print("\n⚡ 非同期操作分析:")
        for size, operations in async_results.items():
            print(f"\n  データサイズ: {size}")
            for op_name, stats in operations.items():
                ops_per_sec = size / stats['execution_time'] if stats['execution_time'] > 0 else 0
                print(f"    {op_name:15}: {stats['execution_time']:6.4f}s ({ops_per_sec:8.0f} ops/sec) メモリ: {stats['memory_diff']:+6.2f}MB")
        
        # 並行性分析
        print("\n🚀 並行性分析:")
        for thread_count, stats in concurrent_results.items():
            total_ops = thread_count * 250 * 2
            throughput = total_ops / stats['execution_time']
            print(f"  {thread_count:2d}スレッド: {stats['execution_time']:6.4f}s ({throughput:8.0f} ops/sec) メモリ: {stats['memory_diff']:+6.2f}MB")
        
        # ボトルネック特定
        print("\n🎯 ボトルネック分析:")
        
        # 最も遅い操作を特定
        slowest_ops = []
        for size, operations in sync_results.items():
            for op_name, stats in operations.items():
                ops_per_sec = size / stats['execution_time'] if stats['execution_time'] > 0 else 0
                slowest_ops.append((f"{op_name}({size})", ops_per_sec, stats['memory_diff']))
        
        slowest_ops.sort(key=lambda x: x[1])  # ops/secで昇順ソート
        
        print("  最も遅い操作 (改善の余地あり):")
        for i, (op_name, ops_per_sec, memory_diff) in enumerate(slowest_ops[:5]):
            print(f"    {i+1}. {op_name}: {ops_per_sec:.0f} ops/sec (メモリ: {memory_diff:+.2f}MB)")
        
        # メモリ消費が大きい操作
        memory_hungry = sorted(slowest_ops, key=lambda x: abs(x[2]), reverse=True)
        print("\n  メモリ消費が大きい操作:")
        for i, (op_name, ops_per_sec, memory_diff) in enumerate(memory_hungry[:5]):
            print(f"    {i+1}. {op_name}: {memory_diff:+.2f}MB (速度: {ops_per_sec:.0f} ops/sec)")
        
        print("\n" + "="*80)


async def main():
    """メインプロファイリング実行"""
    profiler = PerformanceProfiler()
    
    print("🚀 DictSQLite-Fastest 高度パフォーマンス分析を開始")
    print("="*60)
    
    # 同期操作プロファイリング
    sync_results = profiler.benchmark_sync_operations()
    
    # 非同期操作プロファイリング
    async_results = await profiler.benchmark_async_operations()
    
    # 並行性プロファイリング
    concurrent_results = profiler.benchmark_concurrency()
    
    # 包括的レポート生成
    profiler.generate_report(sync_results, async_results, concurrent_results)
    
    print("\n✅ パフォーマンス分析完了!")
    

if __name__ == "__main__":
    asyncio.run(main())