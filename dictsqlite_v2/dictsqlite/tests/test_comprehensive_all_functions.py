#!/usr/bin/env python3
"""
網羅的テストスイート - DictSQLite v4.2

このテストスイートは、DictSQLiteの全機能を網羅的にテストします。
各関数の応答データ、エッジケース、ネスト構造、エラー処理を検証します。

テスト対象:
1. 基本CRUD操作（Create, Read, Update, Delete）
2. 辞書インターフェース（__getitem__, __setitem__, __delitem__, __contains__, __len__)
3. ストレージモード（Pickle, JSON, JSONB, Bytes）
4. 永続化モード（Memory, Lazy, WriteThrough）
5. テーブル機能
6. 暗号化機能
7. Safe Pickle検証
8. 非同期操作
9. 応答データの詳細検証
10. 深いネスト構造の処理

各テストには詳細なコメントを付けて、何をテストしているかを明確にします。
"""

import pytest
import tempfile
import os
import sys
import pickle
import asyncio
from typing import Any, Dict, List

# テスト用ヘルパー関数をインポート
from .conftest import windows_safe_temp_db

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite, is_native_available
    DICTSQLITE_V4_AVAILABLE = is_native_available()
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None
    AsyncDictSQLite = None


# =============================================================================
# セクション1: 応答データの詳細検証
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestResponseDataValidation:
    """
    応答データの詳細検証テスト
    
    各操作から返されるデータの型、値、形式を厳密にチェックします。
    これにより、APIの一貫性と正確性を保証します。
    """
    
    def test_get_returns_exact_value_type(self):
        """
        get()メソッドの戻り値の型と値を検証
        
        確認項目:
        - 戻り値の型が期待通りか
        - 値が設定した値と完全に一致するか
        - デフォルト値が正しく返されるか
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # バイト列を設定
            original_value = b"test_value_12345"
            db["test_key"] = original_value
            
            # get()で取得した値を検証
            retrieved = db.get("test_key")
            
            # 型の検証
            assert isinstance(retrieved, bytes), f"Expected bytes, got {type(retrieved)}"
            
            # 値の完全一致を検証
            assert retrieved == original_value, f"Value mismatch: {retrieved} != {original_value}"
            
            # 長さの検証
            assert len(retrieved) == len(original_value), "Length mismatch"
            
            # 存在しないキーのデフォルト値検証
            default_result = db.get("nonexistent_key")
            assert default_result is None, f"Expected None, got {default_result}"
            
            # カスタムデフォルト値の検証
            custom_default = b"custom_default"
            default_with_value = db.get("nonexistent_key", custom_default)
            assert default_with_value == custom_default
            
            db.close()
    
    def test_getitem_returns_deserialized_value(self):
        """
        __getitem__（db[key]）の戻り値を検証
        
        各ストレージモードで適切にデシリアライズされることを確認:
        - Pickle: Python オブジェクトとして返される
        - JSONB: dict/list として返される
        - Bytes: bytes として返される
        """
        with windows_safe_temp_db() as db_path:
            # Pickleモードのテスト
            db_pickle = DictSQLiteV4(db_path, storage_mode="pickle")
            test_dict = {"key": "value", "number": 42, "list": [1, 2, 3]}
            db_pickle["test"] = test_dict
            
            retrieved_pickle = db_pickle["test"]
            
            # 型の検証
            assert isinstance(retrieved_pickle, dict), f"Expected dict, got {type(retrieved_pickle)}"
            
            # キーと値の検証
            assert retrieved_pickle["key"] == "value"
            assert retrieved_pickle["number"] == 42
            assert retrieved_pickle["list"] == [1, 2, 3]
            
            db_pickle.close()
        
        with windows_safe_temp_db() as db_path:
            # JSONBモードのテスト
            db_jsonb = DictSQLiteV4(db_path, storage_mode="jsonb")
            test_data = {"name": "Alice", "age": 30}
            db_jsonb["user"] = test_data
            
            retrieved_jsonb = db_jsonb["user"]
            
            # 型の検証
            assert isinstance(retrieved_jsonb, dict), f"Expected dict, got {type(retrieved_jsonb)}"
            assert retrieved_jsonb == test_data
            
            db_jsonb.close()
        
        with windows_safe_temp_db() as db_path:
            # Bytesモードのテスト
            db_bytes = DictSQLiteV4(db_path, storage_mode="bytes")
            test_bytes = b"\x00\x01\x02\xff"
            db_bytes["binary"] = test_bytes
            
            retrieved_bytes = db_bytes["binary"]
            
            # 型の検証
            assert isinstance(retrieved_bytes, bytes), f"Expected bytes, got {type(retrieved_bytes)}"
            assert retrieved_bytes == test_bytes
            
            db_bytes.close()
    
    def test_keys_returns_list_of_strings(self):
        """
        keys()メソッドの戻り値を検証
        
        確認項目:
        - 戻り値がリスト型か
        - 各要素が文字列か
        - 全てのキーが含まれているか
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # テストデータを設定
            expected_keys = {"key1", "key2", "key3", "special_キー", "emoji_🎉"}
            for key in expected_keys:
                db[key] = b"value"
            
            # keys()の結果を検証
            result = db.keys()
            
            # 型の検証
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            
            # 各要素が文字列であることを検証
            for key in result:
                assert isinstance(key, str), f"Expected str, got {type(key)}"
            
            # 全てのキーが含まれていることを検証
            result_set = set(result)
            assert result_set == expected_keys, f"Key mismatch: {result_set} != {expected_keys}"
            
            db.close()
    
    def test_values_returns_list_of_values(self):
        """
        values()メソッドの戻り値を検証
        
        確認項目:
        - 戻り値がリスト型か
        - 各要素が正しい型か
        - 全ての値が含まれているか
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # テストデータを設定
            test_data = {
                "key1": b"value1",
                "key2": b"value2",
                "key3": b"value3"
            }
            for key, value in test_data.items():
                db[key] = value
            
            # values()の結果を検証
            result = db.values()
            
            # 型の検証
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            
            # 値の数が一致することを検証
            assert len(result) == len(test_data), f"Count mismatch: {len(result)} != {len(test_data)}"
            
            # 全ての値が含まれていることを検証
            result_set = set(result)
            expected_set = set(test_data.values())
            assert result_set == expected_set, "Values mismatch"
            
            db.close()
    
    def test_items_returns_list_of_tuples(self):
        """
        items()メソッドの戻り値を検証
        
        確認項目:
        - 戻り値がリスト型か
        - 各要素が(key, value)タプルか
        - 全てのアイテムが含まれているか
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # テストデータを設定
            test_data = {
                "key1": b"value1",
                "key2": b"value2",
                "key3": b"value3"
            }
            for key, value in test_data.items():
                db[key] = value
            
            # items()の結果を検証
            result = db.items()
            
            # 型の検証
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            
            # 各要素がタプルであることを検証
            for item in result:
                assert isinstance(item, tuple), f"Expected tuple, got {type(item)}"
                assert len(item) == 2, f"Expected 2 elements, got {len(item)}"
            
            # 内容を辞書に変換して検証
            result_dict = dict(result)
            assert result_dict == test_data, "Items mismatch"
            
            db.close()
    
    def test_len_returns_integer(self):
        """
        len()の戻り値を検証
        
        確認項目:
        - 戻り値が整数型か
        - 値が正確か
        - 追加・削除後に正しく更新されるか
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 初期状態で0であることを確認
            initial_len = len(db)
            assert isinstance(initial_len, int), f"Expected int, got {type(initial_len)}"
            assert initial_len == 0, f"Expected 0, got {initial_len}"
            
            # アイテムを追加
            for i in range(10):
                db[f"key{i}"] = f"value{i}".encode()
            
            # 追加後のサイズを確認
            after_add = len(db)
            assert after_add == 10, f"Expected 10, got {after_add}"
            
            # アイテムを削除
            del db["key0"]
            del db["key1"]
            
            # 削除後のサイズを確認
            after_delete = len(db)
            assert after_delete == 8, f"Expected 8, got {after_delete}"
            
            db.close()
    
    def test_stats_returns_dict_with_expected_keys(self):
        """
        stats()メソッドの戻り値を検証
        
        確認項目:
        - 戻り値が辞書型か
        - 期待されるキーが全て含まれているか
        - 各値の型が正しいか
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # データを追加
            for i in range(100):
                db[f"key{i}"] = f"value{i}".encode()
            
            # statsを取得
            stats = db.stats()
            
            # 型の検証
            assert isinstance(stats, dict), f"Expected dict, got {type(stats)}"
            
            # 期待されるキーの存在を検証
            expected_keys = {
                "hot_tier_size",
                "hot_tier_capacity",
                "num_shards",
                "encryption_enabled",
                "safe_pickle_enabled",
                "persist_mode"
            }
            for key in expected_keys:
                assert key in stats, f"Missing key: {key}"
            
            # 値の型を検証
            assert isinstance(stats["hot_tier_size"], int)
            assert isinstance(stats["hot_tier_capacity"], int)
            assert isinstance(stats["num_shards"], int)
            assert isinstance(stats["encryption_enabled"], bool)
            assert isinstance(stats["safe_pickle_enabled"], bool)
            assert isinstance(stats["persist_mode"], str)
            
            # hot_tier_sizeが正しいことを検証
            assert stats["hot_tier_size"] == 100, f"Expected 100, got {stats['hot_tier_size']}"
            
            db.close()


# =============================================================================
# セクション2: 深いネスト構造のテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDeepNestedStructures:
    """
    深いネスト構造のテスト
    
    複雑なネスト構造のデータが正しく保存・取得できることを確認します。
    """
    
    def test_deeply_nested_dict_pickle(self):
        """
        深くネストされた辞書構造のテスト（Pickleモード）
        
        10レベル以上のネストが正しく処理されることを確認
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # 10レベルのネスト構造を作成
            def create_nested(depth: int, value: Any) -> Dict:
                if depth == 0:
                    return {"value": value, "depth": depth}
                return {
                    "level": depth,
                    "data": create_nested(depth - 1, value),
                    "metadata": {"created": True, "level": depth}
                }
            
            nested_data = create_nested(10, "bottom_value")
            
            # 保存と取得
            db["nested"] = nested_data
            retrieved = db["nested"]
            
            # 完全一致を検証
            assert retrieved == nested_data, "Nested structure mismatch"
            
            # 深さの検証
            current = retrieved
            for expected_level in range(10, 0, -1):
                assert current["level"] == expected_level, f"Level mismatch at {expected_level}"
                current = current["data"]
            
            assert current["value"] == "bottom_value", "Bottom value mismatch"
            
            db.close()
    
    def test_deeply_nested_dict_jsonb(self):
        """
        深くネストされた辞書構造のテスト（JSONBモード）
        
        JSONBでの深いネストの処理を確認
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            # 5レベルのネスト構造を作成（JSONBでも対応）
            nested_data = {
                "users": [
                    {
                        "name": "Alice",
                        "profile": {
                            "settings": {
                                "notifications": {
                                    "email": True,
                                    "push": False,
                                    "preferences": {
                                        "frequency": "daily"
                                    }
                                }
                            }
                        }
                    }
                ]
            }
            
            db["config"] = nested_data
            retrieved = db["config"]
            
            # ネスト構造の各レベルを検証
            assert retrieved["users"][0]["name"] == "Alice"
            assert retrieved["users"][0]["profile"]["settings"]["notifications"]["email"] is True
            assert retrieved["users"][0]["profile"]["settings"]["notifications"]["preferences"]["frequency"] == "daily"
            
            db.close()
    
    def test_mixed_nested_types_pickle(self):
        """
        異なる型が混在したネスト構造のテスト（Pickleモード）
        
        辞書、リスト、タプル、セットが混在した構造を処理
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            mixed_data = {
                "list_of_dicts": [
                    {"a": 1, "b": 2},
                    {"c": 3, "d": 4}
                ],
                "tuple": (1, 2, (3, 4, (5, 6))),
                "set": {1, 2, 3},
                "nested_list": [[1, 2], [3, 4], [[5, 6], [7, 8]]],
                "dict_with_list": {
                    "items": [1, 2, 3],
                    "nested": {
                        "more_items": [4, 5, 6]
                    }
                }
            }
            
            db["mixed"] = mixed_data
            retrieved = db["mixed"]
            
            # 各要素の型と値を検証
            assert retrieved["list_of_dicts"] == mixed_data["list_of_dicts"]
            assert retrieved["tuple"] == mixed_data["tuple"]
            assert retrieved["set"] == mixed_data["set"]
            assert retrieved["nested_list"] == mixed_data["nested_list"]
            assert retrieved["dict_with_list"]["nested"]["more_items"] == [4, 5, 6]
            
            db.close()
    
    def test_large_nested_array_jsonb(self):
        """
        大きなネスト配列のテスト（JSONBモード）
        
        100要素x10要素のネスト配列を処理
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            # 大きなネスト配列を作成
            large_array = [
                [j * 10 + i for i in range(10)]
                for j in range(100)
            ]
            
            db["large_array"] = large_array
            retrieved = db["large_array"]
            
            # サイズの検証
            assert len(retrieved) == 100, f"Expected 100 rows, got {len(retrieved)}"
            assert all(len(row) == 10 for row in retrieved), "Row length mismatch"
            
            # 値の検証（サンプリング）
            assert retrieved[0][0] == 0
            assert retrieved[50][5] == 505
            assert retrieved[99][9] == 999
            
            db.close()


# =============================================================================
# セクション3: 全関数カバレッジテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAllFunctionsCoverage:
    """
    全関数カバレッジテスト
    
    DictSQLiteV4のすべての公開メソッドをテストします。
    """
    
    def test_constructor_all_parameters(self):
        """
        コンストラクタの全パラメータをテスト
        
        各パラメータの組み合わせが正しく動作することを確認
        """
        with windows_safe_temp_db() as db_path:
            # 全パラメータを指定してインスタンスを作成
            db = DictSQLiteV4(
                db_path=db_path,
                hot_capacity=10000,
                enable_async=True,
                persist_mode="writethrough",
                storage_mode="pickle",
                table_name="main",
                encryption_password=None,
                enable_safe_pickle=False,
                safe_pickle_allowed_modules=None,
                buffer_size=50
            )
            
            # 基本操作が動作することを確認
            db["test"] = "value"
            assert db["test"] == "value"
            
            db.close()
        
        # 異なるパラメータの組み合わせ
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path=db_path,
                persist_mode="lazy",
                storage_mode="jsonb",
                hot_capacity=100
            )
            
            db["key"] = {"data": 123}
            db.flush()
            
            db.close()
    
    def test_setitem_all_modes(self):
        """
        __setitem__のすべてのストレージモードをテスト
        """
        # Pickleモード
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            db["key"] = {"complex": [1, 2, 3]}
            assert db["key"] == {"complex": [1, 2, 3]}
            db.close()
        
        # JSONBモード
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            db["key"] = {"simple": "value"}
            assert db["key"] == {"simple": "value"}
            db.close()
        
        # JSONモード
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="json")
            db["key"] = {"json": True}
            assert db["key"] == {"json": True}
            db.close()
        
        # Bytesモード
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            db["key"] = b"raw_bytes"
            assert db["key"] == b"raw_bytes"
            db.close()
    
    def test_delitem_removes_correctly(self):
        """
        __delitem__が正しく削除することをテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 複数のキーを設定
            keys = ["key1", "key2", "key3", "key4", "key5"]
            for key in keys:
                db[key] = f"value_{key}".encode()
            
            # 中間のキーを削除
            del db["key3"]
            
            # 削除されたことを確認
            assert "key3" not in db
            
            # 他のキーは残っていることを確認
            assert "key1" in db
            assert "key2" in db
            assert "key4" in db
            assert "key5" in db
            
            # 存在しないキーの削除でKeyError
            with pytest.raises(KeyError):
                del db["nonexistent"]
            
            db.close()
    
    def test_contains_all_cases(self):
        """
        __contains__（in演算子）のすべてのケースをテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 存在しないキーの確認
            assert "nonexistent" not in db
            
            # キーを追加して確認
            db["exists"] = b"value"
            assert "exists" in db
            
            # 削除後の確認
            del db["exists"]
            assert "exists" not in db
            
            # 空文字列キー
            db[""] = b"empty_key"
            assert "" in db
            
            # Unicodeキー
            db["日本語キー"] = b"value"
            assert "日本語キー" in db
            
            # 絵文字キー
            db["🎉"] = b"emoji"
            assert "🎉" in db
            
            db.close()
    
    def test_pop_with_and_without_default(self):
        """
        pop()メソッドのすべてのケースをテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # キーを設定
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            
            # 存在するキーをpop
            value = db.pop("key1")
            assert value == b"value1"
            assert "key1" not in db
            
            # 存在しないキーにデフォルト値を指定してpop
            # Note: bytes modeでは戻り値の型が異なる可能性
            value = db.pop("nonexistent", b"default")
            assert value == b"default"
            
            # 存在しないキーにデフォルトなしでpopするとKeyError
            with pytest.raises(KeyError):
                db.pop("also_nonexistent")
            
            db.close()
    
    def test_setdefault_behavior(self):
        """
        setdefault()メソッドの動作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 存在しないキーにデフォルトを設定
            result = db.setdefault("new_key", b"default_value")
            assert result == b"default_value"
            assert db["new_key"] == b"default_value"
            
            # 既存のキーに対しては変更しない
            db["existing"] = b"existing_value"
            result = db.setdefault("existing", b"ignored_default")
            assert result == b"existing_value"
            assert db["existing"] == b"existing_value"
            
            db.close()
    
    def test_update_method(self):
        """
        update()メソッドのすべてのケースをテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空のデータベースにupdate
            update_data = {
                "key1": b"value1",
                "key2": b"value2"
            }
            db.update(update_data)
            
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            
            # 既存のキーを上書き
            db.update({"key1": b"new_value1"})
            assert db["key1"] == b"new_value1"
            
            db.close()
    
    def test_clear_removes_all(self):
        """
        clear()メソッドが全データを削除することをテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 多数のキーを設定
            for i in range(100):
                db[f"key{i}"] = f"value{i}".encode()
            
            assert len(db) == 100
            
            # クリア
            db.clear()
            
            # 全て削除されていることを確認
            assert len(db) == 0
            
            # 以前のキーが存在しないことを確認
            for i in range(100):
                assert f"key{i}" not in db
            
            db.close()
    
    def test_flush_method(self):
        """
        flush()メソッドの動作をテスト
        """
        with windows_safe_temp_db() as db_path:
            # Lazyモードでテスト
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            
            # データを書き込み
            db["key1"] = b"value1"
            
            # flush前は永続化されていない可能性がある
            db.flush()
            
            # flush後は永続化されている
            db.close()
            
            # 再度開いてデータが存在することを確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            db2.close()
    
    def test_close_method(self):
        """
        close()メソッドの動作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key"] = b"value"
            
            # close()を呼び出し
            db.close()
            
            # close()後も操作可能（内部的に再オープンするか、エラーになる）
            # 実装によって動作が異なる
            
            # 新しいインスタンスでデータが永続化されていることを確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key"] == b"value"
            db2.close()


# =============================================================================
# セクション4: テーブル機能の詳細テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestTableFunctionality:
    """
    テーブル機能の詳細テスト
    
    table()メソッドとTableProxyの動作を網羅的にテストします。
    """
    
    def test_table_basic_operations(self):
        """
        テーブルの基本操作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # テーブルを取得
            users = db.table("users")
            
            # テーブルに値を設定
            users["user1"] = {"name": "Alice", "age": 30}
            users["user2"] = {"name": "Bob", "age": 25}
            
            # テーブルから値を取得
            assert users["user1"] == {"name": "Alice", "age": 30}
            assert users["user2"] == {"name": "Bob", "age": 25}
            
            # テーブル内のキー数を確認
            keys = users.keys()
            assert len(keys) == 2
            assert set(keys) == {"user1", "user2"}
            
            db.close()
    
    def test_multiple_tables_isolation(self):
        """
        複数テーブル間のデータ分離をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # 複数のテーブルを作成
            users = db.table("users")
            products = db.table("products")
            orders = db.table("orders")
            
            # 各テーブルにデータを設定
            users["user1"] = {"name": "Alice"}
            products["product1"] = {"name": "Widget", "price": 100}
            orders["order1"] = {"user_id": "user1", "product_id": "product1"}
            
            # テーブル間でデータが分離されていることを確認
            assert "user1" in users
            assert "user1" not in products
            assert "user1" not in orders
            
            assert "product1" in products
            assert "product1" not in users
            assert "product1" not in orders
            
            db.close()
    
    def test_table_contains(self):
        """
        テーブルのcontains操作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            table = db.table("test_table")
            
            # 存在しないキー
            assert "nonexistent" not in table
            
            # キーを追加
            table["key1"] = b"value1"
            assert "key1" in table
            
            db.close()
    
    def test_table_clear(self):
        """
        テーブルのクリア操作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            table1 = db.table("table1")
            table2 = db.table("table2")
            
            # 両方のテーブルにデータを設定
            for i in range(5):
                table1[f"key{i}"] = f"value{i}".encode()
                table2[f"key{i}"] = f"value{i}".encode()
            
            # table1のみクリア
            table1.clear()
            
            # table1は空、table2はデータが残っている
            assert len(table1.keys()) == 0
            assert len(table2.keys()) == 5
            
            db.close()
    
    def test_table_items_and_values(self):
        """
        テーブルのitems()とvalues()をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            table = db.table("test")
            
            test_data = {
                "key1": {"data": 1},
                "key2": {"data": 2},
                "key3": {"data": 3}
            }
            
            for k, v in test_data.items():
                table[k] = v
            
            # items()のテスト
            items = table.items()
            assert len(items) == 3
            items_dict = dict(items)
            assert items_dict == test_data
            
            # values()のテスト
            values = table.values()
            assert len(values) == 3
            
            db.close()


# =============================================================================
# セクション5: 永続化モードの詳細テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPersistenceModes:
    """
    永続化モードの詳細テスト
    
    Memory, Lazy, WriteThroughの各モードの動作を検証します。
    """
    
    def test_memory_mode_no_persistence(self):
        """
        Memoryモードでデータが永続化されないことを確認
        """
        with windows_safe_temp_db() as db_path:
            # Memoryモードでデータを作成
            db1 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            db1["key"] = b"value"
            assert db1["key"] == b"value"
            db1.close()
            
            # 再度開いてもデータがないことを確認
            # Note: memory modeでもファイルが作られる場合があるが、データは空
            db2 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            # キーが存在しないことを確認
            assert "key" not in db2
            db2.close()
    
    def test_lazy_mode_requires_flush(self):
        """
        LazyモードでFlush前後の永続化をテスト
        """
        with windows_safe_temp_db() as db_path:
            # Lazyモードでデータを作成
            db1 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            db1["before_flush"] = b"value1"
            
            # flush()を呼ぶ
            db1.flush()
            
            db1["after_flush"] = b"value2"
            db1.close()  # close()もflushを行う
            
            # 再度開いて確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["before_flush"] == b"value1"
            assert db2["after_flush"] == b"value2"
            db2.close()
    
    def test_writethrough_mode_immediate_persistence(self):
        """
        WriteThroughモードで即時永続化されることを確認
        """
        with windows_safe_temp_db() as db_path:
            # WriteThroughモードでデータを作成
            db1 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            db1["key"] = b"value"
            
            # flush()なしでcloseする前に別インスタンスで確認
            # 注意: 同じファイルを複数インスタンスで開く場合の動作は実装依存
            db1.close()
            
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key"] == b"value"
            db2.close()


# =============================================================================
# セクション6: 暗号化機能のテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEncryptionFeatures:
    """
    暗号化機能のテスト
    
    AES-256-GCM暗号化の動作を検証します。
    """
    
    def test_encryption_basic(self):
        """
        基本的な暗号化・復号化のテスト
        """
        with windows_safe_temp_db() as db_path:
            password = "test_password_123"
            
            # 暗号化を有効にしてデータを作成
            db1 = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            db1["secret_key"] = b"secret_value"
            db1.close()
            
            # 同じパスワードで開いて確認
            db2 = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            assert db2["secret_key"] == b"secret_value"
            db2.close()
    
    def test_encryption_with_different_types(self):
        """
        異なるデータ型の暗号化テスト
        """
        with windows_safe_temp_db() as db_path:
            password = "complex_password_!@#"
            
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="pickle")
            
            # 異なる型のデータを保存
            db["string"] = "Hello World"
            db["int"] = 12345
            db["float"] = 3.14159
            db["dict"] = {"nested": {"key": "value"}}
            db["list"] = [1, 2, 3, 4, 5]
            
            # 取得して検証
            assert db["string"] == "Hello World"
            assert db["int"] == 12345
            assert abs(db["float"] - 3.14159) < 0.00001
            assert db["dict"] == {"nested": {"key": "value"}}
            assert db["list"] == [1, 2, 3, 4, 5]
            
            db.close()
    
    def test_encryption_stats_shows_enabled(self):
        """
        暗号化が有効な場合にstatsに反映されることを確認
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, encryption_password="password", storage_mode="bytes")
            
            stats = db.stats()
            assert stats["encryption_enabled"] is True
            
            db.close()
        
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            stats = db.stats()
            assert stats["encryption_enabled"] is False
            
            db.close()


# =============================================================================
# セクション7: 非同期操作のテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncOperations:
    """
    非同期操作のテスト
    
    AsyncDictSQLiteの非同期メソッドをテストします。
    """
    
    @pytest.mark.asyncio
    async def test_async_basic_operations(self):
        """
        非同期の基本操作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # 非同期でデータを設定
            await db.aset("key1", b"value1")
            await db.aset("key2", b"value2")
            
            # 非同期でデータを取得
            value1 = await db.aget("key1")
            value2 = await db.aget("key2")
            
            assert value1 == b"value1"
            assert value2 == b"value2"
            
            db.close()
    
    @pytest.mark.asyncio
    async def test_async_contains(self):
        """
        非同期のcontainsをテスト
        """
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # 存在しないキー
            exists = await db.acontains("nonexistent")
            assert exists is False
            
            # キーを追加
            await db.aset("key", b"value")
            
            # 存在するキー
            exists = await db.acontains("key")
            assert exists is True
            
            db.close()
    
    @pytest.mark.asyncio
    async def test_async_delete(self):
        """
        非同期の削除をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # キーを設定
            await db.aset("to_delete", b"value")
            
            # 削除
            await db.adelete("to_delete")
            
            # 存在しないことを確認
            exists = await db.acontains("to_delete")
            assert exists is False
            
            db.close()
    
    @pytest.mark.asyncio
    async def test_async_batch_operations(self):
        """
        非同期のバッチ操作をテスト
        """
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            # バッチ設定
            items = [(f"key{i}", f"value{i}".encode()) for i in range(10)]
            await db.abatch_set(items)
            
            # バッチ取得
            keys = [f"key{i}" for i in range(10)]
            values = await db.abatch_get(keys)
            
            # 検証
            assert len(values) == 10
            for i, value in enumerate(values):
                assert value == f"value{i}".encode()
            
            db.close()
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """
        非同期コンテキストマネージャーをテスト
        """
        with windows_safe_temp_db() as db_path:
            async with AsyncDictSQLite(db_path, storage_mode="bytes") as db:
                await db.aset("key", b"value")
                value = await db.aget("key")
                assert value == b"value"


# =============================================================================
# セクション8: エラーハンドリングの詳細テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestErrorHandling:
    """
    エラーハンドリングの詳細テスト
    
    各種エラー状況での適切なエラー処理を確認します。
    """
    
    def test_keyerror_messages(self):
        """
        KeyErrorのメッセージを検証
        """
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            try:
                _ = db["nonexistent_key"]
                assert False, "KeyError should have been raised"
            except KeyError as e:
                # エラーメッセージにキー名が含まれていることを確認
                error_msg = str(e)
                assert "nonexistent_key" in error_msg or "Key not found" in error_msg
            
            db.close()
    
    def test_invalid_parameters(self):
        """
        無効なパラメータでのエラーを検証
        """
        with windows_safe_temp_db() as db_path:
            # 無効な永続化モード
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, persist_mode="invalid_mode")
            
            # 無効なストレージモード
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, storage_mode="invalid_storage")
    
    def test_type_errors(self):
        """
        型エラーの検証
        """
        with windows_safe_temp_db() as db_path:
            # Bytesモードで辞書を保存しようとするとエラー
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            with pytest.raises((TypeError, ValueError, RuntimeError)):
                db["key"] = {"dict": "not_bytes"}
            
            db.close()
        
        with windows_safe_temp_db() as db_path:
            # JSONBモードでシリアライズ不可能なオブジェクトを保存
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            class CustomClass:
                pass
            
            with pytest.raises((TypeError, ValueError, RuntimeError)):
                db["key"] = CustomClass()
            
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
