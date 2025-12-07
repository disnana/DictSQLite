"""
v6.0 テスト - PyO3 0.27移行と最適化検証

このテストモジュールは以下を検証します:
- PyO3 0.27 API移行後の動作確認
- 圧縮機能の動作
- pythonize統合の互換性
"""

import pytest
import tempfile
import os
import sys

# dictsqliteモジュールのインポート
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
except ImportError:
    pytest.skip("dictsqlite module not installed", allow_module_level=True)


class TestV6BasicOperations:
    """v6基本操作テスト"""

    def test_dictsqlite_v4_creation(self, tmp_path):
        """DictSQLiteV4インスタンス作成テスト"""
        db_path = str(tmp_path / "test_v6.db")
        db = DictSQLiteV4(db_path)
        assert db is not None

    def test_basic_set_get(self, tmp_path):
        """基本的なset/getテスト"""
        db_path = str(tmp_path / "test_basic.db")
        db = DictSQLiteV4(db_path)
        
        db["key1"] = {"name": "Alice", "age": 30}
        result = db["key1"]
        
        assert result is not None
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_string_values(self, tmp_path):
        """文字列値のテスト"""
        db_path = str(tmp_path / "test_string.db")
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        db["greeting"] = "Hello, World!"
        assert db["greeting"] == "Hello, World!"

    def test_list_values(self, tmp_path):
        """リスト値のテスト"""
        db_path = str(tmp_path / "test_list.db")
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        db["numbers"] = [1, 2, 3, 4, 5]
        result = db["numbers"]
        assert result == [1, 2, 3, 4, 5]

    def test_nested_dict(self, tmp_path):
        """ネストされたdictテスト"""
        db_path = str(tmp_path / "test_nested.db")
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        data = {
            "user": {
                "profile": {
                    "name": "Bob",
                    "settings": {"theme": "dark"}
                }
            }
        }
        db["nested"] = data
        result = db["nested"]
        assert result["user"]["profile"]["name"] == "Bob"
        assert result["user"]["profile"]["settings"]["theme"] == "dark"


class TestV6StorageModes:
    """ストレージモードテスト"""

    @pytest.mark.parametrize("mode", ["pickle", "json", "jsonb"])
    def test_storage_mode_compatibility(self, tmp_path, mode):
        """各ストレージモードの互換性テスト"""
        db_path = str(tmp_path / f"test_{mode}.db")
        db = DictSQLiteV4(db_path, storage_mode=mode)
        
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        db["test"] = test_data
        result = db["test"]
        
        assert result["key"] == "value"
        assert result["number"] == 42
        assert result["list"] == [1, 2, 3]


class TestV6DictCompatibility:
    """辞書互換APIテスト"""

    def test_contains(self, tmp_path):
        """__contains__テスト"""
        db_path = str(tmp_path / "test_contains.db")
        db = DictSQLiteV4(db_path)
        
        db["exists"] = "value"
        assert "exists" in db
        assert "not_exists" not in db

    def test_delete(self, tmp_path):
        """__delitem__テスト"""
        db_path = str(tmp_path / "test_delete.db")
        db = DictSQLiteV4(db_path)
        
        db["to_delete"] = "value"
        assert "to_delete" in db
        del db["to_delete"]
        assert "to_delete" not in db

    def test_keys(self, tmp_path):
        """keysメソッドテスト"""
        db_path = str(tmp_path / "test_keys.db")
        db = DictSQLiteV4(db_path)
        
        db["key1"] = "value1"
        db["key2"] = "value2"
        keys = db.keys()
        
        assert "key1" in keys
        assert "key2" in keys

    def test_len(self, tmp_path):
        """__len__テスト"""
        db_path = str(tmp_path / "test_len.db")
        db = DictSQLiteV4(db_path)
        
        db["a"] = 1
        db["b"] = 2
        db["c"] = 3
        assert len(db) == 3


class TestV6TableProxy:
    """テーブルプロキシテスト"""

    def test_table_creation(self, tmp_path):
        """テーブル作成テスト"""
        db_path = str(tmp_path / "test_table.db")
        db = DictSQLiteV4(db_path)
        
        users = db.table("users")
        assert users is not None

    def test_table_operations(self, tmp_path):
        """テーブル操作テスト"""
        db_path = str(tmp_path / "test_table_ops.db")
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        users = db.table("users")
        users["user1"] = {"name": "Alice"}
        
        result = users["user1"]
        assert result["name"] == "Alice"

    def test_multiple_tables(self, tmp_path):
        """複数テーブルテスト"""
        db_path = str(tmp_path / "test_multi_table.db")
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        users = db.table("users")
        products = db.table("products")
        
        users["u1"] = {"name": "User1"}
        products["p1"] = {"name": "Product1"}
        
        assert users["u1"]["name"] == "User1"
        assert products["p1"]["name"] == "Product1"


class TestV6Async:
    """非同期操作テスト"""

    def test_async_creation(self, tmp_path):
        """AsyncDictSQLiteインスタンス作成テスト"""
        db_path = str(tmp_path / "test_async.db")
        db = AsyncDictSQLite(db_path)
        assert db is not None

    def test_async_sync_operations(self, tmp_path):
        """AsyncDictSQLite同期操作テスト"""
        db_path = str(tmp_path / "test_async_sync.db")
        db = AsyncDictSQLite(db_path)
        
        db["key"] = b"value"
        result = db["key"]
        assert result == b"value"


class TestV6EdgeCases:
    """エッジケーステスト"""

    def test_empty_string_key(self, tmp_path):
        """空文字列キーテスト"""
        db_path = str(tmp_path / "test_empty_key.db")
        db = DictSQLiteV4(db_path)
        
        db[""] = "empty_key_value"
        assert db[""] == "empty_key_value"

    def test_unicode_key(self, tmp_path):
        """Unicodeキーテスト"""
        db_path = str(tmp_path / "test_unicode.db")
        db = DictSQLiteV4(db_path)
        
        db["日本語キー"] = "unicode_value"
        assert db["日本語キー"] == "unicode_value"

    def test_large_value(self, tmp_path):
        """大きな値テスト"""
        db_path = str(tmp_path / "test_large.db")
        db = DictSQLiteV4(db_path)
        
        large_data = {"data": "x" * 100000}
        db["large"] = large_data
        result = db["large"]
        assert len(result["data"]) == 100000

    def test_special_characters(self, tmp_path):
        """特殊文字テスト"""
        db_path = str(tmp_path / "test_special.db")
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        special = {"quote": '"', "backslash": "\\", "newline": "\n", "tab": "\t"}
        db["special"] = special
        result = db["special"]
        assert result["quote"] == '"'
        assert result["backslash"] == "\\"


class TestV6Performance:
    """パフォーマンス関連テスト"""

    def test_batch_operations(self, tmp_path):
        """バッチ操作テスト"""
        db_path = str(tmp_path / "test_batch.db")
        db = DictSQLiteV4(db_path)
        
        # 多数のキーを挿入
        for i in range(100):
            db[f"key_{i}"] = f"value_{i}"
        
        # 確認
        for i in range(100):
            assert db[f"key_{i}"] == f"value_{i}"

    def test_repeated_access(self, tmp_path):
        """繰り返しアクセステスト（キャッシュ動作確認）"""
        db_path = str(tmp_path / "test_cache.db")
        db = DictSQLiteV4(db_path)
        
        db["cached_key"] = "cached_value"
        
        # 複数回アクセス
        for _ in range(10):
            result = db["cached_key"]
            assert result == "cached_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
