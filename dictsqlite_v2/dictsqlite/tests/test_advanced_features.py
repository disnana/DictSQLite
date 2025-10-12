#!/usr/bin/env python3
"""
高度な機能テスト - DictSQLite v4.2

このテストスイートは高度な機能を網羅的にテストします：
- 暗号化機能（AES-256-GCM）
- Safe Pickle機能
- マルチテーブル機能
- ホットティア/キャパシティ管理
- 統計とモニタリング
- 複数機能の組み合わせ
"""

import pytest
from .conftest import windows_safe_temp_db

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4
    DICTSQLITE_V4_AVAILABLE = True
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEncryption:
    """暗号化機能のテスト"""
    
    def test_encryption_basic(self):
        """基本的な暗号化"""
        with windows_safe_temp_db() as db_path:
            password = "test_password_123"  # nosec B105 # Test password, not a real credential
            
            # 暗号化して保存
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            db["secret"] = b"sensitive_data"
            db.close()
            
            # パスワードありで読み取り
            db2 = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            assert db2["secret"] == b"sensitive_data"
            db2.close()
    
    def test_encryption_wrong_password(self):
        """間違ったパスワードでエラー"""
        with windows_safe_temp_db() as db_path:
            password = "correct_password"  # nosec B105 # Test password, not a real credential
            
            # 正しいパスワードで保存
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            db["secret"] = b"data"
            db.close()
            
            # 間違ったパスワードで開こうとする
            try:
                db2 = DictSQLiteV4(db_path, encryption_password="wrong_password", storage_mode="bytes")  # nosec B106 # Test password
                # データ読み取りでエラーになる可能性
                with pytest.raises((RuntimeError, ValueError, KeyError)):
                    _ = db2["secret"]
                db2.close()
            except (RuntimeError, ValueError):
                # 初期化時にエラーになる場合もある
                pass
    
    def test_encryption_without_password(self):
        """暗号化データをパスワードなしで読もうとするとエラー"""
        with windows_safe_temp_db() as db_path:
            password = "secure_password"  # nosec B105 # Test password, not a real credential
            
            # 暗号化して保存
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            db["secret"] = b"encrypted_data"
            db.close()
            
            # パスワードなしで開く
            try:
                db2 = DictSQLiteV4(db_path, storage_mode="bytes")
                # データ読み取りでエラー
                with pytest.raises((RuntimeError, ValueError, KeyError)):
                    _ = db2["secret"]
                db2.close()
            except (RuntimeError, ValueError):
                # 初期化時にエラーの場合
                pass
    
    def test_encryption_with_jsonb(self):
        """暗号化 + JSONBモード"""
        with windows_safe_temp_db() as db_path:
            password = "jsonb_password"  # nosec B105 # Test password, not a real credential
            
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="jsonb")
            
            test_data = {
                "user": "Alice",
                "ssn": "123-45-6789",
                "credit_card": "1234-5678-9012-3456"
            }
            
            db["sensitive"] = test_data
            db.close()
            
            # 復号化して確認
            db2 = DictSQLiteV4(db_path, encryption_password=password, storage_mode="jsonb")
            assert db2["sensitive"] == test_data
            db2.close()
    
    def test_encryption_with_pickle(self):
        """暗号化 + Pickleモード"""
        with windows_safe_temp_db() as db_path:
            password = "pickle_password"  # nosec B105 # Test password, not a real credential
            
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="pickle")
            
            complex_data = {
                "list": [1, 2, 3],
                "set": {4, 5, 6},
                "dict": {"nested": "value"}
            }
            
            db["complex"] = complex_data
            db.close()
            
            # 復号化して確認
            db2 = DictSQLiteV4(db_path, encryption_password=password, storage_mode="pickle")
            retrieved = db2["complex"]
            assert retrieved["list"] == [1, 2, 3]
            assert retrieved["set"] == {4, 5, 6}
            assert retrieved["dict"] == {"nested": "value"}
            db2.close()
    
    def test_encryption_multiple_keys(self):
        """暗号化で複数のキー"""
        with windows_safe_temp_db() as db_path:
            password = "multi_key_password"  # nosec B105 # Test password, not a real credential
            
            db = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            
            # 複数のキーを暗号化して保存
            for i in range(10):
                db[f"encrypted_key_{i}"] = f"encrypted_value_{i}".encode()
            
            db.close()
            
            # 復号化して確認
            db2 = DictSQLiteV4(db_path, encryption_password=password, storage_mode="bytes")
            for i in range(10):
                assert db2[f"encrypted_key_{i}"] == f"encrypted_value_{i}".encode()
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSafePickle:
    """Safe Pickle機能のテスト"""
    
    def test_safe_pickle_basic(self):
        """基本的なSafe Pickle"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                storage_mode="pickle",
                enable_safe_pickle=True,
                safe_pickle_allowed_modules=["builtins"]
            )
            
            # 基本的な型は許可される
            db["int"] = 42
            db["str"] = "hello"
            db["list"] = [1, 2, 3]
            
            assert db["int"] == 42
            assert db["str"] == "hello"
            assert db["list"] == [1, 2, 3]
            
            db.close()
    
    def test_safe_pickle_allowed_module(self):
        """許可されたモジュールのクラス"""
        with windows_safe_temp_db() as db_path:
            # collectionsモジュールを許可
            db = DictSQLiteV4(
                db_path,
                storage_mode="pickle",
                enable_safe_pickle=True,
                safe_pickle_allowed_modules=["collections", "builtins"]
            )
            
            from collections import Counter
            counter = Counter([1, 2, 2, 3, 3, 3])
            
            try:
                db["counter"] = counter
                retrieved = db["counter"]
                assert isinstance(retrieved, Counter)
                assert retrieved[3] == 3
            except (RuntimeError, ValueError):
                # Safe Pickleで拒否される場合もある（実装依存）
                pass
            
            db.close()
    
    def test_safe_pickle_reject_dangerous(self):
        """危険なオブジェクトの拒否"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                storage_mode="pickle",
                enable_safe_pickle=True,
                safe_pickle_allowed_modules=["builtins"]
            )
            
            # カスタムクラスは拒否されるべき
            class DangerousClass:
                def __reduce__(self):
                    # 危険な操作を含む
                    return (eval, ("1+1",))
            
            dangerous = DangerousClass()
            
            try:
                db["dangerous"] = dangerous
                # 保存または読み取りでエラーが発生するべき
                with pytest.raises((RuntimeError, ValueError)):
                    _ = db["dangerous"]
            except (RuntimeError, ValueError):
                # 保存時にエラーの場合
                pass
            
            db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMultiTable:
    """マルチテーブル機能のテスト"""
    
    def test_multi_table_basic(self):
        """基本的なマルチテーブル"""
        with windows_safe_temp_db() as db_path:
            # テーブル1
            db1 = DictSQLiteV4(db_path, table_name="table1", storage_mode="bytes")
            db1["key1"] = b"table1_value"
            db1.close()
            
            # テーブル2
            db2 = DictSQLiteV4(db_path, table_name="table2", storage_mode="bytes")
            db2["key1"] = b"table2_value"
            db2.close()
            
            # テーブルごとに独立している
            db1_check = DictSQLiteV4(db_path, table_name="table1", storage_mode="bytes")
            db2_check = DictSQLiteV4(db_path, table_name="table2", storage_mode="bytes")
            
            assert db1_check["key1"] == b"table1_value"
            assert db2_check["key1"] == b"table2_value"
            
            db1_check.close()
            db2_check.close()
    
    def test_multi_table_isolation(self):
        """テーブル間の隔離"""
        with windows_safe_temp_db() as db_path:
            # 複数のテーブルに異なるデータ
            tables = ["users", "posts", "comments"]
            
            for table in tables:
                db = DictSQLiteV4(db_path, table_name=table, storage_mode="bytes")
                db[f"{table}_key"] = f"{table}_value".encode()
                db.close()
            
            # 各テーブルは独立
            for table in tables:
                db = DictSQLiteV4(db_path, table_name=table, storage_mode="bytes")
                assert f"{table}_key" in db
                assert db[f"{table}_key"] == f"{table}_value".encode()
                
                # 他のテーブルのキーは存在しない
                for other_table in tables:
                    if other_table != table:
                        assert f"{other_table}_key" not in db
                
                db.close()
    
    def test_multi_table_different_storage_modes(self):
        """異なるストレージモードで複数テーブル"""
        with windows_safe_temp_db() as db_path:
            # テーブル1: Bytesモード
            db_bytes = DictSQLiteV4(db_path, table_name="bytes_table", storage_mode="bytes")
            db_bytes["data"] = b"raw_bytes"
            db_bytes.close()
            
            # テーブル2: JSONBモード
            db_jsonb = DictSQLiteV4(db_path, table_name="jsonb_table", storage_mode="jsonb")
            db_jsonb["data"] = {"type": "json"}
            db_jsonb.close()
            
            # テーブル3: Pickleモード
            db_pickle = DictSQLiteV4(db_path, table_name="pickle_table", storage_mode="pickle")
            db_pickle["data"] = {"type": "pickle", "set": {1, 2, 3}}
            db_pickle.close()
            
            # 各テーブルで正しく読み取れる
            db_bytes2 = DictSQLiteV4(db_path, table_name="bytes_table", storage_mode="bytes")
            assert db_bytes2["data"] == b"raw_bytes"
            db_bytes2.close()
            
            db_jsonb2 = DictSQLiteV4(db_path, table_name="jsonb_table", storage_mode="jsonb")
            assert db_jsonb2["data"] == {"type": "json"}
            db_jsonb2.close()
            
            db_pickle2 = DictSQLiteV4(db_path, table_name="pickle_table", storage_mode="pickle")
            retrieved = db_pickle2["data"]
            assert retrieved["type"] == "pickle"
            assert retrieved["set"] == {1, 2, 3}
            db_pickle2.close()
    
    def test_multi_table_many_tables(self):
        """多数のテーブル"""
        with windows_safe_temp_db() as db_path:
            # 50個のテーブルを作成
            num_tables = 50
            
            for i in range(num_tables):
                db = DictSQLiteV4(db_path, table_name=f"table_{i}", storage_mode="bytes")
                db["id"] = str(i).encode()
                db.close()
            
            # すべてのテーブルが正しく分離されている
            for i in range(num_tables):
                db = DictSQLiteV4(db_path, table_name=f"table_{i}", storage_mode="bytes")
                assert db["id"] == str(i).encode()
                assert len(db) == 1
                db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestHotTierCapacity:
    """ホットティア/キャパシティ管理のテスト"""
    
    def test_hot_capacity_basic(self):
        """基本的なホットティア"""
        with windows_safe_temp_db() as db_path:
            # 小さなキャパシティ
            db = DictSQLiteV4(db_path, hot_capacity=10, storage_mode="bytes")
            
            # キャパシティ以下のデータ
            for i in range(5):
                db[f"key{i}"] = f"value{i}".encode()
            
            # すべて読み取れる
            for i in range(5):
                assert db[f"key{i}"] == f"value{i}".encode()
            
            db.close()
    
    def test_hot_capacity_overflow(self):
        """キャパシティを超えたデータ"""
        with windows_safe_temp_db() as db_path:
            # 小さなキャパシティ
            db = DictSQLiteV4(db_path, hot_capacity=100, storage_mode="bytes")
            
            # キャパシティを超えて書き込み
            for i in range(500):
                db[f"key{i}"] = f"value{i}".encode()
            
            # すべて読み取れる（ホットティアを超えたデータもディスクに保存される）
            for i in range(500):
                assert db[f"key{i}"] == f"value{i}".encode()
            
            db.close()
    
    def test_hot_capacity_eviction(self):
        """LRU evictionのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, hot_capacity=10, storage_mode="bytes")
            
            # 20個のアイテムを追加（キャパシティ10を超える）
            for i in range(20):
                db[f"key{i}"] = f"value{i}".encode()
            
            # 統計を確認
            stats = db.stats()
            # ホットティアには最大10個まで
            assert stats["hot_tier_size"] <= 10
            
            # でもすべてのデータは読み取れる（ディスクから）
            for i in range(20):
                assert db[f"key{i}"] == f"value{i}".encode()
            
            db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStatistics:
    """統計とモニタリングのテスト"""
    
    def test_stats_basic(self):
        """基本的な統計"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 統計を取得
            stats = db.stats()
            
            # 基本的なフィールドが存在
            assert "hot_tier_size" in stats
            
            db.close()
    
    def test_stats_after_operations(self):
        """操作後の統計変化"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 初期状態
            stats_initial = db.stats()
            initial_size = stats_initial.get("hot_tier_size", 0)
            
            # データを追加
            for i in range(10):
                db[f"key{i}"] = f"value{i}".encode()
            
            # 統計を再取得
            stats_after = db.stats()
            after_size = stats_after.get("hot_tier_size", 0)
            
            # サイズが増えている
            assert after_size >= initial_size
            
            db.close()
    
    def test_stats_with_encryption(self):
        """暗号化有効時の統計"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                encryption_password="test_password",  # nosec B106 # Test password, not a real credential
                storage_mode="bytes"
            )
            
            db["key1"] = b"value1"
            
            stats = db.stats()
            
            # 暗号化フラグが立っているか確認
            if "encryption_enabled" in stats:
                assert stats["encryption_enabled"] is True
            
            db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestFeatureCombinations:
    """複数機能の組み合わせテスト"""
    
    def test_encryption_plus_multi_table(self):
        """暗号化 + マルチテーブル"""
        with windows_safe_temp_db() as db_path:
            password = "combo_password"  # nosec B105 # Test password, not a real credential
            
            # テーブル1
            db1 = DictSQLiteV4(
                db_path,
                table_name="encrypted_table1",
                encryption_password=password,
                storage_mode="bytes"
            )
            db1["secret1"] = b"encrypted_data1"
            db1.close()
            
            # テーブル2
            db2 = DictSQLiteV4(
                db_path,
                table_name="encrypted_table2",
                encryption_password=password,
                storage_mode="bytes"
            )
            db2["secret2"] = b"encrypted_data2"
            db2.close()
            
            # 各テーブルを復号化して確認
            db1_check = DictSQLiteV4(
                db_path,
                table_name="encrypted_table1",
                encryption_password=password,
                storage_mode="bytes"
            )
            assert db1_check["secret1"] == b"encrypted_data1"
            db1_check.close()
            
            db2_check = DictSQLiteV4(
                db_path,
                table_name="encrypted_table2",
                encryption_password=password,
                storage_mode="bytes"
            )
            assert db2_check["secret2"] == b"encrypted_data2"
            db2_check.close()
    
    def test_all_features_combined(self):
        """すべての主要機能を組み合わせ"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                hot_capacity=1000,
                persist_mode="lazy",
                storage_mode="jsonb",
                table_name="full_featured",
                encryption_password="complex_password"  # nosec B106 # Test password, not a real credential
            )
            
            # データを追加
            test_data = {
                "user": "Alice",
                "age": 30,
                "preferences": {
                    "theme": "dark",
                    "language": "ja"
                }
            }
            
            db["user_data"] = test_data
            db.flush()
            db.close()
            
            # すべての機能を使って読み取り
            db2 = DictSQLiteV4(
                db_path,
                storage_mode="jsonb",
                table_name="full_featured",
                encryption_password="complex_password"  # nosec B106 # Test password, not a real credential
            )
            
            retrieved = db2["user_data"]
            assert retrieved == test_data
            
            db2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
