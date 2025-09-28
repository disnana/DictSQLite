"""Performance comparison tests between DictSQLite and DictSQLite-Fastest."""

import time
import asyncio
import tempfile
import os
from pathlib import Path
import pytest

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


class TestSyncPerformanceComparison:
    """同期版のパフォーマンス比較"""

    def test_bulk_insert_performance(self, tmp_db_paths):
        """一括挿入のパフォーマンス比較"""
        
        @measure_time
        def bulk_insert_original(db_path, n=1000):
            with DictSQLite(str(db_path)) as db:
                for i in range(n):
                    db[f"key_{i}"] = f"value_{i}"
                    
        @measure_time
        def bulk_insert_fastest(db_path, n=1000):
            with DictSQLiteFastest(str(db_path)) as db:
                for i in range(n):
                    db[f"key_{i}"] = f"value_{i}"
        
        n_items = 1000
        _, time_original = bulk_insert_original(tmp_db_paths['original'], n_items)
        _, time_fastest = bulk_insert_fastest(tmp_db_paths['fastest'], n_items)
        
        print(f"\n一括挿入 ({n_items} items):")
        print(f"  DictSQLite: {time_original:.4f}s")
        print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
        print(f"  Speed up: {time_original/time_fastest:.2f}x")
        
        # Fastest should be faster (or at least not significantly slower)
        assert time_fastest <= time_original * 1.2  # Allow 20% margin

    def test_bulk_read_performance(self, tmp_db_paths):
        """一括読み取りのパフォーマンス比較"""
        n_items = 1000
        
        # データをセットアップ
        with DictSQLite(str(tmp_db_paths['original'])) as db:
            for i in range(n_items):
                db[f"key_{i}"] = f"value_{i}"
                
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db:
            for i in range(n_items):
                db[f"key_{i}"] = f"value_{i}"
        
        @measure_time
        def bulk_read_original(db_path, n):
            with DictSQLite(str(db_path)) as db:
                values = []
                for i in range(n):
                    values.append(db[f"key_{i}"])
                return values
                    
        @measure_time
        def bulk_read_fastest(db_path, n):
            with DictSQLiteFastest(str(db_path)) as db:
                values = []
                for i in range(n):
                    values.append(db[f"key_{i}"])
                return values
        
        _, time_original = bulk_read_original(tmp_db_paths['original'], n_items)
        _, time_fastest = bulk_read_fastest(tmp_db_paths['fastest'], n_items)
        
        print(f"\n一括読み取り ({n_items} items):")
        print(f"  DictSQLite: {time_original:.4f}s")
        print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
        print(f"  Speed up: {time_original/time_fastest:.2f}x")
        
        # Fastest should be faster
        assert time_fastest <= time_original * 1.2

    def test_mixed_operations_performance(self, tmp_db_paths):
        """混合操作のパフォーマンス比較"""
        n_ops = 500
        
        @measure_time
        def mixed_ops_original(db_path, n):
            with DictSQLite(str(db_path)) as db:
                # 挿入
                for i in range(n):
                    db[f"key_{i}"] = {"value": i, "data": f"item_{i}"}
                
                # 読み取り＆更新
                for i in range(0, n, 2):
                    value = db[f"key_{i}"]
                    value["updated"] = True
                    db[f"key_{i}"] = value
                
                # 削除
                for i in range(0, n, 4):
                    del db[f"key_{i}"]
                    
        @measure_time
        def mixed_ops_fastest(db_path, n):
            with DictSQLiteFastest(str(db_path)) as db:
                # 挿入
                for i in range(n):
                    db[f"key_{i}"] = {"value": i, "data": f"item_{i}"}
                
                # 読み取り＆更新
                for i in range(0, n, 2):
                    value = db[f"key_{i}"]
                    value["updated"] = True
                    db[f"key_{i}"] = value
                
                # 削除
                for i in range(0, n, 4):
                    del db[f"key_{i}"]
        
        _, time_original = mixed_ops_original(tmp_db_paths['original'], n_ops)
        _, time_fastest = mixed_ops_fastest(tmp_db_paths['fastest'], n_ops)
        
        print(f"\n混合操作 ({n_ops} ops):")
        print(f"  DictSQLite: {time_original:.4f}s")
        print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
        print(f"  Speed up: {time_original/time_fastest:.2f}x")
        
        assert time_fastest <= time_original * 1.2

    def test_large_value_performance(self, tmp_db_paths):
        """大きな値のパフォーマンス比較"""
        large_data = "x" * 10000  # 10KB strings
        n_items = 100
        
        @measure_time
        def large_value_ops_original(db_path, data, n):
            with DictSQLite(str(db_path)) as db:
                for i in range(n):
                    db[f"large_key_{i}"] = {"data": data, "index": i}
                    
                # Read back
                for i in range(n):
                    _ = db[f"large_key_{i}"]
                    
        @measure_time
        def large_value_ops_fastest(db_path, data, n):
            with DictSQLiteFastest(str(db_path)) as db:
                for i in range(n):
                    db[f"large_key_{i}"] = {"data": data, "index": i}
                    
                # Read back
                for i in range(n):
                    _ = db[f"large_key_{i}"]
        
        _, time_original = large_value_ops_original(tmp_db_paths['original'], large_data, n_items)
        _, time_fastest = large_value_ops_fastest(tmp_db_paths['fastest'], large_data, n_items)
        
        print(f"\n大きな値の操作 ({n_items} items, 10KB each):")
        print(f"  DictSQLite: {time_original:.4f}s")
        print(f"  DictSQLite-Fastest: {time_fastest:.4f}s")
        print(f"  Speed up: {time_original/time_fastest:.2f}x")
        
        assert time_fastest <= time_original * 1.2


@pytest.mark.asyncio
class TestAsyncPerformanceComparison:
    """非同期版のパフォーマンス比較"""
    
    async def test_async_bulk_operations(self):
        """非同期一括操作のテスト"""
        
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            async def async_bulk_ops(n=500):
                async with AsyncDictSQLiteFastest(db_path) as db:
                    # 一括挿入
                    tasks = []
                    for i in range(n):
                        tasks.append(db.aset(f"async_key_{i}", f"async_value_{i}"))
                    await asyncio.gather(*tasks)
                    
                    # 一括読み取り
                    tasks = []
                    for i in range(n):
                        tasks.append(db.aget(f"async_key_{i}"))
                    values = await asyncio.gather(*tasks)
                    return values
            
            start = time.perf_counter()
            values = await async_bulk_ops(200)
            end = time.perf_counter()
            
            print(f"\n非同期一括操作 (200 items): {end-start:.4f}s")
            
            # 値が正しく設定されていることを確認
            assert len(values) == 200
            assert all(v == f"async_value_{i}" for i, v in enumerate(values))
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    async def test_concurrent_access(self):
        """並行アクセスのテスト"""
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
            
        try:
            async def worker(worker_id, n_ops=100):
                """ワーカータスク"""
                async with AsyncDictSQLiteFastest(db_path) as db:
                    for i in range(n_ops):
                        key = f"worker_{worker_id}_key_{i}"
                        value = f"worker_{worker_id}_value_{i}"
                        await db.aset(key, value)
                        retrieved = await db.aget(key)
                        assert retrieved == value
            
            # 複数のワーカーを並行実行
            start = time.perf_counter()
            await asyncio.gather(*[worker(i, 50) for i in range(4)])
            end = time.perf_counter()
            
            print(f"\n並行アクセス (4 workers, 50 ops each): {end-start:.4f}s")
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


def test_feature_compatibility(tmp_db_paths):
    """機能互換性のテスト"""
    
    # 両方で同じデータを保存
    test_data = {
        "string": "hello",
        "number": 42,
        "float": 3.14,
        "bool": True,
        "none": None,
        "list": [1, 2, 3],
        "dict": {"nested": "value"},
        "set": {1, 2, 3}
    }
    
    # Original DictSQLite
    with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
        for key, value in test_data.items():
            db_orig[key] = value
    
    # DictSQLite-Fastest
    with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
        for key, value in test_data.items():
            db_fast[key] = value
    
    # 読み戻して比較
    with DictSQLite(str(tmp_db_paths['original'])) as db_orig:
        with DictSQLiteFastest(str(tmp_db_paths['fastest'])) as db_fast:
            for key, expected_value in test_data.items():
                orig_value = db_orig[key]
                fast_value = db_fast[key]
                
                if isinstance(expected_value, set):
                    # セットは順序が不定なので別途比較
                    assert isinstance(orig_value, set)
                    assert isinstance(fast_value, set)
                    assert orig_value == fast_value == expected_value
                else:
                    assert orig_value == fast_value == expected_value
    
    print("\n機能互換性: ✓ 全データタイプで互換性確認")


def test_storage_mode_compatibility(tmp_db_paths):
    """ストレージモード互換性テスト"""
    
    # JSON mode testing
    test_data = {
        "json_string": "hello", 
        "json_number": 123,
        "json_list": [1, 2, 3],
        "json_dict": {"a": 1, "b": 2},
        "json_set": {1, 2, 3}
    }
    
    # Original in JSON mode
    with DictSQLite(str(tmp_db_paths['original']), storage_mode='json') as db_orig:
        for key, value in test_data.items():
            db_orig[key] = value
    
    # Fastest in JSON mode  
    with DictSQLiteFastest(str(tmp_db_paths['fastest']), storage_mode='json') as db_fast:
        for key, value in test_data.items():
            db_fast[key] = value
    
    # 検証
    with DictSQLite(str(tmp_db_paths['original']), storage_mode='json') as db_orig:
        with DictSQLiteFastest(str(tmp_db_paths['fastest']), storage_mode='json') as db_fast:
            for key, expected_value in test_data.items():
                orig_value = db_orig[key]
                fast_value = db_fast[key]
                
                if isinstance(expected_value, set):
                    assert orig_value == fast_value == expected_value
                else:
                    assert orig_value == fast_value == expected_value
    
    print("\nストレージモード互換性: ✓ JSONモードで互換性確認")