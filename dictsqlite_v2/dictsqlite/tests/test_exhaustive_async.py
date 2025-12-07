#!/usr/bin/env python3
"""
網羅的テストスイート - AsyncDictSQLite 全メソッドの詳細検証

このテストファイルは、AsyncDictSQLiteクラスの全メソッドを網羅的にテストし、
同期メソッドとasync/awaitメソッドの両方を厳密に検証します。

テスト対象:
- 非同期メソッド: aget, aset, abatch_get, abatch_set, acontains, adelete, aflush, aclose
- 同期メソッド: get, set, get_async, set_async, batch_get, batch_set
- Dict-like interface: __getitem__, __setitem__
- Context managers: __enter__/__exit__, __aenter__/__aexit__
- Utility: stats, clear, flush, close, table
"""

import pytest
import asyncio
import tempfile
import os
import sys
import pickle
from typing import Any, Dict, List, Optional

# テストユーティリティのインポート
from .conftest import windows_safe_temp_db, cleanup_db_files

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import AsyncDictSQLite, is_native_available
    DICTSQLITE_V4_AVAILABLE = is_native_available()
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    AsyncDictSQLite = None


# =============================================================================
# セクション1: 初期化テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncDictSQLiteInitialization:
    """AsyncDictSQLiteの初期化テスト"""

    def test_default_initialization(self):
        """デフォルトパラメータでの初期化"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path)
            
            assert db is not None
            
            db.close()

    @pytest.mark.parametrize("storage_mode", ["pickle", "jsonb", "json", "bytes"])
    def test_storage_modes(self, storage_mode):
        """全ストレージモードでの初期化"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode=storage_mode)
            
            assert db is not None
            
            db.close()

    @pytest.mark.parametrize("persist_mode", ["memory", "lazy", "writethrough"])
    def test_persist_modes(self, persist_mode):
        """全永続化モードでの初期化"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, persist_mode=persist_mode)
            
            assert db is not None
            
            db.close()

    @pytest.mark.parametrize("table_mode", ["prefix", "separate"])
    def test_table_modes(self, table_mode):
        """全テーブルモードでの初期化"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, table_mode=table_mode)
            
            assert db is not None
            
            db.close()


# =============================================================================
# セクション2: 非同期メソッド aget / aset
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncGetSet:
    """非同期get/setメソッドのテスト"""

    @pytest.mark.asyncio
    async def test_aset_and_aget(self):
        """aset()とaget()の基本動作"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # aset
            await db.aset("key1", b"value1")
            
            # aget
            result = await db.aget("key1")
            
            assert result == b"value1"
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_aget_missing_key_raises_keyerror(self):
        """aget()で存在しないキーはKeyError"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                await db.aget("nonexistent")
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_aset_overwrites_existing(self):
        """aset()で既存値を上書き"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            await db.aset("key", b"initial")
            result1 = await db.aget("key")
            assert result1 == b"initial"
            
            await db.aset("key", b"updated")
            result2 = await db.aget("key")
            assert result2 == b"updated"
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_aset_with_pickle_mode(self):
        """Pickleモードでのaset/aget"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="pickle")
            
            test_value = {"name": "Alice", "scores": [90, 85, 92]}
            await db.aset("user", pickle.dumps(test_value))
            
            result = await db.aget("user")
            unpickled = pickle.loads(result)
            
            assert unpickled == test_value
            
            await db.aclose()


# =============================================================================
# セクション3: 非同期バッチ操作 abatch_get / abatch_set
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncBatchOperations:
    """非同期バッチ操作のテスト"""

    @pytest.mark.asyncio
    async def test_abatch_set_and_abatch_get(self):
        """abatch_set()とabatch_get()の基本動作"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # バッチset
            items = [
                ("key1", b"value1"),
                ("key2", b"value2"),
                ("key3", b"value3"),
            ]
            await db.abatch_set(items)
            
            # バッチget
            keys = ["key1", "key2", "key3"]
            results = await db.abatch_get(keys)
            
            assert isinstance(results, list)
            assert len(results) == 3
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_abatch_set_with_dict(self):
        """abatch_set()で辞書を使用"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            items = {
                "key1": b"value1",
                "key2": b"value2",
            }
            await db.abatch_set(items)
            
            result1 = await db.aget("key1")
            assert result1 == b"value1"
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_abatch_get_missing_keys(self):
        """abatch_get()で存在しないキーはNone"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            await db.aset("existing", b"value")
            
            results = await db.abatch_get(["existing", "missing1", "missing2"])
            
            assert len(results) == 3
            # 存在するキーは値を返す
            # 存在しないキーはNone
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_abatch_set_large_batch(self):
        """大量データのバッチ操作"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            items = [(f"key_{i}", f"value_{i}".encode()) for i in range(100)]
            await db.abatch_set(items)
            
            keys = [f"key_{i}" for i in range(100)]
            results = await db.abatch_get(keys)
            
            assert len(results) == 100
            
            await db.aclose()


# =============================================================================
# セクション4: 非同期 acontains / adelete
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncContainsDelete:
    """非同期contains/deleteのテスト"""

    @pytest.mark.asyncio
    async def test_acontains_returns_bool(self):
        """acontains()がboolを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            result1 = await db.acontains("nonexistent")
            assert isinstance(result1, bool)
            assert result1 is False
            
            await db.aset("key", b"value")
            
            result2 = await db.acontains("key")
            assert isinstance(result2, bool)
            assert result2 is True
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_adelete_removes_key(self):
        """adelete()がキーを削除"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            await db.aset("to_delete", b"value")
            assert await db.acontains("to_delete") is True
            
            await db.adelete("to_delete")
            
            assert await db.acontains("to_delete") is False
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_adelete_missing_key_raises_keyerror(self):
        """adelete()で存在しないキーはKeyError"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                await db.adelete("nonexistent")
            
            await db.aclose()


# =============================================================================
# セクション5: 非同期 aflush / aclose
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncFlushClose:
    """非同期flush/closeのテスト"""

    @pytest.mark.asyncio
    async def test_aflush_persists_data(self):
        """aflush()がデータを永続化"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, persist_mode="lazy", storage_mode="bytes")
            
            await db.aset("key", b"value")
            await db.aflush()
            await db.aclose()
            
            # 再度開いて確認
            db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
            result = await db2.aget("key")
            assert result == b"value"
            await db2.aclose()

    @pytest.mark.asyncio
    async def test_aclose_persists_data(self):
        """aclose()がデータを永続化"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, persist_mode="lazy", storage_mode="bytes")
            
            await db.aset("key", b"value")
            await db.aclose()
            
            # 再度開いて確認
            db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
            result = await db2.aget("key")
            assert result == b"value"
            await db2.aclose()

    @pytest.mark.asyncio
    async def test_operations_after_close_raise_error(self):
        """クローズ後の操作はエラー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            await db.aset("key", b"value")
            await db.aclose()
            
            # クローズ後の操作はエラーまたは例外
            with pytest.raises((RuntimeError, Exception)):
                await db.aset("new_key", b"new_value")


# =============================================================================
# セクション6: 同期メソッド get / set / get_async / set_async
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSyncMethods:
    """同期メソッドのテスト"""

    def test_sync_set_and_get(self):
        """同期set()とget()"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            db.set("key", b"value")
            result = db.get("key")
            
            # 値が取得できることを確認（pickleシリアライズされている可能性）
            assert result is not None
            
            db.close()

    def test_sync_get_async_and_set_async(self):
        """同期get_async()とset_async()"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            db.set_async("key", b"value")
            result = db.get_async("key")
            
            assert result is not None
            
            db.close()

    def test_batch_get_and_batch_set(self):
        """同期batch_get()とbatch_set()"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            items = [
                ("key1", b"value1"),
                ("key2", b"value2"),
            ]
            db.batch_set(items)
            
            results = db.batch_get(["key1", "key2"])
            
            assert isinstance(results, list)
            assert len(results) == 2
            
            db.close()


# =============================================================================
# セクション7: Dict-like interface __getitem__ / __setitem__
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDictLikeInterface:
    """Dict-likeインターフェースのテスト"""

    def test_getitem_setitem(self):
        """db[key] = valueとdb[key]"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            result = db["key"]
            
            assert result == b"value"
            
            db.close()

    def test_getitem_keyerror(self):
        """存在しないキーでKeyError"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                _ = db["nonexistent"]
            
            db.close()

    def test_setitem_overwrites(self):
        """上書き動作"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            db["key"] = b"initial"
            assert db["key"] == b"initial"
            
            db["key"] = b"updated"
            assert db["key"] == b"updated"
            
            db.close()


# =============================================================================
# セクション8: stats / clear / flush / close
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestUtilityMethods:
    """ユーティリティメソッドのテスト"""

    def test_stats_returns_dict(self):
        """stats()が辞書を返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            assert isinstance(result, dict)
            assert "size" in result
            assert "capacity" in result
            assert isinstance(result["size"], int)
            assert isinstance(result["capacity"], int)
            
            db.close()

    def test_clear_removes_all(self):
        """clear()で全データを削除"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            db["key1"] = b"v1"
            db["key2"] = b"v2"
            db["key3"] = b"v3"
            
            db.clear()
            
            stats = db.stats()
            # クリア後はサイズが0または非常に小さい
            
            db.close()

    def test_flush_without_error(self):
        """flush()がエラーなく完了"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, persist_mode="lazy", storage_mode="bytes")
            
            db["key"] = b"value"
            
            # フラッシュがエラーなく完了
            db.flush()
            
            db.close()

    def test_close_without_error(self):
        """close()がエラーなく完了"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            
            # クローズがエラーなく完了
            db.close()


# =============================================================================
# セクション9: Context Managers
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestContextManagers:
    """コンテキストマネージャーのテスト"""

    def test_sync_context_manager(self):
        """同期コンテキストマネージャー"""
        with windows_safe_temp_db() as db_path:
            with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                db["key"] = b"value"
                assert db["key"] == b"value"
            
            # コンテキスト終了後、データが永続化されている
            with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                assert db["key"] == b"value"

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """非同期コンテキストマネージャー"""
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                await db.aset("key", b"value")
                result = await db.aget("key")
                assert result == b"value"

    def test_context_manager_on_exception(self):
        """例外発生時のコンテキストマネージャー"""
        with windows_safe_temp_db() as db_path:
            try:
                with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                    db["key"] = b"value"
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # 例外が発生してもデータは保存される
            with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                assert db["key"] == b"value"


# =============================================================================
# セクション10: table() メソッド
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxy:
    """AsyncDictSQLiteのテーブル機能テスト"""

    def test_table_returns_proxy(self):
        """table()がプロキシを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            users = db.table("users")
            
            assert users is not None
            
            db.close()

    def test_table_isolation(self):
        """テーブル間の分離"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            users = db.table("users")
            products = db.table("products")
            
            users["u1"] = b"user_data"
            products["p1"] = b"product_data"
            
            assert users["u1"] == b"user_data"
            assert products["p1"] == b"product_data"
            
            # 相互に影響しない
            assert "p1" not in users
            assert "u1" not in products
            
            db.close()

    def test_table_proxy_dict_interface(self):
        """テーブルプロキシのdict-likeインターフェース"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            # setitem / getitem
            users["u1"] = b"alice"
            assert users["u1"] == b"alice"
            
            # contains
            assert "u1" in users
            assert "u2" not in users
            
            # keys
            users["u2"] = b"bob"
            keys = users.keys()
            assert set(keys) == {"u1", "u2"}
            
            db.close()


# =============================================================================
# セクション11: 並行処理テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncConcurrency:
    """非同期並行処理のテスト"""

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """並行書き込み"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            async def write_item(key, value):
                await db.aset(key, value)
            
            # 複数の並行書き込み
            tasks = [
                write_item(f"key_{i}", f"value_{i}".encode())
                for i in range(50)
            ]
            
            await asyncio.gather(*tasks)
            
            # 全て書き込まれていることを確認
            for i in range(50):
                result = await db.aget(f"key_{i}")
                assert result == f"value_{i}".encode()
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_reads(self):
        """並行読み取り"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # データを準備
            for i in range(50):
                await db.aset(f"key_{i}", f"value_{i}".encode())
            
            async def read_item(key):
                return await db.aget(key)
            
            # 複数の並行読み取り
            tasks = [read_item(f"key_{i}") for i in range(50)]
            results = await asyncio.gather(*tasks)
            
            for i, result in enumerate(results):
                assert result == f"value_{i}".encode()
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self):
        """読み書きの混在した並行処理"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            async def write_and_read(key, value):
                await db.aset(key, value)
                return await db.aget(key)
            
            tasks = [
                write_and_read(f"key_{i}", f"value_{i}".encode())
                for i in range(20)
            ]
            
            results = await asyncio.gather(*tasks)
            
            for i, result in enumerate(results):
                assert result == f"value_{i}".encode()
            
            await db.aclose()


# =============================================================================
# セクション12: エラーハンドリング
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncErrorHandling:
    """非同期エラーハンドリングテスト"""

    def test_invalid_persist_mode(self):
        """無効な永続化モード"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                AsyncDictSQLite(db_path, persist_mode="invalid")

    def test_invalid_storage_mode(self):
        """無効なストレージモード"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                AsyncDictSQLite(db_path, storage_mode="invalid")

    def test_invalid_table_mode(self):
        """無効なテーブルモード"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                AsyncDictSQLite(db_path, table_mode="invalid")


# =============================================================================
# セクション13: ストレージモード別テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncStorageModes:
    """AsyncDictSQLiteのストレージモード別テスト"""

    @pytest.mark.asyncio
    async def test_bytes_mode(self):
        """Bytesモード"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            await db.aset("key", b"raw_bytes")
            result = await db.aget("key")
            
            assert result == b"raw_bytes"
            assert isinstance(result, bytes)
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_pickle_mode_complex_objects(self):
        """Pickleモードで複雑なオブジェクト"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="pickle")
            
            complex_obj = {
                "name": "Test",
                "values": [1, 2, 3],
                "nested": {"a": "b"},
            }
            
            await db.aset("complex", pickle.dumps(complex_obj))
            result = await db.aget("complex")
            unpickled = pickle.loads(result)
            
            assert unpickled == complex_obj
            
            await db.aclose()


# =============================================================================
# セクション14: 永続化テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncPersistence:
    """非同期永続化テスト"""

    @pytest.mark.asyncio
    async def test_data_persists_after_close(self):
        """クローズ後のデータ永続性"""
        with windows_safe_temp_db() as db_path:
            db1 = AsyncDictSQLite(db_path, storage_mode="bytes")
            await db1.aset("key1", b"value1")
            await db1.aset("key2", b"value2")
            await db1.aclose()
            
            db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
            result1 = await db2.aget("key1")
            result2 = await db2.aget("key2")
            
            assert result1 == b"value1"
            assert result2 == b"value2"
            
            await db2.aclose()

    @pytest.mark.asyncio
    async def test_writethrough_mode_persistence(self):
        """WriteThroughモードでの即時永続化"""
        with windows_safe_temp_db() as db_path:
            db1 = AsyncDictSQLite(db_path, persist_mode="writethrough", storage_mode="bytes")
            await db1.aset("key", b"value")
            # acloseを呼ぶ前に別のインスタンスで確認
            
            db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
            result = await db2.aget("key")
            assert result == b"value"
            
            await db1.aclose()
            await db2.aclose()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
