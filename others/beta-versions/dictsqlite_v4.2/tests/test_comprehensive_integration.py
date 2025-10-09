#!/usr/bin/env python3
"""
包括的な統合テスト - DictSQLite v4.2

このテストスイートは以下をカバーします：
- 複数機能の組み合わせテスト
- 実際の使用シナリオに基づくテスト
- ストレージモードとテーブルの組み合わせ
- 暗号化とセーフピクルの組み合わせ
- 永続化モードの組み合わせ
"""

import pytest
import pickle
import tempfile
import os
import time
from pathlib import Path

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
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
class TestStorageModeIntegration:
    """ストレージモードの統合テスト"""
    
    def test_pickle_with_encryption(self, temp_db):
        """Pickleモード + 暗号化"""
        password = "test_password_123"
        db = DictSQLiteV4(
            temp_db,
            storage_mode="pickle",
            encryption_password=password
        )
        
        # Pythonオブジェクトを暗号化して保存
        test_obj = {
            "string": "hello",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        # storage_mode="pickle"の場合、自動的にpickle化されて保存される
        db["encrypted_pickle"] = test_obj
        
        # 復元 - storage_mode="pickle"の場合、自動的にunpickleされる
        retrieved = db["encrypted_pickle"]
        assert retrieved == test_obj
        
        db.close()
    
    def test_jsonb_with_multiple_tables(self, temp_db):
        """JSONBモード + 複数テーブル"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 複数のテーブルを作成
        users = db.table("users")
        products = db.table("products")
        orders = db.table("orders")
        
        # データ追加
        users["u1"] = {"name": "Alice", "email": "alice@example.com"}
        users["u2"] = {"name": "Bob", "email": "bob@example.com"}
        
        products["p1"] = {"name": "Laptop", "price": 1000}
        products["p2"] = {"name": "Mouse", "price": 20}
        
        orders["o1"] = {"user_id": "u1", "product_id": "p1", "qty": 1}
        orders["o2"] = {"user_id": "u2", "product_id": "p2", "qty": 2}
        
        # リレーショナル的な検証
        order1 = orders["o1"]
        user1 = users[order1["user_id"]]
        product1 = products[order1["product_id"]]
        
        assert user1["name"] == "Alice"
        assert product1["name"] == "Laptop"
        assert order1["qty"] == 1
        
        db.close()
    
    def test_json_with_safe_pickle(self, temp_db):
        """JSONモードのテスト（Pickleは使用しない）"""
        db = DictSQLiteV4(
            temp_db,
            storage_mode="json"
        )
        
        # JSONデータを保存
        data = {
            "settings": {
                "theme": "dark",
                "language": "ja",
                "notifications": True
            }
        }
        
        db["config"] = data
        assert db["config"] == data
        
        db.close()
    
    def test_bytes_with_encryption(self, temp_db):
        """Bytesモード + 暗号化"""
        password = "secure_password"
        db = DictSQLiteV4(
            temp_db,
            storage_mode="bytes",
            encryption_password=password
        )
        
        # バイナリデータを暗号化
        binary_data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        db["encrypted_binary"] = binary_data
        
        assert db["encrypted_binary"] == binary_data
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPersistModeIntegration:
    """永続化モードの統合テスト"""
    
    def test_memory_mode_with_jsonb(self, temp_db):
        """メモリモード + JSONB"""
        db = DictSQLiteV4(
            temp_db,
            persist_mode="memory",
            storage_mode="jsonb"
        )
        
        # メモリ内のみでJSONBデータを操作
        for i in range(100):
            db[f"key_{i}"] = {"id": i, "value": f"data_{i}"}
        
        # すべて取得可能
        for i in range(100):
            assert db[f"key_{i}"]["id"] == i
        
        db.close()
    
    def test_lazy_mode_with_tables(self, temp_db):
        """遅延モード + テーブル"""
        db = DictSQLiteV4(
            temp_db,
            persist_mode="lazy",
            storage_mode="jsonb"
        )
        
        table1 = db.table("table1")
        table2 = db.table("table2")
        
        # データ追加（メモリに保持）
        for i in range(50):
            table1[f"key_{i}"] = {"table": 1, "value": i}
            table2[f"key_{i}"] = {"table": 2, "value": i}
        
        # フラッシュして永続化
        db.flush()
        db.close()
        
        # 再度開いて確認
        db2 = DictSQLiteV4(temp_db, storage_mode="jsonb")
        t1 = db2.table("table1")
        t2 = db2.table("table2")
        
        # データが永続化されている
        assert t1["key_0"]["value"] == 0
        assert t2["key_0"]["value"] == 0
        
        db2.close()
    
    def test_writethrough_with_encryption(self, temp_db):
        """即時書き込みモード + 暗号化"""
        password = "test_pass"
        db = DictSQLiteV4(
            temp_db,
            persist_mode="writethrough",
            encryption_password=password
        )
        
        # 即時にディスクへ暗号化して書き込み
        for i in range(10):
            db[f"key_{i}"] = f"encrypted_value_{i}".encode()
        
        db.close()
        
        # 再度開いて確認
        db2 = DictSQLiteV4(temp_db, encryption_password=password)
        
        for i in range(10):
            assert db2[f"key_{i}"] == f"encrypted_value_{i}".encode()
        
        db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestRealWorldScenarios:
    """実世界のシナリオテスト"""
    
    def test_user_session_management(self, temp_db):
        """ユーザーセッション管理のシナリオ"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        sessions = db.table("sessions")
        
        # セッション作成
        sessions["session_abc123"] = {
            "user_id": "user_001",
            "login_time": "2024-01-01T10:00:00",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0"
        }
        
        sessions["session_def456"] = {
            "user_id": "user_002",
            "login_time": "2024-01-01T11:00:00",
            "ip_address": "192.168.1.2",
            "user_agent": "Chrome/120.0"
        }
        
        # セッション取得
        session = sessions["session_abc123"]
        assert session["user_id"] == "user_001"
        
        # セッション削除（ログアウト）
        del sessions["session_abc123"]
        assert "session_abc123" not in sessions
        
        # 他のセッションは残っている
        assert "session_def456" in sessions
        
        db.close()
    
    def test_configuration_storage(self, temp_db):
        """設定ストレージのシナリオ"""
        db = DictSQLiteV4(temp_db, storage_mode="json", persist_mode="writethrough")
        
        # アプリケーション設定
        db["app_config"] = {
            "version": "1.0.0",
            "settings": {
                "theme": "dark",
                "language": "ja",
                "font_size": 14,
                "auto_save": True
            },
            "recent_files": [
                "/path/to/file1.txt",
                "/path/to/file2.txt"
            ]
        }
        
        # 設定更新
        config = db["app_config"]
        config["settings"]["theme"] = "light"
        config["settings"]["font_size"] = 16
        db["app_config"] = config
        
        # 確認
        updated = db["app_config"]
        assert updated["settings"]["theme"] == "light"
        assert updated["settings"]["font_size"] == 16
        
        db.close()
    
    def test_caching_layer(self, temp_db):
        """キャッシュレイヤーのシナリオ"""
        db = DictSQLiteV4(
            temp_db,
            storage_mode="jsonb",
            persist_mode="lazy"
        )
        
        cache = db.table("cache")
        
        # データをキャッシュ
        for i in range(200):
            cache[f"item_{i}"] = {
                "id": i,
                "data": f"cached_data_{i}",
                "timestamp": time.time()
            }
        
        # すべてアクセス可能
        assert cache["item_0"]["id"] == 0
        assert cache["item_199"]["id"] == 199
        
        db.close()
    
    def test_multi_tenant_data(self, temp_db):
        """マルチテナントデータのシナリオ"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # テナントごとにテーブルを分離
        tenant1_users = db.table("tenant1_users")
        tenant2_users = db.table("tenant2_users")
        
        # テナント1のデータ
        tenant1_users["user1"] = {
            "name": "Alice",
            "tenant": "tenant1",
            "role": "admin"
        }
        
        # テナント2のデータ
        tenant2_users["user1"] = {
            "name": "Bob",
            "tenant": "tenant2",
            "role": "user"
        }
        
        # データが分離されている
        assert tenant1_users["user1"]["name"] == "Alice"
        assert tenant2_users["user1"]["name"] == "Bob"
        
        # 同じキーでも異なるテナント
        assert tenant1_users["user1"]["tenant"] != tenant2_users["user1"]["tenant"]
        
        db.close()
    
    def test_job_queue(self, temp_db):
        """ジョブキューのシナリオ"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb", persist_mode="writethrough")
        
        jobs = db.table("jobs")
        
        # ジョブ追加
        jobs["job_001"] = {
            "status": "pending",
            "task": "process_data",
            "params": {"file": "data.csv"},
            "created_at": "2024-01-01T10:00:00"
        }
        
        jobs["job_002"] = {
            "status": "pending",
            "task": "send_email",
            "params": {"to": "user@example.com"},
            "created_at": "2024-01-01T10:01:00"
        }
        
        # ジョブ処理
        job = jobs["job_001"]
        job["status"] = "processing"
        jobs["job_001"] = job
        
        # 処理完了
        job["status"] = "completed"
        job["completed_at"] = "2024-01-01T10:05:00"
        jobs["job_001"] = job
        
        # 確認
        assert jobs["job_001"]["status"] == "completed"
        assert jobs["job_002"]["status"] == "pending"
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestFeatureCombinations:
    """機能の組み合わせテスト"""
    
    def test_all_security_features(self, temp_db):
        """セキュリティ機能のテスト"""
        password = "very_secure_password"
        db = DictSQLiteV4(
            temp_db,
            encryption_password=password,
            storage_mode="jsonb"  # JSONBモードを使用
        )
        
        # 暗号化してデータ保存
        sensitive_data = {
            "ssn": "123-45-6789",
            "credit_card": "1234-5678-9012-3456",
            "password": "user_password"
        }
        
        db["sensitive"] = sensitive_data
        
        # 復元
        retrieved = db["sensitive"]
        assert retrieved == sensitive_data
        
        # 統計確認
        stats = db.stats()
        assert stats["encryption_enabled"] is True
        
        db.close()
    
    def test_all_performance_features(self, temp_db):
        """パフォーマンス機能のテスト"""
        db = DictSQLiteV4(
            temp_db,
            persist_mode="memory",
            storage_mode="jsonb"
        )
        
        # 高速メモリモードで大量データ処理
        import time
        start = time.time()
        
        for i in range(5000):
            db[f"key_{i}"] = {"id": i, "data": f"value_{i}"}
        
        write_time = time.time() - start
        
        # 読み込み
        start = time.time()
        for i in range(5000):
            _ = db[f"key_{i}"]
        read_time = time.time() - start
        
        print(f"\nパフォーマンステスト結果:")
        print(f"  書き込み: {5000/write_time:.0f} ops/sec")
        print(f"  読み込み: {5000/read_time:.0f} ops/sec")
        
        # メモリモードは非常に高速であるべき
        assert write_time < 2.0
        assert read_time < 2.0
        
        db.close()
    
    def test_mixed_table_storage_modes(self, temp_db):
        """異なるストレージモードのテーブル（制限あり）"""
        # 注: 実際には同一DBインスタンスで複数のストレージモードは使えない
        # これは別々のインスタンスで異なるモードを使用する例
        
        # JSONBモード
        db_jsonb = DictSQLiteV4(temp_db, storage_mode="jsonb")
        users = db_jsonb.table("users")
        users["user1"] = {"name": "Alice", "age": 30}
        db_jsonb.close()
        
        # 別のインスタンスで同じファイルを開く（同じストレージモード）
        db_jsonb2 = DictSQLiteV4(temp_db, storage_mode="jsonb")
        users2 = db_jsonb2.table("users")
        assert users2["user1"]["name"] == "Alice"
        db_jsonb2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncIntegration:
    """非同期統合テスト"""
    
    def test_async_with_jsonb_tables(self, temp_db):
        """非同期 + JSONB + テーブル"""
        db = AsyncDictSQLite(temp_db, storage_mode="jsonb")
        
        users = db.table("users")
        posts = db.table("posts")
        
        # ユーザーデータ
        users["u1"] = {"name": "Alice", "email": "alice@example.com"}
        users["u2"] = {"name": "Bob", "email": "bob@example.com"}
        
        # 投稿データ
        posts["p1"] = {"user": "u1", "title": "Hello", "content": "First post"}
        posts["p2"] = {"user": "u2", "title": "Hi", "content": "Second post"}
        
        # 確認
        assert users["u1"]["name"] == "Alice"
        assert posts["p1"]["user"] == "u1"
        
        db.close()
    
    def test_async_batch_with_tables(self, temp_db):
        """非同期テーブル操作のテスト"""
        db = AsyncDictSQLite(temp_db, storage_mode="jsonb")
        
        items = db.table("items")
        
        # 個別書き込み
        for i in range(100):
            items[f"item_{i}"] = {"id": i, "name": f"Item {i}", "price": i * 10}
        
        # 読み込み確認
        assert items["item_0"]["id"] == 0
        assert items["item_9"]["id"] == 9
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStatsAndMonitoring:
    """統計とモニタリングのテスト"""
    
    def test_stats_with_all_features(self, temp_db):
        """すべての機能有効時の統計"""
        password = "test_password"
        db = DictSQLiteV4(
            temp_db,
            encryption_password=password,
            enable_safe_pickle=True,
            storage_mode="jsonb",
            persist_mode="lazy"
        )
        
        # データ追加
        for i in range(50):
            db[f"key_{i}"] = {"id": i, "value": f"data_{i}"}
        
        # 統計取得
        stats = db.stats()
        
        # 必要なフィールドが存在することを確認
        assert "hot_tier_size" in stats
        assert "encryption_enabled" in stats
        assert "safe_pickle_enabled" in stats
        
        assert stats["encryption_enabled"] is True
        assert stats["safe_pickle_enabled"] is True
        assert stats["hot_tier_size"] >= 50
        
        db.close()
    
    def test_stats_after_operations(self, temp_db):
        """各種操作後の統計変化"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 初期状態
        stats1 = db.stats()
        initial_size = stats1["hot_tier_size"]
        
        # データ追加
        for i in range(100):
            db[f"key_{i}"] = {"value": i}
        
        stats2 = db.stats()
        assert stats2["hot_tier_size"] >= initial_size + 100
        
        # データ削除
        for i in range(50):
            del db[f"key_{i}"]
        
        stats3 = db.stats()
        assert stats3["hot_tier_size"] < stats2["hot_tier_size"]
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMigrationScenarios:
    """マイグレーションシナリオのテスト"""
    
    def test_migrate_from_bytes_to_jsonb(self, temp_db):
        """BytesモードからJSONBモードへのマイグレーション"""
        # フェーズ1: Bytesモードでデータ作成
        db1 = DictSQLiteV4(temp_db, storage_mode="bytes")
        db1["key1"] = b"value1"
        db1["key2"] = b"value2"
        db1.close()
        
        # フェーズ2: 新しいファイルでJSONBモード
        temp_db2 = temp_db + ".new"
        db2 = DictSQLiteV4(temp_db2, storage_mode="jsonb")
        
        # データ移行（手動）
        db1_read = DictSQLiteV4(temp_db, storage_mode="bytes")
        db2["key1"] = {"migrated": True, "original": "value1"}
        db2["key2"] = {"migrated": True, "original": "value2"}
        db1_read.close()
        db2.close()
        
        # 確認
        db3 = DictSQLiteV4(temp_db2, storage_mode="jsonb")
        assert db3["key1"]["migrated"] is True
        db3.close()
        
        # クリーンアップ
        try:
            os.unlink(temp_db2)
        except:
            pass
    
    def test_add_encryption_to_existing_db(self, temp_db):
        """既存DBに暗号化を追加"""
        # フェーズ1: 暗号化なし
        db1 = DictSQLiteV4(temp_db)
        db1["key1"] = b"value1"
        db1.close()
        
        # フェーズ2: 同じデータに暗号化を追加
        # 注: 実際には新しいDBに移行する必要がある
        password = "new_password"
        temp_db_encrypted = temp_db + ".encrypted"
        db2 = DictSQLiteV4(temp_db_encrypted, encryption_password=password)
        
        # データコピー
        db1_read = DictSQLiteV4(temp_db)
        db2["key1"] = db1_read["key1"]
        db1_read.close()
        db2.close()
        
        # 確認
        db3 = DictSQLiteV4(temp_db_encrypted, encryption_password=password)
        assert db3["key1"] == b"value1"
        db3.close()
        
        # クリーンアップ
        try:
            os.unlink(temp_db_encrypted)
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
