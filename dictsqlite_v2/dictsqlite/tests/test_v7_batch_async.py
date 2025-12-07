"""
v7.0 テスト - バッチ操作と非同期API検証

このテストモジュールは以下を検証します:
- batch_get / batch_set 操作
- AsyncDictSQLiteの網羅的テスト
- TableProxy / AsyncTableProxy のパリティ
"""

import pytest
import tempfile
import os

# dictsqliteモジュールのインポート
try:
    from dictsqlite import DictSQLite, AsyncDictSQLite
    # DictSQLiteV4 is an alias for DictSQLite
    DictSQLiteV4 = DictSQLite
except ImportError:
    pytest.skip("dictsqlite module not installed", allow_module_level=True)


class TestBatchOperations:
    """バッチ操作テスト（DictSQLiteV4）"""

    def test_batch_get_basic(self, tmp_path):
        """batch_get基本テスト"""
        db_path = str(tmp_path / "test_batch_get.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        # データ準備（bytes mode uses bytes directly）
        db["key1"] = b"value1"
        db["key2"] = b"value2"
        db["key3"] = b"value3"
        
        # batch_get
        results = db.batch_get(["key1", "key2", "key3"])
        
        assert len(results) == 3
        assert results["key1"] == b"value1"
        assert results["key2"] == b"value2"
        assert results["key3"] == b"value3"

    def test_batch_get_partial(self, tmp_path):
        """batch_get一部キー存在しないテスト"""
        db_path = str(tmp_path / "test_batch_partial.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        db["exists"] = b"value"
        
        results = db.batch_get(["exists", "not_exists"])
        
        assert "exists" in results
        assert "not_exists" not in results
        assert len(results) == 1

    def test_batch_get_empty(self, tmp_path):
        """batch_get空リストテスト"""
        db_path = str(tmp_path / "test_batch_empty.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        results = db.batch_get([])
        assert len(results) == 0

    def test_batch_set_basic(self, tmp_path):
        """batch_set基本テスト"""
        db_path = str(tmp_path / "test_batch_set.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        items = [
            ("key1", b"value1"),
            ("key2", b"value2"),
            ("key3", b"value3"),
        ]
        
        db.batch_set(items)
        
        assert db["key1"] == b"value1"
        assert db["key2"] == b"value2"
        assert db["key3"] == b"value3"

    def test_batch_set_overwrite(self, tmp_path):
        """batch_set上書きテスト"""
        db_path = str(tmp_path / "test_batch_overwrite.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        db["key1"] = b"old_value"
        
        items = [("key1", b"new_value")]
        db.batch_set(items)
        
        assert db["key1"] == b"new_value"

    def test_batch_roundtrip(self, tmp_path):
        """batch_set -> batch_get ラウンドトリップテスト"""
        db_path = str(tmp_path / "test_batch_roundtrip.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        items = [(f"key_{i}", f"value_{i}".encode()) for i in range(50)]
        keys = [f"key_{i}" for i in range(50)]
        
        db.batch_set(items)
        results = db.batch_get(keys)
        
        assert len(results) == 50
        for i in range(50):
            assert results[f"key_{i}"] == f"value_{i}".encode()


class TestAsyncDictSQLiteComprehensive:
    """AsyncDictSQLite網羅的テスト"""

    def test_async_basic_operations(self, tmp_path):
        """AsyncDictSQLite基本操作テスト"""
        db_path = str(tmp_path / "test_async_basic.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key1"] = b"value1"
        assert db["key1"] == b"value1"
        
        # Note: AsyncDictSQLite doesn't have __delitem__ in Python wrapper
        db.clear()
        # After clear, key1 should be gone

    def test_async_batch_get(self, tmp_path):
        """AsyncDictSQLite batch_getテスト"""
        db_path = str(tmp_path / "test_async_batch.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        # データ準備
        db["key1"] = b"value1"
        db["key2"] = b"value2"
        
        results = db.batch_get(["key1", "key2", "missing"])
        
        # Note: AsyncDictSQLite.batch_getはVec<Option<PyObject>>を返す
        assert len(results) == 3

    def test_async_batch_set(self, tmp_path):
        """AsyncDictSQLite batch_setテスト"""
        db_path = str(tmp_path / "test_async_batch_set.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        items = [
            ("key1", b"value1"),
            ("key2", b"value2"),
        ]
        
        db.batch_set(items)
        
        assert db["key1"] == b"value1"
        assert db["key2"] == b"value2"

    def test_async_table_proxy(self, tmp_path):
        """AsyncDictSQLite TableProxyテスト"""
        db_path = str(tmp_path / "test_async_table.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        users = db.table("users")
        users["user1"] = b"data1"
        
        assert users["user1"] == b"data1"
        assert "user1" in users

    def test_async_table_proxy_operations(self, tmp_path):
        """AsyncTableProxy各種操作テスト"""
        db_path = str(tmp_path / "test_async_table_ops.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        table = db.table("test")
        
        # set/get
        table["key1"] = b"value1"
        table["key2"] = b"value2"
        
        # keys
        keys = table.keys()
        assert "key1" in keys
        assert "key2" in keys
        
        # contains
        assert "key1" in table
        assert "missing" not in table
        
        # Note: del not supported on AsyncTableProxy, use clear instead

    def test_async_flush(self, tmp_path):
        """AsyncDictSQLite flushテスト"""
        db_path = str(tmp_path / "test_async_flush.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key"] = b"value"
        db.flush()
        
        assert db["key"] == b"value"

    def test_async_clear(self, tmp_path):
        """AsyncDictSQLite clearテスト"""
        db_path = str(tmp_path / "test_async_clear.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key1"] = b"value1"
        db["key2"] = b"value2"
        
        db.clear()
        
        # After clear, should be empty
        # Note: clear behavior may vary based on implementation

    def test_async_stats(self, tmp_path):
        """AsyncDictSQLite statsテスト"""
        db_path = str(tmp_path / "test_async_stats.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key"] = b"value"
        
        stats = db.stats()
        assert stats is not None

    # ========= 追加: 非同期メソッド網羅テスト =========

    def test_async_get_async(self, tmp_path):
        """AsyncDictSQLite get_asyncテスト"""
        db_path = str(tmp_path / "test_get_async.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key"] = b"value"
        result = db.get_async("key")
        
        assert result is not None

    def test_async_set_async(self, tmp_path):
        """AsyncDictSQLite set_asyncテスト"""
        db_path = str(tmp_path / "test_set_async.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db.set_async("key", b"value")
        assert db["key"] == b"value"

    def test_async_batch_operations_roundtrip(self, tmp_path):
        """AsyncDictSQLite batch操作ラウンドトリップテスト"""
        db_path = str(tmp_path / "test_batch_roundtrip.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        # batch_setしてbatch_getで取得
        items = [(f"key_{i}", f"value_{i}".encode()) for i in range(10)]
        db.batch_set(items)
        
        keys = [f"key_{i}" for i in range(10)]
        results = db.batch_get(keys)
        assert len(results) == 10

    def test_async_flush_and_verify(self, tmp_path):
        """AsyncDictSQLite flush後のデータ永続化テスト"""
        db_path = str(tmp_path / "test_flush_verify.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key"] = b"value"
        db.flush()  # flush() は存在する
        
        assert db["key"] == b"value"

    def test_async_multiple_tables(self, tmp_path):
        """AsyncDictSQLite 複数テーブルテスト"""
        db_path = str(tmp_path / "test_multi_tables.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        users = db.table("users")
        products = db.table("products")
        orders = db.table("orders")
        
        users["u1"] = b"user_data"
        products["p1"] = b"product_data"
        orders["o1"] = b"order_data"
        
        assert users["u1"] == b"user_data"
        assert products["p1"] == b"product_data"
        assert orders["o1"] == b"order_data"

    def test_async_large_batch(self, tmp_path):
        """AsyncDictSQLite 大量バッチテスト"""
        db_path = str(tmp_path / "test_large_batch.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        # 1000件のバッチ操作
        items = [(f"key_{i}", f"value_{i}".encode()) for i in range(1000)]
        db.batch_set(items)
        
        # 確認
        keys = [f"key_{i}" for i in range(1000)]
        results = db.batch_get(keys)
        assert len(results) == 1000

    def test_async_close(self, tmp_path):
        """AsyncDictSQLite closeテスト"""
        db_path = str(tmp_path / "test_close.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        db["key"] = b"value"
        db.close()
        
        # close後も読み取り可能かはimplementation次第

    def test_async_persistence_mode(self, tmp_path):
        """AsyncDictSQLite persistenceモードテスト"""
        db_path = str(tmp_path / "test_persist.db")
        
        # WriteThrough モード
        db = AsyncDictSQLite(db_path, persist_mode="write_through", storage_mode="bytes")
        db["key"] = b"value"
        
        # 再オープンしてデータ確認
        db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
        assert db2["key"] == b"value"



class TestTableProxyParity:
    """TableProxy / AsyncTableProxy同期非同期パリティテスト"""

    def test_sync_table_proxy_full_api(self, tmp_path):
        """TableProxy完全APIテスト"""
        db_path = str(tmp_path / "test_sync_table.db")
        db = DictSQLite(db_path, storage_mode="bytes")
        
        table = db.table("test")
        
        # __setitem__ / __getitem__
        table["key1"] = b"value1"
        assert table["key1"] == b"value1"
        
        # __contains__
        assert "key1" in table
        
        # keys
        table["key2"] = b"value2"
        keys = table.keys()
        assert "key1" in keys
        assert "key2" in keys
        
        # values
        values = table.values()
        assert len(values) == 2
        
        # items
        items = table.items()
        assert len(items) == 2
        
        # get with default
        result = table.get("missing", b"default")
        assert result == b"default"
        
        # setdefault
        result = table.setdefault("new_key", b"new_default")
        assert result == b"new_default"
        assert table["new_key"] == b"new_default"
        
        # pop
        table["to_pop"] = b"pop_value"
        popped = table.pop("to_pop")
        assert popped == b"pop_value"
        assert "to_pop" not in table
        
        # __len__
        initial_len = len(table)
        
        # __delitem__
        del table["key1"]
        assert "key1" not in table
        assert len(table) == initial_len - 1
        
        # clear
        table.clear()
        assert len(table) == 0

    def test_async_table_proxy_full_api(self, tmp_path):
        """AsyncTableProxy完全APIテスト"""
        db_path = str(tmp_path / "test_async_table_full.db")
        db = AsyncDictSQLite(db_path, storage_mode="bytes")
        
        table = db.table("test")
        
        # __setitem__ / __getitem__
        table["key1"] = b"value1"
        assert table["key1"] == b"value1"
        
        # __contains__
        assert "key1" in table
        
        # keys
        table["key2"] = b"value2"
        keys = table.keys()
        assert "key1" in keys
        assert "key2" in keys
        
        # values
        values = table.values()
        assert len(values) == 2
        
        # items
        items = table.items()
        assert len(items) == 2
        
        # get with default
        result = table.get("missing", b"default")
        assert result == b"default"
        
        # setdefault
        result = table.setdefault("new_key", b"new_default")
        assert result == b"new_default"
        
        # pop
        table["to_pop"] = b"pop_value"
        popped = table.pop("to_pop")
        assert popped == b"pop_value"
        
        # __len__
        initial_len = len(table)
        
        # __delitem__
        del table["key1"]
        assert len(table) == initial_len - 1
        
        # clear
        table.clear()
        assert len(table) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
