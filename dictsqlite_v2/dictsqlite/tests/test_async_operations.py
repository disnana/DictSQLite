#!/usr/bin/env python3
"""
非同期操作テスト - DictSQLite v4.2

このテストスイートは非同期機能を網羅的にテストします：
- 基本的な非同期CRUD操作
- 非同期バッチ操作
- 並行非同期操作
- 異なるストレージモードでの非同期操作
- 非同期エラーハンドリング
- 同期APIとの互換性
"""

import pytest
import asyncio
from .conftest import windows_safe_temp_db

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import AsyncDictSQLite
    ASYNC_DICTSQLITE_AVAILABLE = True
except ImportError:
    ASYNC_DICTSQLITE_AVAILABLE = False
    AsyncDictSQLite = None


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncBasicCRUD:
    """非同期基本CRUD操作のテスト"""
    
    async def test_async_create_and_read(self):
        """非同期での作成と読み取り"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 非同期で書き込み
                await db.aset("key1", b"value1")
                
                # 非同期で読み取り
                value = await db.aget("key1")
                assert value == b"value1"
    
    async def test_async_update(self):
        """非同期での更新"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 初期値
                await db.aset("key1", b"initial")
                assert await db.aget("key1") == b"initial"
                
                # 更新
                await db.aset("key1", b"updated")
                assert await db.aget("key1") == b"updated"
    
    async def test_async_delete(self):
        """非同期での削除"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # データを追加
                await db.aset("key1", b"value1")
                assert await db.acontains("key1") is True
                
                # 削除
                await db.adelete("key1")
                assert await db.acontains("key1") is False
    
    async def test_async_contains(self):
        """非同期でのcontainsチェック"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 存在しないキー
                assert await db.acontains("nonexistent") is False
                
                # キーを追加
                await db.aset("exists", b"value")
                assert await db.acontains("exists") is True
                
                # 削除
                await db.adelete("exists")
                assert await db.acontains("exists") is False


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncBatchOperations:
    """非同期バッチ操作のテスト"""
    
    async def test_async_bulk_set(self):
        """非同期一括設定"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 複数のキーを非同期で設定
                items = {
                    "key1": b"value1",
                    "key2": b"value2",
                    "key3": b"value3",
                }
                
                # 一括設定（メソッドがあれば）
                for k, v in items.items():
                    await db.aset(k, v)
                
                # すべて読み取れることを確認
                for k, v in items.items():
                    assert await db.aget(k) == v
    
    async def test_async_bulk_get(self):
        """非同期一括取得"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # データを準備
                for i in range(10):
                    await db.aset(f"key{i}", f"value{i}".encode())
                
                # 一括取得
                results = []
                for i in range(10):
                    value = await db.aget(f"key{i}")
                    results.append(value)
                
                # すべて正しく取得できている
                for i in range(10):
                    assert results[i] == f"value{i}".encode()
    
    async def test_async_sequential_operations(self):
        """非同期順次操作"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 順次操作
                await db.aset("step1", b"data1")
                await db.aset("step2", b"data2")
                await db.aset("step3", b"data3")
                
                # 順次読み取り
                assert await db.aget("step1") == b"data1"
                assert await db.aget("step2") == b"data2"
                assert await db.aget("step3") == b"data3"


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncConcurrentOperations:
    """非同期並行操作のテスト"""
    
    async def test_concurrent_async_writes(self):
        """並行非同期書き込み"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 100個の並行書き込み
                write_tasks = [
                    db.aset(f"concurrent_key_{i}", f"concurrent_value_{i}".encode())
                    for i in range(100)
                ]
                
                await asyncio.gather(*write_tasks)
                
                # すべて書き込まれている
                for i in range(100):
                    value = await db.aget(f"concurrent_key_{i}")
                    assert value == f"concurrent_value_{i}".encode()
    
    async def test_concurrent_async_reads(self):
        """並行非同期読み取り"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # データを準備
                for i in range(100):
                    await db.aset(f"key_{i}", f"value_{i}".encode())
                
                # 100個の並行読み取り
                read_tasks = [
                    db.aget(f"key_{i}")
                    for i in range(100)
                ]
                
                results = await asyncio.gather(*read_tasks)
                
                # すべて正しく読み取れている
                for i in range(100):
                    assert results[i] == f"value_{i}".encode()
    
    async def test_concurrent_mixed_operations(self):
        """並行混合操作（読み書き混在）"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 初期データ
                for i in range(50):
                    await db.aset(f"key_{i}", f"initial_{i}".encode())
                
                # 混合操作: 読み取り、書き込み、更新を並行実行
                tasks = []
                
                # 読み取りタスク
                for i in range(25):
                    tasks.append(db.aget(f"key_{i}"))
                
                # 書き込みタスク（新しいキー）
                for i in range(50, 75):
                    tasks.append(db.aset(f"key_{i}", f"new_{i}".encode()))
                
                # 更新タスク（既存キー）
                for i in range(25, 50):
                    tasks.append(db.aset(f"key_{i}", f"updated_{i}".encode()))
                
                await asyncio.gather(*tasks)
                
                # 検証
                # 古いデータ（更新されていない）
                for i in range(25):
                    value = await db.aget(f"key_{i}")
                    assert value == f"initial_{i}".encode()
                
                # 更新されたデータ
                for i in range(25, 50):
                    value = await db.aget(f"key_{i}")
                    assert value == f"updated_{i}".encode()
                
                # 新しいデータ
                for i in range(50, 75):
                    value = await db.aget(f"key_{i}")
                    assert value == f"new_{i}".encode()
    
    async def test_high_concurrency(self):
        """高い並行度のテスト"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, capacity=10000, storage_mode="bytes") as db:
                # 1000個の並行操作
                tasks = [
                    db.aset(f"high_concurrency_{i}", f"value_{i}".encode())
                    for i in range(1000)
                ]
                
                await asyncio.gather(*tasks)
                
                # ランダムにいくつか確認
                assert await db.aget("high_concurrency_0") == b"value_0"
                assert await db.aget("high_concurrency_500") == b"value_500"
                assert await db.aget("high_concurrency_999") == b"value_999"


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncWithStorageModes:
    """各ストレージモードでの非同期操作"""
    
    async def test_async_with_bytes_mode(self):
        """Bytesモードでの非同期操作"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                await db.aset("bytes_key", b"bytes_value")
                value = await db.aget("bytes_key")
                assert value == b"bytes_value"
    
    async def test_async_with_pickle_mode(self):
        """Pickleモードでの非同期操作"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="pickle") as db:
                test_dict = {"name": "Alice", "age": 30}
                await db.aset("pickle_key", test_dict)
                value = await db.aget("pickle_key")
                assert value == test_dict
    
    async def test_async_with_jsonb_mode(self):
        """JSONBモードでの非同期操作"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="jsonb") as db:
                test_data = {"user": "Bob", "scores": [90, 85, 92]}
                await db.aset("jsonb_key", test_data)
                value = await db.aget("jsonb_key")
                assert value == test_data
    
    async def test_async_mode_specific_data(self):
        """各モードで固有のデータタイプ"""
        # Pickleモード: セット
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="pickle") as db:
                test_set = {1, 2, 3, 4, 5}
                await db.aset("set_data", test_set)
                value = await db.aget("set_data")
                assert value == test_set
        
        # JSONBモード: ネストされた構造
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="jsonb") as db:
                nested = {
                    "level1": {
                        "level2": {
                            "level3": "deep_value"
                        }
                    }
                }
                await db.aset("nested", nested)
                value = await db.aget("nested")
                assert value == nested


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncPersistence:
    """非同期での永続化テスト"""
    
    async def test_async_data_persists(self):
        """非同期で書き込んだデータの永続化"""
        with windows_safe_temp_db() as db_path:
            # 非同期で書き込み
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                await db.aset("persist_key", b"persist_value")
            
            # 同期で読み取り（互換性テスト）
            from dictsqlite import DictSQLiteV4
            if DictSQLiteV4 is not None:
                db_sync = DictSQLiteV4(db_path, storage_mode="bytes")
                assert db_sync["persist_key"] == b"persist_value"
                db_sync.close()
    
    async def test_async_flush(self):
        """非同期flushのテスト"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, persist_mode="lazy", storage_mode="bytes") as db:
                await db.aset("key1", b"value1")
                await db.aflush()
                
                # flush後は永続化されている
                # 別インスタンスで確認
                from dictsqlite import DictSQLiteV4
                if DictSQLiteV4 is not None:
                    db2 = DictSQLiteV4(db_path, storage_mode="bytes")
                    assert db2["key1"] == b"value1"
                    db2.close()


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncErrorHandling:
    """非同期エラーハンドリングのテスト"""
    
    async def test_async_keyerror_on_missing_key(self):
        """存在しないキーへの非同期アクセスでKeyError"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                with pytest.raises(KeyError):
                    await db.aget("nonexistent_key")
    
    async def test_async_delete_missing_key(self):
        """存在しないキーの非同期削除でKeyError"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                with pytest.raises(KeyError):
                    await db.adelete("nonexistent_key")
    
    async def test_async_operation_after_close(self):
        """close後の非同期操作でエラー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            await db.aset("key1", b"value1")
            await db.aclose()
            
            # close後の操作はエラー
            with pytest.raises((RuntimeError, ValueError)):
                await db.aget("key1")


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncBackwardCompatibility:
    """同期メソッドとの互換性テスト"""
    
    async def test_sync_methods_on_async_instance(self):
        """AsyncDictSQLiteで同期メソッドも使える"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 同期メソッド
                db.set("sync_key", b"sync_value")
                value = db.get("sync_key")
                assert value == b"sync_value"
                
                # 非同期メソッド
                await db.aset("async_key", b"async_value")
                async_value = await db.aget("async_key")
                assert async_value == b"async_value"
    
    async def test_mixed_sync_async_operations(self):
        """同期と非同期操作の混在"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                # 同期で書き込み
                db.set("key1", b"value1")
                
                # 非同期で読み取り
                value = await db.aget("key1")
                assert value == b"value1"
                
                # 非同期で書き込み
                await db.aset("key2", b"value2")
                
                # 同期で読み取り
                value = db.get("key2")
                assert value == b"value2"


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncContextManager:
    """非同期コンテキストマネージャーのテスト"""
    
    async def test_async_with_statement(self):
        """async with文でのテスト"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                await db.aset("key1", b"value1")
                value = await db.aget("key1")
                assert value == b"value1"
            
            # with文を抜けた後も永続化されている
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                value = await db.aget("key1")
                assert value == b"value1"
    
    async def test_async_exception_in_context(self):
        """非同期コンテキスト内で例外が発生"""
        with windows_safe_temp_db() as db_path:
            try:
                async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                    await db.aset("key1", b"value1")
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # 例外が発生してもデータは保存される
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                value = await db.aget("key1")
                assert value == b"value1"


@pytest.mark.skipif(not ASYNC_DICTSQLITE_AVAILABLE, reason="AsyncDictSQLite module not built")
@pytest.mark.asyncio
class TestAsyncPerformance:
    """非同期パフォーマンステスト"""
    
    async def test_async_throughput(self):
        """非同期スループット"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, capacity=10000, storage_mode="bytes") as db:
                # 10000個のアイテムを並行書き込み
                tasks = [
                    db.aset(f"throughput_key_{i}", f"value_{i}".encode())
                    for i in range(10000)
                ]
                
                import time
                start = time.time()
                await asyncio.gather(*tasks)
                elapsed = time.time() - start
                
                # パフォーマンス確認（参考値）
                ops_per_sec = 10000 / elapsed if elapsed > 0 else float('inf')
                print(f"\nAsync throughput: {ops_per_sec:.0f} ops/sec")
                
                # データが正しく保存されている
                value = await db.aget("throughput_key_5000")
                assert value == b"value_5000"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
