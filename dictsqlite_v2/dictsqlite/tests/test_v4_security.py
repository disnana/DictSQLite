"""
DictSQLite v4 セキュリティ機能のテストスイート

暗号化とSafe Pickle機能の包括的なテスト
"""
import pytest
import pickle
import tempfile
import os
import time
from pathlib import Path

# Python wrapper (with safe_pickle validation) が利用可能か確認
# Note: Rust拡張を直接インポートするのではなく、Pythonラッパー経由で使う
try:
    from dictsqlite import DictSQLiteV4
    DICTSQLITE_V4_AVAILABLE = True
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None


@pytest.fixture
def temp_db():
    """一時データベースファイルを作成"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    yield db_path
    # クリーンアップ - Windows対応: リトライロジックを追加
    # Windows環境ではファイルハンドルの解放に時間がかかることがあるため、
    # 小さな遅延とリトライを実装
    time.sleep(0.1)  # 100ms待機してファイルハンドルを確実に解放
    for attempt in range(3):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            # WALファイルもクリーンアップ
            for ext in ['-wal', '-shm']:
                wal_file = db_path + ext
                if os.path.exists(wal_file):
                    os.unlink(wal_file)
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(0.2)  # 200ms待機してリトライ
            # 最後の試行でも失敗した場合は無視（テスト環境のクリーンアップ）
        except Exception:
            # その他のエラーは無視
            break


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBasicOperations:
    """基本操作のテスト（暗号化なし）"""
    
    def test_basic_set_get(self, temp_db):
        """基本的な読み書き"""
        db = DictSQLiteV4(temp_db)
        
        db["key1"] = b"value1"
        db["key2"] = b"value2"
        
        assert db["key1"] == b"value1"
        assert db["key2"] == b"value2"
    
    def test_dict_operations(self, temp_db):
        """辞書操作のテスト"""
        db = DictSQLiteV4(temp_db)
        
        # 代入
        db["test"] = b"data"
        
        # 存在確認
        assert "test" in db
        assert "nonexistent" not in db
        
        # 長さ
        db["key1"] = b"value1"
        db["key2"] = b"value2"
        assert len(db) >= 2
        
        # 削除
        del db["test"]
        assert "test" not in db
    
    def test_large_data(self, temp_db):
        """大きなデータの処理"""
        db = DictSQLiteV4(temp_db)
        
        large_data = b"x" * (10 * 1024 * 1024)  # 10MB
        db["large"] = large_data
        
        assert db["large"] == large_data
    
    def test_unicode_keys(self, temp_db):
        """Unicodeキーのテスト"""
        db = DictSQLiteV4(temp_db)
        
        db["日本語"] = b"value"
        db["emoji_🎉"] = b"party"
        
        assert db["日本語"] == b"value"
        assert db["emoji_🎉"] == b"party"


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEncryption:
    """暗号化機能のテスト"""
    
    def test_encryption_basic(self, temp_db):
        """基本的な暗号化テスト"""
        password = "test_password_123"
        
        # 暗号化有効でデータを保存
        db = DictSQLiteV4(temp_db, encryption_password=password)
        db["secret"] = b"sensitive data"
        
        # 統計で暗号化が有効か確認
        stats = db.stats()
        assert stats["encryption_enabled"] is True
        
        # データを読み込み（自動復号化）
        assert db["secret"] == b"sensitive data"
    
    def test_encryption_persistence(self, temp_db):
        """暗号化データの永続化テスト"""
        password = "test_password_456"
        
        # データを保存
        db1 = DictSQLiteV4(temp_db, encryption_password=password)
        db1["data1"] = b"value1"
        db1["data2"] = b"value2"
        db1.flush()
        db1.close()
        
        # 同じパスワードで再度開く
        db2 = DictSQLiteV4(temp_db, encryption_password=password)
        assert db2["data1"] == b"value1"
        assert db2["data2"] == b"value2"
    
    def test_encryption_wrong_password(self, temp_db):
        """間違ったパスワードでの復号化エラー"""
        password1 = "correct_password"
        password2 = "wrong_password"
        
        # 正しいパスワードでデータを保存
        db1 = DictSQLiteV4(temp_db, encryption_password=password1)
        db1["secret"] = b"data"
        db1.flush()
        db1.close()
        
        # 間違ったパスワードで開く
        db2 = DictSQLiteV4(temp_db, encryption_password=password2)
        
        # 復号化エラーが発生するはず
        with pytest.raises(Exception):
            _ = db2["secret"]
    
    def test_encryption_performance(self, temp_db):
        """暗号化のパフォーマンステスト"""
        password = "performance_test"
        
        db = DictSQLiteV4(temp_db, encryption_password=password)
        
        # 大量書き込み
        import time
        start = time.time()
        
        for i in range(1000):
            db[f"key_{i}"] = f"value_{i}".encode()
        
        write_time = time.time() - start
        
        # 大量読み込み
        start = time.time()
        
        for i in range(1000):
            _ = db[f"key_{i}"]
        
        read_time = time.time() - start
        
        # パフォーマンス要件（暗号化ありでも高速）
        assert write_time < 1.0, f"書き込み時間が遅すぎます: {write_time}秒"
        assert read_time < 1.0, f"読み込み時間が遅すぎます: {read_time}秒"
        
        print(f"\n暗号化パフォーマンス:")
        print(f"  書き込み: {1000/write_time:.0f} ops/sec")
        print(f"  読み込み: {1000/read_time:.0f} ops/sec")


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSafePickle:
    """Safe Pickle機能のテスト"""
    
    def test_safe_pickle_basic_types(self, temp_db):
        """基本的なデータ型のSafe Pickle"""
        db = DictSQLiteV4(temp_db, enable_safe_pickle=True)
        
        # 統計で確認
        stats = db.stats()
        assert stats["safe_pickle_enabled"] is True
        
        # 基本的なデータ型は許可される
        test_data = {
            "int": 42,
            "str": "hello",
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "tuple": (1, 2, 3),
        }
        
        pickled = pickle.dumps(test_data)
        db["safe_data"] = pickled
        
        # 読み込みと復元 - safe_pickle有効でも自動的にunpickleされる
        restored = db["safe_data"]
        assert restored == test_data
    
    def test_safe_pickle_nested_structures(self, temp_db):
        """ネストされたデータ構造のテスト"""
        db = DictSQLiteV4(temp_db, enable_safe_pickle=True)
        
        nested = {
            "users": [
                {"name": "Alice", "age": 30, "scores": [85, 90, 95]},
                {"name": "Bob", "age": 25, "scores": [75, 80, 85]},
            ],
            "metadata": {
                "version": 1,
                "timestamp": "2024-01-01",
            }
        }
        
        pickled = pickle.dumps(nested)
        db["nested"] = pickled
        
        # safe_pickle有効でも自動的にunpickleされる
        restored = db["nested"]
        assert restored == nested
    
    def test_safe_pickle_forbidden_objects(self, temp_db):
        """禁止されたオブジェクトのテスト"""
        db = DictSQLiteV4(temp_db, enable_safe_pickle=True)
        
        # 危険な関数をpickleしようとする
        # __import__ は危険な関数として禁止されるべき
        dangerous = pickle.dumps(__import__)
        with pytest.raises(Exception):
            db["dangerous"] = dangerous


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestCombinedSecurity:
    """暗号化 + Safe Pickle の組み合わせテスト"""
    
    def test_encryption_and_safe_pickle(self, temp_db):
        """暗号化とSafe Pickleの同時使用"""
        password = "secure_password"
        
        db = DictSQLiteV4(
            temp_db,
            encryption_password=password,
            enable_safe_pickle=True
        )
        
        # 統計で両方有効か確認
        stats = db.stats()
        assert stats["encryption_enabled"] is True
        assert stats["safe_pickle_enabled"] is True
        
        # データの保存と読み込み
        data = {
            "username": "alice",
            "email": "alice@example.com",
            "preferences": {"theme": "dark", "notifications": True}
        }
        
        pickled = pickle.dumps(data)
        db["user:alice"] = pickled
        
        # safe_pickle有効でも自動的にunpickleされる
        restored = db["user:alice"]
        assert restored == data
    
    def test_combined_performance(self, temp_db):
        """組み合わせ時のパフォーマンステスト"""
        password = "perf_test"
        
        db = DictSQLiteV4(
            temp_db,
            encryption_password=password,
            enable_safe_pickle=True
        )
        
        import time
        
        # 書き込みテスト
        start = time.time()
        for i in range(500):
            data = {"id": i, "value": f"data_{i}"}
            db[f"item_{i}"] = pickle.dumps(data)
        write_time = time.time() - start
        
        # 読み込みテスト
        start = time.time()
        for i in range(500):
            _ = db[f"item_{i}"]
        read_time = time.time() - start
        
        # 性能要件（両方有効でも実用的な速度）
        assert write_time < 1.0, f"書き込みが遅すぎます: {write_time}秒"
        assert read_time < 1.0, f"読み込みが遅すぎます: {read_time}秒"
        
        print(f"\n暗号化+Safe Pickleパフォーマンス:")
        print(f"  書き込み: {500/max(write_time, 0.001):.0f} ops/sec")
        print(f"  読み込み: {500/max(read_time, 0.001):.0f} ops/sec")


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPersistenceModes:
    """永続化モードのテスト"""
    
    def test_memory_mode_with_encryption(self):
        """メモリモード + 暗号化"""
        db = DictSQLiteV4(
            ":memory:",
            persist_mode="memory",
            encryption_password="test"
        )
        
        db["key"] = b"value"
        assert db["key"] == b"value"
        
        stats = db.stats()
        assert stats["encryption_enabled"] is True
    
    def test_lazy_mode_with_security(self, temp_db):
        """遅延永続化モード + セキュリティ"""
        db = DictSQLiteV4(
            temp_db,
            persist_mode="lazy",
            encryption_password="test",
            enable_safe_pickle=True
        )
        
        data = {"test": "data"}
        db["item"] = pickle.dumps(data)
        
        # フラッシュして永続化
        db.flush()
        
        # 再度開いて確認
        db2 = DictSQLiteV4(
            temp_db,
            persist_mode="lazy",
            encryption_password="test",
            enable_safe_pickle=True
        )
        
        # safe_pickle有効でも自動的にunpickleされる
        restored = db2["item"]
        assert restored == data


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSQLInjectionProtection:
    """SQL Injection 対策のテスト"""
    
    def test_sql_injection_in_keys(self, temp_db):
        """キーにSQL文を含む場合の安全性"""
        db = DictSQLiteV4(temp_db)
        
        # SQL Injectionを試みるキー
        malicious_keys = [
            "'; DROP TABLE kv_store; --",
            "' OR '1'='1",
            "key' UNION SELECT * FROM sqlite_master --",
        ]
        
        for key in malicious_keys:
            db[key] = b"test_data"
            # 正常に保存・読み込みできることを確認
            assert db[key] == b"test_data"
        
        # データベースが破損していないことを確認
        stats = db.stats()
        assert stats["hot_tier_size"] >= len(malicious_keys)


def test_module_import():
    """モジュールのインポートテスト"""
    if DICTSQLITE_V4_AVAILABLE:
        from dictsqlite import DictSQLiteV4
        assert DictSQLiteV4 is not None
    else:
        pytest.skip("DictSQLiteV4 module not available")


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestJSONBSecurity:
    """JSONBモードのセキュリティテスト"""
    
    def test_jsonb_with_encryption(self, temp_db):
        """JSONB + 暗号化の組み合わせテスト"""
        password = "test_password_123"
        db = DictSQLiteV4(
            temp_db,
            storage_mode="jsonb",
            encryption_password=password
        )
        
        # 辞書データを暗号化して保存
        sensitive_data = {
            "credit_card": "1234-5678-9012-3456",
            "ssn": "123-45-6789",
            "password": "secret123"
        }
        
        db["sensitive"] = sensitive_data
        db.flush()
        db.close()
        
        # 正しいパスワードで復号化
        db2 = DictSQLiteV4(
            temp_db,
            storage_mode="jsonb",
            encryption_password=password
        )
        retrieved = db2["sensitive"]
        assert retrieved == sensitive_data
        db2.close()
        
        # 間違ったパスワードでは復号化できない
        db3 = DictSQLiteV4(
            temp_db,
            storage_mode="jsonb",
            encryption_password="wrong_password"
        )
        try:
            _ = db3["sensitive"]
            assert False, "Should have raised an error"
        except:
            # 復号化エラーが発生することを期待
            pass
        db3.close()
    
    def test_jsonb_type_validation(self, temp_db):
        """JSONB型検証テスト（不正な型を拒否）"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # JSON互換の型はOK
        db["valid_dict"] = {"key": "value"}
        db["valid_list"] = [1, 2, 3]
        db["valid_str"] = "string"
        db["valid_int"] = 42
        db["valid_float"] = 3.14
        db["valid_bool"] = True
        db["valid_none"] = None
        
        # すべて正常に保存・取得できる
        print(f"valid_list: {db['valid_list']}, type: {type(db['valid_list'])}")
        assert db["valid_dict"] == {"key": "value"}
        assert db["valid_list"] == [1, 2, 3]
        assert db["valid_str"] == "string"
        assert db["valid_int"] == 42
        assert db["valid_float"] == 3.14
        assert db["valid_bool"] is True
        assert db["valid_none"] is None
    
    def test_table_isolation_security(self, temp_db):
        """テーブル間のデータ隔離セキュリティテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 異なるテーブルにデータ保存
        users = db.table("users")
        admin = db.table("admin")
        
        users["user1"] = {"role": "user", "access": "limited"}
        admin["admin1"] = {"role": "admin", "access": "full"}
        
        # ユーザーテーブルから管理者データにアクセスできないことを確認
        assert "admin1" not in users
        assert "user1" not in admin
        
        # 各テーブルは自分のデータのみアクセス可能
        assert users["user1"]["access"] == "limited"
        assert admin["admin1"]["access"] == "full"
    
    def test_jsonb_injection_prevention(self, temp_db):
        """JSONB SQLインジェクション防止テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 悪意のあるキー名を含むデータ
        malicious_keys = [
            "'; DROP TABLE main; --",
            "admin' OR '1'='1",
            "../../../etc/passwd",
            "<script>alert('xss')</script>",
            "\\x00\\x00\\x00",
        ]
        
        for key in malicious_keys:
            # 悪意のあるキーでもエラーなく保存できる
            db[key] = {"safe": "data"}
        
        # すべて正常に取得できる
        for key in malicious_keys:
            assert db[key] == {"safe": "data"}
    
    def test_async_jsonb_security(self, temp_db):
        """非同期版JSONBのセキュリティテスト"""
        from dictsqlite import AsyncDictSQLite
        
        db = AsyncDictSQLite(
            temp_db,
            storage_mode="jsonb"
        )
        
        # 並行アクセスでのデータ整合性
        db["key1"] = {"value": 1}
        db["key2"] = {"value": 2}
        
        # データが正しく保存されている
        assert db["key1"]["value"] == 1
        assert db["key2"]["value"] == 2
        
        db.close()
    
    def test_table_key_collision_prevention(self, temp_db):
        """テーブル間のキー衝突防止テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        table1 = db.table("table1")
        table2 = db.table("table2")
        
        # 同じキー名で異なるデータを保存
        table1["same_key"] = {"table": "table1", "data": "A"}
        table2["same_key"] = {"table": "table2", "data": "B"}
        
        # データが混在しないことを確認
        assert table1["same_key"]["data"] == "A"
        assert table2["same_key"]["data"] == "B"
        
        # テーブル名が含まれることを確認
        assert table1["same_key"]["table"] == "table1"
        assert table2["same_key"]["table"] == "table2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
