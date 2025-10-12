#!/usr/bin/env python3
"""
ストレージモードテスト - DictSQLite v4.2

このテストスイートは各ストレージモードを網羅的にテストします：
- Pickleモード: Pythonオブジェクトの直列化
- JSONBモード: JSONオブジェクトの保存（バイナリ）
- JSONモード: JSONオブジェクトの保存（テキスト）
- Bytesモード: 生のバイト列の保存
- モード間の互換性と変換
"""

import pytest
import tempfile
import os
from .conftest import windows_safe_temp_db

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4
    DICTSQLITE_V4_AVAILABLE = True
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBytesMode:
    """Bytesモードのテスト"""
    
    def test_bytes_basic(self):
        """基本的なバイト列の保存と取得"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 単純なバイト列
            db["key1"] = b"hello"
            assert db["key1"] == b"hello"
            
            # 空のバイト列
            db["empty"] = b""
            assert db["empty"] == b""
            
            # バイナリデータ
            db["binary"] = bytes([0, 1, 2, 255])
            assert db["binary"] == bytes([0, 1, 2, 255])
            
            db.close()
    
    def test_bytes_all_byte_values(self):
        """すべてのバイト値（0-255）のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            all_bytes = bytes(range(256))
            db["all_bytes"] = all_bytes
            assert db["all_bytes"] == all_bytes
            
            db.close()
    
    def test_bytes_large_value(self):
        """大きなバイト列のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 1MBのデータ
            large_data = b"x" * (1024 * 1024)
            db["large"] = large_data
            assert db["large"] == large_data
            
            db.close()
    
    def test_bytes_persistence(self):
        """Bytesモードでの永続化"""
        with windows_safe_temp_db() as db_path:
            # データを書き込む
            db1 = DictSQLiteV4(db_path, storage_mode="bytes")
            db1["key1"] = b"persistent_value"
            db1.close()
            
            # 再度開いて確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"persistent_value"
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPickleMode:
    """Pickleモードのテスト"""
    
    def test_pickle_python_dict(self):
        """Python辞書の保存"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            test_dict = {"name": "Alice", "age": 30, "city": "Tokyo"}
            db["user"] = test_dict
            
            retrieved = db["user"]
            assert retrieved == test_dict
            assert isinstance(retrieved, dict)
            
            db.close()
    
    def test_pickle_python_list(self):
        """Pythonリストの保存"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            test_list = [1, 2, 3, "four", 5.0, None]
            db["list"] = test_list
            
            retrieved = db["list"]
            assert retrieved == test_list
            assert isinstance(retrieved, list)
            
            db.close()
    
    def test_pickle_nested_structures(self):
        """ネストされた構造の保存"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            nested = {
                "users": [
                    {"name": "Alice", "scores": [90, 85, 92]},
                    {"name": "Bob", "scores": [88, 91, 87]},
                ],
                "metadata": {
                    "version": 1,
                    "timestamp": "2024-01-01",
                }
            }
            
            db["data"] = nested
            retrieved = db["data"]
            assert retrieved == nested
            
            db.close()
    
    def test_pickle_various_types(self):
        """様々なPython型の保存"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # 数値
            db["int"] = 42
            db["float"] = 3.14159
            db["bool"] = True
            
            # 文字列
            db["str"] = "hello"
            db["unicode"] = "こんにちは🎉"
            
            # None
            db["none"] = None
            
            # タプル
            db["tuple"] = (1, 2, 3)
            
            # セット
            db["set"] = {1, 2, 3}
            
            # 取得して確認
            assert db["int"] == 42
            assert db["float"] == 3.14159
            assert db["bool"] is True
            assert db["str"] == "hello"
            assert db["unicode"] == "こんにちは🎉"
            assert db["none"] is None
            assert db["tuple"] == (1, 2, 3)
            assert db["set"] == {1, 2, 3}
            
            db.close()
    
    def test_pickle_persistence(self):
        """Pickleモードでの永続化"""
        with windows_safe_temp_db() as db_path:
            # データを書き込む
            db1 = DictSQLiteV4(db_path, storage_mode="pickle")
            test_data = {"key": "value", "number": 123}
            db1["data"] = test_data
            db1.close()
            
            # 再度開いて確認
            db2 = DictSQLiteV4(db_path, storage_mode="pickle")
            assert db2["data"] == test_data
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestJSONBMode:
    """JSONBモードのテスト"""
    
    def test_jsonb_dict(self):
        """JSON辞書の保存"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            test_dict = {"name": "Alice", "age": 30, "active": True}
            db["user"] = test_dict
            
            retrieved = db["user"]
            assert retrieved == test_dict
            
            db.close()
    
    def test_jsonb_list(self):
        """JSONリストの保存"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            test_list = [1, 2, 3, "four", 5.5, True, None]
            db["list"] = test_list
            
            retrieved = db["list"]
            assert retrieved == test_list
            
            db.close()
    
    def test_jsonb_nested(self):
        """ネストされたJSON構造"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            nested = {
                "user": {
                    "name": "Alice",
                    "address": {
                        "city": "Tokyo",
                        "country": "Japan"
                    }
                },
                "items": [1, 2, 3]
            }
            
            db["data"] = nested
            retrieved = db["data"]
            assert retrieved == nested
            
            db.close()
    
    def test_jsonb_unicode(self):
        """Unicodeデータのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            unicode_data = {
                "japanese": "こんにちは",
                "emoji": "🎉🎊🎈",
                "mixed": "Hello世界🌏"
            }
            
            db["unicode"] = unicode_data
            retrieved = db["unicode"]
            assert retrieved == unicode_data
            
            db.close()
    
    def test_jsonb_numeric_precision(self):
        """数値の精度テスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            numbers = {
                "int": 42,
                "float": 3.14159,
                "negative": -100,
                "zero": 0,
                "large": 1000000000,
            }
            
            db["numbers"] = numbers
            retrieved = db["numbers"]
            
            assert retrieved["int"] == 42
            assert abs(retrieved["float"] - 3.14159) < 0.00001
            assert retrieved["negative"] == -100
            assert retrieved["zero"] == 0
            assert retrieved["large"] == 1000000000
            
            db.close()
    
    def test_jsonb_null_values(self):
        """null値のテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            data_with_null = {
                "field1": "value",
                "field2": None,
                "field3": [1, None, 3],
            }
            
            db["nulls"] = data_with_null
            retrieved = db["nulls"]
            assert retrieved == data_with_null
            assert retrieved["field2"] is None
            
            db.close()
    
    def test_jsonb_empty_containers(self):
        """空のコンテナのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            db["empty_dict"] = {}
            db["empty_list"] = []
            
            assert db["empty_dict"] == {}
            assert db["empty_list"] == []
            
            db.close()
    
    def test_jsonb_persistence(self):
        """JSONBモードでの永続化"""
        with windows_safe_temp_db() as db_path:
            # データを書き込む
            db1 = DictSQLiteV4(db_path, storage_mode="jsonb")
            test_data = {"key": "value", "number": 123, "list": [1, 2, 3]}
            db1["data"] = test_data
            db1.close()
            
            # 再度開いて確認
            db2 = DictSQLiteV4(db_path, storage_mode="jsonb")
            assert db2["data"] == test_data
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestJSONMode:
    """JSONモードのテスト（もし実装されている場合）"""
    
    def test_json_basic(self):
        """基本的なJSON操作"""
        with windows_safe_temp_db() as db_path:
            try:
                db = DictSQLiteV4(db_path, storage_mode="json")
                
                test_dict = {"name": "Alice", "age": 30}
                db["user"] = test_dict
                
                retrieved = db["user"]
                assert retrieved == test_dict
                
                db.close()
            except (ValueError, RuntimeError):
                # JSONモードが実装されていない場合はスキップ
                pytest.skip("JSON mode not implemented")


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStorageModeComparison:
    """ストレージモード間の比較テスト"""
    
    def test_bytes_vs_pickle_for_bytes(self):
        """バイト列の保存: BytesモードとPickleモードの比較"""
        with windows_safe_temp_db() as db_path1, windows_safe_temp_db() as db_path2:
            # Bytesモード
            db_bytes = DictSQLiteV4(db_path1, storage_mode="bytes")
            db_bytes["data"] = b"test_bytes"
            bytes_result = db_bytes["data"]
            db_bytes.close()
            
            # Pickleモード
            db_pickle = DictSQLiteV4(db_path2, storage_mode="pickle")
            db_pickle["data"] = b"test_bytes"
            pickle_result = db_pickle["data"]
            db_pickle.close()
            
            # どちらも同じバイト列が返る
            assert bytes_result == b"test_bytes"
            assert pickle_result == b"test_bytes"
    
    def test_pickle_vs_jsonb_for_dict(self):
        """辞書の保存: PickleモードとJSONBモードの比較"""
        with windows_safe_temp_db() as db_path1, windows_safe_temp_db() as db_path2:
            test_dict = {"name": "Alice", "age": 30, "active": True}
            
            # Pickleモード
            db_pickle = DictSQLiteV4(db_path1, storage_mode="pickle")
            db_pickle["data"] = test_dict
            pickle_result = db_pickle["data"]
            db_pickle.close()
            
            # JSONBモード
            db_jsonb = DictSQLiteV4(db_path2, storage_mode="jsonb")
            db_jsonb["data"] = test_dict
            jsonb_result = db_jsonb["data"]
            db_jsonb.close()
            
            # どちらも同じ辞書が返る
            assert pickle_result == test_dict
            assert jsonb_result == test_dict
    
    def test_mode_specific_capabilities(self):
        """モード固有の機能のテスト"""
        with windows_safe_temp_db() as db_path:
            # Pickleモードはセットを保存できる
            db_pickle = DictSQLiteV4(db_path, storage_mode="pickle")
            db_pickle["set_data"] = {1, 2, 3}
            assert db_pickle["set_data"] == {1, 2, 3}
            db_pickle.close()
        
        with windows_safe_temp_db() as db_path:
            # JSONBモードはセットを保存できない（リストに変換されるか、エラー）
            db_jsonb = DictSQLiteV4(db_path, storage_mode="jsonb")
            try:
                db_jsonb["set_data"] = {1, 2, 3}
                # セットがリストに変換される可能性がある
                result = db_jsonb["set_data"]
                # リストとして保存されている場合
                assert isinstance(result, list) or isinstance(result, set)
            except (TypeError, ValueError):
                # エラーが発生する場合もOK
                pass
            finally:
                db_jsonb.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStorageModeEdgeCases:
    """ストレージモードのエッジケース"""
    
    def test_bytes_mode_with_dict_fails(self):
        """Bytesモードで辞書を保存しようとするとエラー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 辞書は保存できない
            with pytest.raises((TypeError, ValueError, RuntimeError)):
                db["dict"] = {"key": "value"}
            
            db.close()
    
    def test_jsonb_mode_with_non_json_serializable(self):
        """JSONBモードでJSON非対応オブジェクトを保存しようとするとエラー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            # カスタムクラスは保存できない
            class CustomClass:
                pass
            
            with pytest.raises((TypeError, ValueError, RuntimeError)):
                db["custom"] = CustomClass()
            
            db.close()
    
    def test_pickle_mode_custom_class(self):
        """Pickleモードではカスタムクラスも保存可能"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # シンプルなデータクラス
            class SimpleData:
                def __init__(self, value):
                    self.value = value
                
                def __eq__(self, other):
                    return isinstance(other, SimpleData) and self.value == other.value
            
            data = SimpleData(42)
            db["custom"] = data
            
            retrieved = db["custom"]
            assert isinstance(retrieved, SimpleData)
            assert retrieved.value == 42
            
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
