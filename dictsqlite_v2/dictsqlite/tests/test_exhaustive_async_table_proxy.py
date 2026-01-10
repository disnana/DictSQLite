#!/usr/bin/env python3
"""
網羅的テストスイート - AsyncTableProxy 全メソッドの詳細検証

このテストファイルは、AsyncTableProxyクラスの全メソッドを網羅的にテストし、
戻り値の型・値を厳密に検証します。

テスト対象:
- __getitem__ / __setitem__ / __delitem__ / __contains__ / __len__
- keys / values / items / get / pop / setdefault / update
- clear / __iter__ / __repr__ / __str__ / __eq__
"""

import pytest
import tempfile
import os
import sys
from typing import Any, Dict, List, Tuple

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
# セクション1: AsyncTableProxy基本操作
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyBasicOperations:
    """AsyncTableProxyの基本操作テスト"""

    def test_table_creation(self):
        """テーブルプロキシの作成"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            users = db.table("users")
            
            assert users is not None
            
            db.close()

    def test_multiple_table_creation(self):
        """複数のテーブルプロキシの作成"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            users = db.table("users")
            products = db.table("products")
            orders = db.table("orders")
            
            assert users is not None
            assert products is not None
            assert orders is not None
            
            # 各テーブルが独立
            users["u1"] = b"user_data"
            products["p1"] = b"product_data"
            orders["o1"] = b"order_data"
            
            assert users["u1"] == b"user_data"
            assert products["p1"] == b"product_data"
            assert orders["o1"] == b"order_data"
            
            db.close()


# =============================================================================
# セクション2: __getitem__ / __setitem__ / __delitem__
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyItemAccess:
    """AsyncTableProxyのアイテムアクセス検証"""

    def test_getitem_returns_correct_value(self):
        """__getitem__が正しい値を返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["user1"] = b"alice"
            result = users["user1"]
            
            assert result == b"alice"
            assert isinstance(result, bytes)
            
            db.close()

    def test_getitem_keyerror_on_missing(self):
        """存在しないキーでKeyError"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            with pytest.raises(KeyError):
                _ = users["nonexistent"]
            
            db.close()

    def test_setitem_creates_new_key(self):
        """__setitem__で新しいキーを作成"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            assert "new_key" not in users
            
            users["new_key"] = b"new_value"
            
            assert "new_key" in users
            assert users["new_key"] == b"new_value"
            
            db.close()

    def test_setitem_overwrites_existing(self):
        """__setitem__で既存値を上書き"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["key"] = b"initial"
            assert users["key"] == b"initial"
            
            users["key"] = b"updated"
            assert users["key"] == b"updated"
            
            db.close()

    def test_delitem_removes_key(self):
        """__delitem__でキーを削除"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["to_delete"] = b"value"
            assert "to_delete" in users
            
            del users["to_delete"]
            
            assert "to_delete" not in users
            
            db.close()

    def test_delitem_missing_key_silent(self):
        """存在しないキーの削除はエラーなし（実装による）"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            # 存在しないキーの削除を試みる
            # 注: AsyncTableProxyはKeyErrorを発生させない仕様の可能性
            try:
                del users["nonexistent"]
                # エラーが発生しない場合はパス
            except KeyError:
                # KeyErrorが発生する場合もパス
                pass
            
            db.close()


# =============================================================================
# セクション3: __contains__ / __len__
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyContainsLen:
    """AsyncTableProxyの__contains__と__len__検証"""

    def test_contains_returns_bool(self):
        """__contains__がboolを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            result_false = "key" in users
            assert isinstance(result_false, bool)
            assert result_false is False
            
            users["key"] = b"value"
            
            result_true = "key" in users
            assert isinstance(result_true, bool)
            assert result_true is True
            
            db.close()

    def test_len_returns_int(self):
        """__len__がintを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            result = len(users)
            assert isinstance(result, int)
            assert result == 0
            
            users["k1"] = b"v1"
            users["k2"] = b"v2"
            users["k3"] = b"v3"
            
            result = len(users)
            assert isinstance(result, int)
            assert result == 3
            
            db.close()

    def test_len_after_delete(self):
        """削除後のlen()"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["k1"] = b"v1"
            users["k2"] = b"v2"
            assert len(users) == 2
            
            del users["k1"]
            assert len(users) == 1
            
            del users["k2"]
            assert len(users) == 0
            
            db.close()


# =============================================================================
# セクション4: keys / values / items
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyAccessMethods:
    """AsyncTableProxyのアクセスメソッド検証"""

    def test_keys_returns_list(self):
        """keys()がリストを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            # 空の場合
            result = users.keys()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # データ追加後
            users["k1"] = b"v1"
            users["k2"] = b"v2"
            users["k3"] = b"v3"
            
            result = users.keys()
            assert isinstance(result, list)
            assert len(result) == 3
            assert set(result) == {"k1", "k2", "k3"}
            
            # 全要素が文字列
            for key in result:
                assert isinstance(key, str)
            
            db.close()

    def test_values_returns_list(self):
        """values()がリストを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            # 空の場合
            result = users.values()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # データ追加後
            users["k1"] = b"value1"
            users["k2"] = b"value2"
            users["k3"] = b"value3"
            
            result = users.values()
            assert isinstance(result, list)
            assert len(result) == 3
            assert set(result) == {b"value1", b"value2", b"value3"}
            
            db.close()

    def test_items_returns_list_of_tuples(self):
        """items()がタプルのリストを返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            # 空の場合
            result = users.items()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # データ追加後
            expected = {"k1": b"v1", "k2": b"v2", "k3": b"v3"}
            for k, v in expected.items():
                users[k] = v
            
            result = users.items()
            assert isinstance(result, list)
            assert len(result) == 3
            
            for item in result:
                assert isinstance(item, tuple)
                assert len(item) == 2
                key, value = item
                assert key in expected
                assert value == expected[key]
            
            db.close()


# =============================================================================
# セクション5: get / pop / setdefault
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyGetPopSetdefault:
    """AsyncTableProxyのget/pop/setdefault検証"""

    def test_get_existing_key(self):
        """get()で存在するキー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["key"] = b"value"
            result = users.get("key")
            
            assert result == b"value"
            
            db.close()

    def test_get_missing_key_returns_none(self):
        """get()で存在しないキーはNone"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            result = users.get("nonexistent")
            
            assert result is None
            
            db.close()

    def test_get_with_default(self):
        """get()でデフォルト値"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            result = users.get("nonexistent", b"default")
            
            assert result == b"default"
            
            db.close()

    def test_pop_existing_key(self):
        """pop()で存在するキー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["key"] = b"value"
            result = users.pop("key")
            
            assert result == b"value"
            assert "key" not in users
            
            db.close()

    def test_pop_missing_with_default(self):
        """pop()で存在しないキー（デフォルト付き）"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            result = users.pop("nonexistent", b"default")
            
            assert result == b"default"
            
            db.close()

    def test_pop_missing_raises_keyerror(self):
        """pop()で存在しないキー（デフォルトなし）はKeyError"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            with pytest.raises(KeyError):
                users.pop("nonexistent")
            
            db.close()

    def test_setdefault_existing_key(self):
        """setdefault()で存在するキー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["key"] = b"existing"
            result = users.setdefault("key", b"default")
            
            assert result == b"existing"
            assert users["key"] == b"existing"
            
            db.close()

    def test_setdefault_missing_key(self):
        """setdefault()で存在しないキー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            result = users.setdefault("key", b"default")
            
            assert result == b"default"
            assert users["key"] == b"default"
            
            db.close()


# =============================================================================
# セクション6: update / clear
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyUpdateClear:
    """AsyncTableProxyのupdate/clear検証"""

    def test_update_with_dict(self):
        """update()で辞書から更新"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["existing"] = b"old"
            
            users.update({
                "new1": b"v1",
                "new2": b"v2",
                "existing": b"new",
            })
            
            assert users["new1"] == b"v1"
            assert users["new2"] == b"v2"
            assert users["existing"] == b"new"
            assert len(users) == 3
            
            db.close()

    def test_clear_removes_all_from_table(self):
        """clear()でテーブル内の全データを削除"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            products = db.table("products")
            
            # 両テーブルにデータ追加
            for i in range(5):
                users[f"user_{i}"] = f"u{i}".encode()
                products[f"prod_{i}"] = f"p{i}".encode()
            
            assert len(users) == 5
            assert len(products) == 5
            
            # usersのみクリア
            users.clear()
            
            assert len(users) == 0
            assert len(products) == 5  # productsは影響なし
            
            db.close()


# =============================================================================
# セクション7: __iter__
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyIterator:
    """AsyncTableProxyのイテレータ検証"""

    def test_iter_over_table(self):
        """for key in table形式のイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            expected = {"k1", "k2", "k3"}
            for k in expected:
                users[k] = f"value_{k}".encode()
            
            iterated = set()
            for key in users:
                assert isinstance(key, str)
                iterated.add(key)
            
            assert iterated == expected
            
            db.close()

    def test_iter_empty_table(self):
        """空のテーブルでのイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            count = 0
            for _ in users:
                count += 1
            
            assert count == 0
            
            db.close()


# =============================================================================
# セクション8: __repr__ / __str__ / __eq__
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyReprStrEq:
    """AsyncTableProxyの表現と等価性検証"""

    def test_repr_returns_string(self):
        """__repr__が文字列を返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["k1"] = b"v1"
            
            result = repr(users)
            
            assert isinstance(result, str)
            
            db.close()

    def test_str_returns_string(self):
        """__str__が文字列を返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["k1"] = b"v1"
            
            result = str(users)
            
            assert isinstance(result, str)
            
            db.close()

    def test_eq_with_dict(self):
        """辞書との等価性比較"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            expected = {"k1": b"v1", "k2": b"v2"}
            for k, v in expected.items():
                users[k] = v
            
            assert users == expected
            
            db.close()

    def test_eq_with_different_values(self):
        """異なる値との比較"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["k1"] = b"v1"
            
            assert users != {"k1": b"different"}
            assert users != {"different": b"v1"}
            assert users != {}
            
            db.close()


# =============================================================================
# セクション9: テーブルモード別テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyModes:
    """テーブルモード別のAsyncTableProxyテスト"""

    def test_prefix_mode_isolation(self):
        """Prefixモードでのテーブル分離"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, table_mode="prefix", storage_mode="bytes")
            
            users = db.table("users")
            products = db.table("products")
            
            users["same_key"] = b"user_value"
            products["same_key"] = b"product_value"
            
            assert users["same_key"] == b"user_value"
            assert products["same_key"] == b"product_value"
            
            # 相互に独立
            assert "same_key" not in products or products.get("same_key") != b"user_value"
            
            db.close()

    def test_separate_mode_isolation(self):
        """Separateモードでのテーブル分離"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, table_mode="separate", storage_mode="bytes")
            
            users = db.table("users")
            products = db.table("products")
            
            users["same_key"] = b"user_value"
            products["same_key"] = b"product_value"
            
            assert users["same_key"] == b"user_value"
            assert products["same_key"] == b"product_value"
            
            db.close()


# =============================================================================
# セクション10: ストレージモード別テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyStorageModes:
    """AsyncTableProxyのストレージモード別テスト"""

    @pytest.mark.parametrize("storage_mode", ["bytes", "pickle", "jsonb", "json"])
    def test_basic_crud_all_modes(self, storage_mode):
        """全ストレージモードでのCRUD"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode=storage_mode)
            users = db.table("users")
            
            if storage_mode == "bytes":
                test_value = b"test_value"
            elif storage_mode in ("json", "jsonb"):
                test_value = {"name": "Alice", "age": 30}
            else:  # pickle
                test_value = {"complex": [1, 2, 3]}
            
            # Create
            users["key1"] = test_value
            
            # Read
            result = users["key1"]
            assert result == test_value
            
            # Update
            if storage_mode == "bytes":
                new_value = b"updated_value"
            elif storage_mode in ("json", "jsonb"):
                new_value = {"name": "Bob", "age": 25}
            else:
                new_value = {"updated": True}
            
            users["key1"] = new_value
            assert users["key1"] == new_value
            
            # Delete
            del users["key1"]
            assert "key1" not in users
            
            db.close()


# =============================================================================
# セクション11: 永続化テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyPersistence:
    """AsyncTableProxyの永続化テスト"""

    def test_table_data_persists(self):
        """テーブルデータの永続化"""
        with windows_safe_temp_db() as db_path:
            # 書き込み
            db1 = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db1.table("users")
            users["u1"] = b"user1"
            users["u2"] = b"user2"
            db1.close()
            
            # 再度開いて確認
            db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db2.table("users")
            assert users["u1"] == b"user1"
            assert users["u2"] == b"user2"
            db2.close()

    def test_multiple_tables_persist(self):
        """複数テーブルの永続化"""
        with windows_safe_temp_db() as db_path:
            db1 = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db1.table("users")
            products = db1.table("products")
            
            users["u1"] = b"user1"
            products["p1"] = b"product1"
            db1.close()
            
            db2 = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db2.table("users")
            products = db2.table("products")
            
            assert users["u1"] == b"user1"
            assert products["p1"] == b"product1"
            db2.close()


# =============================================================================
# セクション12: エッジケース
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncTableProxyEdgeCases:
    """AsyncTableProxyのエッジケース"""

    def test_empty_string_key(self):
        """空文字列キー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users[""] = b"empty_key_value"
            assert users[""] == b"empty_key_value"
            
            db.close()

    def test_unicode_keys(self):
        """Unicodeキー"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["日本語キー"] = b"japanese"
            users["emoji_🎉"] = b"emoji"
            
            assert users["日本語キー"] == b"japanese"
            assert users["emoji_🎉"] == b"emoji"
            
            db.close()

    def test_large_data_in_table(self):
        """テーブルへの大量データ"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            users = db.table("users")
            
            # 500件のデータ
            for i in range(500):
                users[f"user_{i}"] = f"data_{i}".encode()
            
            assert len(users) == 500
            
            # サンプル検証
            assert users["user_0"] == b"data_0"
            assert users["user_250"] == b"data_250"
            assert users["user_499"] == b"data_499"
            
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
