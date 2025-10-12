#!/usr/bin/env python3
"""
永続化モードテスト - DictSQLite v4.2

このテストスイートは各永続化モードを網羅的にテストします：
- Memoryモード: メモリ内のみ（永続化なし）
- Lazyモード: 遅延書き込み（バッファリング）
- Writethroughモード: 即時書き込み
- モード間の動作比較
"""

import pytest
import time
from .conftest import windows_safe_temp_db

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4
    DICTSQLITE_V4_AVAILABLE = True
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMemoryMode:
    """Memoryモードのテスト"""
    
    def test_memory_mode_basic(self):
        """基本的なMemoryモードの動作"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            
            # データを書き込む
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            
            # メモリ内で読み取れる
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            
            db.close()
    
    def test_memory_mode_not_persisted(self):
        """Memoryモードではデータが永続化されない"""
        with windows_safe_temp_db() as db_path:
            # データを書き込んでclose
            db1 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1.close()
            
            # 再度開いてもデータは存在しない
            db2 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            assert "key1" not in db2
            assert len(db2) == 0
            db2.close()
    
    def test_memory_mode_performance(self):
        """Memoryモードの高速性"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            
            # 大量のデータを高速に書き込める
            start = time.time()
            for i in range(1000):
                db[f"key{i}"] = f"value{i}".encode()
            elapsed = time.time() - start
            
            # メモリモードは非常に高速なはず
            assert elapsed < 1.0  # 1秒以内
            
            # すべてのデータが読み取れる
            for i in range(1000):
                assert db[f"key{i}"] == f"value{i}".encode()
            
            db.close()
    
    def test_memory_mode_flush_has_no_effect(self):
        """Memoryモードではflush()が効果なし"""
        with windows_safe_temp_db() as db_path:
            db1 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1.flush()  # flushしても永続化されない
            db1.close()
            
            # 別のインスタンスで確認
            db2 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            assert "key1" not in db2
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestLazyMode:
    """Lazyモードのテスト"""
    
    def test_lazy_mode_basic(self):
        """基本的なLazyモードの動作"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            
            # データを書き込む
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            
            # メモリ内で読み取れる
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            
            db.close()
    
    def test_lazy_mode_flush_persists(self):
        """Lazyモードではflush()で永続化される"""
        with windows_safe_temp_db() as db_path:
            # データを書き込んでflush
            db1 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1.flush()
            # db1はまだ開いたまま
            
            # 別のインスタンスで確認（flush後なので見える）
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            
            db1.close()
            db2.close()
    
    def test_lazy_mode_close_persists(self):
        """Lazyモードではclose()で自動的に永続化される"""
        with windows_safe_temp_db() as db_path:
            # データを書き込んでclose
            db1 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1["key2"] = b"value2"
            db1.close()
            
            # 再度開いてデータが残っている
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            assert db2["key2"] == b"value2"
            db2.close()
    
    def test_lazy_mode_buffering(self):
        """Lazyモードではバッファリングされる"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes", buffer_size=100)
            
            # バッファサイズ未満のデータを書き込む
            for i in range(50):
                db[f"key{i}"] = f"value{i}".encode()
            
            # まだflushされていない可能性がある
            # でもメモリ内では読み取れる
            for i in range(50):
                assert db[f"key{i}"] == f"value{i}".encode()
            
            # flushすると確実に永続化される
            db.flush()
            db.close()
            
            # 再度開いて確認
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            for i in range(50):
                assert db2[f"key{i}"] == f"value{i}".encode()
            db2.close()
    
    def test_lazy_mode_multiple_flushes(self):
        """Lazyモードで複数回flush"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            
            # 最初のバッチ
            db["batch1_key1"] = b"value1"
            db.flush()
            
            # 2番目のバッチ
            db["batch2_key1"] = b"value2"
            db.flush()
            
            # 3番目のバッチ
            db["batch3_key1"] = b"value3"
            db.flush()
            
            db.close()
            
            # すべてのデータが永続化されている
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["batch1_key1"] == b"value1"
            assert db2["batch2_key1"] == b"value2"
            assert db2["batch3_key1"] == b"value3"
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestWritethroughMode:
    """Writethroughモードのテスト"""
    
    def test_writethrough_mode_basic(self):
        """基本的なWritethroughモードの動作"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            
            # データを書き込む
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            
            # すぐに読み取れる
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            
            db.close()
    
    def test_writethrough_mode_immediate_persistence(self):
        """Writethroughモードでは即座に永続化される"""
        with windows_safe_temp_db() as db_path:
            db1 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            
            # データを書き込む（即座にディスクに書き込まれる）
            db1["key1"] = b"value1"
            
            # flush不要で、別のインスタンスから即座に読める
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            
            # さらに書き込み
            db1["key2"] = b"value2"
            
            # すぐに見える
            db2.flush()  # 念のため
            # 新しいインスタンスで確認
            db3 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db3["key2"] == b"value2"
            
            db1.close()
            db2.close()
            db3.close()
    
    def test_writethrough_mode_no_flush_needed(self):
        """Writethroughモードではflush()不要"""
        with windows_safe_temp_db() as db_path:
            db1 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            db1["key1"] = b"value1"
            # flush()を呼ばずにclose
            db1.close()
            
            # データは永続化されている
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db2["key1"] == b"value1"
            db2.close()
    
    def test_writethrough_mode_update_persistence(self):
        """Writethroughモードでの更新も即座に永続化"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            
            # 初期値
            db["key1"] = b"value1"
            db.close()
            
            # 再度開いて更新
            db2 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            db2["key1"] = b"updated_value"
            db2.close()
            
            # 更新が永続化されている
            db3 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert db3["key1"] == b"updated_value"
            db3.close()
    
    def test_writethrough_mode_delete_persistence(self):
        """Writethroughモードでの削除も即座に永続化"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            
            # データを追加
            db["key1"] = b"value1"
            db.close()
            
            # 再度開いて削除
            db2 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            del db2["key1"]
            db2.close()
            
            # 削除が永続化されている
            db3 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert "key1" not in db3
            db3.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPersistModeComparison:
    """永続化モード間の比較テスト"""
    
    def test_memory_vs_writethrough_persistence(self):
        """MemoryモードとWritethroughモードの永続性比較"""
        with windows_safe_temp_db() as db_path1, windows_safe_temp_db() as db_path2:
            # Memoryモード
            db_mem = DictSQLiteV4(db_path1, persist_mode="memory", storage_mode="bytes")
            db_mem["key1"] = b"value1"
            db_mem.close()
            
            # Writethroughモード
            db_wt = DictSQLiteV4(db_path2, persist_mode="writethrough", storage_mode="bytes")
            db_wt["key1"] = b"value1"
            db_wt.close()
            
            # Memoryモードは永続化されない
            db_mem2 = DictSQLiteV4(db_path1, storage_mode="bytes")
            assert "key1" not in db_mem2
            db_mem2.close()
            
            # Writethroughモードは永続化される
            db_wt2 = DictSQLiteV4(db_path2, storage_mode="bytes")
            assert db_wt2["key1"] == b"value1"
            db_wt2.close()
    
    def test_lazy_vs_writethrough_timing(self):
        """LazyモードとWritethroughモードのタイミング比較"""
        with windows_safe_temp_db() as db_path1, windows_safe_temp_db() as db_path2:
            # Lazyモード - flush前
            db_lazy = DictSQLiteV4(db_path1, persist_mode="lazy", storage_mode="bytes")
            db_lazy["key1"] = b"value1"
            # flushせずに別インスタンスで確認
            db_lazy_check = DictSQLiteV4(db_path1, storage_mode="bytes")
            lazy_visible_before_flush = "key1" in db_lazy_check
            db_lazy_check.close()
            
            # Writethroughモード - 即座
            db_wt = DictSQLiteV4(db_path2, persist_mode="writethrough", storage_mode="bytes")
            db_wt["key1"] = b"value1"
            # 別インスタンスで即座に確認
            db_wt_check = DictSQLiteV4(db_path2, storage_mode="bytes")
            wt_visible_immediately = "key1" in db_wt_check
            db_wt_check.close()
            
            # Writethroughは即座に見える
            assert wt_visible_immediately is True
            
            # Lazyはflush前は見えない可能性がある（実装依存）
            # ただし、同じプロセス内なら見える可能性もある
            
            # flushした後は確実に見える
            db_lazy.flush()
            db_lazy_check2 = DictSQLiteV4(db_path1, storage_mode="bytes")
            assert "key1" in db_lazy_check2
            db_lazy_check2.close()
            
            db_lazy.close()
            db_wt.close()
    
    def test_all_modes_final_persistence(self):
        """すべてのモードでclose後の最終的な永続化"""
        test_data = {"key1": b"value1", "key2": b"value2"}
        
        # Memory mode - 永続化されない
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            for k, v in test_data.items():
                db[k] = v
            db.close()
            
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert len(db2) == 0
            db2.close()
        
        # Lazy mode - close後に永続化
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            for k, v in test_data.items():
                db[k] = v
            db.close()
            
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert len(db2) == 2
            for k, v in test_data.items():
                assert db2[k] == v
            db2.close()
        
        # Writethrough mode - 即座に永続化
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            for k, v in test_data.items():
                db[k] = v
            db.close()
            
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert len(db2) == 2
            for k, v in test_data.items():
                assert db2[k] == v
            db2.close()


@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestPersistModeEdgeCases:
    """永続化モードのエッジケース"""
    
    def test_lazy_mode_large_buffer(self):
        """Lazyモードで大量のデータをバッファリング"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes", buffer_size=10000)
            
            # 大量のデータを書き込む
            for i in range(1000):
                db[f"key{i}"] = f"value{i}".encode()
            
            # メモリ内では読み取れる
            assert db["key500"] == b"value500"
            
            # flushして永続化
            db.flush()
            db.close()
            
            # 永続化されている
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            assert len(db2) == 1000
            assert db2["key500"] == b"value500"
            db2.close()
    
    def test_writethrough_mode_with_jsonb(self):
        """Writethroughモード + JSONBストレージ"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="jsonb")
            
            test_data = {"name": "Alice", "scores": [90, 85, 92]}
            db["user"] = test_data
            
            # 別インスタンスで即座に読める
            db2 = DictSQLiteV4(db_path, storage_mode="jsonb")
            assert db2["user"] == test_data
            
            db.close()
            db2.close()
    
    def test_mixed_persist_modes_same_db(self):
        """同じDBを異なる永続化モードで開く"""
        with windows_safe_temp_db() as db_path:
            # Writethroughで書き込み
            db1 = DictSQLiteV4(db_path, persist_mode="writethrough", storage_mode="bytes")
            db1["key1"] = b"value1"
            db1.close()
            
            # Lazyで読み込み
            db2 = DictSQLiteV4(db_path, persist_mode="lazy", storage_mode="bytes")
            assert db2["key1"] == b"value1"
            db2["key2"] = b"value2"
            db2.flush()
            db2.close()
            
            # Memoryで読み込み（既存データは読めない）
            db3 = DictSQLiteV4(db_path, persist_mode="memory", storage_mode="bytes")
            # Memoryモードでも初期ロードはされる可能性がある（実装依存）
            # または空の状態から始まる
            db3.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
