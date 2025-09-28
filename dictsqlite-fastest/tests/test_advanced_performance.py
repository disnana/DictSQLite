"""Advanced performance tests and benchmarks for DictSQLite-Fastest."""

import time
import asyncio
import tempfile
import os
from pathlib import Path
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import both versions
from dictsqlite.main import DictSQLite
from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest


@pytest.fixture()
def tmp_db_paths(tmp_path):
    """一時的なDBファイルパスを提供"""
    return {
        'original': tmp_path / "original.db",
        'fastest': tmp_path / "fastest.db"
    }


def measure_time(func):
    """実行時間を測定するデコレータ"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    return wrapper


class TestAdvancedPerformance:
    """高度なパフォーマンステスト"""

    def test_wal_mode_performance(self, tmp_db_paths):
        """WALモードでのパフォーマンステスト"""
        n_items = 1000
        
        @measure_time
        def wal_operations_original(db_path, n):
            with DictSQLite(str(db_path), journal_mode='WAL') as db:
                # 一括挿入
                for i in range(n):
                    db[f"wal_key_{i}"] = f"wal_value_{i}"
                
                # 読み取り
                values = []
                for i in range(n):
                    values.append(db[f"wal_key_{i}"])
                return values
                    
        @measure_time
        def wal_operations_fastest(db_path, n):
            with DictSQLiteFastest(str(db_path), journal_mode='WAL') as db:
                # 一括挿入
                for i in range(n):
                    db[f"wal_key_{i}"] = f"wal_value_{i}"
                
                # 読み取り
                values = []
                for i in range(n):
                    values.append(db[f"wal_key_{i}"])
                return values
        
        _, time_original = wal_operations_original(tmp_db_paths['original'], n_items)
        _, time_fastest = wal_operations_fastest(tmp_db_paths['fastest'], n_items)
        
        print(f"\nWALモード操作 ({n_items} items):")
        print(f"  DictSQLite: {time_original:.4f}s")
        print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
        print(f"  Speed up: {time_original/time_fastest:.2f}x")
        
        # Fastest should be faster
        assert time_fastest <= time_original * 1.2

    def test_threaded_performance(self, tmp_db_paths):
        """マルチスレッドでのパフォーマンステスト"""
        n_threads = 4
        n_ops_per_thread = 250
        
        def worker_original(db_path, thread_id, n_ops):
            with DictSQLite(str(db_path), journal_mode='WAL') as db:
                for i in range(n_ops):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    db[key] = value
                    retrieved = db[key]
                    assert retrieved == value
        
        def worker_fastest(db_path, thread_id, n_ops):
            with DictSQLiteFastest(str(db_path), journal_mode='WAL') as db:
                for i in range(n_ops):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    db[key] = value
                    retrieved = db[key]
                    assert retrieved == value
        
        # Original版
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = [
                executor.submit(worker_original, tmp_db_paths['original'], i, n_ops_per_thread)
                for i in range(n_threads)
            ]
            for future in as_completed(futures):
                future.result()
        time_original = time.perf_counter() - start
        
        # Fastest版
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = [
                executor.submit(worker_fastest, tmp_db_paths['fastest'], i, n_ops_per_thread)
                for i in range(n_threads)
            ]
            for future in as_completed(futures):
                future.result()
        time_fastest = time.perf_counter() - start
        
        print(f"\nマルチスレッド操作 ({n_threads} threads, {n_ops_per_thread} ops each):")
        print(f"  DictSQLite: {time_original:.4f}s")
        print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
        print(f"  Speed up: {time_original/time_fastest:.2f}x")
        
        # Fastest should handle threading better
        assert time_fastest <= time_original * 1.5

    def test_batch_operations_performance(self, tmp_db_paths):
        """バッチ操作のパフォーマンステスト"""
        batch_sizes = [100, 500, 1000]
        
        for batch_size in batch_sizes:
            @measure_time
            def batch_ops_original(db_path, n):
                with DictSQLite(str(db_path)) as db:
                    # バッチ挿入
                    batch_data = {f"batch_key_{i}": {"index": i, "data": f"batch_data_{i}"} for i in range(n)}
                    for key, value in batch_data.items():
                        db[key] = value
                    
                    # バッチ読み取り
                    retrieved = {}
                    for key in batch_data.keys():
                        retrieved[key] = db[key]
                    return retrieved
                        
            @measure_time
            def batch_ops_fastest(db_path, n):
                with DictSQLiteFastest(str(db_path)) as db:
                    # バッチ挿入
                    batch_data = {f"batch_key_{i}": {"index": i, "data": f"batch_data_{i}"} for i in range(n)}
                    for key, value in batch_data.items():
                        db[key] = value
                    
                    # バッチ読み取り
                    retrieved = {}
                    for key in batch_data.keys():
                        retrieved[key] = db[key]
                    return retrieved
            
            _, time_original = batch_ops_original(tmp_db_paths['original'], batch_size)
            _, time_fastest = batch_ops_fastest(tmp_db_paths['fastest'], batch_size)
            
            print(f"\nバッチ操作 ({batch_size} items):")
            print(f"  DictSQLite: {time_original:.4f}s")
            print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
            print(f"  Speed up: {time_original/time_fastest:.2f}x")
            
            assert time_fastest <= time_original * 1.3

    def test_memory_usage_comparison(self, tmp_db_paths):
        """メモリ使用量の比較（簡易版）"""
        import psutil
        import os
        
        n_items = 5000
        large_data = "x" * 1000  # 1KB strings
        
        def measure_memory_usage(func, *args):
            process = psutil.Process()
            
            # ガベージコレクションを実行してベースラインを設定
            import gc
            gc.collect()
            mem_start = process.memory_info().rss
            
            result = func(*args)
            
            mem_end = process.memory_info().rss
            return result, mem_end - mem_start
        
        def memory_test_original(db_path, n, data):
            with DictSQLite(str(db_path)) as db:
                for i in range(n):
                    db[f"mem_key_{i}"] = {"data": data, "index": i}
                return db.keys()
        
        def memory_test_fastest(db_path, n, data):
            with DictSQLiteFastest(str(db_path)) as db:
                for i in range(n):
                    db[f"mem_key_{i}"] = {"data": data, "index": i}
                return db.keys()
        
        _, mem_original = measure_memory_usage(memory_test_original, tmp_db_paths['original'], n_items, large_data)
        _, mem_fastest = measure_memory_usage(memory_test_fastest, tmp_db_paths['fastest'], n_items, large_data)
        
        print(f"\nメモリ使用量 ({n_items} items, 1KB each):")
        print(f"  DictSQLite: {mem_original/1024/1024:.2f} MB")
        print(f"  DictSQLite-Fastest: {mem_fastest/1024/1024:.2f} MB")
        if mem_original > 0:
            print(f"  Memory efficiency: {mem_original/mem_fastest:.2f}x")


@pytest.mark.asyncio
class TestAsyncAdvancedPerformance:
    """非同期の高度なパフォーマンステスト"""
    
    async def test_async_concurrent_operations(self):
        """非同期の同時操作パフォーマンス"""
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
            
        try:
            async def concurrent_worker(worker_id, n_ops=100):
                """同時実行ワーカー"""
                db = AsyncDictSQLiteFastest(db_path)
                try:
                    tasks = []
                    # 書き込みタスク
                    for i in range(n_ops):
                        key = f"async_worker_{worker_id}_key_{i}"
                        value = f"async_worker_{worker_id}_value_{i}"
                        tasks.append(db.aset(key, value))
                    
                    await asyncio.gather(*tasks)
                    
                    # 読み取りタスク
                    read_tasks = []
                    for i in range(n_ops):
                        key = f"async_worker_{worker_id}_key_{i}"
                        read_tasks.append(db.aget(key))
                    
                    values = await asyncio.gather(*read_tasks)
                    return len(values)
                finally:
                    await db.aclose()
            
            # 複数ワーカーを同時実行
            start = time.perf_counter()
            results = await asyncio.gather(*[concurrent_worker(i, 50) for i in range(3)])
            end = time.perf_counter()
            
            print(f"\n非同期同時操作 (3 workers, 50 ops each): {end-start:.4f}s")
            print(f"  Total operations: {sum(results) * 2}")  # read + write
            print(f"  Operations per second: {sum(results) * 2 / (end-start):.0f}")
            
            assert all(r == 50 for r in results)
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    async def test_async_bulk_performance(self):
        """非同期バルク操作のパフォーマンス"""
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            batch_sizes = [100, 300, 500]
            
            for batch_size in batch_sizes:
                db = AsyncDictSQLiteFastest(db_path)
                
                try:
                    # 書き込みパフォーマンス
                    start = time.perf_counter()
                    write_tasks = [
                        db.aset(f"bulk_key_{i}", f"bulk_value_{i}")
                        for i in range(batch_size)
                    ]
                    await asyncio.gather(*write_tasks)
                    write_time = time.perf_counter() - start
                    
                    # 読み取りパフォーマンス
                    start = time.perf_counter()
                    read_tasks = [
                        db.aget(f"bulk_key_{i}")
                        for i in range(batch_size)
                    ]
                    values = await asyncio.gather(*read_tasks)
                    read_time = time.perf_counter() - start
                    
                    print(f"\n非同期バルク操作 ({batch_size} items):")
                    print(f"  Write time: {write_time:.4f}s ({batch_size/write_time:.0f} ops/s)")
                    print(f"  Read time: {read_time:.4f}s ({batch_size/read_time:.0f} ops/s)")
                    
                    assert len(values) == batch_size
                    assert all(v == f"bulk_value_{i}" for i, v in enumerate(values))
                    
                finally:
                    await db.aclose()
                    
                # クリーンアップ for next iteration
                if os.path.exists(db_path):
                    os.unlink(db_path)
                    
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


def test_comparison_summary(tmp_db_paths):
    """パフォーマンス比較の総合サマリー"""
    
    print("\n" + "="*80)
    print("DICTSQLITE-FASTEST PERFORMANCE SUMMARY")
    print("="*80)
    
    # 基本的な操作テスト
    operations = [
        ("Insert", lambda db, n: [db.__setitem__(f"key_{i}", f"value_{i}") for i in range(n)]),
        ("Read", lambda db, n: [db.__getitem__(f"key_{i}") for i in range(n)]),
        ("Contains", lambda db, n: [f"key_{i}" in db for i in range(n)]),
    ]
    
    n_ops = 1000
    
    for op_name, op_func in operations:
        # Original
        with DictSQLite(str(tmp_db_paths['original']), journal_mode='WAL') as db_orig:
            if op_name != "Insert":
                # データをプリロード
                for i in range(n_ops):
                    db_orig[f"key_{i}"] = f"value_{i}"
            
            start = time.perf_counter()
            op_func(db_orig, n_ops)
            time_orig = time.perf_counter() - start
        
        # Fastest
        with DictSQLiteFastest(str(tmp_db_paths['fastest']), journal_mode='WAL') as db_fast:
            if op_name != "Insert":
                # データをプリロード
                for i in range(n_ops):
                    db_fast[f"key_{i}"] = f"value_{i}"
            
            start = time.perf_counter()
            op_func(db_fast, n_ops)
            time_fast = time.perf_counter() - start
        
        speedup = time_orig / time_fast
        print(f"{op_name:10} | Original: {time_orig:6.4f}s | Fastest: {time_fast:6.4f}s | Speedup: {speedup:5.2f}x")
    
    print("="*80)