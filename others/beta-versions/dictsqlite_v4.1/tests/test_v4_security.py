"""
DictSQLite v4 セキュリティ機能のテストスイート

暗号化とSafe Pickle機能の包括的なテスト
"""
import pytest
import pickle
import tempfile
import os
from pathlib import Path

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite_v4 import DictSQLiteV4
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
    # クリーンアップ
    try:
        os.unlink(db_path)
    except:
        pass


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
        
        # 読み込みと復元
        restored = pickle.loads(db["safe_data"])
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
        
        restored = pickle.loads(db["nested"])
        assert restored == nested
    
    def test_safe_pickle_forbidden_objects(self, temp_db):
        """禁止されたオブジェクトのテスト"""
        db = DictSQLiteV4(temp_db, enable_safe_pickle=True)
        
        # 危険な関数をpickleしようとする
        import os
        
        # os.systemのような危険な関数は拒否されるべき
        # （注: pickleできないかもしれないが、できる場合は拒否）
        try:
            dangerous = pickle.dumps(os.system)
            with pytest.raises(Exception):
                db["dangerous"] = dangerous
        except (TypeError, pickle.PicklingError):
            # pickle自体が失敗する場合もある
            pass


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
        
        restored = pickle.loads(db["user:alice"])
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
            _ = pickle.loads(db[f"item_{i}"])
        read_time = time.time() - start
        
        # 性能要件（両方有効でも実用的な速度）
        assert write_time < 1.0, f"書き込みが遅すぎます: {write_time}秒"
        assert read_time < 1.0, f"読み込みが遅すぎます: {read_time}秒"
        
        print(f"\n暗号化+Safe Pickleパフォーマンス:")
        print(f"  書き込み: {500/write_time:.0f} ops/sec")
        print(f"  読み込み: {500/read_time:.0f} ops/sec")


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
        
        restored = pickle.loads(db2["item"])
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
        from dictsqlite_v4 import DictSQLiteV4
        assert DictSQLiteV4 is not None
    else:
        pytest.skip("DictSQLiteV4 module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
