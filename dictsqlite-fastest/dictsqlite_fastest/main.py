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
            self._local.conn.pragma("cache_size", -64000)     # 64MB cache
            self._local.conn.pragma("temp_store", "MEMORY")   # temp tables in memory
            self._local.conn.pragma("mmap_size", 268435456)   # 256MB mmap
            
            # WALモードの場合はさらに最適化
            if self.journal_mode == "WAL":
                self._local.conn.pragma("synchronous", "NORMAL")
                self._local.conn.pragma("wal_autocheckpoint", 1000)
                    
        return self._local.conn

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
            conn = self.db._get_connection()
            cursor = conn.cursor()
            try:
                result = cursor.execute(self.db._select_stmt, (key,)).fetchone()
                if result is None:
                    raise KeyError(f"Key {key} not found in table {self.table_name}.")

                value_str = result[0]
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
            finally:
                cursor.close()

        def __getitem__(self, key):
            raw_value = self.get_raw_value(key)
            return self.db.wrap_in_proxy(key, self, raw_value)

        def __setitem__(self, key, value):
            # storage_mode に応じてシリアライズ
            if self.db.storage_mode == 'pickle':
                value_bytes = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                value_str = base64.b64encode(value_bytes).decode('ascii')
            else:  # json モード
                try:
                    value_str = json.dumps(
                        value,
                        default=self.db._extended_json_encoder_hook,
                        ensure_ascii=False,
                        separators=(',', ':')
                    )
                except TypeError as e:  # JSON化できない
                    raise TypeError(
                        f"Value for key '{key}' is not JSON serializable. "
                        "Use pickle storage_mode or provide JSON-serializable object."
                    ) from e

            if self.db.password is not None:
                value_str = self.db._encrypt(value_str)

            conn = self.db._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(self.db._insert_stmt, (key, value_str))
            finally:
                cursor.close()

        def __delitem__(self, key):
            conn = self.db._get_connection()
            cursor = conn.cursor()
            try:
                # Simply delete - don't check for existence first to match original behavior
                cursor.execute(self.db._delete_stmt, (key,))
            finally:
                cursor.close()

        def __contains__(self, key):
            conn = self.db._get_connection()
            cursor = conn.cursor()
            try:
                result = cursor.execute(self.db._exists_stmt, (key,)).fetchone()
                return result is not None
            finally:
                cursor.close()

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
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            return [row[0] for row in cursor.execute(f"SELECT key FROM {self._quote_ident(self.table_name)}")]
        finally:
            cursor.close()

    def has_key(self, key):
        """キーが存在するか確認。"""
        return key in self

    def clear_table(self):
        """テーブルを空にする。"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"DELETE FROM {self._quote_ident(self.table_name)}")
        finally:
            cursor.close()

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


class AsyncDictSQLiteFastest:
    """非同期版のDictSQLiteFastest with per-operation connections"""
    
    def __init__(self, *args, **kwargs):
        # 引数を保存して各操作で新しい接続を使用
        self._args = args
        self._kwargs = kwargs
        # セマフォで同時接続数を制限
        self._semaphore = asyncio.Semaphore(10)  # 最大10同時接続
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
        """非同期でクリーンアップ（実際にはnoop）"""
        pass
        
    async def _run_in_thread(self, func, *args, **kwargs):
        """スレッドプールでDB操作を実行"""
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                db = self._create_sync_db()
                try:
                    result = await loop.run_in_executor(executor, func, db, *args, **kwargs)
                    return result
                finally:
                    db.close()
        
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