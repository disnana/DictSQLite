#!/usr/bin/env python3
"""
網羅的テストスイート - 境界条件とエッジケースの詳細検証

このテストファイルは、DictSQLiteの境界条件とエッジケースを網羅的にテストします。

テスト対象:
- 空文字列キー、Unicode/絵文字キー
- 非常に大きなデータ（1MB+）
- 深くネストされた構造（20レベル+）
- hot_capacity=1（最小キャッシュ）
- 並行アクセスシナリオ
- pool_size境界値テスト
- 暗号化モードでの全操作
- 特殊なキー・値のパターン
"""

import pytest
import asyncio
import tempfile
import os
import sys
import threading
import concurrent.futures
from typing import Any, Dict, List

# テストユーティリティのインポート
from .conftest import windows_safe_temp_db, cleanup_db_files

# Rust拡張モジュールが利用可能か確認
try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite, is_native_available
    DICTSQLITE_V4_AVAILABLE = is_native_available()
except ImportError:
    DICTSQLITE_V4_AVAILABLE = False
    DictSQLiteV4 = None
    AsyncDictSQLite = None


# =============================================================================
# セクション1: 空文字列・特殊キーのテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestSpecialKeys:
    """特殊なキーのテスト"""

    def test_empty_string_key(self):
        """空文字列キー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db[""] = b"empty_key_value"
            
            assert "" in db
            assert db[""] == b"empty_key_value"
            assert db.get("") == b"empty_key_value"
            
            # キーリストに含まれる
            keys = db.keys()
            assert "" in keys
            
            db.close()

    def test_whitespace_only_key(self):
        """空白のみのキー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db[" "] = b"space"
            db["  "] = b"two_spaces"
            db["\t"] = b"tab"
            db["\n"] = b"newline"
            
            assert db[" "] == b"space"
            assert db["  "] == b"two_spaces"
            assert db["\t"] == b"tab"
            assert db["\n"] == b"newline"
            
            db.close()

    def test_unicode_keys(self):
        """Unicodeキー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 日本語
            db["日本語"] = b"japanese"
            # 中国語
            db["中文"] = b"chinese"
            # 韓国語
            db["한국어"] = b"korean"
            # アラビア語
            db["العربية"] = b"arabic"
            # ロシア語
            db["Русский"] = b"russian"
            
            assert db["日本語"] == b"japanese"
            assert db["中文"] == b"chinese"
            assert db["한국어"] == b"korean"
            assert db["العربية"] == b"arabic"
            assert db["Русский"] == b"russian"
            
            db.close()

    def test_emoji_keys(self):
        """絵文字キー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["🎉"] = b"party"
            db["🔥"] = b"fire"
            db["💻"] = b"computer"
            db["🚀🌙"] = b"rocket_moon"
            db["👨‍👩‍👧‍👦"] = b"family"  # ZWJ sequence
            
            assert db["🎉"] == b"party"
            assert db["🔥"] == b"fire"
            assert db["💻"] == b"computer"
            assert db["🚀🌙"] == b"rocket_moon"
            assert db["👨‍👩‍👧‍👦"] == b"family"
            
            db.close()

    def test_very_long_key(self):
        """非常に長いキー（1000文字）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            long_key = "k" * 1000
            db[long_key] = b"value"
            
            assert long_key in db
            assert db[long_key] == b"value"
            
            db.close()

    def test_special_characters_in_keys(self):
        """特殊文字を含むキー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            special_keys = [
                "key with spaces",
                "key\twith\ttabs",
                "key\nwith\nnewlines",
                "key/with/slashes",
                "key\\with\\backslashes",
                "key\"with\"quotes",
                "key'with'apostrophes",
                "key`with`backticks",
                "key=with=equals",
                "key;with;semicolons",
                "key:with:colons",
            ]
            
            for key in special_keys:
                db[key] = f"value_for_{key[:10]}".encode()
            
            for key in special_keys:
                assert key in db
                assert db[key] is not None
            
            db.close()


# =============================================================================
# セクション2: 大きなデータのテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestLargeData:
    """大きなデータのテスト"""

    def test_large_value_1mb(self):
        """1MBの値"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            large_value = b"x" * (1024 * 1024)  # 1MB
            db["large"] = large_value
            
            result = db["large"]
            assert len(result) == 1024 * 1024
            assert result == large_value
            
            db.close()

    def test_large_value_5mb(self):
        """5MBの値"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            large_value = b"y" * (5 * 1024 * 1024)  # 5MB
            db["large"] = large_value
            
            result = db["large"]
            assert len(result) == 5 * 1024 * 1024
            
            db.close()

    def test_many_keys(self):
        """大量のキー（10,000件）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            for i in range(10000):
                db[f"key_{i:05d}"] = f"value_{i}".encode()
            
            assert len(db) == 10000
            
            # ランダムサンプリングで検証
            assert db["key_00000"] == b"value_0"
            assert db["key_05000"] == b"value_5000"
            assert db["key_09999"] == b"value_9999"
            
            db.close()

    def test_large_nested_structure_pickle(self):
        """大きなネスト構造（Pickleモード）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # 100要素x100要素の2次元リスト
            large_list = [[f"item_{i}_{j}" for j in range(100)] for i in range(100)]
            db["large_list"] = large_list
            
            result = db["large_list"]
            assert len(result) == 100
            assert len(result[0]) == 100
            assert result[50][50] == "item_50_50"
            
            db.close()


# =============================================================================
# セクション3: 深いネスト構造のテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestDeepNesting:
    """深いネスト構造のテスト"""

    def test_deeply_nested_dict_20_levels(self):
        """20レベルの深いネスト（dict）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            # 20レベルのネスト構造を作成
            depth = 20
            nested = "deepest_value"
            for i in range(depth):
                nested = {f"level_{depth - i}": nested}
            
            db["deep"] = nested
            result = db["deep"]
            
            # 検証: 最深部まで到達できる
            current = result
            for i in range(depth):
                current = current[f"level_{i + 1}"]
            assert current == "deepest_value"
            
            db.close()

    def test_deeply_nested_list_20_levels(self):
        """20レベルの深いネスト（list）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="pickle")
            
            depth = 20
            nested = ["deepest_value"]
            for _ in range(depth - 1):
                nested = [nested]
            
            db["deep"] = nested
            result = db["deep"]
            
            # 検証
            current = result
            for _ in range(depth - 1):
                current = current[0]
            assert current[0] == "deepest_value"
            
            db.close()

    def test_deep_nested_jsonb_10_levels(self):
        """10レベルの深いネスト（JSONBモード）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="jsonb")
            
            depth = 10
            nested = {"value": "deepest"}
            for i in range(depth - 1):
                nested = {f"level_{depth - 1 - i}": nested}
            
            db["deep"] = nested
            result = db["deep"]
            
            assert isinstance(result, dict)
            
            db.close()


# =============================================================================
# セクション4: 最小キャパシティのテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestMinimumCapacity:
    """最小キャパシティ設定のテスト"""

    def test_hot_capacity_1(self):
        """hot_capacity=1でのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, hot_capacity=1, storage_mode="bytes")
            
            # 複数のキーを追加
            db["key1"] = b"value1"
            db["key2"] = b"value2"
            db["key3"] = b"value3"
            
            # 全て取得可能
            assert db["key1"] == b"value1"
            assert db["key2"] == b"value2"
            assert db["key3"] == b"value3"
            
            db.close()

    def test_hot_capacity_1_persistence(self):
        """hot_capacity=1での永続化"""
        with windows_safe_temp_db() as db_path:
            db1 = DictSQLiteV4(db_path, hot_capacity=1, storage_mode="bytes")
            
            for i in range(10):
                db1[f"key_{i}"] = f"value_{i}".encode()
            
            db1.close()
            
            # 再度開いて全て取得可能
            db2 = DictSQLiteV4(db_path, storage_mode="bytes")
            for i in range(10):
                assert db2[f"key_{i}"] == f"value_{i}".encode()
            
            db2.close()

    def test_pool_size_1(self):
        """pool_size=1でのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, pool_size=1, storage_mode="bytes")
            
            for i in range(100):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            assert len(db) == 100
            
            db.close()

    def test_buffer_size_1(self):
        """buffer_size=1でのテスト"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path, 
                buffer_size=1, 
                persist_mode="lazy",
                storage_mode="bytes"
            )
            
            for i in range(10):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            db.flush()
            
            for i in range(10):
                assert db[f"key_{i}"] == f"value_{i}".encode()
            
            db.close()


# =============================================================================
# セクション5: 並行アクセステスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestConcurrentAccess:
    """並行アクセスのテスト"""

    def test_concurrent_writes_threads(self):
        """マルチスレッドでの並行書き込み"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            def write_items(thread_id, count):
                for i in range(count):
                    db[f"thread_{thread_id}_key_{i}"] = f"value_{thread_id}_{i}".encode()
            
            threads = []
            for t_id in range(5):
                t = threading.Thread(target=write_items, args=(t_id, 20))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # 全て書き込まれている
            assert len(db) == 5 * 20
            
            db.close()

    def test_concurrent_reads_threads(self):
        """マルチスレッドでの並行読み取り"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # データを事前に追加
            for i in range(100):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            results = []
            lock = threading.Lock()
            
            def read_items(start, count):
                local_results = []
                for i in range(start, start + count):
                    val = db[f"key_{i}"]
                    local_results.append(val)
                with lock:
                    results.extend(local_results)
            
            threads = []
            for t_id in range(5):
                t = threading.Thread(target=read_items, args=(t_id * 20, 20))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            assert len(results) == 100
            
            db.close()

    def test_concurrent_mixed_operations(self):
        """マルチスレッドでの混在操作"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 初期データ
            for i in range(50):
                db[f"key_{i}"] = f"value_{i}".encode()
            
            errors = []
            
            def worker(worker_id):
                try:
                    for i in range(10):
                        # 書き込み
                        db[f"worker_{worker_id}_key_{i}"] = f"w{worker_id}_{i}".encode()
                        # 読み取り
                        _ = db[f"key_{i % 50}"]
                except Exception as e:
                    errors.append(e)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(worker, i) for i in range(5)]
                concurrent.futures.wait(futures)
            
            assert len(errors) == 0, f"Errors occurred: {errors}"
            
            db.close()


# =============================================================================
# セクション6: 暗号化モードのテスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEncryptionEdgeCases:
    """暗号化モードのエッジケース"""

    def test_encryption_with_empty_value(self):
        """暗号化モードで空の値"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                encryption_password="password123",
                storage_mode="bytes"
            )
            
            db["empty"] = b""
            assert db["empty"] == b""
            
            db.close()

    def test_encryption_with_large_value(self):
        """暗号化モードで大きな値"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                encryption_password="password123",
                storage_mode="bytes"
            )
            
            large_value = b"x" * (100 * 1024)  # 100KB
            db["large"] = large_value
            
            result = db["large"]
            assert result == large_value
            
            db.close()

    def test_encryption_persistence(self):
        """暗号化データの永続化"""
        with windows_safe_temp_db() as db_path:
            password = "secure_password_456"
            
            db1 = DictSQLiteV4(
                db_path,
                encryption_password=password,
                storage_mode="bytes"
            )
            db1["secret"] = b"my_secret_data"
            db1.close()
            
            db2 = DictSQLiteV4(
                db_path,
                encryption_password=password,
                storage_mode="bytes"
            )
            assert db2["secret"] == b"my_secret_data"
            db2.close()

    def test_encryption_with_unicode_password(self):
        """ユニコードパスワードでの暗号化"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(
                db_path,
                encryption_password="パスワード123🔐",
                storage_mode="bytes"
            )
            
            db["key"] = b"value"
            assert db["key"] == b"value"
            
            db.close()


# =============================================================================
# セクション7: 空のDB操作テスト
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestEmptyDatabaseOperations:
    """空のデータベースでの操作テスト"""

    def test_keys_on_empty_db(self):
        """空DBでkeys()"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.keys()
            
            assert isinstance(result, list)
            assert len(result) == 0
            
            db.close()

    def test_values_on_empty_db(self):
        """空DBでvalues()"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.values()
            
            assert isinstance(result, list)
            assert len(result) == 0
            
            db.close()

    def test_items_on_empty_db(self):
        """空DBでitems()"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = db.items()
            
            assert isinstance(result, list)
            assert len(result) == 0
            
            db.close()

    def test_len_on_empty_db(self):
        """空DBでlen()"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            result = len(db)
            
            assert result == 0
            
            db.close()

    def test_iter_on_empty_db(self):
        """空DBでイテレーション"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            count = 0
            for _ in db:
                count += 1
            
            assert count == 0
            
            db.close()

    def test_clear_on_empty_db(self):
        """空DBでclear()"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # エラーなく完了
            db.clear()
            
            assert len(db) == 0
            
            db.close()


# =============================================================================
# セクション8: バイナリデータのエッジケース
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestBinaryDataEdgeCases:
    """バイナリデータのエッジケース"""

    def test_all_byte_values(self):
        """全256バイト値（0x00-0xFF）を含むデータ"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            all_bytes = bytes(range(256))
            db["all_bytes"] = all_bytes
            
            result = db["all_bytes"]
            assert result == all_bytes
            assert len(result) == 256
            
            db.close()

    def test_null_bytes_in_value(self):
        """NULLバイトを含む値"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            value_with_nulls = b"before\x00middle\x00after"
            db["nulls"] = value_with_nulls
            
            result = db["nulls"]
            assert result == value_with_nulls
            
            db.close()

    def test_empty_bytes_value(self):
        """空のバイト列"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            db["empty"] = b""
            
            assert db["empty"] == b""
            
            db.close()


# =============================================================================
# セクション9: 非同期エッジケース
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestAsyncEdgeCases:
    """非同期操作のエッジケース"""

    @pytest.mark.asyncio
    async def test_async_rapid_writes(self):
        """高速な連続書き込み"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            for i in range(100):
                await db.aset(f"rapid_key_{i}", f"value_{i}".encode())
            
            await db.aflush()
            
            # 全て書き込まれている
            for i in range(100):
                result = await db.aget(f"rapid_key_{i}")
                assert result == f"value_{i}".encode()
            
            await db.aclose()

    @pytest.mark.asyncio
    async def test_async_concurrent_operations(self):
        """非同期での並行操作"""
        with windows_safe_temp_db() as db_path:
            db = AsyncDictSQLite(db_path, storage_mode="bytes")
            
            async def write_and_read(key, value):
                await db.aset(key, value)
                return await db.aget(key)
            
            tasks = [
                write_and_read(f"key_{i}", f"value_{i}".encode())
                for i in range(50)
            ]
            
            results = await asyncio.gather(*tasks)
            
            for i, result in enumerate(results):
                assert result == f"value_{i}".encode()
            
            await db.aclose()


# =============================================================================
# セクション10: テーブルのエッジケース
# =============================================================================

@pytest.mark.skipif(not DICTSQLITE_V4_AVAILABLE, reason="DictSQLiteV4 module not built")
class TestTableEdgeCases:
    """テーブルのエッジケース"""

    def test_same_key_different_tables(self):
        """異なるテーブルで同じキー"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            t1 = db.table("table1")
            t2 = db.table("table2")
            
            t1["shared_key"] = b"value_from_t1"
            t2["shared_key"] = b"value_from_t2"
            
            assert t1["shared_key"] == b"value_from_t1"
            assert t2["shared_key"] == b"value_from_t2"
            
            db.close()

    def test_table_with_special_name(self):
        """特殊な名前のテーブル"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            # 数字で始まるテーブル名
            t1 = db.table("123table")
            t1["key"] = b"value"
            assert t1["key"] == b"value"
            
            # スペースを含むテーブル名
            t2 = db.table("my table")
            t2["key"] = b"value"
            assert t2["key"] == b"value"
            
            # Unicode テーブル名
            t3 = db.table("日本語テーブル")
            t3["key"] = b"value"
            assert t3["key"] == b"value"
            
            db.close()

    def test_many_tables(self):
        """大量のテーブル（100個）"""
        with windows_safe_temp_db() as db_path:
            db = DictSQLiteV4(db_path, storage_mode="bytes")
            
            tables = []
            for i in range(100):
                t = db.table(f"table_{i}")
                t["key"] = f"value_{i}".encode()
                tables.append(t)
            
            # 全テーブルのデータを検証
            for i, t in enumerate(tables):
                assert t["key"] == f"value_{i}".encode()
            
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
