#!/usr/bin/env python3
"""
包括的なストレステスト・パフォーマンステスト - DictSQLite v4.2

このテストスイートは以下をカバーします：
- 大量データのストレステスト
- 極端な使用パターンのテスト
- パフォーマンス境界のテスト
- メモリ使用量のテスト
- 長時間実行テスト
"""

import pytest
import tempfile
import os
import time
import gc
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
class TestLargeScaleData:
    """大規模データのテスト"""
    
    def test_100k_entries(self, temp_db):
        """10万エントリのテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        start = time.time()
        
        # 10万エントリ書き込み
        for i in range(100000):
            db[f"key_{i}"] = {"id": i, "value": f"data_{i}"}
            
            if i % 10000 == 0:
                print(f"  進捗: {i:,} / 100,000")
        
        write_time = time.time() - start
        print(f"\n10万エントリ書き込み時間: {write_time:.2f}秒")
        print(f"書き込み速度: {100000/write_time:.0f} ops/sec")
        
        # ランダムアクセステスト
        import random
        samples = random.sample(range(100000), 1000)
        
        start = time.time()
        for i in samples:
            value = db[f"key_{i}"]
            assert value["id"] == i
        read_time = time.time() - start
        
        print(f"1000件ランダム読み込み時間: {read_time:.3f}秒")
        
        db.close()
    
    def test_large_values(self, temp_db):
        """大きな値のテスト（各1MB）"""
        db = DictSQLiteV4(temp_db, storage_mode="bytes")
        
        # 100個の1MBデータ
        for i in range(100):
            large_data = b"x" * (1024 * 1024)  # 1MB
            db[f"large_{i}"] = large_data
            
            if i % 10 == 0:
                print(f"  大きな値の進捗: {i} / 100")
        
        # 検証
        for i in range(0, 100, 10):
            data = db[f"large_{i}"]
            assert len(data) == 1024 * 1024
        
        db.close()
    
    def test_many_tables(self, temp_db):
        """多数のテーブルのテスト（1000テーブル）"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        tables = []
        for i in range(1000):
            table = db.table(f"table_{i}")
            table[f"key_{i}"] = {"table_id": i, "data": f"value_{i}"}
            tables.append(table)
            
            if i % 100 == 0:
                print(f"  テーブル作成進捗: {i} / 1000")
        
        # ランダム検証
        import random
        samples = random.sample(range(1000), 50)
        for i in samples:
            value = tables[i][f"key_{i}"]
            assert value["table_id"] == i
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestStressPatterns:
    """ストレスパターンのテスト"""
    
    def test_rapid_updates(self, temp_db):
        """高速連続更新テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 同じキーを1万回更新
        key = "stress_key"
        
        start = time.time()
        for i in range(10000):
            db[key] = {"iteration": i, "timestamp": time.time()}
        update_time = time.time() - start
        
        print(f"\n1万回更新時間: {update_time:.2f}秒")
        print(f"更新速度: {10000/update_time:.0f} ops/sec")
        
        # 最終値を確認
        final = db[key]
        assert final["iteration"] == 9999
        
        db.close()
    
    def test_alternating_operations(self, temp_db):
        """交互操作のストレステスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 書き込み・読み込み・削除を交互に実行
        for i in range(1000):
            # 書き込み
            db[f"key_{i}"] = {"value": i}
            
            # 読み込み
            value = db[f"key_{i}"]
            assert value["value"] == i
            
            # 半分は削除
            if i % 2 == 0:
                del db[f"key_{i}"]
                assert f"key_{i}" not in db
        
        # 奇数番号のキーだけ残っているはず
        for i in range(1000):
            if i % 2 == 0:
                assert f"key_{i}" not in db
            else:
                assert f"key_{i}" in db
        
        db.close()
    
    def test_bulk_delete(self, temp_db):
        """一括削除のストレステスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 1万エントリ作成
        for i in range(10000):
            db[f"key_{i}"] = {"value": i}
        
        # すべて削除
        start = time.time()
        for i in range(10000):
            del db[f"key_{i}"]
        delete_time = time.time() - start
        
        print(f"\n1万エントリ削除時間: {delete_time:.2f}秒")
        print(f"削除速度: {10000/delete_time:.0f} ops/sec")
        
        # すべて削除されたことを確認
        stats = db.stats()
        assert stats["hot_tier_size"] == 0
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPerformanceBoundaries:
    """パフォーマンス境界のテスト"""
    
    def test_hot_tier_overflow(self, temp_db):
        """大量データの処理テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 大量のデータ
        for i in range(1000):
            db[f"key_{i}"] = {"value": i}
        
        # すべてアクセス可能
        import random
        samples = random.sample(range(1000), 100)
        for i in samples:
            assert db[f"key_{i}"]["value"] == i
        
        db.close()
    
    def test_memory_mode_limits(self, temp_db):
        """メモリモードの大量データテスト"""
        db = DictSQLiteV4(
            temp_db,
            persist_mode="memory",
            storage_mode="jsonb"
        )
        
        # 大量データをメモリに保持
        for i in range(10000):
            db[f"key_{i}"] = {
                "id": i,
                "data": "x" * 100  # 各エントリ100文字
            }
        
        # すべてメモリから取得可能
        for i in range(0, 10000, 100):
            assert db[f"key_{i}"]["id"] == i
        
        db.close()
    
    def test_lazy_mode_buffer(self, temp_db):
        """遅延モードのバッファテスト"""
        db = DictSQLiteV4(temp_db, persist_mode="lazy", storage_mode="jsonb")
        
        # フラッシュせずに大量書き込み
        for i in range(5000):
            db[f"key_{i}"] = {"value": i}
        
        # フラッシュ
        start = time.time()
        db.flush()
        flush_time = time.time() - start
        
        print(f"\n5000エントリのフラッシュ時間: {flush_time:.3f}秒")
        
        db.close()
        
        # 再度開いて永続化を確認
        db2 = DictSQLiteV4(temp_db, storage_mode="jsonb")
        assert db2["key_0"]["value"] == 0
        assert db2["key_4999"]["value"] == 4999
        db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncStress:
    """非同期のストレステスト"""
    
    def test_async_high_throughput(self, temp_db):
        """非同期高スループットテスト"""
        db = AsyncDictSQLite(temp_db, storage_mode="jsonb")
        
        start = time.time()
        
        # 1万エントリを高速書き込み
        for i in range(10000):
            db[f"key_{i}"] = {"id": i, "value": f"async_data_{i}"}
        
        write_time = time.time() - start
        print(f"\n非同期1万エントリ書き込み: {write_time:.2f}秒")
        print(f"書き込み速度: {10000/write_time:.0f} ops/sec")
        
        # 読み込み
        start = time.time()
        for i in range(0, 10000, 10):
            _ = db[f"key_{i}"]
        read_time = time.time() - start
        
        print(f"1000件読み込み: {read_time:.3f}秒")
        
        db.close()
    
    def test_async_batch_operations(self, temp_db):
        """非同期個別操作のストレステスト"""
        db = AsyncDictSQLite(temp_db, storage_mode="jsonb")
        
        # 個別書き込み
        for i in range(10000):
            db[f"key_{i}"] = {"batch": 0, "id": i, "value": f"data_{i}"}
        
        # 検証
        for i in range(0, 10000, 100):
            assert db[f"key_{i}"]["id"] == i
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEncryptionPerformance:
    """暗号化パフォーマンステスト"""
    
    def test_encryption_overhead(self, temp_db):
        """暗号化のオーバーヘッドを測定"""
        # 暗号化なし
        db1 = DictSQLiteV4(temp_db + ".plain", storage_mode="bytes")
        
        start = time.time()
        for i in range(1000):
            db1[f"key_{i}"] = f"value_{i}".encode()
        plain_time = time.time() - start
        db1.close()
        
        # 暗号化あり
        db2 = DictSQLiteV4(
            temp_db + ".encrypted",
            storage_mode="bytes",
            encryption_password="test_password"
        )
        
        start = time.time()
        for i in range(1000):
            db2[f"key_{i}"] = f"value_{i}".encode()
        encrypted_time = time.time() - start
        db2.close()
        
        overhead = (encrypted_time - plain_time) / plain_time * 100
        print(f"\n暗号化なし: {plain_time:.3f}秒")
        print(f"暗号化あり: {encrypted_time:.3f}秒")
        print(f"オーバーヘッド: {overhead:.1f}%")
        
        # クリーンアップ
        try:
            os.unlink(temp_db + ".plain")
            os.unlink(temp_db + ".encrypted")
        except:
            pass


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestConcurrencyPatterns:
    """並行パターンのテスト"""
    
    def test_interleaved_table_access(self, temp_db):
        """複数テーブルへの交互アクセス"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        table1 = db.table("table1")
        table2 = db.table("table2")
        table3 = db.table("table3")
        
        # 3つのテーブルに交互に書き込み
        start = time.time()
        for i in range(1000):
            table1[f"key_{i}"] = {"table": 1, "value": i}
            table2[f"key_{i}"] = {"table": 2, "value": i * 2}
            table3[f"key_{i}"] = {"table": 3, "value": i * 3}
        write_time = time.time() - start
        
        print(f"\n3テーブル交互書き込み（3000エントリ）: {write_time:.2f}秒")
        
        # 交互読み込み
        start = time.time()
        for i in range(0, 1000, 10):
            _ = table1[f"key_{i}"]
            _ = table2[f"key_{i}"]
            _ = table3[f"key_{i}"]
        read_time = time.time() - start
        
        print(f"交互読み込み（300回）: {read_time:.3f}秒")
        
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestLongRunningOperations:
    """長時間実行テスト"""
    
    def test_sustained_write_load(self, temp_db):
        """持続的な書き込み負荷テスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb", persist_mode="lazy")
        
        # 10秒間連続書き込み
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < 10:
            db[f"key_{count}"] = {"id": count, "timestamp": time.time()}
            count += 1
        
        total_time = time.time() - start_time
        ops_per_sec = count / total_time
        
        print(f"\n10秒間の持続書き込み:")
        print(f"  総エントリ数: {count:,}")
        print(f"  平均速度: {ops_per_sec:.0f} ops/sec")
        
        db.flush()
        db.close()
    
    def test_repeated_session_cycles(self, temp_db):
        """繰り返しセッションサイクルテスト"""
        # 100回のオープン・クローズサイクル
        for session in range(100):
            db = DictSQLiteV4(temp_db, storage_mode="jsonb", persist_mode="writethrough")
            
            # 各セッションでデータ追加
            db[f"session_{session}"] = {
                "session_id": session,
                "timestamp": time.time()
            }
            
            db.close()
        
        # 最終確認
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        assert db["session_0"]["session_id"] == 0
        assert db["session_99"]["session_id"] == 99
        db.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMemoryManagement:
    """メモリ管理のテスト"""
    
    def test_memory_cleanup_after_delete(self, temp_db):
        """削除後のメモリクリーンアップテスト"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        # 大量データ作成
        for i in range(10000):
            db[f"key_{i}"] = {"id": i, "data": "x" * 1000}
        
        stats1 = db.stats()
        size1 = stats1["hot_tier_size"]
        
        # 半分削除
        for i in range(5000):
            del db[f"key_{i}"]
        
        stats2 = db.stats()
        size2 = stats2["hot_tier_size"]
        
        print(f"\n削除前: {size1:,} エントリ")
        print(f"削除後: {size2:,} エントリ")
        
        assert size2 < size1
        
        db.close()
    
    def test_gc_after_close(self, temp_db):
        """クローズ後のガベージコレクション"""
        db = DictSQLiteV4(temp_db, storage_mode="jsonb")
        
        for i in range(1000):
            db[f"key_{i}"] = {"value": i}
        
        db.close()
        
        # ガベージコレクション
        gc.collect()
        
        # 新しいインスタンスは正常に動作
        db2 = DictSQLiteV4(temp_db, storage_mode="jsonb")
        assert db2["key_0"]["value"] == 0
        db2.close()


if __name__ == "__main__":
    # ストレステストは時間がかかるので、verbose出力で実行
    pytest.main([__file__, "-v", "-s", "-k", "not test_100k"])
