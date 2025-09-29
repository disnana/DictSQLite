"""DictSQLite-Fastest: High-performance SQLite dictionary using APSW."""

import base64
import collections.abc
import json
import pickle
import random
import secrets
import string
import threading
import logging
import asyncio
import queue
import zlib  # 圧縮サポートのため追加
from typing import Optional, Any
from concurrent.futures import ThreadPoolExecutor

import apsw
import portalocker

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
        
        # ロックファイル設定
        if lock_file is None:
            self.lock_file = f"{db_name}.lock"
        else:
            self.lock_file = lock_file

        # データベースの初期化を一度だけ実行
        self._initialize_database(schema)
        
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

    def _initialize_database(self, schema=None):
        """データベースの初期化を一度だけ実行（グローバル同期）"""
        global _db_init_locks, _db_init_states, _db_init_lock
        
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
                finally:
                    cursor.close()
                
                # 初期化完了フラグを設定
                init_conn.close()
                _db_init_states[init_key] = True

    def _get_connection(self):
        """スレッドローカルなAPSW接続を取得"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # 新しい接続を作成
            self._local.conn = apsw.Connection(self.db_name)
            
            # busy_timeoutを設定（ロック解決のため）
            self._local.conn.pragma("busy_timeout", 30000)  # 30 second timeout
            
            # APSWのパフォーマンス最適化設定（journal_modeは初期化時に設定済み）
            self._local.conn.pragma("synchronous", "NORMAL")  # FULL -> NORMALで高速化
            self._local.conn.pragma("cache_size", self.cache_size)
            self._local.conn.pragma("temp_store", "MEMORY")   # temp tables in memory
            self._local.conn.pragma("mmap_size", self.mmap_size)
            
            # さらなる最適化設定
            self._local.conn.pragma("locking_mode", "NORMAL")  # 同期処理モード
            self._local.conn.pragma("query_only", 0)  # 読み書き両方許可
            
            # メモリ最適化設定
            if self.enable_memory_optimization:
                self._local.conn.pragma("page_size", 65536)  # より大きなページサイズ
                self._local.conn.pragma("auto_vacuum", "INCREMENTAL")  # 自動バキューム
                self._local.conn.pragma("freelist_count", 0)  # フリーリストの最適化
            
            # カスタムPRAGMA設定の適用
            for pragma_name, pragma_value in self.custom_pragma_settings.items():
                self._local.conn.pragma(pragma_name, pragma_value)
            
            # WALモードの場合はさらに最適化
            if self.journal_mode == "WAL":
                self._local.conn.pragma("synchronous", "NORMAL")
                self._local.conn.pragma("wal_autocheckpoint", self.wal_autocheckpoint)
            
            # Prepared statement cache for this connection
            self._local.stmt_cache = {}
            # Cursor cache for reuse
            self._local.cursor_cache = None
                    
        return self._local.conn

    def _get_cursor(self):
        """再利用可能なカーソルを取得"""
        conn = self._get_connection()
        if not hasattr(self._local, 'cursor_cache') or self._local.cursor_cache is None:
            self._local.cursor_cache = conn.cursor()
        return self._local.cursor_cache

    def _execute_with_cursor(self, query, params=None):
        """カーソルを使用してクエリを実行し、結果を返す"""
        cursor = self._get_cursor()
        if params:
            return cursor.execute(query, params)
        else:
            return cursor.execute(query)

    def _get_prepared_statement(self, stmt_type):
        """プリペアドステートメントをキャッシュから取得"""
        if not hasattr(self._local, 'stmt_cache'):
            self._local.stmt_cache = {}
        
        if stmt_type not in self._local.stmt_cache:
            if stmt_type == 'insert':
                self._local.stmt_cache[stmt_type] = self._insert_stmt
            elif stmt_type == 'select':
                self._local.stmt_cache[stmt_type] = self._select_stmt
            elif stmt_type == 'delete':
                self._local.stmt_cache[stmt_type] = self._delete_stmt
            elif stmt_type == 'exists':
                self._local.stmt_cache[stmt_type] = self._exists_stmt
            elif stmt_type == 'select_all':
                self._local.stmt_cache[stmt_type] = self._select_all_stmt
        
        return self._local.stmt_cache[stmt_type]

    def _ensure_table_exists(self, schema=None):
        """テーブルが存在することを確認 (初期化時に既に作成済み)"""
        # テーブルは _initialize_database で既に作成済み
        pass

    def _prepare_statements(self):
        """パフォーマンス向上のためのprepared statements"""
        # よく使用されるクエリのprepared statementを作成
        self._insert_stmt = f"INSERT OR REPLACE INTO {self._quote_ident(self.table_name)} (key, value) VALUES (?, ?)"
        self._select_stmt = f"SELECT value FROM {self._quote_ident(self.table_name)} WHERE key = ?"
        self._delete_stmt = f"DELETE FROM {self._quote_ident(self.table_name)} WHERE key = ?"
        self._exists_stmt = f"SELECT 1 FROM {self._quote_ident(self.table_name)} WHERE key = ?"
        self._select_all_stmt = f"SELECT key, value FROM {self._quote_ident(self.table_name)}"

    def _compress_value(self, value_str: str) -> str:
        """大きな値を圧縮する"""
        if not self.enable_compression or len(value_str.encode('utf-8')) < self.compression_threshold:
            return value_str
        
        # 圧縮
        compressed = zlib.compress(value_str.encode('utf-8'), level=6)  # バランスの取れた圧縮レベル
        # 圧縮されたデータをbase64エンコード + プレフィックス
        compressed_str = "ZLIB:" + base64.b64encode(compressed).decode('ascii')
        
        # 圧縮率が十分でない場合は元の値を返す
        if len(compressed_str) >= len(value_str):
            return value_str
        
        return compressed_str
    
    def _decompress_value(self, value_str: str) -> str:
        """圧縮された値を展開する"""
        if not value_str.startswith("ZLIB:"):
            return value_str
        
        # プレフィックスを除去してbase64デコード
        compressed_data = base64.b64decode(value_str[5:])
        # 展開
        return zlib.decompress(compressed_data).decode('utf-8')

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
            result = self.db._execute_with_cursor(stmt, (key,)).fetchone()
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
            result = self.db._execute_with_cursor(stmt, (key,)).fetchone()
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
        """DB接続を閉じる。"""
        if hasattr(self._local, 'cursor_cache') and self._local.cursor_cache:
            self._local.cursor_cache.close()
            self._local.cursor_cache = None
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

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

    def keys(self):
        """全キーを返す。"""
        # 再利用可能なカーソルを使用
        result = self._execute_with_cursor(f"SELECT key FROM {self._quote_ident(self.table_name)}")
        return [row[0] for row in result]

    def keys_iter(self):
        """メモリ効率的なキーのイテレータ"""
        # 大量のデータに対してメモリ効率的
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for row in cursor.execute(f"SELECT key FROM {self._quote_ident(self.table_name)}"):
                yield row[0]
        finally:
            cursor.close()

    def items_iter(self, batch_size=1000):
        """メモリ効率的なアイテムのイテレータ（バッチ処理）"""
        # バッチ処理で大量のデータを扱う
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            offset = 0
            while True:
                query = f"SELECT key, value FROM {self._quote_ident(self.table_name)} LIMIT {batch_size} OFFSET {offset}"
                rows = list(cursor.execute(query))
                if not rows:
                    break
                
                for key, value_str in rows:
                    if self.storage_mode == 'pickle':
                        value = pickle.loads(base64.b64decode(value_str.encode('ascii')))
                    else:  # json
                        value = json.loads(value_str, object_hook=self._extended_json_decoder_hook)
                    yield key, value
                
                offset += batch_size
        finally:
            cursor.close()

    def has_key(self, key):
        """キーが存在するか確認。"""
        return key in self

    def clear_table(self):
        """テーブルを空にする。"""
        # 再利用可能なカーソルを使用
        self._execute_with_cursor(f"DELETE FROM {self._quote_ident(self.table_name)}")

    def bulk_insert(self, items):
        """バルク挿入 - 大量のキー/値ペアを効率的に挿入（トランザクション最適化）"""
        if not items:
            return
        
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
            if item_count < 100:
                # 少量データは通常の個別挿入で十分
                for key, value in (items.items() if hasattr(items, 'items') else items):
                    self[key] = value
            elif item_count < 1000:
                # 中量データはexecutemanyが高速
                self.bulk_insert_executemany(items)
            else:
                # 大量データはチャンク処理で安全に
                self.bulk_insert_chunked(items, chunk_size=min(1000, item_count // 10))
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
                    # チャンクを挿入
                    for k, v in chunk:
                        cursor.execute(self._insert_stmt, (k, v))
                    chunk = []
            
            # 残りのチャンクを処理
            if chunk:
                for k, v in chunk:
                    cursor.execute(self._insert_stmt, (k, v))
            
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
        
        # 再利用可能なカーソルを使用
        # IN句を使用した効率的な一括検索
        placeholders = ','.join('?' * len(keys))
        query = f"SELECT key, value FROM {self._quote_ident(self.table_name)} WHERE key IN ({placeholders})"
        
        results = {}
        for key, value_str in self._execute_with_cursor(query, list(keys)):
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
            
            # IN句を使用した効率的な一括削除
            placeholders = ','.join('?' * len(keys))
            query = f"DELETE FROM {self._quote_ident(self.table_name)} WHERE key IN ({placeholders})"
            cursor.execute(query, list(keys))
            
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


class AsyncDictSQLiteFastest:
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