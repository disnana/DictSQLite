#!/usr/bin/env python3
"""
網羅的テストスイート - 戻り値型の厳密検証

このテストファイルは、全メソッドの戻り値の型を厳密に検証します。
各ストレージモードでの型変換、None処理、構造体の検証を行います。

テスト対象:
- 各ストレージモード（pickle, jsonb, json, bytes）での型検証
- None/デフォルト値の正確な返却
- リスト・辞書・タプルの構造検証
- stats()の全フィールド検証
"""

import pytest
import tempfile
import os
import sys
import pickle
import json
from typing import Any, Dict, List, Tuple, Optional

# テストユーティリティのインポート
from .conftest import windows_safe_temp_db, cleanup_db_files

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite, is_native_available
    DICTSQLITE_V4_AVAILABLE = is_native_available()
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None
    AsyncDictSQLite = None


# =============================================================================
# セクション1: Bytesモードの戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBytesStorageReturnTypes:
    """Bytesストレージモードの戻り値型検証"""

    def test_getitem_returns_bytes(self):
        """__getitem__がbytesを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            db["key"] = b"value"
            
            result = db["key"]
            
            assert isinstance(result, bytes), f"Expected bytes, got {type(result).__name__}"
            assert result == b"value"
            
            db.close()

    def test_get_returns_bytes_or_none(self):
        """get()がbytesまたはNoneを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 存在しない場合はNone
            result1 = db.get("missing")
            assert result1 is None, f"Expected None, got {type(result1).__name__}"
            
            # 存在する場合はbytes
            db["key"] = b"value"
            result2 = db.get("key")
            assert isinstance(result2, bytes), f"Expected bytes, got {type(result2).__name__}"
            
            db.close()

    def test_values_returns_list_of_bytes(self):
        """values()がbytesのリストを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["k1"] = b"v1"
            db["k2"] = b"v2"
            db["k3"] = b"v3"
            
            result = db.values()
            
            assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
            for item in result:
                assert isinstance(item, bytes), f"Expected bytes in list, got {type(item).__name__}"
            
            db.close()

    def test_items_returns_list_of_str_bytes_tuples(self):
        """items()が(str, bytes)タプルのリストを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["k1"] = b"v1"
            db["k2"] = b"v2"
            
            result = db.items()
            
            assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
            for item in result:
                assert isinstance(item, tuple), f"Expected tuple, got {type(item).__name__}"
                assert len(item) == 2, f"Expected 2-tuple, got {len(item)}-tuple"
                key, value = item
                assert isinstance(key, str), f"Expected str key, got {type(key).__name__}"
                assert isinstance(value, bytes), f"Expected bytes value, got {type(value).__name__}"
            
            db.close()


# =============================================================================
# セクション2: Pickleモードの戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPickleStorageReturnTypes:
    """Pickleストレージモードの戻り値型検証"""

    def test_int_preserves_type(self):
        """int型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["int_key"] = 42
            result = db["int_key"]
            
            assert isinstance(result, int), f"Expected int, got {type(result).__name__}"
            assert result == 42
            
            db.close()

    def test_float_preserves_type(self):
        """float型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["float_key"] = 3.14159
            result = db["float_key"]
            
            assert isinstance(result, float), f"Expected float, got {type(result).__name__}"
            assert abs(result - 3.14159) < 1e-10
            
            db.close()

    def test_str_preserves_type(self):
        """str型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["str_key"] = "hello world"
            result = db["str_key"]
            
            assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
            assert result == "hello world"
            
            db.close()

    def test_list_preserves_type(self):
        """list型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["list_key"] = [1, 2, 3, "four", 5.0]
            result = db["list_key"]
            
            assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
            assert result == [1, 2, 3, "four", 5.0]
            
            # 各要素の型も検証
            assert isinstance(result[0], int)
            assert isinstance(result[3], str)
            assert isinstance(result[4], float)
            
            db.close()

    def test_dict_preserves_type(self):
        """dict型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            test_dict = {"name": "Alice", "age": 30, "active": True}
            db["dict_key"] = test_dict
            result = db["dict_key"]
            
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
            assert result == test_dict
            
            # 各値の型も検証
            assert isinstance(result["name"], str)
            assert isinstance(result["age"], int)
            assert isinstance(result["active"], bool)
            
            db.close()

    def test_tuple_preserves_type(self):
        """tuple型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["tuple_key"] = (1, 2, 3)
            result = db["tuple_key"]
            
            assert isinstance(result, tuple), f"Expected tuple, got {type(result).__name__}"
            assert result == (1, 2, 3)
            
            db.close()

    def test_bool_preserves_type(self):
        """bool型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["true_key"] = True
            db["false_key"] = False
            
            result_true = db["true_key"]
            result_false = db["false_key"]
            
            assert isinstance(result_true, bool), f"Expected bool, got {type(result_true).__name__}"
            assert isinstance(result_false, bool), f"Expected bool, got {type(result_false).__name__}"
            assert result_true is True
            assert result_false is False
            
            db.close()

    def test_none_preserves_type(self):
        """None型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["none_key"] = None
            result = db["none_key"]
            
            assert result is None, f"Expected None, got {result}"
            
            db.close()

    def test_nested_structure_preserves_types(self):
        """ネストした構造の型が保存される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            nested = {
                "users": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25},
                ],
                "metadata": {
                    "count": 2,
                    "active": True,
                }
            }
            
            db["nested"] = nested
            result = db["nested"]
            
            assert isinstance(result, dict)
            assert isinstance(result["users"], list)
            assert isinstance(result["users"][0], dict)
            assert isinstance(result["users"][0]["name"], str)
            assert isinstance(result["users"][0]["age"], int)
            assert isinstance(result["metadata"]["count"], int)
            assert isinstance(result["metadata"]["active"], bool)
            
            db.close()


# =============================================================================
# セクション3: JSONBモードの戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestJsonbStorageReturnTypes:
    """JSONBストレージモードの戻り値型検証"""

    def test_dict_returns_dict(self):
        """dict型がdictとして返される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            db["dict_key"] = {"name": "Alice", "age": 30}
            result = db["dict_key"]
            
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
            
            db.close()

    def test_list_returns_list(self):
        """list型がlistとして返される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            db["list_key"] = [1, 2, 3, "four"]
            result = db["list_key"]
            
            assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
            
            db.close()

    def test_json_compatible_types(self):
        """JSON互換型の検証"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            test_data = {
                "string": "hello",
                "number_int": 42,
                "number_float": 3.14,
                "boolean": True,
                "null": None,
                "array": [1, 2, 3],
                "object": {"nested": "value"}
            }
            
            db["data"] = test_data
            result = db["data"]
            
            assert isinstance(result["string"], str)
            assert isinstance(result["number_int"], (int, float))
            assert isinstance(result["number_float"], float)
            assert isinstance(result["boolean"], bool)
            assert result["null"] is None
            assert isinstance(result["array"], list)
            assert isinstance(result["object"], dict)
            
            db.close()


# =============================================================================
# セクション4: JSONモードの戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestJsonStorageReturnTypes:
    """JSONストレージモードの戻り値型検証"""

    def test_dict_returns_dict(self):
        """dict型がdictとして返される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="json")
            
            db["dict_key"] = {"key": "value"}
            result = db["dict_key"]
            
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
            
            db.close()

    def test_list_returns_list(self):
        """list型がlistとして返される"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="json")
            
            db["list_key"] = [1, 2, 3]
            result = db["list_key"]
            
            assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
            
            db.close()


# =============================================================================
# セクション5: keys()の戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestKeysReturnType:
    """keys()メソッドの戻り値型検証"""

    @pytest.mark.parametrize("storage_mode", ["bytes", "pickle", "jsonb", "json"])
    def test_keys_returns_list_of_strings(self, storage_mode):
        """全モードでkeys()がstr型リストを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode=storage_mode)
            
            if storage_mode == "bytes":
                db["key1"] = b"v1"
                db["key2"] = b"v2"
            else:
                db["key1"] = {"val": 1}
                db["key2"] = {"val": 2}
            
            result = db.keys()
            
            # リスト型
            assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
            
            # 全要素がstr型
            for key in result:
                assert isinstance(key, str), f"Expected str, got {type(key).__name__}"
            
            # 期待されるキーが含まれている
            assert set(result) == {"key1", "key2"}
            
            db.close()

    def test_keys_empty_db(self):
        """空のDBでkeys()が空リストを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.keys()
            
            assert isinstance(result, list)
            assert len(result) == 0
            
            db.close()


# =============================================================================
# セクション6: len()の戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestLenReturnType:
    """len()の戻り値型検証"""

    @pytest.mark.parametrize("storage_mode", ["bytes", "pickle", "jsonb", "json"])
    def test_len_returns_int(self, storage_mode):
        """全モードでlen()がintを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode=storage_mode)
            
            # 空の場合
            result0 = len(db)
            assert isinstance(result0, int), f"Expected int, got {type(result0).__name__}"
            assert result0 == 0
            
            # データ追加後
            if storage_mode == "bytes":
                db["k1"] = b"v1"
                db["k2"] = b"v2"
            else:
                db["k1"] = {"val": 1}
                db["k2"] = {"val": 2}
            
            result2 = len(db)
            assert isinstance(result2, int), f"Expected int, got {type(result2).__name__}"
            assert result2 == 2
            
            db.close()


# =============================================================================
# セクション7: contains()の戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestContainsReturnType:
    """__contains__の戻り値型検証"""

    @pytest.mark.parametrize("storage_mode", ["bytes", "pickle", "jsonb", "json"])
    def test_contains_returns_bool(self, storage_mode):
        """全モードで__contains__がboolを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode=storage_mode)
            
            # 存在しない場合
            result_false = "nonexistent" in db
            assert isinstance(result_false, bool), f"Expected bool, got {type(result_false).__name__}"
            assert result_false is False
            
            # 存在する場合
            if storage_mode == "bytes":
                db["key"] = b"value"
            else:
                db["key"] = {"val": 1}
            
            result_true = "key" in db
            assert isinstance(result_true, bool), f"Expected bool, got {type(result_true).__name__}"
            assert result_true is True
            
            db.close()


# =============================================================================
# セクション8: stats()の戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStatsReturnType:
    """stats()の戻り値型検証"""

    def test_stats_returns_dict(self):
        """stats()がdictを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
            
            db.close()

    def test_stats_keys_are_strings(self):
        """stats()のキーが全てstr"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            for key in result.keys():
                assert isinstance(key, str), f"Expected str key, got {type(key).__name__}"
            
            db.close()

    def test_stats_contains_expected_keys(self):
        """stats()が期待されるキーを含む"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # データを追加
            for i in range(10):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            result = db.stats()
            
            # 必須キーの確認 (実際のAPI: hot_tier_size, hot_tier_capacity)
            expected_keys = ["hot_tier_size", "hot_tier_capacity", "num_shards"]
            for key in expected_keys:
                assert key in result, f"Expected key '{key}' not in stats"
            
            db.close()

    def test_stats_numeric_values_are_int(self):
        """stats()の数値がint型"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            numeric_keys = ["hot_tier_size", "hot_tier_capacity", "num_shards"]
            for key in numeric_keys:
                if key in result:
                    assert isinstance(result[key], int), f"stats['{key}'] should be int, got {type(result[key]).__name__}"
            
            db.close()


# =============================================================================
# セクション9: pop()の戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPopReturnType:
    """pop()の戻り値型検証"""

    def test_pop_returns_correct_type_bytes(self):
        """pop()がbytes型を返す（bytesモード）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            result = db.pop("key")
            
            assert isinstance(result, bytes), f"Expected bytes, got {type(result).__name__}"
            assert result == b"value"
            
            db.close()

    def test_pop_returns_correct_type_pickle(self):
        """pop()が元の型を返す（pickleモード）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            db["dict_key"] = {"name": "Alice"}
            result = db.pop("dict_key")
            
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
            assert result == {"name": "Alice"}
            
            db.close()

    def test_pop_returns_default_type(self):
        """pop()がデフォルト値の型を返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.pop("nonexistent", b"default")
            
            assert isinstance(result, bytes), f"Expected bytes, got {type(result).__name__}"
            assert result == b"default"
            
            db.close()


# =============================================================================
# セクション10: setdefault()の戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSetdefaultReturnType:
    """setdefault()の戻り値型検証"""

    def test_setdefault_returns_existing_type(self):
        """setdefault()が既存値の型を返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"existing"
            result = db.setdefault("key", b"default")
            
            assert isinstance(result, bytes), f"Expected bytes, got {type(result).__name__}"
            assert result == b"existing"
            
            db.close()

    def test_setdefault_returns_default_type(self):
        """setdefault()がデフォルト値の型を返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.setdefault("new_key", b"default")
            
            assert isinstance(result, bytes), f"Expected bytes, got {type(result).__name__}"
            assert result == b"default"
            
            db.close()


# =============================================================================
# セクション11: TableProxyの戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestTableProxyReturnTypes:
    """TableProxyの戻り値型検証"""

    def test_table_proxy_getitem_returns_correct_type(self):
        """TableProxyの__getitem__が正しい型を返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["u1"] = b"alice"
            result = users["u1"]
            
            assert isinstance(result, bytes), f"Expected bytes, got {type(result).__name__}"
            
            db.close()

    def test_table_proxy_keys_returns_list_of_str(self):
        """TableProxyのkeys()がstr型リストを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["u1"] = b"alice"
            users["u2"] = b"bob"
            
            result = users.keys()
            
            assert isinstance(result, list)
            for key in result:
                assert isinstance(key, str)
            
            db.close()

    def test_table_proxy_items_returns_list_of_tuples(self):
        """TableProxyのitems()がタプルリストを返す"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            users = db.table("users")
            
            users["u1"] = b"alice"
            
            result = users.items()
            
            assert isinstance(result, list)
            for item in result:
                assert isinstance(item, tuple)
                assert len(item) == 2
            
            db.close()


# =============================================================================
# セクション12: AsyncDictSQLiteの戻り値型検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncReturnTypes:
    """AsyncDictSQLiteの戻り値型検証"""

    def test_stats_returns_dict_with_size_capacity(self):
        """AsyncDictSQLiteのstats()が正しい構造を返す"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            result = db.stats()
            
            assert isinstance(result, dict)
            assert "size" in result
            assert "capacity" in result
            assert isinstance(result["size"], int)
            assert isinstance(result["capacity"], int)
            
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
