#!/usr/bin/env python3
"""
基本操作テスト - DictSQLite v4.2

このテストスイートは基本的な機能を網羅的にテストします：
- CRUD操作（Create, Read, Update, Delete）
- 辞書型インターフェース（__getitem__, __setitem__, __delitem__, __contains__）
- コンテキストマネージャー
- イテレータ
- 基本的なエラーハンドリング
"""

import pytest
import tempfile
import os
import sys
from .conftest import windows_safe_temp_db

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
    DICTSQLITE_V4_AVAILABLE = True
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None
    AsyncDictSQLite = None


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBasicCRUD:
    """基本的なCRUD操作のテスト"""
    
    def test_create_and_read(self):
        """作成と読み取りのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 単純な作成と読み取り
            db["key1"] = b"value1"
            assert db["key1"] == b"value1"
            
            # 複数のキーを作成
            db["key2"] = b"value2"
            db["key3"] = b"value3"
            
            # すべて読み取れることを確認
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            assert db["key3"] == b"value3"
            
            db.close()
    
    def test_update(self):
        """更新のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 初期値を設定
            db["key1"] = b"initial_value"
            assert db["key1"] == b"initial_value"
            
            # 値を更新
            db["key1"] = b"updated_value"
            assert db["key1"] == b"updated_value"
            
            # 複数回更新
            db["key1"] = b"value_v2"
            assert db["key1"] == b"value_v2"
            
            db["key1"] = b"value_v3"
            assert db["key1"] == b"value_v3"
            
            db.close()
    
    def test_delete(self):
        """削除のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # キーを作成
            db["key_to_delete"] = b"value"
            assert "key_to_delete" in db
            
            # 削除
            del db["key_to_delete"]
            assert "key_to_delete" not in db
            
            # 削除後のアクセスはKeyErrorを発生
            with pytest.raises(KeyError):
                _ = db["key_to_delete"]
            
            db.close()
    
    def test_contains(self):
        """in演算子のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 存在しないキー
            assert "nonexistent" not in db
            
            # キーを追加
            db["exists"] = b"value"
            assert "exists" in db
            
            # 削除後
            del db["exists"]
            assert "exists" not in db
            
            db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDictInterface:
    """辞書型インターフェースのテスト"""
    
    def test_get_method(self):
        """get()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key1"] = b"value1"
            
            # 存在するキー
            assert db.get("key1") == b"value1"
            
            # 存在しないキー - デフォルトNone
            assert db.get("nonexistent") is None
            
            # 存在しないキー - カスタムデフォルト
            assert db.get("nonexistent", b"default") == b"default"
            
            db.close()
    
    def test_keys_method(self):
        """keys()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空のデータベース
            keys = list(db.keys())
            assert keys == []
            
            # キーを追加
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            db["key3"] = b"value3"
            
            keys = set(db.keys())
            assert keys == {"key1", "key2", "key3"}
            
            db.close()
    
    def test_values_method(self):
        """values()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空のデータベース
            values = list(db.values())
            assert values == []
            
            # 値を追加
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            db["key3"] = b"value3"
            
            values = set(db.values())
            assert values == {b"value1", b"value2", b"value3"}
            
            db.close()
    
    def test_items_method(self):
        """items()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空のデータベース
            items = list(db.items())
            assert items == []
            
            # アイテムを追加
            test_data = {
                "key1": b"value1",
                "key2": b"value2",
                "key3": b"value3",
            }
            
            for k, v in test_data.items():
                db[k] = v
            
            items = dict(db.items())
            assert items == test_data
            
            db.close()
    
    def test_len_method(self):
        """len()関数のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 空のデータベース
            assert len(db) == 0
            
            # アイテムを追加
            db["key1"] = b"value1"
            assert len(db) == 1
            
            db["key2"] = b"value2"
            assert len(db) == 2
            
            # 削除
            del db["key1"]
            assert len(db) == 1
            
            del db["key2"]
            assert len(db) == 0
            
            db.close()
    
    def test_update_method(self):
        """update()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 初期データ
            db["existing"] = b"old_value"
            
            # 辞書でupdateする
            update_data = {
                "new1": b"value1",
                "new2": b"value2",
                "existing": b"new_value",  # 上書き
            }
            db.update(update_data)
            
            assert db["new1"] == b"value1"
            assert db["new2"] == b"value2"
            assert db["existing"] == b"new_value"
            assert len(db) == 3
            
            db.close()
    
    def test_clear_method(self):
        """clear()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # データを追加
            for i in range(10):
                db[f"key{i}"] = f"value{i}".encode()
            
            assert len(db) == 10
            
            # クリア
            db.clear()
            assert len(db) == 0
            
            # キーが存在しないことを確認
            for i in range(10):
                assert f"key{i}" not in db
            
            db.close()
    
    def test_pop_method(self):
        """pop()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["key1"] = b"value1"
            
            # pop with existing key
            value = db.pop("key1")
            assert value == b"value1"
            assert "key1" not in db
            
            # pop with non-existing key and default
            value = db.pop("nonexistent", b"default")
            assert value == b"default"
            
            # pop with non-existing key and no default raises KeyError
            with pytest.raises(KeyError):
                db.pop("nonexistent")
            
            db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestContextManager:
    """コンテキストマネージャーのテスト"""
    
    def test_with_statement(self):
        """with文でのテスト"""
        with windows_safe_temp_db() as db_path:
            with DictSQLiteV4(db_path, storage_mode="bytes") as db:
                db["key1"] = b"value1"
                assert db["key1"] == b"value1"
            
            # with文を抜けた後も値が永続化されている
            with DictSQLiteV4(db_path, storage_mode="bytes") as db:
                assert db["key1"] == b"value1"
    
    def test_exception_in_context(self):
        """コンテキスト内で例外が発生した場合"""
        with windows_safe_temp_db() as db_path:
            try:
                with DictSQLiteV4(db_path, storage_mode="bytes") as db:
                    db["key1"] = b"value1"
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # 例外が発生してもデータは保存される
            with DictSQLiteV4(db_path, storage_mode="bytes") as db:
                assert db["key1"] == b"value1"


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestIteration:
    """イテレーションのテスト"""
    
    def test_iterate_keys(self):
        """キーのイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            test_keys = ["key1", "key2", "key3"]
            for key in test_keys:
                db[key] = f"value_{key}".encode()
            
            # for key in db でイテレート
            iterated_keys = set()
            for key in db:
                iterated_keys.add(key)
            
            assert iterated_keys == set(test_keys)
            
            db.close()
    
    def test_iterate_items(self):
        """アイテムのイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            test_data = {
                "key1": b"value1",
                "key2": b"value2",
                "key3": b"value3",
            }
            
            for k, v in test_data.items():
                db[k] = v
            
            # items()でイテレート
            iterated_data = {}
            for key, value in db.items():
                iterated_data[key] = value
            
            assert iterated_data == test_data
            
            db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestErrorHandling:
    """基本的なエラーハンドリングのテスト"""
    
    def test_keyerror_on_missing_key(self):
        """存在しないキーへのアクセスでKeyErrorが発生"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                _ = db["nonexistent_key"]
            
            db.close()
    
    def test_keyerror_on_delete_missing_key(self):
        """存在しないキーの削除でKeyErrorが発生"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            with pytest.raises(KeyError):
                del db["nonexistent_key"]
            
            db.close()
    
    def test_invalid_persist_mode(self):
        """無効な永続化モードでエラーが発生"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, persist_mode="invalid_mode")
    
    def test_invalid_storage_mode(self):
        """無効なストレージモードでエラーが発生"""
        with windows_safe_temp_db() as db_path:
            with pytest.raises((ValueError, RuntimeError)):
                DictSQLiteV4(db_path, storage_mode="invalid_mode")


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDataPersistence:
    """データの永続化テスト"""
    
    def test_data_persists_after_close(self):
        """close後もデータが永続化される"""
        with windows_safe_temp_db() as db_path:
            # データを書き込んでclose
            db1 = DictSQLiteV4(db_path, storage_mode="bytes")
            db1["key1"] = b"value1"
            db1["key2"] = b"value2"
            db1.close()
            
            # 再度開いてデータが残っていることを確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            assert db2["key2"] == b"value2"
            db2.close()
    
    def test_flush_method(self):
        """flush()メソッドのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            
            # データを書き込む
            db["key1"] = b"value1"
            
            # flush前にdb2で確認（lazy modeだと見えない可能性）
            db.flush()
            
            # flushした後は確実に永続化されている
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            
            db.close()
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMultipleTypes:
    """複数のデータ型のテスト"""
    
    def test_bytes_values(self):
        """バイト型の値"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 様々なバイト列
            db["empty"] = b""
            db["simple"] = b"hello"
            db["binary"] = bytes(range(256))
            
            assert db["empty"] == b""
            assert db["simple"] == b"hello"
            assert db["binary"] == bytes(range(256))
            
            db.close()
    
    def test_string_keys(self):
        """文字列キーのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 様々な文字列キー
            db["simple"] = b"value1"
            db["with spaces"] = b"value2"
            db["日本語"] = b"value3"
            db["emoji_🎉"] = b"value4"
            
            assert db["simple"] == b"value1"
            assert db["with spaces"] == b"value2"
            assert db["日本語"] == b"value3"
            assert db["emoji_🎉"] == b"value4"
            
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
