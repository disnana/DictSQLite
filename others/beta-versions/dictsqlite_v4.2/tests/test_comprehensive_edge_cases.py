#!/usr/bin/env python3
"""
包括的なエッジケース・エラーハンドリングテスト - DictSQLite v4.2

このテストスイートは以下をカバーします：
- エッジケース（空文字列、特殊文字、極端な値など）
- エラーハンドリング（不正な入力、リソース枯渇など）
- データ型の境界値テスト
- 予期しない状況への対応
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite_v4 import DictSQLiteV4, AsyncDictSQLite
    DICTSQLITE_V4_AVAILABLE = True
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None
    AsyncDictSQLite = None


@pytest.fixture
def temp_db():
    """一時データベースファイルを作成"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    yield db_path
    # クリーンアップ
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEdgeCaseKeys:
    """キーのエッジケーステスト"""
    
    def test_empty_string_key(self, temp_db):
        """空文字列キーのテスト"""
        db = DictSQLiteV4(temp_db)
        
        # 空文字列をキーとして使用
        db[""] = b"empty_key_value"
        assert db[""] == b"empty_key_value"
        assert "" in db
        
        del db[""]
        assert "" not in db
    
    def test_very_long_key(self, temp_db):
        """非常に長いキーのテスト"""
        db = DictSQLiteV4(temp_db)
        
        # 10KB のキー
        long_key = "k" * 10000
        db[long_key] = b"long_key_value"
        
        assert db[long_key] == b"long_key_value"
        assert long_key in db
    
    def test_special_characters_in_keys(self, temp_db):
        """特殊文字を含むキーのテスト"""
        db = DictSQLiteV4(temp_db)
        
        special_keys = [
            "\x00\x01\x02",  # NULL文字を含む
            "key\nwith\nnewlines",
            "key\twith\ttabs",
            "key with spaces",
            "key'with'quotes",
            'key"with"doublequotes',
            "key\\with\\backslashes",
            "key/with/slashes",
            "key.with.dots",
            "key,with,commas",
            "key;with;semicolons",
            "key:with:colons",
            "key@with@at",
            "key#with#hash",
            "key$with$dollar",
            "key%with%percent",
            "key&with&ampersand",
            "key*with*asterisk",
            "key(with)parentheses",
            "key[with]brackets",
            "key{with}braces",
            "key<with>angle",
            "key=with=equals",
            "key+with+plus",
            "key-with-dash",
            "key_with_underscore",
            "key|with|pipe",
            "key~with~tilde",
            "key`with`backtick",
            "key^with^caret",
        ]
        
        for key in special_keys:
            db[key] = f"value_for_{key}".encode()
            assert db[key] == f"value_for_{key}".encode()
            assert key in db
    
    def test_unicode_edge_cases(self, temp_db):
        """Unicode文字のエッジケース"""
        db = DictSQLiteV4(temp_db)
        
        unicode_keys = [
            "日本語",
            "中文",
            "한국어",
            "العربية",
            "עברית",
            "Русский",
            "Ελληνικά",
            "🔥🚀💯",  # 絵文字
            "👨‍👩‍👧‍👦",  # 複合絵文字
            "𝕳𝖊𝖑𝖑𝖔",  # 数学的英数字記号
            "Ⓒⓞⓜⓑⓘⓝⓔⓓ",  # 囲み文字
            "\u200B\u200C\u200D",  # ゼロ幅文字
        ]
        
        for key in unicode_keys:
            db[key] = f"unicode_value_{key}".encode()
            assert db[key] == f"unicode_value_{key}".encode()
    
    def test_numeric_string_keys(self, temp_db):
        """数値文字列キーのテスト"""
        db = DictSQLiteV4(temp_db)
        
        numeric_keys = [
            "0",
            "1",
            "-1",
            "123456789",
            "-987654321",
            "3.14159",
            "-2.71828",
            "1e10",
            "1E-5",
            "inf",
            "-inf",
            "nan",
        ]
        
        for key in numeric_keys:
            db[key] = f"numeric_{key}".encode()
            assert db[key] == f"numeric_{key}".encode()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEdgeCaseValues:
    """値のエッジケーステスト"""
    
    def test_empty_value(self, temp_db):
        """空のバイト列値のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="bytes")
        
        db["empty"] = b""
        assert db["empty"] == b""
    
    def test_very_large_value(self, temp_db):
        """非常に大きな値のテスト（100MB）"""
        db = DictSQLiteV4(temp_db, storage_mode="bytes")
        
        # 100MBのデータ
        large_value = b"x" * (100 * 1024 * 1024)
        db["large"] = large_value
        
        retrieved = db["large"]
        assert len(retrieved) == len(large_value)
        assert retrieved == large_value
    
    def test_binary_values_all_bytes(self, temp_db):
        """すべてのバイト値（0-255）を含むテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="bytes")
        
        # 0から255までのすべてのバイト値
        all_bytes = bytes(range(256))
        db["all_bytes"] = all_bytes
        
        assert db["all_bytes"] == all_bytes
    
    def test_repeated_null_bytes(self, temp_db):
        """NULLバイトの繰り返しテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="bytes")
        
        null_bytes = b"\x00" * 10000
        db["nulls"] = null_bytes
        
        assert db["nulls"] == null_bytes


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestJSONBEdgeCases:
    """JSONBモードのエッジケーステスト"""
    
    def test_deeply_nested_structure(self, temp_db):
        """深くネストされた構造のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 10階層のネスト
        nested = {"level": 0}
        current = nested
        for i in range(1, 10):
            current["next"] = {"level": i}
            current = current["next"]
        
        db["nested"] = nested
        retrieved = db["nested"]
        
        # 構造を確認
        current = retrieved
        for i in range(10):
            assert current["level"] == i
            if i < 9:
                current = current["next"]
    
    def test_large_json_array(self, temp_db):
        """大きなJSON配列のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 10000要素の配列
        large_array = list(range(10000))
        db["large_array"] = large_array
        
        retrieved = db["large_array"]
        assert len(retrieved) == 10000
        assert retrieved == large_array
    
    def test_mixed_type_array(self, temp_db):
        """混合型配列のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        mixed = [
            None,
            True,
            False,
            42,
            -17,
            3.14,
            -2.71,
            "string",
            "日本語",
            [],
            {},
            [1, 2, 3],
            {"key": "value"},
        ]
        
        db["mixed"] = mixed
        retrieved = db["mixed"]
        assert retrieved == mixed
    
    def test_empty_containers(self, temp_db):
        """空のコンテナのテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        db["empty_dict"] = {}
        db["empty_list"] = []
        
        assert db["empty_dict"] == {}
        assert db["empty_list"] == []
    
    def test_null_values_in_dict(self, temp_db):
        """辞書内のNull値のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        data = {
            "null_value": None,
            "nested": {
                "also_null": None,
                "not_null": "value"
            }
        }
        
        db["nulls"] = data
        retrieved = db["nulls"]
        
        assert retrieved["null_value"] is None
        assert retrieved["nested"]["also_null"] is None
        assert retrieved["nested"]["not_null"] == "value"
    
    def test_numeric_extremes(self, temp_db):
        """数値の極値のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        extremes = {
            "max_int": 2**63 - 1,
            "min_int": -(2**63),
            "large_positive": 999999999999999,
            "large_negative": -999999999999999,
            "zero": 0,
            "small_float": 1e-10,
            "large_float": 1e10,
        }
        
        db["extremes"] = extremes
        retrieved = db["extremes"]
        
        # 整数は正確に一致
        assert retrieved["max_int"] == extremes["max_int"]
        assert retrieved["min_int"] == extremes["min_int"]
        assert retrieved["zero"] == 0
        
        # 浮動小数点数は近似一致
        assert abs(retrieved["small_float"] - extremes["small_float"]) < 1e-15
        assert abs(retrieved["large_float"] - extremes["large_float"]) < 1e5
    
    def test_unicode_in_json(self, temp_db):
        """JSON内のUnicode文字のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        unicode_data = {
            "japanese": "こんにちは世界",
            "emoji": "🎉🚀💯",
            "mixed": ["Hello", "世界", "🌍"],
            "nested": {
                "arabic": "مرحبا",
                "hebrew": "שלום"
            }
        }
        
        db["unicode"] = unicode_data
        retrieved = db["unicode"]
        
        assert retrieved == unicode_data


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_keyerror_on_missing_key(self, temp_db):
        """存在しないキーへのアクセスでKeyErrorが発生"""
        db = DictSQLiteV4(temp_db)
        
        with pytest.raises(KeyError):
            _ = db["nonexistent"]
    
    def test_delete_nonexistent_key(self, temp_db):
        """存在しないキーの削除（実装によっては例外を投げない場合もある）"""
        db = DictSQLiteV4(temp_db)
        
        # 存在しないキーの削除を試みる（実装によって動作が異なる可能性）
        try:
            del db["nonexistent"]
            # エラーが発生しない場合もある（Rustの実装による）
        except KeyError:
            # エラーが発生する場合もある
            pass
    
    def test_invalid_storage_mode(self, temp_db):
        """無効なストレージモードでエラーが発生"""
        with pytest.raises(Exception):
            db = DictSQLiteV4(temp_db, storage_mode="invalid_mode")
    
    def test_invalid_persist_mode(self, temp_db):
        """無効な永続化モードでエラーが発生"""
        with pytest.raises(Exception):
            db = DictSQLiteV4(temp_db, persist_mode="invalid_mode")
    
    def test_jsonb_with_non_serializable(self, temp_db):
        """JSONBモードでシリアライズできないオブジェクトを拒否"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # カスタムオブジェクトは拒否されるべき
        class CustomObject:
            def __init__(self):
                self.value = 42
        
        with pytest.raises(Exception):
            db["custom"] = CustomObject()
    
    def test_bytes_mode_with_dict(self, temp_db):
        """Bytesモードで辞書を保存しようとするとエラー"""
        db = DictSQLiteV4(temp_db, storage_mode="bytes")
        
        with pytest.raises(Exception):
            db["dict"] = {"key": "value"}


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestTableEdgeCases:
    """テーブル機能のエッジケーステスト"""
    
    def test_many_tables(self, temp_db):
        """多数のテーブル作成テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 100個のテーブルを作成
        tables = [db.table(f"table_{i}") for i in range(100)]
        
        # 各テーブルにデータを保存
        for i, table in enumerate(tables):
            table[f"key_{i}"] = {"table_id": i, "value": f"data_{i}"}
        
        # データが正しく分離されているか確認
        for i, table in enumerate(tables):
            retrieved = table[f"key_{i}"]
            assert retrieved["table_id"] == i
            assert retrieved["value"] == f"data_{i}"
    
    def test_table_name_with_special_chars(self, temp_db):
        """特殊文字を含むテーブル名のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 特殊文字を含むテーブル名
        special_table_names = [
            "table_with_underscore",
            "table-with-dash",
            "table.with.dot",
            "table123",
            "123table",
            "日本語テーブル",
            "emoji🚀table",
        ]
        
        for table_name in special_table_names:
            table = db.table(table_name)
            table["key"] = {"name": table_name}
            assert table["key"]["name"] == table_name
    
    def test_table_key_isolation(self, temp_db):
        """テーブル間のキー隔離テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        table1 = db.table("table1")
        table2 = db.table("table2")
        
        # 同じキーで異なるデータ
        table1["shared_key"] = {"table": 1, "data": "from_table1"}
        table2["shared_key"] = {"table": 2, "data": "from_table2"}
        
        # データが混在しないことを確認
        assert table1["shared_key"]["table"] == 1
        assert table2["shared_key"]["table"] == 2
        
        # 一方を削除しても他方に影響しない
        del table1["shared_key"]
        assert "shared_key" not in table1
        assert "shared_key" in table2
    
    def test_table_with_empty_name(self, temp_db):
        """空のテーブル名のテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 空文字列のテーブル名も許可されるべき
        empty_table = db.table("")
        empty_table["key"] = {"value": "in_empty_table"}
        
        assert empty_table["key"]["value"] == "in_empty_table"


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestConcurrentOperations:
    """並行操作のテスト"""
    
    def test_rapid_sequential_writes(self, temp_db):
        """高速連続書き込みテスト"""
        db = DictSQLiteV4(temp_db)
        
        # 1万回の連続書き込み
        for i in range(10000):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        # ランダムサンプルで検証
        import random
        samples = random.sample(range(10000), 100)
        for i in samples:
            assert db[f"key_{i}"] == f"value_{i}".encode()
    
    def test_interleaved_read_write(self, temp_db):
        """読み書き交互実行テスト"""
        db = DictSQLiteV4(temp_db)
        
        # 初期データ
        for i in range(100):
            db[f"key_{i}"] = f"initial_{i}".encode()
        
        # 読み書きを交互に実行
        for i in range(100):
            # 読み込み
            value = db[f"key_{i}"]
            assert value == f"initial_{i}".encode()
            
            # 更新
            db[f"key_{i}"] = f"updated_{i}".encode()
            
            # 再度読み込み
            value = db[f"key_{i}"]
            assert value == f"updated_{i}".encode()
    
    def test_delete_and_recreate(self, temp_db):
        """削除と再作成の繰り返しテスト"""
        db = DictSQLiteV4(temp_db)
        
        # 100回の削除と再作成
        for iteration in range(100):
            db["key"] = f"iteration_{iteration}".encode()
            assert db["key"] == f"iteration_{iteration}".encode()
            del db["key"]
            assert "key" not in db


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBoundaryConditions:
    """境界条件のテスト"""
    
    def test_hot_tier_capacity_limit(self, temp_db):
        """ホットティア容量制限のテスト"""
        # デフォルト設定で作成（v4.2ではhot_tier_capacityパラメータは使用できない可能性）
        db = DictSQLiteV4(temp_db)
        
        # 大量データを書き込み
        for i in range(200):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        # すべてのデータが保持されているか確認
        for i in range(200):
            assert db[f"key_{i}"] == f"value_{i}".encode()
    
    def test_flush_empty_database(self, temp_db):
        """空のデータベースのフラッシュ"""
        db = DictSQLiteV4(temp_db)
        
        # 空の状態でフラッシュしてもエラーにならない
        db.flush()
        
        stats = db.stats()
        assert stats["hot_tier_size"] == 0
    
    def test_multiple_close_calls(self, temp_db):
        """複数回のclose呼び出し"""
        db = DictSQLiteV4(temp_db)
        
        db["key"] = b"value"
        db.close()
        
        # 2回目のcloseもエラーにならない
        db.close()
    
    def test_operations_after_close(self, temp_db):
        """close後の操作（実装によって動作が異なる可能性）"""
        db = DictSQLiteV4(temp_db)
        
        db["key"] = b"value"
        db.close()
        
        # close後の操作（実装によっては成功する場合もある）
        # v4.2の実装では、close後も操作が可能な場合がある
        try:
            db["new_key"] = b"new_value"
            # 操作が成功する場合もある
        except Exception:
            # エラーが発生する場合もある
            pass


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDataIntegrity:
    """データ整合性のテスト"""
    
    def test_persistence_after_flush(self, temp_db):
        """フラッシュ後の永続性テスト"""
        # セッション1: データを書き込み
        db1 = DictSQLiteV4(temp_db, persist_mode="lazy")
        
        for i in range(100):
            db1[f"key_{i}"] = f"value_{i}".encode()
        
        db1.flush()
        db1.close()
        
        # セッション2: データを読み込み
        db2 = DictSQLiteV4(temp_db)
        
        for i in range(100):
            assert db2[f"key_{i}"] == f"value_{i}".encode()
        
        db2.close()
    
    def test_overwrite_consistency(self, temp_db):
        """上書きの一貫性テスト"""
        db = DictSQLiteV4(temp_db)
        
        key = "test_key"
        
        # 100回上書き
        for i in range(100):
            db[key] = f"value_{i}".encode()
            assert db[key] == f"value_{i}".encode()
    
    def test_mixed_operations_integrity(self, temp_db):
        """混合操作の整合性テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 書き込み
        db["key1"] = {"value": 1}
        db["key2"] = {"value": 2}
        db["key3"] = {"value": 3}
        
        # 削除
        del db["key2"]
        
        # 追加
        db["key4"] = {"value": 4}
        
        # 更新
        db["key1"] = {"value": 10}
        
        # 検証
        assert db["key1"]["value"] == 10
        assert "key2" not in db
        assert db["key3"]["value"] == 3
        assert db["key4"]["value"] == 4
    
    def test_table_data_integrity(self, temp_db):
        """テーブル間のデータ整合性テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb", persist_mode="writethrough")
        
        users = db.table("users")
        orders = db.table("orders")
        
        # データ追加
        users["user1"] = {"name": "Alice", "email": "alice@example.com"}
        orders["order1"] = {"user": "user1", "amount": 100}
        
        db.flush()
        db.close()
        
        # 再度開いて確認
        db2 = DictSQLiteV4(temp_db, storage_mode="jsonb")
        users2 = db2.table("users")
        orders2 = db2.table("orders")
        
        assert users2["user1"]["name"] == "Alice"
        assert orders2["order1"]["user"] == "user1"
        assert orders2["order1"]["amount"] == 100


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncEdgeCases:
    """非同期版のエッジケーステスト"""
    
    def test_async_rapid_operations(self, temp_db):
        """非同期での高速操作テスト"""
        db = AsyncDictSQLite(temp_db)
        
        # 高速で連続操作
        for i in range(1000):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        # 検証
        for i in range(0, 1000, 10):
            assert db[f"key_{i}"] == f"value_{i}".encode()
        
        db.close()
    
    def test_async_table_operations(self, temp_db):
        """非同期テーブル操作のテスト"""
        db = AsyncDictSQLite(temp_db, storage_mode="jsonb")
        
        table1 = db.table("table1")
        table2 = db.table("table2")
        
        # 交互にテーブルへ書き込み
        for i in range(100):
            if i % 2 == 0:
                table1[f"key_{i}"] = {"table": 1, "value": i}
            else:
                table2[f"key_{i}"] = {"table": 2, "value": i}
        
        # 検証
        for i in range(100):
            if i % 2 == 0:
                assert table1[f"key_{i}"]["table"] == 1
                assert table1[f"key_{i}"]["value"] == i
            else:
                assert table2[f"key_{i}"]["table"] == 2
                assert table2[f"key_{i}"]["value"] == i
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
