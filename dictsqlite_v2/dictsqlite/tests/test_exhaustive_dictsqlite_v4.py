#!/usr/bin/env python3
"""
網羅的テストスイート - DictSQLiteV4 全メソッドの詳細検証

このテストファイルは、DictSQLiteV4クラスの全メソッドを網羅的にテストし、
戻り値の型・値を厳密に検証します。

テスト対象:
- 初期化パラメータの全組み合わせ
- CRUD操作の詳細検証
- 辞書互換インターフェース
- stats()の全フィールド検証
- テーブル機能
- 永続化動作
"""

import pytest
import tempfile
import os
import sys
import pickle
import json
from typing import Any, Dict, List, Tuple

# テストユーティリティのインポート
from .conftest import windows_safe_temp_db, cleanup_db_files

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite, is_native_available, Modes
    DICTSQLITE_V4_AVAILABLE = is_native_available()
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None
    AsyncDictSQLite = None
    Modes = None


# =============================================================================
# セクション1: 初期化パラメータの網羅的テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestInitializationParameters:
    """初期化パラメータの全組み合わせテスト"""

    def test_default_initialization(self):
        """デフォルトパラメータでの初期化"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path)
            
            # 初期化が成功していることを確認
            assert db is not None
            assert len(db) == 0
            
            db.close()

    @pytest.mark.parametrize("storage_mode", ["pickle", "jsonb", "json", "bytes"])
    def test_storage_modes(self, storage_mode):
        """全ストレージモードでの初期化と動作確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode=storage_mode)
            
            # ストレージモードに応じたテスト値
            if storage_mode == "bytes":
                test_value = b"test_bytes_value"
            elif storage_mode in ("json", "jsonb"):
                test_value = {"key": "value", "number": 42}
            else:  # pickle
                test_value = {"complex": [1, 2, 3], "nested": {"a": "b"}}
            
            db["test_key"] = test_value
            retrieved = db["test_key"]
            
            # 戻り値の検証
            assert retrieved == test_value
            assert type(retrieved) == type(test_value)
            
            db.close()

    @pytest.mark.parametrize("persist_mode", ["memory", "lazy", "writethrough"])
    def test_persist_modes(self, persist_mode):
        """全永続化モードでの初期化と動作確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode=persist_mode, storage_mode="bytes")
            
            db["key1"] = b"value1"
            assert db["key1"] == b"value1"
            
            db.flush()
            db.close()

    @pytest.mark.parametrize("table_mode", ["prefix", "separate"])
    def test_table_modes(self, table_mode):
        """テーブルモードでの初期化と動作確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, table_mode=table_mode, storage_mode="bytes")
            
            # メインテーブルにデータを追加
            db["main_key"] = b"main_value"
            
            # サブテーブルを作成
            users = db.table("users")
            users["user1"] = b"user_data"
            
            # 検証
            assert db["main_key"] == b"main_value"
            assert users["user1"] == b"user_data"
            
            db.close()

    @pytest.mark.parametrize("hot_capacity", [1, 100, 10000, 1000000])
    def test_hot_capacity_values(self, hot_capacity):
        """様々なホットキャパシティ値でのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, hot_capacity=hot_capacity, storage_mode="bytes")
            
            # キャパシティ以上のデータを追加
            for i in range(min(hot_capacity + 10, 200)):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            # データが正しく保存されていることを確認
            assert len(db) == min(hot_capacity + 10, 200)
            
            db.close()

    @pytest.mark.parametrize("pool_size", [1, 5, 20, 50])
    def test_pool_size_values(self, pool_size):
        """様々なプールサイズでのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, pool_size=pool_size, storage_mode="bytes")
            
            db["test"] = b"value"
            assert db["test"] == b"value"
            
            db.close()

    @pytest.mark.parametrize("buffer_size", [1, 10, 100, 1000])
    def test_buffer_size_values(self, buffer_size):
        """様々なバッファサイズでのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path, 
                buffer_size=buffer_size, 
                persist_mode="lazy",
                storage_mode="bytes"
            )
            
            # バッファサイズ以上のデータを追加
            for i in range(buffer_size + 5):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            db.flush()
            assert len(db) == buffer_size + 5
            
            db.close()


# =============================================================================
# セクション2: __getitem__ / __setitem__ / __delitem__ / __contains__ / __len__
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDunderMethods:
    """ダンダーメソッドの詳細検証"""

    def test_getitem_return_type_bytes(self):
        """__getitem__の戻り値型検証（bytes）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            result = db["key"]
            
            # 型と値の厳密検証
            assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"
            assert result == b"value"
            
            db.close()

    def test_getitem_return_type_pickle(self):
        """__getitem__の戻り値型検証（pickle）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # 様々な型をテスト
            test_cases = [
                ("int_key", 42),
                ("float_key", 3.14159),
                ("str_key", "hello world"),
                ("list_key", [1, 2, 3, "four"]),
                ("dict_key", {"nested": {"deep": "value"}}),
                ("tuple_key", (1, 2, 3)),
                ("bool_key", True),
                ("none_key", None),
            ]
            
            for key, value in test_cases:
                db[key] = value
                result = db[key]
                
                assert result == value, f"Key {key}: expected {value}, got {result}"
                assert type(result) == type(value), f"Key {key}: expected {type(value)}, got {type(result)}"
            
            db.close()

    def test_getitem_return_type_jsonb(self):
        """__getitem__の戻り値型検証（jsonb）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            test_dict = {"name": "Alice", "age": 30, "active": True}
            db["user"] = test_dict
            result = db["user"]
            
            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
            assert result == test_dict
            assert result["name"] == "Alice"
            assert result["age"] == 30
            assert result["active"] is True
            
            db.close()

    def test_getitem_return_type_json(self):
        """__getitem__の戻り値型検証（json）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="json")
            
            test_list = [1, 2, 3, {"nested": "value"}]
            db["list_data"] = test_list
            result = db["list_data"]
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert result == test_list
            
            db.close()

    def test_getitem_keyerror(self):
        """存在しないキーでKeyErrorが発生することを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError) as exc_info:
                _ = db["nonexistent_key"]
            
            # KeyErrorの内容を検証
            assert "nonexistent_key" in str(exc_info.value) or exc_info.value is not None
            
            db.close()

    def test_setitem_overwrites_existing(self):
        """__setitem__が既存値を上書きすることを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"initial"
            assert db["key"] == b"initial"
            
            db["key"] = b"updated"
            assert db["key"] == b"updated"
            
            db["key"] = b"final"
            assert db["key"] == b"final"
            
            # 長さは変わらない
            assert len(db) == 1
            
            db.close()

    def test_delitem_removes_key(self):
        """__delitem__がキーを削除することを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["to_delete"] = b"value"
            assert "to_delete" in db
            assert len(db) == 1
            
            del db["to_delete"]
            
            assert "to_delete" not in db
            assert len(db) == 0
            
            with pytest.raises(KeyError):
                _ = db["to_delete"]
            
            db.close()

    def test_delitem_keyerror_on_missing(self):
        """存在しないキーの削除でKeyErrorが発生"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                del db["nonexistent"]
            
            db.close()

    def test_contains_returns_bool(self):
        """__contains__がboolを返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result_false = "key" in db
            assert isinstance(result_false, bool)
            assert result_false is False
            
            db["key"] = b"value"
            
            result_true = "key" in db
            assert isinstance(result_true, bool)
            assert result_true is True
            
            db.close()

    def test_len_returns_int(self):
        """__len__がintを返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = len(db)
            assert isinstance(result, int)
            assert result == 0
            
            db["key1"] = b"v1"
            db["key2"] = b"v2"
            db["key3"] = b"v3"
            
            result = len(db)
            assert isinstance(result, int)
            assert result == 3
            
            db.close()


# =============================================================================
# セクション3: get / keys / values / items メソッドの詳細検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAccessMethods:
    """アクセスメソッドの詳細検証"""

    def test_get_with_existing_key(self):
        """get()で存在するキーを取得"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            result = db.get("key")
            
            assert result == b"value"
            assert isinstance(result, bytes)
            
            db.close()

    def test_get_with_missing_key_returns_none(self):
        """get()で存在しないキーはNoneを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.get("nonexistent")
            
            assert result is None
            
            db.close()

    def test_get_with_default_value(self):
        """get()でデフォルト値を指定"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.get("nonexistent", b"default")
            
            assert result == b"default"
            assert isinstance(result, bytes)
            
            db.close()

    def test_get_does_not_raise_keyerror(self):
        """get()はKeyErrorを発生させない"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 例外が発生しないことを確認
            try:
                result = db.get("nonexistent")
                assert result is None
            except KeyError:
                pytest.fail("get() should not raise KeyError")
            
            db.close()

    def test_keys_returns_list(self):
        """keys()がリストを返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空の場合
            result = db.keys()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # データ追加後
            db["key1"] = b"v1"
            db["key2"] = b"v2"
            db["key3"] = b"v3"
            
            result = db.keys()
            assert isinstance(result, list)
            assert len(result) == 3
            
            # 全要素が文字列
            for key in result:
                assert isinstance(key, str)
            
            # 全キーが含まれている
            assert set(result) == {"key1", "key2", "key3"}
            
            db.close()

    def test_values_returns_list(self):
        """values()がリストを返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空の場合
            result = db.values()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # データ追加後
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            db["key3"] = b"value3"
            
            result = db.values()
            assert isinstance(result, list)
            assert len(result) == 3
            
            # 全値が含まれている
            assert set(result) == {b"value1", b"value2", b"value3"}
            
            db.close()

    def test_items_returns_list_of_tuples(self):
        """items()がタプルのリストを返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空の場合
            result = db.items()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # データ追加後
            expected = {
                "key1": b"value1",
                "key2": b"value2",
                "key3": b"value3",
            }
            
            for k, v in expected.items():
                db[k] = v
            
            result = db.items()
            assert isinstance(result, list)
            assert len(result) == 3
            
            # 各要素がタプル
            for item in result:
                assert isinstance(item, tuple)
                assert len(item) == 2
                key, value = item
                assert isinstance(key, str)
                assert key in expected
                assert value == expected[key]
            
            db.close()


# =============================================================================
# セクション4: update / pop / setdefault / clear メソッド
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMutationMethods:
    """データ変更メソッドの詳細検証"""

    def test_update_with_dict(self):
        """update()で辞書から更新"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 初期データ
            db["existing"] = b"old"
            
            # update
            update_data = {
                "new1": b"v1",
                "new2": b"v2",
                "existing": b"new",  # 上書き
            }
            db.update(update_data)
            
            # 検証
            assert db["new1"] == b"v1"
            assert db["new2"] == b"v2"
            assert db["existing"] == b"new"
            assert len(db) == 3
            
            db.close()

    def test_update_with_kwargs(self):
        """update()でkwargsから更新"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db.update(key1=b"v1", key2=b"v2")
            
            assert db["key1"] == b"v1"
            assert db["key2"] == b"v2"
            
            db.close()

    def test_pop_existing_key(self):
        """pop()で存在するキーを取得・削除"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            result = db.pop("key")
            
            assert result == b"value"
            assert "key" not in db
            assert len(db) == 0
            
            db.close()

    def test_pop_missing_key_with_default(self):
        """pop()で存在しないキー（デフォルト値付き）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.pop("nonexistent", b"default")
            
            assert result == b"default"
            
            db.close()

    def test_pop_missing_key_raises_keyerror(self):
        """pop()で存在しないキー（デフォルト値なし）はKeyError"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                db.pop("nonexistent")
            
            db.close()

    def test_setdefault_existing_key(self):
        """setdefault()で存在するキーは既存値を返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"existing"
            result = db.setdefault("key", b"default")
            
            assert result == b"existing"
            assert db["key"] == b"existing"
            
            db.close()

    def test_setdefault_missing_key(self):
        """setdefault()で存在しないキーはデフォルト値を設定・返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.setdefault("key", b"default")
            
            assert result == b"default"
            assert db["key"] == b"default"
            assert "key" in db
            
            db.close()

    def test_clear_removes_all(self):
        """clear()で全データを削除"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # データ追加
            for i in range(100):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            assert len(db) == 100
            
            # クリア
            db.clear()
            
            assert len(db) == 0
            assert list(db.keys()) == []
            
            # 全キーが存在しない
            for i in range(100):
                assert f"key_{i}" not in db
            
            db.close()


# =============================================================================
# セクション5: stats() メソッドの詳細検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStatsMethod:
    """stats()メソッドの詳細検証"""

    def test_stats_returns_dict(self):
        """stats()が辞書を返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            assert isinstance(result, dict)
            
            db.close()

    def test_stats_contains_expected_keys(self):
        """stats()が期待されるキーを含むことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # いくつかのデータを追加
            for i in range(10):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            result = db.stats()
            
            # 必須キーの存在確認 (実際のAPI: hot_tier_size, hot_tier_capacity)
            expected_keys = ["hot_tier_size", "hot_tier_capacity", "num_shards"]
            for key in expected_keys:
                assert key in result, f"Expected key '{key}' not in stats: {result}"
            
            db.close()

    def test_stats_values_are_correct_types(self):
        """stats()の各値が正しい型であることを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            # 数値型のキー
            numeric_keys = ["hot_tier_size", "hot_tier_capacity", "num_shards"]
            for key in numeric_keys:
                if key in result:
                    assert isinstance(result[key], int), f"stats['{key}'] should be int, got {type(result[key])}"
            
            db.close()

    def test_stats_reflects_data_changes(self):
        """stats()がデータ変更を反映することを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            initial_stats = db.stats()
            initial_size = initial_stats.get("hot_tier_size", 0)
            
            # データ追加
            for i in range(50):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            after_insert_stats = db.stats()
            after_insert_size = after_insert_stats.get("hot_tier_size", 0)
            
            assert after_insert_size >= initial_size
            
            db.close()


# =============================================================================
# セクション6: テーブル機能の詳細検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestTableFunctionality:
    """テーブル機能の詳細検証"""

    def test_table_returns_proxy(self):
        """table()がTableProxyを返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            users = db.table("users")
            
            # オブジェクトが返されることを確認
            assert users is not None
            
            db.close()

    def test_table_isolation_prefix_mode(self):
        """prefixモードでのテーブル分離"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, table_mode="prefix", storage_mode="bytes")
            
            users = db.table("users")
            products = db.table("products")
            
            users["user1"] = b"alice"
            products["prod1"] = b"laptop"
            
            # 各テーブルが独立
            assert users["user1"] == b"alice"
            assert products["prod1"] == b"laptop"
            
            # 相互に影響しない
            assert "prod1" not in users
            assert "user1" not in products
            
            db.close()

    def test_table_isolation_separate_mode(self):
        """separateモードでのテーブル分離"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, table_mode="separate", storage_mode="bytes")
            
            users = db.table("users")
            products = db.table("products")
            
            users["user1"] = b"alice"
            products["prod1"] = b"laptop"
            
            # 各テーブルが独立
            assert users["user1"] == b"alice"
            assert products["prod1"] == b"laptop"
            
            db.close()

    def test_multiple_tables_work_independently(self):
        """複数テーブルが独立して動作することを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, table_mode="prefix", storage_mode="bytes")
            
            # 複数のテーブルを使用
            users = db.table("users")
            products = db.table("products")
            orders = db.table("orders")
            
            users["u1"] = b"user"
            products["p1"] = b"product"
            orders["o1"] = b"order"
            
            # 各テーブルが独立して動作
            assert users["u1"] == b"user"
            assert products["p1"] == b"product"
            assert orders["o1"] == b"order"
            
            # 相互に影響しない
            assert "p1" not in users
            assert "o1" not in users
            assert "u1" not in products
            
            db.close()


# =============================================================================
# セクション7: 永続化動作の検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPersistence:
    """永続化動作の詳細検証"""

    def test_flush_persists_data(self):
        """flush()がデータを永続化することを確認"""
        with windows_safe_temp_db() as db_path:
            # lazy modeで書き込み
            db1 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1.flush()
            db1.close()
            
            # 再度開いて確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            db2.close()

    def test_close_persists_data(self):
        """close()がデータを永続化することを確認"""
        with windows_safe_temp_db() as db_path:
            db1 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1.close()  # flush + close
            
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            db2.close()

    def test_writethrough_immediate_persistence(self):
        """writethroughモードで即時永続化されることを確認"""
        with windows_safe_temp_db() as db_path:
            db1 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            db1["key1"] = b"value1"
            # flush/closeなしでも永続化されている
            
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            
            db1.close()
            db2.close()

    def test_context_manager_persists_data(self):
        """コンテキストマネージャーがデータを永続化"""
        with windows_safe_temp_db() as db_path:
            with DictSQLiteV4(db_path, storage_mode="bytes") as db:
                db["key1"] = b"value1"
            
            with DictSQLiteV4(db_path, storage_mode="bytes") as db:
                assert db["key1"] == b"value1"


# =============================================================================
# セクション8: bulk_insert の詳細検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBulkInsert:
    """bulk_insert()メソッドの詳細検証"""

    def test_bulk_insert_dict(self):
        """bulk_insert()で辞書を一括挿入"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            data = {
                "key1": b"value1",
                "key2": b"value2",
                "key3": b"value3",
            }
            
            db.bulk_insert(data)
            
            assert len(db) == 3
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            assert db["key3"] == b"value3"
            
            db.close()

    def test_bulk_insert_list_of_tuples(self):
        """bulk_insert()でタプルのリストを一括挿入"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            data = [
                ("key1", b"value1"),
                ("key2", b"value2"),
                ("key3", b"value3"),
            ]
            
            db.bulk_insert(data)
            
            assert len(db) == 3
            assert db["key1"] == b"value1"
            
            db.close()

    def test_bulk_insert_large_dataset(self):
        """大量データのbulk_insert()"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            data = {f"key_{i}": f"value_{i}".encode() for i in range(1000)}
            
            db.bulk_insert(data)
            
            assert len(db) == 1000
            
            # サンプル検証
            assert db["key_0"] == b"value_0"
            assert db["key_500"] == b"value_500"
            assert db["key_999"] == b"value_999"
            
            db.close()


# =============================================================================
# セクション9: イテレータの詳細検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestIterator:
    """イテレータの詳細検証"""

    def test_iter_over_db(self):
        """for key in db形式のイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            expected_keys = {"key1", "key2", "key3"}
            for key in expected_keys:
                db[key] = f"value_{key}".encode()
            
            iterated_keys = set()
            for key in db:
                assert isinstance(key, str)
                iterated_keys.add(key)
            
            assert iterated_keys == expected_keys
            
            db.close()

    def test_iter_empty_db(self):
        """空のDBでのイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            count = 0
            for _ in db:
                count += 1
            
            assert count == 0
            
            db.close()

    def test_iter_is_consistent(self):
        """イテレーションの一貫性"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            for i in range(100):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            # 複数回イテレートして同じ結果を得る
            first_pass = set(db)
            second_pass = set(db)
            
            assert first_pass == second_pass
            assert len(first_pass) == 100
            
            db.close()


# =============================================================================
# セクション10: __eq__ / __repr__ の検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEqualityAndRepresentation:
    """等価性と文字列表現の検証"""

    def test_eq_with_dict(self):
        """辞書との等価性比較"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            expected = {"key1": b"value1", "key2": b"value2"}
            
            for k, v in expected.items():
                db[k] = v
            
            # 等価性チェック
            assert db == expected
            
            db.close()

    def test_eq_different_values(self):
        """異なる値との比較"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key1"] = b"value1"
            
            assert db != {"key1": b"different"}
            assert db != {"different_key": b"value1"}
            assert db != {}
            
            db.close()

    def test_repr_returns_string(self):
        """__repr__が文字列を返すことを確認"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key1"] = b"value1"
            
            result = repr(db)
            
            assert isinstance(result, str)
            
            db.close()


# =============================================================================
# セクション11: エラーハンドリングの検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestErrorHandling:
    """エラーハンドリングの検証"""

    def test_invalid_persist_mode_raises_error(self):
        """無効な永続化モードでエラー発生"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, persist_mode="invalid")

    def test_invalid_storage_mode_raises_error(self):
        """無効なストレージモードでエラー発生"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, storage_mode="invalid")

    def test_invalid_table_mode_raises_error(self):
        """無効なテーブルモードでエラー発生"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, table_mode="invalid")


# =============================================================================
# セクション12: 暗号化機能の検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEncryption:
    """暗号化機能の検証"""

    def test_encryption_enabled(self):
        """暗号化が有効な状態でのCRUD操作"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                encryption_password="secure_password_123",
                storage_mode="bytes"
            )
            
            db["secret"] = b"encrypted_value"
            assert db["secret"] == b"encrypted_value"
            
            db.close()

    def test_encrypted_data_persists(self):
        """暗号化されたデータの永続化"""
        with windows_safe_temp_db() as db_path:
            # 暗号化して保存
            db1 = DictSQLiteV4(
                db_path,
                encryption_password="secure_password_123",
                storage_mode="bytes"
            )
            db1["secret"] = b"my_secret_data"
            db1.close()
            
            # 同じパスワードで再度開く
            db2 = DictSQLiteV4(
                db_path,
                encryption_password="secure_password_123",
                storage_mode="bytes"
            )
            assert db2["secret"] == b"my_secret_data"
            db2.close()


# =============================================================================
# セクション13: Safe Pickle機能の検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSafePickle:
    """Safe Pickle機能の検証"""

    def test_safe_pickle_enabled(self):
        """Safe Pickleが有効な状態での操作"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                enable_safe_pickle=True,
                storage_mode="pickle"
            )
            
            # 安全なデータ型
            db["dict_data"] = {"key": "value"}
            db["list_data"] = [1, 2, 3]
            db["int_data"] = 42
            
            assert db["dict_data"] == {"key": "value"}
            assert db["list_data"] == [1, 2, 3]
            assert db["int_data"] == 42
            
            db.close()


# =============================================================================
# セクション14: Modesクラスの検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestModesClass:
    """Modesクラスの値検証"""

    def test_persistence_modes(self):
        """永続化モードの定数"""
        assert Modes.MEMORY == "memory"
        assert Modes.LAZY == "lazy"
        assert Modes.WRITETHROUGH == "writethrough"

    def test_storage_modes(self):
        """ストレージモードの定数"""
        assert Modes.PICKLE == "pickle"
        assert Modes.JSONB == "jsonb"
        assert Modes.BYTES == "bytes"
        assert Modes.JSON == "json"

    def test_table_modes(self):
        """テーブルモードの定数"""
        assert Modes.TABLE_PREFIX == "prefix"
        assert Modes.TABLE_SEPARATE == "separate"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
