"""DictSQLite-Fastest: High-performance SQLite dictionary using APSW."""

import base64
import collections.abc
import json
import pickle
import secrets
import string
import threading
import logging
import asyncio
import queue
import zlib  # 圧縮サポートのため追加
import weakref  # 弱参照によるメモリ最適化
import time
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import apsw

# aiosqlite サポート（非同期版で使用）
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    aiosqlite = None

# ZSTDサポート（オプション）
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    zstd = None

from dictsqlite_fastest.modules import crypto, utils
from dictsqlite_fastest.modules.safe_pickle import SafePolicy, safe_loads
from dictsqlite_fastest.modules import safe_pickle

__version__ = '1.0.0'

# 公開API
__all__ = [
    'DictSQLiteFastest',
    'AsyncDictSQLiteFastest',
    'randomstrings',
    'expiring_dict',
    'safe_pickle',
    'SafePolicy',
    'safe_loads'
]

# ロガーの設定
logger = logging.getLogger(__name__)

class AdvancedConnectionPool:
    """スレッドプール対応の高性能APSWコネクションプール"""

    def __init__(self, db_name: str, max_connections: int = 20, **db_args):
        self.db_name = db_name
        self.max_connections = max_connections
        self.db_args = db_args
        self._pool = queue.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()

    def get_connection(self) -> apsw.Connection:
        """プールからコネクションを取得"""
        try:
            # 既存のコネクションを試す
            conn = self._pool.get_nowait()
            # コネクションが有効かチェック
            try:
                conn.cursor().execute("SELECT 1")
                return conn
            except Exception:  # pylint: disable=broad-exception-caught
                # 無効なコネクションの場合は新しいものを作成
                pass
        except queue.Empty:
            pass

        # 新しいコネクションを作成
        with self._lock:
            if self._created_connections < self.max_connections:
                conn = self._create_connection()
                self._created_connections += 1
                return conn

        # プールが満杯の場合は待機
        return self._pool.get()

    def return_connection(self, conn: apsw.Connection):
        """コネクションをプールに返却"""
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            # プールが満杯の場合はコネクションを閉じる
            try:
                conn.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            with self._lock:
                self._created_connections -= 1

    def _create_connection(self) -> apsw.Connection:
        """新しいAPSWコネクションを作成して最適化"""
        conn = apsw.Connection(self.db_name)

        # 高度な最適化設定を適用
        self._optimize_connection(conn)

        return conn

    def _optimize_connection(self, conn: apsw.Connection):
        """コネクションの最適化設定を適用"""
        db_args = self.db_args

        # 基本PRAGMA設定
        conn.pragma("busy_timeout", 30000)  # 30秒タイムアウト
        conn.pragma("synchronous", "NORMAL")  # バランスの取れた同期設定
        conn.pragma("cache_size", db_args.get('cache_size', -64000))  # 64MBキャッシュ
        conn.pragma("temp_store", "MEMORY")  # 一時データをメモリに
        conn.pragma("mmap_size", db_args.get('mmap_size', 268435456))  # 256MB mmap
        conn.pragma("journal_mode", db_args.get('journal_mode', 'WAL'))

        if db_args.get('journal_mode') == 'WAL':
            conn.pragma("wal_autocheckpoint", db_args.get('wal_autocheckpoint', 1000))
            # WAL最適化: メモリ優先設定
            if db_args.get('enable_memory_optimization', True):
                conn.pragma("locking_mode", "EXCLUSIVE")  # 排他ロックでWAL性能向上
                conn.pragma("journal_size_limit", 67108864)  # 64MB WALサイズ上限

        # メモリ最適化設定
        if db_args.get('enable_memory_optimization', True):
            conn.pragma("secure_delete", "OFF")  # セキュア削除無効で高速化
            conn.pragma("read_uncommitted", "ON")  # 未コミット読み取りで性能向上
            conn.pragma("cell_size_check", "OFF")  # セルサイズチェック無効

        # カスタムPRAGMA設定
        custom_settings = db_args.get('custom_pragma_settings', {})
        for key, value in custom_settings.items():
            conn.pragma(key, value)

    def close_all(self):
        """全てのコネクションを閉じる"""
        while True:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
            except queue.Empty:
                break

        with self._lock:
            self._created_connections = 0


class AdvancedStatementCache:
    """高度なAPSWプリペアドステートメントキャッシュ（スレッドセーフ）"""

    def __init__(self, max_cache_size: int = 100):
        self.max_cache_size = max_cache_size
        self._local = threading.local()

    def _get_cache(self):
        """スレッドローカルキャッシュを取得"""
        if not hasattr(self._local, 'cache'):
            self._local.cache = {}
            self._local.access_times = {}
            self._local.cache_lock = threading.Lock()

        return self._local.cache, self._local.access_times, self._local.cache_lock

    def get_prepared_cursor(self, conn: apsw.Connection, sql: str) -> apsw.Cursor:
        """プリペアドステートメント用のカーソルを取得（LRUキャッシュ付き）"""
        cache, access_times, cache_lock = self._get_cache()

        with cache_lock:
            if sql in cache:
                access_times[sql] = time.time()
                cursor = cache[sql]
                # カーソルが有効かチェック
                try:
                    # カーソルの有効性をテスト
                    return cursor
                except Exception:  # pylint: disable=broad-exception-caught
                    # 無効なカーソルの場合は削除
                    del cache[sql]
                    del access_times[sql]

            # キャッシュサイズ制限チェック
            if len(cache) >= self.max_cache_size:
                # 最も古いエントリを削除
                oldest_sql = min(access_times.keys(), key=lambda k: access_times[k])
                old_cursor = cache.pop(oldest_sql)
                try:
                    old_cursor.close()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
                del access_times[oldest_sql]

            # 新しいカーソルを作成してキャッシュ
            cursor = conn.cursor()
            cache[sql] = cursor
            access_times[sql] = time.time()
            return cursor

    def clear_cache(self):
        """現在のスレッドのキャッシュをクリア"""
        if hasattr(self._local, 'cache'):
            cache, access_times, cache_lock = self._get_cache()
            with cache_lock:
                for cursor in cache.values():
                    try:
                        cursor.close()
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                cache.clear()
                access_times.clear()


class APSWBulkOperator:
    """APSW最適化バルク操作クラス"""

    def __init__(self, connection: apsw.Connection, table_name: str):
        self.connection = connection
        self.table_name = table_name
        self._insert_sql = f"INSERT OR REPLACE INTO {table_name} (key, value) VALUES (?, ?)"
        self._select_sql = f"SELECT value FROM {table_name} WHERE key = ?"
        self._delete_sql = f"DELETE FROM {table_name} WHERE key = ?"
        self._bulk_select_template = f"SELECT key, value FROM {table_name} WHERE key IN ({{}})"
        self._bulk_delete_template = f"DELETE FROM {table_name} WHERE key IN ({{}})"

    def bulk_insert_optimized(self, items: List[Tuple[str, str]]) -> None:
        """APSW最適化バルク挿入"""
        cursor = self.connection.cursor()
        try:
            # トランザクション開始
            cursor.execute("BEGIN IMMEDIATE")

            # APSWの高速バインド実行
            cursor.executemany(self._insert_sql, items)

            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()

    def bulk_select_optimized(self, keys: List[str]) -> Dict[str, str]:
        """APSW最適化バルク取得（IN句の最適化）"""
        if not keys:
            return {}

        # 大量のキーの場合は分割処理（メモリ効率とパフォーマンスのバランス）
        chunk_size = 999  # SQLiteのIN句制限対策（最大999パラメータ）
        results = {}

        cursor = self.connection.cursor()
        try:
            for i in range(0, len(keys), chunk_size):
                chunk_keys = keys[i:i + chunk_size]
                placeholders = ','.join('?' * len(chunk_keys))
                sql = self._bulk_select_template.format(placeholders)

                for key, value in cursor.execute(sql, chunk_keys):
                    results[key] = value
        finally:
            cursor.close()

        return results

    def bulk_delete_optimized(self, keys: List[str]) -> int:
        """APSW最適化バルク削除"""
        if not keys:
            return 0

        cursor = self.connection.cursor()
        deleted_count = 0
        try:
            cursor.execute("BEGIN IMMEDIATE")

            # 分割削除で制限回避（メモリ効率とパフォーマンスのバランス）
            chunk_size = 999  # SQLiteのIN句制限対策（最大999パラメータ）
            for i in range(0, len(keys), chunk_size):
                chunk_keys = keys[i:i + chunk_size]
                placeholders = ','.join('?' * len(chunk_keys))
                sql = self._bulk_delete_template.format(placeholders)

                cursor.execute(sql, chunk_keys)
                deleted_count += self.connection.changes()  # Use connection.changes() instead of cursor.changes()

            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()

        return deleted_count


# グローバルデータベース初期化管理
_db_init_locks = {}
_db_init_states = {}  # データベースファイルごとの初期化状態
_db_init_lock = threading.RLock()


def randomstrings(n):
    """英字からなる長さnのランダム文字列を返す。"""
    return ''.join(secrets.choice(string.ascii_letters) for _ in range(n))


def expiring_dict(expiration_time: int):
    """指定秒数の有効期限を持つ辞書を生成する。"""
    return utils.ExpiringDict(expiration_time)


class DBSyncedSet(set):
    """DBと自動同期するSetクラス"""

    def __init__(self, key, proxy, initial=None):
        super().__init__(initial if initial is not None else set())
        self._key = key
        self._proxy = proxy

    def sync(self):
        """現在のset内容をDBに保存"""
        self._proxy[self._key] = set(self)

    def add(self, element):
        super().add(element)
        self.sync()

    def remove(self, element):
        super().remove(element)
        self.sync()

    def discard(self, element):
        super().discard(element)
        self.sync()

    def pop(self):
        val = super().pop()
        self.sync()
        return val

    def clear(self):
        super().clear()
        self.sync()

    def update(self, *others):
        super().update(*others)
        self.sync()

    def intersection_update(self, *others):
        super().intersection_update(*others)
        self.sync()

    def difference_update(self, *others):
        super().difference_update(*others)
        self.sync()

    def symmetric_difference_update(self, other):
        super().symmetric_difference_update(other)
        self.sync()

    def __ior__(self, other):
        result = super().__ior__(other)
        self.sync()
        return result

    def __iand__(self, other):
        result = super().__iand__(other)
        self.sync()
        return result

    def __ixor__(self, other):
        result = super().__ixor__(other)
        self.sync()
        return result

    def __isub__(self, other):
        result = super().__isub__(other)
        self.sync()
        return result


class DBSyncedList(list):
    """DBと自動同期するListクラス"""

    def __init__(self, key, proxy, initial=None):
        super().__init__(initial if initial is not None else [])
        self._key = key
        self._proxy = proxy

    def sync(self):
        """現在のlist内容をDBに保存"""
        self._proxy[self._key] = list(self)

    def append(self, val):
        super().append(val)
        self.sync()

    def extend(self, vals):
        super().extend(vals)
        self.sync()

    def remove(self, val):
        super().remove(val)
        self.sync()

    def pop(self, idx=-1):
        val = super().pop(idx)
        self.sync()
        return val

    def clear(self):
        super().clear()
        self.sync()

    def insert(self, idx, val):
        super().insert(idx, val)
        self.sync()

    def reverse(self):
        super().reverse()
        self.sync()

    def sort(self, key=None, reverse=False):
        super().sort(key=key, reverse=reverse)
        self.sync()

    def __setitem__(self, idx, val):
        super().__setitem__(idx, val)
        self.sync()

    def __delitem__(self, idx):
        super().__delitem__(idx)
        self.sync()

    def __iadd__(self, other):
        result = super().__iadd__(other)
        self.sync()
        return result

    def __imul__(self, other):
        result = super().__imul__(other)
        self.sync()
        return result


class DictSQLiteFastest:
    """High-performance SQLite dictionary using APSW with thread-safe connections."""

    def _validate_journal_mode(self, mode: str) -> str:
        """Journal modeを検証し、正規化する。"""
        if not isinstance(mode, str):
            raise ValueError("journal_mode must be a string")
        value = mode.strip().upper()
        allowed = {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}
        if value not in allowed:
            raise ValueError(f"Invalid journal_mode: {mode}")
        return value

    def _validate_storage_mode(self, mode: str) -> str:
        if not isinstance(mode, str):
            raise ValueError("storage_mode must be a string")
        v = mode.lower().strip()
        allowed = {"pickle", "json"}
        if v not in allowed:
            raise ValueError(f"Invalid storage_mode: {mode}. Choose from {allowed}")
        return v

    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        schema: Optional[str] = None,
        journal_mode: str = "WAL",  # Default to WAL for better concurrency
        lock_file: str = None,
        password: str = None,
        publickey_path: str = "./public_keys.pem",
        privatekey_path: str = "./private_keys.pem",
        version: int = 1,
        key_create: bool = False,
        # 安全pickle関連の設定
        safe_pickle_policy: Optional[SafePolicy] = None,
        safe_pickle_allowed_module_prefixes=(),
        safe_pickle_allowed_builtins=None,
        safe_pickle_allowed_globals=(),
        # 保存形式モード (pickle / json)
        storage_mode: str = 'pickle',
        # パフォーマンス設定
        cache_size: int = -64000,  # 64MB cache (negative = KB)
        mmap_size: int = 268435456,  # 256MB mmap
        wal_autocheckpoint: int = 1000,  # WAL checkpoint interval
        # 新しい最適化オプション
        optimize_on_init: bool = True,  # 初期化時に最適化を実行
        enable_memory_optimization: bool = True,  # メモリ最適化を有効化
        custom_pragma_settings: dict = None,  # カスタムPRAGMA設定
        enable_compression: bool = False,  # 大きな値の圧縮を有効化
        compression_threshold: int = 1024,  # 圧縮閾値（バイト）
        compression_algorithm: str = 'zlib',  # 圧縮アルゴリズム ('zlib', 'zstd')
    ):
        # 基本属性設定
        self.version = version
        self.db_name = db_name
        self.password = password
        self.publickey_path = publickey_path
        self.privatekey_path = privatekey_path
        self.table_name = table_name

        # storage_mode検証
        self.storage_mode = self._validate_storage_mode(storage_mode)

        # パフォーマンス設定
        self.cache_size = cache_size
        self.mmap_size = mmap_size
        self.wal_autocheckpoint = wal_autocheckpoint
        self.optimize_on_init = optimize_on_init
        self.enable_memory_optimization = enable_memory_optimization
        self.custom_pragma_settings = custom_pragma_settings or {}
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold
        self.compression_algorithm = compression_algorithm

        # 圧縮アルゴリズムの検証
        if self.enable_compression:
            if compression_algorithm == 'zstd' and not ZSTD_AVAILABLE:
                logger.warning("ZSTD not available, falling back to zlib compression")
                self.compression_algorithm = 'zlib'
            elif compression_algorithm not in ['zlib', 'zstd']:
                raise ValueError(f"Invalid compression algorithm: {compression_algorithm}. Must be 'zlib' or 'zstd'")

        # ZSTDコンプレッサーの初期化（スレッドセーフ）
        self._zstd_compressor = None
        self._zstd_decompressor = None
        if self.enable_compression and self.compression_algorithm == 'zstd' and ZSTD_AVAILABLE:
            # 高性能設定でZSTDコンプレッサーを初期化
            self._zstd_compressor = zstd.ZstdCompressor(level=3, threads=-1)  # レベル3で高速
            self._zstd_decompressor = zstd.ZstdDecompressor()

        # journal_mode検証
        validated_journal_mode = "WAL"  # Default to WAL
        if journal_mode is not None:
            validated_journal_mode = self._validate_journal_mode(journal_mode)
        self.journal_mode = validated_journal_mode

        # 鍵生成
        if self.password is not None and key_create:
            crypto.key_create(password, publickey_path, privatekey_path)

        # スレッドローカルストレージ用
        self._local = threading.local()
        self._lock = threading.RLock()

        # 高度なステートメントキャッシュ
        self._statement_cache = AdvancedStatementCache(max_cache_size=100)

        # 高度なコネクションプール初期化
        try:
            pool_config = {
                'cache_size': self.cache_size,
                'mmap_size': self.mmap_size,
                'wal_autocheckpoint': self.wal_autocheckpoint,
                'journal_mode': self.journal_mode,
                'custom_pragma_settings': self.custom_pragma_settings
            }
            self._connection_pool = AdvancedConnectionPool(
                self.db_name,
                max_connections=20,
                **pool_config
            )
        except Exception as e:
            logger.warning(f"Could not initialize connection pool: {e}, falling back to single connection")
            self._connection_pool = None

        # ロックファイル設定
        if lock_file is None:
            self.lock_file = f"{db_name}.lock"
        else:
            self.lock_file = lock_file

        # データベースの初期化を一度だけ実行
        self._initialize_database(schema)
        
        # 【重要】初期化直後に現在のスレッドでもテーブルを確認
        # GitHub Actions等のLinux環境でWAL可視性問題を回避
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # テーブル存在を明示的に確認・作成
            if schema is None:
                create_sql = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
            else:
                create_sql = schema
            cursor.execute(create_sql)
            # 確実に反映させる
            cursor.execute(f"SELECT COUNT(*) FROM {self._quote_ident(self.table_name)}")
            cursor.fetchone()
        except Exception as e:
            logger.warning(f"Post-initialization table verification failed: {e}")
        finally:
            cursor.close()

        # 初期化時に最適化を実行
        if self.optimize_on_init:
            self.optimize_database()

        # 安全pickle設定
        self.safe_pickle_policy = safe_pickle_policy
        self.safe_pickle_allowed_module_prefixes = tuple(
            (
                safe_pickle_allowed_module_prefixes
                if safe_pickle_allowed_module_prefixes
                else ("dictsqlite_fastest",)
            )
        )
        self.safe_pickle_allowed_builtins = safe_pickle_allowed_builtins
        default_allowed_globals = {"dictsqlite_fastest.modules.utils.ExpiringDict"}
        add_allowed = set(safe_pickle_allowed_globals) if safe_pickle_allowed_globals else set()
        self.safe_pickle_allowed_globals = default_allowed_globals.union(add_allowed)

        # Prepared statements for performance
        self._prepare_statements()

        # Initialize advanced APSW components (will be created per connection)
        self._stmt_cache = None
        self._bulk_operator = None

    def _initialize_database(self, schema=None):
        """データベースの初期化を一度だけ実行（グローバル同期）- 強化版"""
        global _db_init_locks, _db_init_states, _db_init_lock # noqa:F824

        # データベースファイル+テーブル名をキーとして使用
        init_key = f"{self.db_name}:{self.table_name}"

        # データベースファイルごとの初期化ロック取得
        with _db_init_lock:
            if init_key not in _db_init_locks:
                _db_init_locks[init_key] = threading.RLock()
                _db_init_states[init_key] = False
            db_lock = _db_init_locks[init_key]

        # データベースファイル固有のロックで初期化
        with db_lock:
            if not _db_init_states[init_key]:
                # 初期化用の接続を作成
                init_conn = apsw.Connection(self.db_name)
                init_conn.pragma("busy_timeout", 30000)

                # journal_mode設定
                if self.journal_mode is not None:
                    init_conn.pragma("journal_mode", self.journal_mode)

                # テーブル作成
                cursor = init_conn.cursor()
                try:
                    if schema is None:
                        schema = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
                    cursor.execute(schema)
                    
                    # WALモードの可視性問題を強力に解決
                    if self.journal_mode == 'WAL':
                        try:
                            # TRUNCATEモードで強制的にチェックポイント実行
                            # これにより確実に他のコネクションからも見えるようになる
                            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        except Exception:  # pylint: disable=broad-exception-caught
                            try:
                                # TRUNCATEが失敗したらRESTARTを試す
                                cursor.execute("PRAGMA wal_checkpoint(RESTART)")
                            except Exception:  # pylint: disable=broad-exception-caught
                                # それでも失敗したらPASSIVE
                                try:
                                    cursor.execute("PRAGMA wal_checkpoint(PASSIVE)")
                                except Exception:  # pylint: disable=broad-exception-caught
                                    pass
                finally:
                    cursor.close()

                # 初期化完了フラグを設定
                init_conn.close()
                _db_init_states[init_key] = True

    def _get_connection(self):
        """高性能スレッドローカル接続（最適化済み）"""
        # スレッドローカル接続を優先（コネクションプールのオーバーヘッドを削減）
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = apsw.Connection(self.db_name)
            self._optimize_single_connection(self._local.conn)

            # カーソルキャッシュも初期化
            self._local.cursor_cache = self._local.conn.cursor()

        return self._local.conn

    def _return_connection(self, conn):
        """コネクション返却（スレッドローカルの場合は何もしない）"""
        # スレッドローカル接続では返却不要（パフォーマンス向上）
        pass

    def _optimize_single_connection(self, conn):
        """単一コネクションの最適化（APSW最適化強化）"""
        # 基本PRAGMA設定（最高性能）
        conn.pragma("busy_timeout", 30000)
        conn.pragma("synchronous", "NORMAL")  # OFF -> NORMAL for async safety
        conn.pragma("cache_size", self.cache_size)
        conn.pragma("temp_store", "MEMORY")
        conn.pragma("mmap_size", self.mmap_size)
        conn.pragma("journal_mode", self.journal_mode)

        # APSW高速化設定
        conn.pragma("page_size", 65536)  # 64KBページサイズ
        conn.pragma("auto_vacuum", "NONE")  # バキューム無効で高速化
        conn.pragma("count_changes", "OFF")  # 変更カウント無効
        conn.pragma("legacy_file_format", "OFF")  # 新フォーマットで高速化

        if self.journal_mode == "WAL":
            conn.pragma("wal_autocheckpoint", self.wal_autocheckpoint)
            conn.pragma("wal_checkpoint_threshold", 1000)  # WAL閾値設定
            # WAL最適化: より積極的なメモリ利用
            if self.enable_memory_optimization:
                conn.pragma("locking_mode", "EXCLUSIVE")  # 排他ロックでWAL性能向上
                conn.pragma("journal_size_limit", 67108864)  # 64MB WALサイズ上限

        # メモリ最適化設定（追加の高速化）
        if self.enable_memory_optimization:
            conn.pragma("secure_delete", "OFF")  # セキュア削除無効で高速化
            conn.pragma("read_uncommitted", "ON")  # 未コミット読み取りで性能向上
            conn.pragma("cell_size_check", "OFF")  # セルサイズチェック無効
            # クエリプランナー最適化
            conn.pragma("optimize", 0x10002)  # クエリプランナーの統計を更新

        # カスタム設定適用
        for key, value in self.custom_pragma_settings.items():
            conn.pragma(key, value)

    def _get_prepared_cursor(self, conn, sql):
        """プリペアドステートメント用のカーソルを取得"""
        return self._statement_cache.get_prepared_cursor(conn, sql)

    def _get_cursor(self):
        """高速カーソル取得（キャッシュ使用）"""
        conn = self._get_connection()

        # カーソルキャッシュを使用（新規作成のオーバーヘッド削減）
        if hasattr(self._local, 'cursor_cache') and self._local.cursor_cache:
            return self._local.cursor_cache, conn
        
        cursor = conn.cursor()
        self._local.cursor_cache = cursor
        return cursor, conn

    def _execute_with_cursor(self, query, params=None):
        """高速クエリ実行（オーバーヘッド最小化）"""
        cursor, _ = self._get_cursor()
        # カーソル閉じない＆コネクション返却しない（再利用のため）
        if params:
            return list(cursor.execute(query, params))
        
        return list(cursor.execute(query))

    def _execute_fetchone(self, query, params=None):
        """高速単一結果取得（オーバーヘッド最小化）"""
        cursor, _ = self._get_cursor()
        # カーソル閉じない＆コネクション返却しない（再利用のため）
        if params:
            result = cursor.execute(query, params)
        else:
            result = cursor.execute(query)

        # 最初の行を取得
        try:
            return next(iter(result))
        except StopIteration:
            return None

    def _get_prepared_statement(self, stmt_type):
        """プリペアドステートメントを取得"""
        if stmt_type == 'insert':
            return self._insert_stmt
        elif stmt_type == 'select':
            return self._select_stmt
        elif stmt_type == 'delete':
            return self._delete_stmt
        elif stmt_type == 'exists':
            return self._exists_stmt
        elif stmt_type == 'select_all':
            return self._select_all_stmt
        else:
            raise ValueError(f"Unknown statement type: {stmt_type}")

    def _ensure_table_exists(self, schema=None):
        """テーブルが存在することを確認 (初期化時に既に作成済み)"""
        # テーブルは _initialize_database で既に作成済み
        pass

    def _ensure_table_exists_fast(self):
        """超高速テーブル存在確認（強化版 - WAL対応）
        
        WALモードでのコネクション間可視性問題に対応した堅牢な実装。
        各コネクションで直接テーブルの存在を確認し、必要なら作成。
        
        戦略:
        1. スレッドローカルフラグで2回目以降をスキップ（最速）
        2. グローバルフラグで大部分のケースをスキップ
        3. それでもダメな場合は直接SQLでテーブル確認・作成
        """
        global _db_init_states
        
        # 【超高速パス】スレッドローカルフラグ（このスレッドで既に確認済み）
        if getattr(self._local, 'table_verified', False):
            return  # 2-5ナノ秒
        
        # データベース+テーブルの初期化キー
        init_key = f"{self.db_name}:{self.table_name}"
        
        # 【高速パス】グローバルフラグチェック
        if _db_init_states.get(init_key, False):
            # スレッドローカルフラグを設定して次回から超高速パスを使用
            self._local.table_verified = True
            return  # 約10ナノ秒
        
        # 【確実パス】直接このコネクションでテーブルを確認・作成
        # WALモードでは他のコネクションで作成されたテーブルが見えない可能性があるため
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # テーブルが存在するか確認
            result = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (self.table_name,)
            )
            if not list(result):
                # テーブルが存在しない場合は作成
                schema = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'
                cursor.execute(schema)
                
                # グローバルフラグを更新
                _db_init_states[init_key] = True
            
            # スレッドローカルフラグを設定
            self._local.table_verified = True
        except Exception as e:  # pylint: disable=broad-exception-caught
            # 予期しないエラーの場合はログを出力して初期化を試みる
            logger.warning(f"Table verification failed, attempting initialization: {e}")
            self._initialize_database()
            self._local.table_verified = True

    def _prepare_statements(self):
        """パフォーマンス向上のためのprepared statements"""
        # よく使用されるクエリのprepared statementを作成
        table_name = self._quote_ident(self.table_name)
        self._insert_stmt = (
            f"INSERT OR REPLACE INTO {table_name} (key, value) VALUES (?, ?)"  # nosec B608
        )
        self._select_stmt = f"SELECT value FROM {table_name} WHERE key = ?"  # nosec B608
        self._delete_stmt = f"DELETE FROM {table_name} WHERE key = ?"  # nosec B608
        self._exists_stmt = f"SELECT 1 FROM {table_name} WHERE key = ?"  # nosec B608
        self._select_all_stmt = f"SELECT key, value FROM {table_name}"  # nosec B608

    def _compress_value(self, value_str: str) -> str:
        """大きな値を圧縮する（ZSTD/zlib対応）"""
        if not self.enable_compression or len(value_str.encode('utf-8')) < self.compression_threshold:
            return value_str

        value_bytes = value_str.encode('utf-8')

        if self.compression_algorithm == 'zstd' and ZSTD_AVAILABLE and self._zstd_compressor is not None:
            # ZSTD圧縮
            compressed = self._zstd_compressor.compress(value_bytes)
            prefix = "ZSTD:"
        else:
            # zlib圧縮（デフォルト）
            compressed = zlib.compress(value_bytes, level=6)  # バランスの取れた圧縮レベル
            prefix = "ZLIB:"

        # 圧縮されたデータをbase64エンコード + プレフィックス
        compressed_str = prefix + base64.b64encode(compressed).decode('ascii')

        # 圧縮率が十分でない場合は元の値を返す
        if len(compressed_str) >= len(value_str):
            return value_str

        return compressed_str

    def _decompress_value(self, value_str: str) -> str:
        """圧縮された値を展開する（ZSTD/zlib対応）"""
        if value_str.startswith("ZSTD:"):
            if not ZSTD_AVAILABLE or self._zstd_decompressor is None:
                raise RuntimeError("ZSTD decompression requested but zstandard is not available or not initialized")
            # プレフィックスを除去してbase64デコード
            compressed_data = base64.b64decode(value_str[5:])
            # ZSTD展開
            return self._zstd_decompressor.decompress(compressed_data).decode('utf-8')
        elif value_str.startswith("ZLIB:"):
            # プレフィックスを除去してbase64デコード
            compressed_data = base64.b64decode(value_str[5:])
            # zlib展開
            return zlib.decompress(compressed_data).decode('utf-8')
        else:
            # 圧縮されていない
            return value_str

    def _quote_ident(self, identifier: str) -> str:
        """SQLインジェクション対策でテーブル名をクォート。"""
        return f'"{identifier}"'

    class RecursiveDict(collections.abc.MutableMapping):
        """ネストした辞書をDBと同期しつつ操作するためのプロキシ。"""

        def __init__(self, proxy, base_key, path=()):
            self._proxy = proxy
            self._base_key = base_key
            self._path = path

        def to_dict(self):
            """現在の値を通常のdictとして返す。"""
            return self._get_db_value()

        def _get_db_value(self):
            base_val = self._proxy.get_raw_value(self._base_key)
            val = base_val
            for p in self._path:
                val = val[p]
            return val

        def _update_db(self, new_top_level_value):
            self._proxy[self._base_key] = new_top_level_value

        def __getitem__(self, key):
            current_dict = self._get_db_value()
            value = current_dict[key]
            return self._proxy.db.wrap_in_proxy(
                self._base_key, self._proxy, value, path=self._path + (key,)
            )

        def __setitem__(self, key, value):
            if hasattr(value, 'to_dict'):
                value = value.to_dict()
            elif isinstance(value, (DBSyncedList, DBSyncedSet)):
                value = type(value).__bases__[0](value)

            top_level_dict = self._proxy.get_raw_value(self._base_key)
            target_dict_ref = top_level_dict
            for p in self._path:
                target_dict_ref = target_dict_ref[p]
            target_dict_ref[key] = value
            self._update_db(top_level_dict)

        def __delitem__(self, key):
            top_level_dict = self._proxy.get_raw_value(self._base_key)
            target_dict_ref = top_level_dict
            for p in self._path:
                target_dict_ref = target_dict_ref[p]
            del target_dict_ref[key]
            self._update_db(top_level_dict)

        def __iter__(self):
            return iter(self._get_db_value())

        def __len__(self):
            return len(self._get_db_value())

        def __repr__(self):
            return repr(self._get_db_value())

        def keys(self):
            return self._get_db_value().keys()

        def items(self):
            current_dict = self._get_db_value()
            result = []
            for key, value in current_dict.items():
                wrapped_value = self._proxy.db.wrap_in_proxy(
                    self._base_key, self._proxy, value, path=self._path + (key,)
                )
                result.append((key, wrapped_value))
            return result

        def values(self):
            current_dict = self._get_db_value()
            result = []
            for key, value in current_dict.items():
                wrapped_value = self._proxy.db.wrap_in_proxy(
                    self._base_key, self._proxy, value, path=self._path + (key,)
                )
                result.append(wrapped_value)
            return result

        def copy(self):
            """辞書のコピーを返す"""
            return dict(self._get_db_value())

        def get(self, key, default=None):
            """辞書のget()メソッド"""
            try:
                return self.__getitem__(key)
            except KeyError:
                return default

        def __getstate__(self):
            """Pickle時の状態保存（接続情報を除外）"""
            # 実際のデータのみを保存
            return self.to_dict()

        def __setstate__(self, state):
            """Pickle復元時の状態復元"""
            # 通常の辞書として復元
            if isinstance(state, dict):
                self.__dict__.clear()
                self.__dict__.update(state)
            else:
                # バックアップとして元のstate辞書を設定
                self.__dict__.update(state)

    class TableProxy:
        """特定テーブルのキー/値へ直接アクセスするプロキシ（APSW版）。"""

        def __init__(self, db, table_name):
            self.db = db
            self.table_name = table_name

        def get_raw_value(self, key):
            """DBから生の値を取得し、必要に応じて復号/デコードして返す。"""
            # プリペアドステートメントを使用
            stmt = self.db._get_prepared_statement('select')
            result = self.db._execute_fetchone(stmt, (key,))
            if result is None:
                raise KeyError(f"Key {key} not found in table {self.table_name}.")

            value_str = result[0]

            # 圧縮解除（暗号化解除の前に実行）
            value_str = self.db._decompress_value(value_str)

            if self.db.password is not None:
                value_str = self.db._decrypt(value_str)

            # データ形式を自動判定
            try:
                # まずJSONとして試行（既存データ）
                return json.loads(
                    value_str,
                    object_hook=self.db._extended_json_decoder_hook,
                )
            except (json.JSONDecodeError, TypeError):
                try:
                    # JSONが失敗したらpickleとして試行（新しいデータ）
                    if isinstance(value_str, str):
                        value_bytes = base64.b64decode(value_str)
                    else:
                        value_bytes = value_str
                    # 安全なUnpicklerで復元
                    logger.debug(
                        "SafeUnpickler try: key=%s, table=%s", key, self.table_name
                    )
                    obj = safe_loads(
                        value_bytes,
                        policy=self.db.safe_pickle_policy,
                        allowed_module_prefixes=self.db.safe_pickle_allowed_module_prefixes,
                        allowed_builtins=self.db.safe_pickle_allowed_builtins,
                        allowed_globals=self.db.safe_pickle_allowed_globals,
                    )
                    logger.debug("SafeUnpickler success: key=%s", key)
                    return obj
                except (pickle.UnpicklingError, ValueError, TypeError) as e:
                    logger.warning(
                        "SafeUnpickler failed for key=%s in table=%s: %s", key, self.table_name, e
                    )
                    return value_str

        def __getitem__(self, key):
            raw_value = self.get_raw_value(key)
            return self.db.wrap_in_proxy(key, self, raw_value)

        def __setitem__(self, key, value):
            # ゼロコストテーブル存在確認
            self.db._ensure_table_exists_fast()
            
            # storage_mode に応じてシリアライズ
            if self.db.storage_mode == 'pickle':
                value_bytes = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                value_str = base64.b64encode(value_bytes).decode('ascii')
            else:  # json モード - 最適化されたオプション
                try:
                    value_str = json.dumps(
                        value,
                        default=self.db._extended_json_encoder_hook,
                        ensure_ascii=False,
                        separators=(',', ':')  # よりコンパクトな出力
                    )
                except TypeError as e:  # JSON化できない
                    raise TypeError(
                        f"Value for key '{key}' is not JSON serializable. "
                        "Use pickle storage_mode or provide JSON-serializable object."
                    ) from e

            if self.db.password is not None:
                value_str = self.db._encrypt(value_str)

            # 圧縮サポート（暗号化の後に実行）
            value_str = self.db._compress_value(value_str)

            # 再利用可能なカーソルを使用（プリペアドステートメント）
            stmt = self.db._get_prepared_statement('insert')
            self.db._execute_with_cursor(stmt, (key, value_str))

        def __delitem__(self, key):
            # プリペアドステートメントを使用
            stmt = self.db._get_prepared_statement('delete')
            self.db._execute_with_cursor(stmt, (key,))

        def __contains__(self, key):
            # プリペアドステートメントを使用
            stmt = self.db._get_prepared_statement('exists')
            result = self.db._execute_fetchone(stmt, (key,))
            return result is not None

        def __repr__(self):
            return f"{dict(self)}"

        def __iter__(self):
            conn = self.db._get_connection()
            cursor = conn.cursor()
            try:
                for row in cursor.execute(self.db._select_all_stmt):
                    key = row[0]
                    try:
                        yield key, self[key]
                    except (KeyError, json.JSONDecodeError):
                        yield key, row[1]
            finally:
                cursor.close()

        def get_all_rows(self):
            """テーブル内の全行を (key, value) のタプルで返す。"""
            conn = self.db._get_connection()
            cursor = conn.cursor()
            try:
                return list(cursor.execute(self.db._select_all_stmt))
            finally:
                cursor.close()

    def _encrypt(self, data_str: str) -> bytes:
        """文字列をRSAで暗号化してbytesを返す。"""
        return crypto.encrypt_rsa(
            crypto.load_public_key(self.publickey_path, self.password),
            data_str.encode("utf-8"),
        )

    def _decrypt(self, data: bytes) -> str:
        """RSAで復号して文字列に戻す。"""
        return crypto.decrypt_rsa(
            crypto.load_private_key(self.privatekey_path, self.password),
            data,
        ).decode("utf-8")

    def _extended_json_encoder_hook(self, obj):
        """json.dumpsのdefaultフック。setやカスタムオブジェクトを処理。"""
        if isinstance(obj, set):
            return {"__type__": "set", "value": sorted(list(obj))}
        if isinstance(obj, (DBSyncedList, DBSyncedSet)):
            return self._extended_json_encoder_hook(type(obj).__bases__[0](obj))
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _extended_json_decoder_hook(self, dct):
        """json.loadsのobject_hook。カスタム型を復元。"""
        if "__type__" in dct:
            if dct["__type__"] == "set":
                return set(dct["value"])
        return dct

    def _wrap_in_proxy(self, key, proxy, value, path=()):
        """生の値を適切なプロキシオブジェクトでラップする。"""
        if isinstance(value, collections.abc.Mapping):
            return DictSQLiteFastest.RecursiveDict(proxy, key, path)
        if isinstance(value, list):
            if path:
                return value
            return DBSyncedList(key, proxy, value)
        if isinstance(value, set):
            if path:
                return value
            return DBSyncedSet(key, proxy, value)
        return value

    def wrap_in_proxy(self, key, proxy, value, path=()):
        """_wrap_in_proxy の公開エイリアス。"""
        return self._wrap_in_proxy(key, proxy, value, path)

    def create_table(self, schema=None):
        """テーブルを作成する。"""
        if schema is None:
            schema = f'CREATE TABLE IF NOT EXISTS {self._quote_ident(self.table_name)} (key TEXT PRIMARY KEY, value TEXT)'

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(schema)
        finally:
            cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """データベース接続を安全に閉じる"""
        try:
            # ステートメントキャッシュをクリア
            if hasattr(self, '_statement_cache'):
                self._statement_cache.clear_cache()

            # スレッドローカルカーソルキャッシュをクリア
            if hasattr(self._local, 'cursor_cache') and self._local.cursor_cache:
                try:
                    self._local.cursor_cache.close()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
                self._local.cursor_cache = None

            # コネクションプールを閉じる
            if hasattr(self, '_connection_pool') and self._connection_pool:
                self._connection_pool.close_all()

            # スレッドローカル接続を閉じる
            if hasattr(self._local, 'conn') and self._local.conn:
                self._local.conn.close()
                self._local.conn = None

        except Exception as e:
            logger.warning(f"Error during database close: {e}")

    def __del__(self):
        """デストラクタで自動的にクリーンアップ"""
        try:
            self.close()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    # Dict-like interface (v1 compatibility)
    def __getitem__(self, key):
        if self.version == 2:
            # Table proxy for v2
            return DictSQLiteFastest.TableProxy(self, key)
        else:
            # Direct key access for v1
            return DictSQLiteFastest.TableProxy(self, self.table_name)[key]

    def __setitem__(self, key, value):
        DictSQLiteFastest.TableProxy(self, self.table_name)[key] = value

    def __delitem__(self, key):
        del DictSQLiteFastest.TableProxy(self, self.table_name)[key]

    def __contains__(self, key):
        return key in DictSQLiteFastest.TableProxy(self, self.table_name)

    def __len__(self):
        """エントリ数を返す（現在の table_name の行数）。
        version==2 で複数テーブル運用時も self.table_name を対象。
        """
        try:
            cursor, conn = self._get_cursor()
            result = cursor.execute(f"SELECT COUNT(*) FROM {self._quote_ident(self.table_name)}")
            try:
                return next(result)[0]
            except StopIteration:
                return 0
        except Exception:
            # 予期せぬエラー時は 0 を返し安全側に倒す
            return 0

    def keys(self):
        """全キーを返す。"""
        # 再利用可能なカーソルを使用
        result = self._execute_with_cursor(f"SELECT key FROM {self._quote_ident(self.table_name)}")
        return [row[0] for row in result]

    def keys_iter(self):
        """メモリ効率的なキーのイテレータ"""
        # 大量のデータに対してメモリ効率的
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            try:
                for row in cursor.execute(f"SELECT key FROM {self._quote_ident(self.table_name)}"):
                    yield row[0]
            finally:
                cursor.close()
        finally:
            self._return_connection(conn)

    def items_iter(self, batch_size=1000):
        """メモリ効率的なアイテムのイテレータ（バッチ処理）"""
        # バッチ処理で大量のデータを扱う
        conn = self._get_connection()
        cursor = conn.cursor()

        offset = 0
        while True:
            query = f"SELECT key, value FROM {self._quote_ident(self.table_name)} LIMIT {batch_size} OFFSET {offset}"
            rows = list(cursor.execute(query))
            if not rows:
                break

            for key, value_str in rows:
                # 圧縮解除
                value_str = self._decompress_value(value_str)

                if self.storage_mode == 'pickle':
                    value = pickle.loads(base64.b64decode(value_str.encode('ascii')))
                else:  # json
                    value = json.loads(value_str, object_hook=self._extended_json_decoder_hook)
                yield key, value

            offset += batch_size

    def has_key(self, key):
        """キーが存在するか確認。"""
        return key in self

    def clear_table(self):
        """テーブルを空にする。"""
        # 再利用可能なカーソルを使用
        self._execute_with_cursor(f"DELETE FROM {self._quote_ident(self.table_name)}")

    def bulk_insert_apsw_optimized(self, items):
        """APSWネイティブ最適化バルク挿入 - 最高パフォーマンス"""
        if not items:
            return

        # ゼロコストテーブル存在確認（確実にテーブルを作成）
        self._ensure_table_exists_fast()

        # データを準備
        prepared_items = []
        for key, value in (items.items() if hasattr(items, 'items') else items):
            if self.storage_mode == 'pickle':
                value_str = base64.b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)).decode('ascii')
            else:  # json
                value_str = json.dumps(value, default=self._extended_json_encoder_hook,
                                     separators=(',', ':'), ensure_ascii=False)

            # 圧縮サポート
            value_str = self._compress_value(value_str)
            prepared_items.append((key, value_str))

        # APSWネイティブバルク操作を使用（最高性能）
        conn = self._get_connection()
        cursor = conn.cursor()

        # トランザクション開始（バルク操作用）
        cursor.execute("BEGIN IMMEDIATE")
        try:
            # 超高速バルク挿入（APSW最適化）
            insert_sql = f"INSERT OR REPLACE INTO {self._quote_ident(self.table_name)} (key, value) VALUES (?, ?)"
            cursor.executemany(insert_sql, prepared_items)
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise

    def bulk_get_apsw_optimized(self, keys):
        """APSWネイティブ最適化バルク取得 - 最高パフォーマンス"""
        if not keys:
            return {}

        conn = self._get_connection()
        cursor = conn.cursor()

        # IN句を使用した高速バルク取得
        placeholders = ','.join(['?' for _ in keys])
        query = f"SELECT key, value FROM {self._quote_ident(self.table_name)} WHERE key IN ({placeholders})"

        results = {}
        for row in cursor.execute(query, list(keys)):
            key, value_str = row
            # 圧縮解除
            value_str = self._decompress_value(value_str)

            if self.storage_mode == 'pickle':
                value = pickle.loads(base64.b64decode(value_str.encode('ascii')))
            else:  # json
                value = json.loads(value_str, object_hook=self._extended_json_decoder_hook)
            results[key] = value

        return results

    def bulk_delete_apsw_optimized(self, keys):
        """APSWネイティブ最適化バルク削除"""
        if not keys:
            return 0

        conn = self._get_connection()
        if hasattr(self._local, 'bulk_operator'):
            return self._local.bulk_operator.bulk_delete_optimized(keys)
        else:
            # フォールバック
            self.bulk_delete(keys)
            return len(keys)  # 概算

    def bulk_insert(self, items):
        """バルク挿入 - 大量のキー/値ペアを効率的に挿入（トランザクション最適化）"""
        if not items:
            return

        # ゼロコストテーブル存在確認（確実にテーブルを作成）
        self._ensure_table_exists_fast()

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # トランザクション開始で高速化
            cursor.execute("BEGIN IMMEDIATE")

            # プリペアドステートメント使用でパフォーマンス向上
            stmt = self._get_prepared_statement('insert')

            # バルク挿入のためのデータ準備と実行を組み合わせ（メモリ効率化）
            for key, value in (items.items() if hasattr(items, 'items') else items):
                if self.storage_mode == 'pickle':
                    value_str = base64.b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)).decode('ascii')
                else:  # json - 最適化されたオプション
                    value_str = json.dumps(value, default=self._extended_json_encoder_hook,
                                         separators=(',', ':'), ensure_ascii=False)
                cursor.execute(stmt, (key, value_str))

            # トランザクションをコミット
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()

    def bulk_insert_optimized(self, items, auto_optimize=True):
        """自動最適化バルク挿入 - データ量に応じて最適な手法を選択"""
        if not items:
            return

        # データ量に応じてストラテジーを選択
        item_count = len(items) if hasattr(items, '__len__') else len(list(items))

        if auto_optimize:
            if item_count < 50:
                # 少量データは通常の個別挿入で十分
                for key, value in (items.items() if hasattr(items, 'items') else items):
                    self[key] = value
            elif item_count < 500:
                # 中量データはexecutemanyが高速
                self.bulk_insert_executemany(items)
            else:
                # 大量データはチャンク処理で安全に（メモリ効率重視）
                # より大きなチャンクサイズでメモリを活用
                optimal_chunk_size = min(2000, max(500, item_count // 20))
                self.bulk_insert_chunked(items, chunk_size=optimal_chunk_size)
        else:
            # 従来のメソッドを使用
            self.bulk_insert(items)

    def bulk_insert_executemany(self, items):
        """バルク挿入 - executemanyを使用した最高速度バージョン"""
        if not items:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # トランザクション開始で高速化
            cursor.execute("BEGIN IMMEDIATE")

            # データ準備
            insert_data = []
            for key, value in (items.items() if hasattr(items, 'items') else items):
                if self.storage_mode == 'pickle':
                    value_str = base64.b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)).decode('ascii')
                else:  # json - 最適化されたオプション
                    value_str = json.dumps(value, default=self._extended_json_encoder_hook,
                                         separators=(',', ':'), ensure_ascii=False)
                insert_data.append((key, value_str))

            # executemanyで一括実行（通常最も高速）
            stmt = self._get_prepared_statement('insert')
            cursor.executemany(stmt, insert_data)

            # トランザクションをコミット
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()

    def bulk_insert_chunked(self, items, chunk_size=1000):
        """チャンク処理による大容量データの効率的挿入"""
        if not items:
            return

        # メモリ効率を考慮してチャンク処理
        items_iter = items.items() if hasattr(items, 'items') else items

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")

            chunk = []
            for key, value in items_iter:
                if self.storage_mode == 'pickle':
                    value_str = base64.b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)).decode('ascii')
                else:  # json - 最適化されたオプション
                    value_str = json.dumps(value, default=self._extended_json_encoder_hook,
                                         separators=(',', ':'), ensure_ascii=False)
                chunk.append((key, value_str))

                if len(chunk) >= chunk_size:
                    # executemanyでチャンクを一括挿入（パフォーマンス向上）
                    cursor.executemany(self._insert_stmt, chunk)
                    chunk = []

            # 残りのチャンクを処理
            if chunk:
                cursor.executemany(self._insert_stmt, chunk)

            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()

    def bulk_get(self, keys):
        """バルク取得 - 複数のキーを効率的に取得（最適化版）"""
        if not keys:
            return {}

        # 大量のキーの場合はチャンク処理で安全に
        keys_list = list(keys) if not isinstance(keys, list) else keys
        chunk_size = 999  # SQLiteのIN句制限対策（最大999パラメータ）
        
        results = {}
        
        # チャンク単位で処理
        for i in range(0, len(keys_list), chunk_size):
            chunk_keys = keys_list[i:i + chunk_size]
            placeholders = ','.join('?' * len(chunk_keys))
            query = f"SELECT key, value FROM {self._quote_ident(self.table_name)} WHERE key IN ({placeholders})"
            
            for key, value_str in self._execute_with_cursor(query, chunk_keys):
                if self.storage_mode == 'pickle':
                    value = pickle.loads(base64.b64decode(value_str.encode('ascii')))
                else:  # json
                    value = json.loads(value_str, object_hook=self._extended_json_decoder_hook)
                results[key] = value

        return results

    def bulk_delete(self, keys):
        """バルク削除 - 複数のキーを効率的に削除（トランザクション最適化）"""
        if not keys:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # トランザクション開始で高速化
            cursor.execute("BEGIN IMMEDIATE")

            # 大量のキーの場合はチャンク処理で安全に
            keys_list = list(keys) if not isinstance(keys, list) else keys
            chunk_size = 999  # SQLiteのIN句制限対策（最大999パラメータ）
            
            for i in range(0, len(keys_list), chunk_size):
                chunk_keys = keys_list[i:i + chunk_size]
                placeholders = ','.join('?' * len(chunk_keys))
                query = f"DELETE FROM {self._quote_ident(self.table_name)} WHERE key IN ({placeholders})"
                cursor.execute(query, chunk_keys)

            # トランザクションをコミット
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()

    def warmup_connection(self):
        """接続とキャッシュのウォームアップ"""
        # 接続を初期化
        conn = self._get_connection()
        # カーソルキャッシュを初期化
        self._get_cursor()
        # 統計情報を更新
        self.optimize_database()
        # プリペアドステートメントを事前準備
        self._warmup_prepared_statements()

    def _warmup_prepared_statements(self):
        """プリペアドステートメントのウォームアップ"""
        # よく使用されるステートメントを事前に準備
        self._get_prepared_statement('insert')
        self._get_prepared_statement('select')
        self._get_prepared_statement('delete')
        self._get_prepared_statement('exists')
        self._get_prepared_statement('select_all')

    def optimize_database(self, full_optimization=False):
        """データベースの最適化を実行（統計情報の更新など）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 統計情報を更新してクエリプランナーを最適化
            cursor.execute("ANALYZE")

            # 完全最適化モード（時間がかかる場合があるため オプション）
            if full_optimization:
                # VACUUMは大きなファイルでは時間がかかるため、条件付きで実行
                cursor.execute("VACUUM")
                # WALチェックポイントを強制実行
                if self.journal_mode == "WAL":
                    cursor.execute("PRAGMA wal_checkpoint(FULL)")

            # メモリ最適化が有効な場合のチューニング
            if self.enable_memory_optimization:
                # 自動バキュームのトリガー
                cursor.execute("PRAGMA auto_vacuum = INCREMENTAL")
                # インクリメンタルバキューム実行
                cursor.execute("PRAGMA incremental_vacuum(100)")  # 100ページまで

        finally:
            cursor.close()

    def get_performance_stats(self):
        """パフォーマンス統計情報を取得"""
        stats = {
            'database': self.db_name,
            'table': self.table_name,
            'journal_mode': self.journal_mode,
            'storage_mode': self.storage_mode,
            'version': self.version,
            'cache_size': self.cache_size,
            'mmap_size': self.mmap_size,
        }

        # 接続数の情報を追加
        if hasattr(self._local, 'conn') and self._local.conn:
            stats['connection_active'] = True
        else:
            stats['connection_active'] = False

        return stats

    def __repr__(self):
        """辞書風の表現を返す。"""
        items = []
        proxy = DictSQLiteFastest.TableProxy(self, self.table_name)
        try:
            for key, value in proxy:
                items.append(f"{key!r}: {value!r}")
            return "{" + ", ".join(items) + "}"
        except Exception:
            return f"<DictSQLiteFastest at {self.db_name}>"


class ConnectionPool:
    """Connection pool for async operations"""

    def __init__(self, db_factory_func, max_connections: int = 5):
        self.db_factory_func = db_factory_func
        self.max_connections = max_connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()
        # 統計情報
        self._total_gets = 0
        self._pool_hits = 0

    def get_connection(self):
        """Get a connection from the pool"""
        self._total_gets += 1
        try:
            # Try to get an existing connection
            conn = self._pool.get_nowait()
            self._pool_hits += 1
            return conn
        except queue.Empty:
            # Create a new connection if we haven't reached the limit
            with self._lock:
                if self._created_connections < self.max_connections:
                    self._created_connections += 1
                    return self.db_factory_func()
                else:
                    # Wait for a connection to become available
                    return self._pool.get()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if conn is not None and not self._pool.full():
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                # Pool is full, close the connection
                conn.close()

    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except queue.Empty:
                break

    def get_stats(self):
        """Get pool statistics"""
        hit_rate = (self._pool_hits / self._total_gets * 100) if self._total_gets > 0 else 0
        return {
            'total_gets': self._total_gets,
            'pool_hits': self._pool_hits,
            'hit_rate': f"{hit_rate:.1f}%",
            'created_connections': self._created_connections,
            'pool_size': self._pool.qsize()
        }


class AsyncConnectionPool:
    """高度な非同期接続プール（asyncio native）"""

    def __init__(self, db_factory_func, max_connections: int = 10):
        self.db_factory_func = db_factory_func
        self.max_connections = max_connections
        self._pool = asyncio.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = asyncio.Lock()
        self._stats = {
            'total_gets': 0,
            'pool_hits': 0,
            'active_connections': 0,
            'peak_connections': 0
        }

        # 接続の弱参照リスト（ガベージコレクション対応）
        self._connections = weakref.WeakSet()

    async def get_connection(self):
        """非同期で接続を取得"""
        self._stats['total_gets'] += 1

        try:
            # プールから既存接続を取得
            conn = self._pool.get_nowait()
            self._stats['pool_hits'] += 1
            return conn
        except asyncio.QueueEmpty:
            # 新しい接続を作成
            async with self._lock:
                if self._created_connections < self.max_connections:
                    self._created_connections += 1
                    self._stats['active_connections'] += 1
                    self._stats['peak_connections'] = max(
                        self._stats['peak_connections'],
                        self._stats['active_connections']
                    )

                    # スレッドプールで同期的な接続作成を実行
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        conn = await loop.run_in_executor(executor, self.db_factory_func)
                        self._connections.add(conn)
                        return conn
                else:
                    # プールが満杯の場合は待機
                    return await self._pool.get()

    async def return_connection(self, conn):
        """非同期で接続を返却"""
        if conn is not None:
            try:
                self._pool.put_nowait(conn)
            except asyncio.QueueFull:
                # プールが満杯の場合は接続を閉じる
                try:
                    conn.close()
                    self._stats['active_connections'] -= 1
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

    async def close_all(self):
        """全接続を閉じる"""
        # プールから全接続を取得して閉じる
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                self._stats['active_connections'] -= 1
            except asyncio.QueueEmpty:
                break

        # 弱参照セットからも接続をクリーンアップ
        for conn in list(self._connections):
            try:
                conn.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        self._connections.clear()
        self._stats['active_connections'] = 0

    def get_stats(self):
        """プール統計を取得"""
        hit_rate = (self._stats['pool_hits'] / self._stats['total_gets'] * 100) if self._stats['total_gets'] > 0 else 0
        return {
            **self._stats,
            'hit_rate': f"{hit_rate:.1f}%",
            'pool_size': self._pool.qsize()
        }


class AsyncDictSQLiteFastest:
    """完全aiosqlite実装の高性能非同期DictSQLite
    
    特徴:
    - ✅ 真のasyncio非同期（aiosqliteネイティブ）
    - ✅ 接続プール（再利用可能な接続）
    - ✅ 自動バッチ処理（内部バッファリング）
    - ✅ LRUキャッシュ（メモリ高速化）
    - ❌ ThreadPoolExecutor不使用（非同期ネイティブ）
    """

    def __init__(
        self,
        db_name: str,
        table_name: str = 'main',
        max_connections: int = 5,
        batch_size: int = 100,
        batch_interval: float = 1.0,
        cache_size: int = 1000,
        **kwargs
    ):
        """
        Args:
            db_name: データベースファイルパス
            table_name: テーブル名
            max_connections: 最大接続数
            batch_size: バッチ書き込みサイズ
            batch_interval: バッチコミット間隔（秒）
            cache_size: LRUキャッシュサイズ
        """
        if not AIOSQLITE_AVAILABLE:
            raise ImportError(
                "aiosqlite is required for AsyncDictSQLiteFastest. "
                "Install with: pip install aiosqlite"
            )
        
        self.db_name = db_name
        self.table_name = table_name
        self.max_connections = max_connections
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.cache_size = cache_size
        
        # 接続プール（遅延初期化）
        self._connection_pool = []  # List of aiosqlite.Connection
        self._available_connections = None  # asyncio.Queue
        self._pool_lock = None
        self._initialized = False
        
        # 書き込みバッファ
        self._write_buffer: Dict[str, bytes] = {}
        self._delete_buffer: set = set()
        self._buffer_lock = None
        
        # LRUキャッシュ（読み取り高速化）
        from collections import OrderedDict
        self._cache: OrderedDict = OrderedDict()
        self._cache_lock = None
        
        # バックグラウンドコミットタスク
        self._commit_task = None
        self._commit_stop_event = None
        
        # 統計情報
        self._stats = {
            'total_operations': 0,
            'bulk_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_writes': 0
        }
        
        # 再利用可能なThreadPoolExecutor（1つだけ作成）
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def _ensure_initialized(self):
        """非同期初期化"""
        if self._initialized:
            return
        
        # asyncio関連の初期化
        self._available_connections = asyncio.Queue(maxsize=self.max_connections)
        self._pool_lock = asyncio.Lock()
        self._buffer_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._commit_stop_event = asyncio.Event()
        
        # 接続プールの作成
        for _ in range(self.max_connections):
            conn = await aiosqlite.connect(self.db_name)
            
            # 最適化PRAGMA
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=-64000")  # 64MB
            await conn.execute("PRAGMA temp_store=MEMORY")
            await conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            await conn.execute("PRAGMA busy_timeout=60000")  # 60秒
            
            self._connection_pool.append(conn)
            await self._available_connections.put(conn)
        
        # テーブル作成（最初の接続で）
        conn = self._connection_pool[0]
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )
        """)
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_key ON {self.table_name}(key)")
        await conn.commit()
        
        # バックグラウンドコミットタスク開始
        if self.batch_interval > 0:
            self._commit_task = asyncio.create_task(self._background_commit_worker())
        
        self._initialized = True

    @asynccontextmanager
    async def _get_connection(self):
        """接続プールから接続を取得"""
        await self._ensure_initialized()
        conn = await self._available_connections.get()
        try:
            yield conn
        finally:
            await self._available_connections.put(conn)

    async def __aenter__(self):
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    async def aclose(self):
        """非同期クリーンアップ"""
        if not self._initialized:
            return
        
        # バックグラウンドタスク停止
        if self._commit_task and not self._commit_task.done():
            self._commit_stop_event.set()
            try:
                await asyncio.wait_for(self._commit_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._commit_task.cancel()
                try:
                    await self._commit_task
                except asyncio.CancelledError:
                    pass
        
        # 残りのバッファをフラッシュ
        await self._flush_write_buffer()
        
        # 接続プールをクローズ
        for conn in self._connection_pool:
            await conn.close()
        
        # ThreadPoolExecutorをシャットダウン
        self._executor.shutdown(wait=True)
        
        self._initialized = False

    # LRUキャッシュ管理
    async def _cache_get(self, key):
        """キャッシュから取得"""
        async with self._cache_lock:
            if key in self._cache:
                self._stats['cache_hits'] += 1
                # LRU: 最後に移動
                self._cache.move_to_end(key)
                return self._cache[key]
        self._stats['cache_misses'] += 1
        return None

    async def _cache_put(self, key, value):
        """キャッシュに追加"""
        async with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.cache_size:
                    self._cache.popitem(last=False)
            self._cache[key] = value

    async def _cache_remove(self, key):
        """キャッシュから削除"""
        async with self._cache_lock:
            self._cache.pop(key, None)

    # 基本非同期操作
    async def aget(self, key, default=None):
        """非同期でキーを取得"""
        await self._ensure_initialized()
        
        # キャッシュチェック
        cached = await self._cache_get(key)
        if cached is not None:
            return pickle.loads(cached)
        
        # 書き込みバッファチェック
        async with self._buffer_lock:
            if key in self._write_buffer:
                value_bytes = self._write_buffer[key]
                await self._cache_put(key, value_bytes)
                return pickle.loads(value_bytes)
            
            if key in self._delete_buffer:
                return default
        
        # DBから読み込み
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                f"SELECT value FROM {self.table_name} WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            await cursor.close()
        
        if row is None:
            return default
        
        # キャッシュに追加
        await self._cache_put(key, row[0])
        self._stats['total_operations'] += 1
        
        return pickle.loads(row[0])

    async def aset(self, key, value):
        """非同期でキーを設定（バッファリング）"""
        await self._ensure_initialized()
        
        value_bytes = pickle.dumps(value)
        
        # キャッシュに即座に反映
        await self._cache_put(key, value_bytes)
        
        # バッファに追加
        should_flush = False
        async with self._buffer_lock:
            self._write_buffer[key] = value_bytes
            self._delete_buffer.discard(key)
            should_flush = len(self._write_buffer) >= self.batch_size
        
        # バッチサイズに達したらフラッシュ
        if should_flush:
            await self._flush_write_buffer()
        
        self._stats['total_operations'] += 1

    async def adelete(self, key):
        """非同期でキーを削除"""
        await self._ensure_initialized()
        
        # キャッシュから削除
        await self._cache_remove(key)
        
        # バッファに追加
        should_flush = False
        async with self._buffer_lock:
            self._write_buffer.pop(key, None)
            self._delete_buffer.add(key)
            should_flush = len(self._delete_buffer) >= self.batch_size
        
        # バッチサイズに達したらフラッシュ
        if should_flush:
            await self._flush_write_buffer()
        
        self._stats['total_operations'] += 1

    async def acontains(self, key):
        """非同期でキー存在チェック"""
        result = await self.aget(key, default=object())
        return result is not object()

    async def ahas_key(self, key):
        """非同期でキー存在チェック（has_keyエイリアス）"""
        return await self.acontains(key)

    async def __acontains__(self, key):
        """非同期でキー存在チェック（マジックメソッド）"""
        return await self.acontains(key)

    async def akeys(self):
        """非同期でキー一覧を取得"""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(f"SELECT key FROM {self.table_name}")
            rows = await cursor.fetchall()
            await cursor.close()
        
        return [row[0] for row in rows]

    async def avalues(self):
        """非同期で値一覧を取得"""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(f"SELECT value FROM {self.table_name}")
            rows = await cursor.fetchall()
            await cursor.close()
        
        return [pickle.loads(row[0]) for row in rows]

    async def aitems(self):
        """非同期でアイテム一覧を取得"""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(f"SELECT key, value FROM {self.table_name}")
            rows = await cursor.fetchall()
            await cursor.close()
        
        return [(row[0], pickle.loads(row[1])) for row in rows]

    async def alen(self):
        """非同期でアイテム数を取得"""
        await self._ensure_initialized()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            row = await cursor.fetchone()
            await cursor.close()
        
        return row[0] if row else 0

    # 高度な非同期バルク操作
    async def abulk_insert(self, items):
        """非同期バルク挿入（最適化済み）"""
        await self._ensure_initialized()
        
        if not items:
            return
        
        # キャッシュに追加
        data = []
        for key, value in items.items():
            value_bytes = pickle.dumps(value)
            await self._cache_put(key, value_bytes)
            data.append((key, value_bytes))
        
        # 直接DBに書き込み（バッファをバイパス）
        async with self._get_connection() as conn:
            await conn.executemany(
                f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
                data
            )
            await conn.commit()
        
        self._stats['bulk_operations'] += 1
        self._stats['batch_writes'] += 1

    async def abulk_get(self, keys):
        """非同期バルク取得（最適化済み）"""
        await self._ensure_initialized()
        
        if not keys:
            return {}
        
        result = {}
        uncached_keys = []
        
        # キャッシュからチェック
        for key in keys:
            cached = await self._cache_get(key)
            if cached is not None:
                result[key] = pickle.loads(cached)
            else:
                uncached_keys.append(key)
        
        # DBから取得
        if uncached_keys:
            placeholders = ','.join('?' * len(uncached_keys))
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    f"SELECT key, value FROM {self.table_name} WHERE key IN ({placeholders})",
                    uncached_keys
                )
                rows = await cursor.fetchall()
                await cursor.close()
            
            for key, value_bytes in rows:
                result[key] = pickle.loads(value_bytes)
                await self._cache_put(key, value_bytes)
        
        self._stats['bulk_operations'] += 1
        return result

    async def abulk_delete(self, keys):
        """非同期バルク削除（最適化済み）"""
        await self._ensure_initialized()
        
        if not keys:
            return 0
        
        # キャッシュから削除
        for key in keys:
            await self._cache_remove(key)
        
        # 直接DBから削除（バッファをバイパス）
        placeholders = ','.join('?' * len(keys))
        async with self._get_connection() as conn:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE key IN ({placeholders})",
                keys
            )
            await conn.commit()
        
        self._stats['bulk_operations'] += 1
        return len(keys)

    # バッファ管理
    async def _flush_write_buffer(self):
        """書き込みバッファをフラッシュ"""
        # バッファをコピーしてクリア
        async with self._buffer_lock:
            if not self._write_buffer and not self._delete_buffer:
                return
            
            write_buffer = self._write_buffer.copy()
            delete_buffer = self._delete_buffer.copy()
            
            self._write_buffer.clear()
            self._delete_buffer.clear()
        
        # 書き込み実行
        async with self._get_connection() as conn:
            if write_buffer:
                data = list(write_buffer.items())
                await conn.executemany(
                    f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
                    data
                )
                self._stats['batch_writes'] += 1
            
            # 削除実行
            if delete_buffer:
                placeholders = ','.join('?' * len(delete_buffer))
                await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE key IN ({placeholders})",
                    tuple(delete_buffer)
                )
            
            await conn.commit()

    async def _background_commit_worker(self):
        """バックグラウンドコミットワーカー"""
        try:
            while not self._commit_stop_event.is_set():
                await asyncio.sleep(self.batch_interval)
                
                if self._commit_stop_event.is_set():
                    break
                
                await self._flush_write_buffer()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    # 統計情報とモニタリング
    def get_stats(self):
        """非同期操作統計を取得"""
        return {
            **self._stats,
            'cache_size': len(self._cache),
            'buffer_size': len(self._write_buffer),
            'pending_deletes': len(self._delete_buffer),
            'pool_size': len(self._connection_pool)
        }


# Legacy AsyncDictSQLiteFastest for backward compatibility


# Legacy AsyncDictSQLiteFastest for backward compatibility
class LegacyAsyncDictSQLiteFastest:
    """非同期版のDictSQLiteFastest with connection pooling"""

    def __init__(self, *args, max_connections: int = 5, **kwargs):
        # 引数を保存して各操作で新しい接続を使用
        self._args = args
        self._kwargs = kwargs
        # セマフォで同時接続数を制限
        self._semaphore = asyncio.Semaphore(max_connections)
        # Connection pool for efficiency
        self._connection_pool = ConnectionPool(
            lambda: DictSQLiteFastest(*self._args, **self._kwargs),
            max_connections=max_connections
        )
        # 初期化確保のため一度だけ同期DB作成
        self._ensure_initialized()

    def _ensure_initialized(self):
        """初期化を確保"""
        init_db = DictSQLiteFastest(*self._args, **self._kwargs)
        init_db.close()

    def _create_sync_db(self):
        """新しい同期DB接続を作成"""
        return DictSQLiteFastest(*self._args, **self._kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 特に何もしない（各操作で接続をクリーンアップ）
        pass

    async def aclose(self):
        """非同期でクリーンアップ"""
        self._connection_pool.close_all()

    async def _run_in_thread(self, func, *args, **kwargs):
        """スレッドプールでDB操作を実行（Connection Pool使用）"""
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                db = self._connection_pool.get_connection()
                try:
                    result = await loop.run_in_executor(executor, func, db, *args, **kwargs)
                    return result
                finally:
                    self._connection_pool.return_connection(db)

    async def __agetitem__(self, key):
        """非同期でキーを取得。"""
        def get_item(db, k):
            return db[k]
        return await self._run_in_thread(get_item, key)

    async def __asetitem__(self, key, value):
        """非同期でキーを設定。"""
        def set_item(db, k, v):
            db[k] = v
        await self._run_in_thread(set_item, key, value)

    async def __adelitem__(self, key):
        """非同期でキーを削除。"""
        def del_item(db, k):
            del db[k]
        await self._run_in_thread(del_item, key)

    async def __acontains__(self, key):
        """非同期でキー存在確認。"""
        def contains_item(db, k):
            return k in db
        return await self._run_in_thread(contains_item, key)

    async def akeys(self):
        """非同期で全キーを取得。"""
        def get_keys(db):
            return db.keys()
        return await self._run_in_thread(get_keys)

    async def ahas_key(self, key):
        """非同期でキー存在確認。"""
        return await self.__acontains__(key)

    async def aclear_table(self):
        """非同期でテーブルをクリア。"""
        def clear_table(db):
            db.clear_table()
        await self._run_in_thread(clear_table)

    async def abulk_insert(self, items):
        """非同期バルク挿入 - 大量のキー/値ペアを効率的に挿入（最適化版）"""
        def bulk_insert_optimized(db, items_data):
            # チャンク処理を使用してメモリ効率を改善
            if len(items_data) > 1000:
                db.bulk_insert_chunked(items_data)
            else:
                db.bulk_insert(items_data)
        await self._run_in_thread(bulk_insert_optimized, items)

    async def abulk_get(self, keys):
        """非同期バルク取得 - 複数のキーを効率的に取得"""
        def bulk_get(db, key_list):
            return db.bulk_get(key_list)
        return await self._run_in_thread(bulk_get, keys)

    async def abulk_delete(self, keys):
        """非同期バルク削除 - 複数のキーを効率的に削除"""
        def bulk_delete(db, key_list):
            db.bulk_delete(key_list)
        await self._run_in_thread(bulk_delete, keys)

    # 便利メソッド
    async def aget(self, key, default=None):
        """非同期でキーを取得（デフォルト値付き）。"""
        try:
            return await self.__agetitem__(key)
        except KeyError:
            return default

    async def aset(self, key, value):
        """非同期でキーを設定。"""
        await self.__asetitem__(key, value)

    async def adelete(self, key):
        """非同期でキーを削除。"""
        await self.__adelitem__(key)

