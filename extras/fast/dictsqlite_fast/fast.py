from __future__ import annotations
"""Ultra-fast APSW based implementation (rebuild)

主目的:
  * `dictsqlite` の公開API互換 (必要最小限) + 既存ベンチ/ラッパ互換パラメータ受理
  * キュー/ワーカースレッド排除 -> すべてインライン同期 I/O
  * APSW を必須 (未インストール時は ImportError) / fallback は削除
  * 準備済みSQLキャッシュ + 低オーバーヘッド直列化/復号
  * version=2 モード ( (key, table) でセット / db[table] で TableProxy 取得 ) 維持
  * storage_mode = pickle|json / 安全pickle / RSA暗号 (baseline 互換)
  * bulk_set = トランザクション + 逐次 INSERT (APSW は executemany 無いので高速ループ)
  * aggressive_pragmas / apsw_fast_mode 受理 (両方とも高速PRAGMA適用) / inline_mode 無視
  * AsyncFastDictSQLite は軽量 run_in_executor ラッパ

非目標:
  * 旧 fast 実装の queue / conflict_resolver / lock_file / background flush
  * マルチスレッド同時書き込み安全性 (利用側責務)
"""
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
import pickle, json, base64, inspect
import os

try:  # APSW 必須
    import apsw  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError("This fast implementation requires 'apsw' package") from e

from dictsqlite.modules import crypto, utils  # type: ignore
from dictsqlite.modules.safe_pickle import SafePolicy, safe_loads  # type: ignore

__all__ = ["FastDictSQLite", "AsyncFastDictSQLite", "__version__"]
__version__ = "0.2.0-fast"

_ALLOWED_JOURNAL = {"DELETE","TRUNCATE","PERSIST","MEMORY","WAL","OFF"}

@dataclass
class _Config:
    storage_mode: str = 'pickle'
    version: int = 1
    password: Optional[str] = None
    publickey_path: str = './public_keys.pem'
    privatekey_path: str = './private_keys.pem'
    journal_mode: str = 'WAL'

# ---------------- Core -----------------
class FastDictSQLite:  # noqa: D401
    def __init__(self, db_name: str, table_name: str = 'main', *,
                 schema: str | None = None,
                 storage_mode: str = 'pickle',
                 version: int = 1,
                 journal_mode: str | None = 'WAL',
                 password: str | None = None,
                 publickey_path: str = './public_keys.pem', privatekey_path: str = './private_keys.pem',
                 key_create: bool = False,
                 safe_pickle_policy: Optional[SafePolicy] = None,
                 safe_pickle_allowed_module_prefixes: Iterable[str] | None = None,
                 safe_pickle_allowed_builtins=None,
                 safe_pickle_allowed_globals: Iterable[str] | None = None,
                 # 互換用ダミー引数 (無視)
                 conflict_resolver: bool = False, lock_file: str | None = None,
                 inline_mode: str | None = None,
                 aggressive_pragmas: bool = False, apsw_fast_mode: bool = False,
                 fast_aggressive: bool | None = None,
                 **_ignored: Any):
        storage_mode = storage_mode.lower().strip()
        if storage_mode not in {'pickle','json'}:
            raise ValueError('storage_mode must be pickle or json')
        if journal_mode is not None:
            jm = journal_mode.upper()
            if jm not in _ALLOWED_JOURNAL:
                raise ValueError('invalid journal_mode')
            journal_mode = jm
        # PRAGMA モード判定 (旧引数との互換)
        self._use_aggr = aggressive_pragmas or apsw_fast_mode or (fast_aggressive if fast_aggressive is not None else False)
        self.db_name = db_name
        self.table_name = table_name
        self._config = _Config(storage_mode=storage_mode, version=version, password=password,
                               publickey_path=publickey_path, privatekey_path=privatekey_path,
                               journal_mode= journal_mode if journal_mode else 'WAL')
        # safe pickle 設定
        self._safe_policy = safe_pickle_policy
        self._safe_mod_prefixes = tuple(safe_pickle_allowed_module_prefixes) if safe_pickle_allowed_module_prefixes else ('dictsqlite',)
        self._safe_builtins = safe_pickle_allowed_builtins
        base_globals = {"dictsqlite.modules.utils.ExpiringDict"}
        add_globals = set(safe_pickle_allowed_globals) if safe_pickle_allowed_globals else set()
        self._safe_globals = base_globals.union(add_globals)
        # 鍵生成
        if password and key_create:
            crypto.key_create(password, publickey_path, privatekey_path)  # type: ignore
        self._pub = None; self._priv = None
        # 接続
        self._conn = apsw.Connection(db_name)  # type: ignore[arg-type]
        self._apply_pragmas()
        self._closed = False
        self._stmt_cache: Dict[str, Dict[str,str]] = {}
        self._proxy_cache: Dict[str, FastDictSQLite.TableProxy] = {}
        self.create_table(table_name=table_name, schema=schema)

    # -------- PRAGMA --------
    def _apply_pragmas(self):  # noqa: D401
        cur = self._conn.cursor()
        pragmas = {
            'journal_mode': self._config.journal_mode,
            'synchronous': 'OFF' if self._use_aggr else 'NORMAL',
            'temp_store': 2,
            'cache_size': -160000 if self._use_aggr else -8000,
            'wal_autocheckpoint': 0 if self._use_aggr else 1000,
            'mmap_size': 512*1024*1024 if self._use_aggr else 128*1024*1024,
            'locking_mode': 'EXCLUSIVE'
        }
        # page_size は DB 作成前に影響するが、既存 DB でも FAIL しないよう best-effort
        extra = ['PRAGMA page_size=32768', 'PRAGMA foreign_keys=ON']
        for k,v in pragmas.items():
            try: cur.execute(f'PRAGMA {k}={v}')
            except Exception: pass  # noqa: BLE001
        for stmt in extra:
            try: cur.execute(stmt)
            except Exception: pass  # noqa: BLE001

    # -------- 直列化 / 暗号 --------
    def _encrypt(self, data: bytes) -> bytes:
        if not self._config.password:
            return data
        if self._pub is None:
            self._pub = crypto.load_public_key(self._config.publickey_path, self._config.password)
        return crypto.encrypt_rsa(self._pub, data)
    def _decrypt(self, data: bytes) -> bytes:
        if not self._config.password:
            return data
        if self._priv is None:
            self._priv = crypto.load_private_key(self._config.privatekey_path, self._config.password)
        return crypto.decrypt_rsa(self._priv, data)
    def _serialize(self, obj: Any) -> bytes:
        if self._config.storage_mode == 'pickle':
            raw = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            raw = json.dumps(obj, ensure_ascii=False, default=self._json_default).encode('utf-8')
        return self._encrypt(raw)
    def _deserialize(self, blob: bytes | str) -> Any:
        if isinstance(blob, str):
            blob = blob.encode('utf-8')
        raw = self._decrypt(blob)
        if self._config.storage_mode == 'pickle':
            try:
                return safe_loads(raw, policy=self._safe_policy,
                                  allowed_module_prefixes=self._safe_mod_prefixes,
                                  allowed_builtins=self._safe_builtins,
                                  allowed_globals=self._safe_globals)
            except Exception:  # noqa: BLE001
                # フォールバック: JSON / base64
                try:
                    txt = raw.decode('utf-8')
                    if txt.startswith('{') or txt.startswith('['):
                        return json.loads(txt, object_hook=self._json_object_hook)
                except Exception:  # noqa: BLE001
                    pass
                return base64.b64encode(raw).decode('ascii')
        return json.loads(raw.decode('utf-8'), object_hook=self._json_object_hook)
    @staticmethod
    def _json_default(o):  # noqa: D401
        if isinstance(o, set):
            return {'__type__':'set','value':sorted(o)}
        if isinstance(o, list):
            return o
        if isinstance(o, dict):
            return o
        raise TypeError(f'Not JSON serializable: {type(o)}')
    @staticmethod
    def _json_object_hook(d):  # noqa: D401
        if d.get('__type__') == 'set':
            return set(d['value'])
        return d

    # -------- Table / Schema --------
    def create_table(self, table_name: str | None = None, schema: str | None = None):  # noqa: D401
        if table_name is not None:
            self.table_name = table_name
        if schema is None:
            schema = '(key TEXT PRIMARY KEY, value BLOB)'
        if ';' in schema:
            raise ValueError('schema must not contain semicolons')
        cur = self._conn.cursor()
        cur.execute(f'CREATE TABLE IF NOT EXISTS "{self.table_name}" {schema}')
        self._ensure_stmt_cache(self.table_name)

    def tables(self) -> List[str]:  # noqa: D401
        cur = self._conn.cursor()
        return [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]

    def keys(self, table_name: str | None = None) -> List[str]:  # noqa: D401
        t = table_name or self.table_name
        cur = self._conn.cursor()
        return [r[0] for r in cur.execute(f'SELECT key FROM "{t}"')]

    # -------- Statement Cache --------
    def _ensure_stmt_cache(self, table: str):  # noqa: D401
        if table in self._stmt_cache:
            return
        self._stmt_cache[table] = {
            'insert': f'INSERT OR REPLACE INTO "{table}"(key,value) VALUES(?,?)',
            'select': f'SELECT value FROM "{table}" WHERE key=?',
            'exists': f'SELECT 1 FROM "{table}" WHERE key=?',
            'delete': f'DELETE FROM "{table}" WHERE key=?',
            'scan': f'SELECT key,value FROM "{table}"',
            'delete_all': f'DELETE FROM "{table}"'
        }

    # -------- Proxy Wrapping --------
    class RecursiveDict(dict):  # noqa: D401
        def __init__(self, proxy, base_key, path=()):
            self._proxy = proxy; self._base_key = base_key; self._path = path
        def _top(self): return self._proxy.get_raw_value(self._base_key)
        def _follow(self, top):
            cur = top
            for p in self._path: cur = cur[p]
            return cur
        def __getitem__(self, k):  # noqa: D401
            top=self._top(); parent=self._follow(top); v=parent[k]
            return self._proxy.db._wrap_for_user(self._base_key, self._proxy, v, self._path+(k,))  # noqa: SLF001
        def __setitem__(self,k,v):  # noqa: D401
            if hasattr(v,'to_dict'): v=v.to_dict()
            top=self._top(); parent=self._follow(top); parent[k]=v; self._proxy[self._base_key]=top
        def __delitem__(self,k): top=self._top(); parent=self._follow(top); del parent[k]; self._proxy[self._base_key]=top
        def get(self,k,d=None):
            try: return self[k]
            except KeyError: return d
        def to_dict(self): top=self._top(); return self._follow(top)
        def items(self):
            d=self.to_dict(); out=[]
            for k,v in d.items(): out.append((k,self._proxy.db._wrap_for_user(self._base_key,self._proxy,v,self._path+(k,))))  # noqa: SLF001
            return out
        def keys(self): return self.to_dict().keys()
        def values(self): return [v for _,v in self.items()]
        def __contains__(self,k):
            try: self[k]; return True
            except KeyError: return False
        def __iter__(self): return iter(self.to_dict())
        def __len__(self): return len(self.to_dict())
        def __repr__(self): return repr(self.to_dict())

    class DBSyncedList(list):  # noqa: D401
        def __init__(self, key, proxy, initial=None): super().__init__(initial if initial is not None else []); self._key=key; self._proxy=proxy
        def _sync(self): self._proxy[self._key]=list(self)
        def append(self,v): super().append(v); self._sync()
        def extend(self,it): super().extend(it); self._sync()
        def remove(self,v): super().remove(v); self._sync()
        def pop(self,i=-1): r=super().pop(i); self._sync(); return r
        def clear(self): super().clear(); self._sync()
        def insert(self,i,v): super().insert(i,v); self._sync()
        def reverse(self): super().reverse(); self._sync()
        def sort(self,*a,**k): super().sort(*a,**k); self._sync()
        def __setitem__(self,i,v): super().__setitem__(i,v); self._sync()
        def __delitem__(self,i): super().__delitem__(i); self._sync()
        def __iadd__(self,o): r=super().__iadd__(o); self._sync(); return r
        def __imul__(self,o): r=super().__imul__(o); self._sync(); return r

    class DBSyncedSet(set):  # noqa: D401
        def __init__(self, key, proxy, initial=None): super().__init__(initial if initial is not None else set()); self._key=key; self._proxy=proxy
        def _sync(self): self._proxy[self._key]=set(self)
        def add(self,e): super().add(e); self._sync()
        def remove(self,e): super().remove(e); self._sync()
        def discard(self,e): super().discard(e); self._sync()
        def pop(self): r=super().pop(); self._sync(); return r
        def clear(self): super().clear(); self._sync()
        def update(self,*o): super().update(*o); self._sync()
        def intersection_update(self,*o): super().intersection_update(*o); self._sync()
        def difference_update(self,*o): super().difference_update(*o); self._sync()
        def symmetric_difference_update(self,o): super().symmetric_difference_update(o); self._sync()
        def __ior__(self,o): r=super().__ior__(o); self._sync(); return r
        def __iand__(self,o): r=super().__iand__(o); self._sync(); return r
        def __isub__(self,o): r=super().__isub__(o); self._sync(); return r
        def __ixor__(self,o): r=super().__ixor__(o); self._sync(); return r

    class TableProxy:  # noqa: D401
        def __init__(self, db: 'FastDictSQLite', table: str): self.db=db; self.table=table
        def _sql(self, name: str): return self.db._stmt_cache[self.table][name]  # noqa: SLF001
        def get_raw_value(self, key):  # noqa: D401
            cur=self.db._conn.cursor(); row=cur.execute(self._sql('select'), (key,)).fetchone()
            if row is None: raise KeyError(key)
            return self.db._deserialize(row[0])  # noqa: SLF001
        def __getitem__(self,k): return self.db._wrap_for_user(k,self,self.get_raw_value(k))
        def __setitem__(self,k,v):
            blob=self.db._serialize(v); cur=self.db._conn.cursor(); cur.execute(self._sql('insert'), (k,blob))  # noqa: SLF001
        def __delitem__(self,k): cur=self.db._conn.cursor(); cur.execute(self._sql('delete'), (k,))  # noqa: SLF001
        def __contains__(self,k): cur=self.db._conn.cursor(); r=cur.execute(self._sql('exists'), (k,)).fetchone(); return r is not None  # noqa: SLF001
        def clear(self): cur=self.db._conn.cursor(); cur.execute(self._sql('delete_all'))  # noqa: SLF001
        def __iter__(self):
            cur=self.db._conn.cursor()
            for k,v in cur.execute(self._sql('scan')):  # noqa: SLF001
                yield k, self.db._wrap_for_user(k,self,self.db._deserialize(v))  # noqa: SLF001
        def items(self): return list(iter(self))
        def __repr__(self):  # noqa: D401
            try: return f'TableProxy({self.table}, size={len(list(self))})'
            except Exception: return f'TableProxy({self.table})'  # noqa: BLE001

    # -------- User wrap --------
    def _wrap_for_user(self, key, proxy, value, path=()):  # noqa: D401
        if isinstance(value, dict): return self.RecursiveDict(proxy, key, path)
        if isinstance(value, list): return value if path else self.DBSyncedList(key, proxy, value)
        if isinstance(value, set): return value if path else self.DBSyncedSet(key, proxy, value)
        return value
    # 追加: baseline 互換の公開メソッド
    def wrap_in_proxy(self, key, proxy, value, path=()):  # noqa: D401
        return self._wrap_for_user(key, proxy, value, path)
    def _get_proxy(self, table: str):
        p = self._proxy_cache.get(table)
        if p is None:
            self._ensure_stmt_cache(table)
            p = self.TableProxy(self, table)
            self._proxy_cache[table] = p
        return p

    # -------- Dict-like 基本 --------
    def __setitem__(self, key, value):  # noqa: D401
        if self._config.version == 2:
            if not isinstance(key, tuple) or len(key)!=2:
                raise ValueError('version=2 keys must be (key, table)')
            k, table = key
            self.create_table(table)
            self._get_proxy(table)[k] = value
            return
        self._get_proxy(self.table_name)[key] = value
    def __getitem__(self, key):  # noqa: D401
        if self._config.version == 2:
            # table アクセス: db['table'] -> TableProxy
            if key in self.tables():
                return self._get_proxy(key)
            raise KeyError(key)
        return self._get_proxy(self.table_name)[key]
    def get(self, key, default=None):  # noqa: D401
        try: return self[key]
        except KeyError: return default
    def __delitem__(self, key):  # noqa: D401
        self._get_proxy(self.table_name).__delitem__(key)
    def __contains__(self, key):  # noqa: D401
        return key in self._get_proxy(self.table_name)
    def items(self):  # noqa: D401
        return list(self._get_proxy(self.table_name))
    def has_key(self, key): return key in self  # noqa: D401

    # -------- Bulk / Maintenance --------
    def bulk_set(self, items: Iterable[Tuple[str, Any]], table_name: str | None = None, use_transaction: bool = True):  # noqa: D401
        t = table_name or self.table_name
        self.create_table(t)
        sql = self._stmt_cache[t]['insert']
        cur = self._conn.cursor()
        if use_transaction:
            self.begin()
        count = 0
        for k, v in items:
            blob = self._serialize(v)
            cur.execute(sql, (k, blob))
            count += 1
        if use_transaction:
            self.commit()
        return count
    def clear_table(self, table_name: str | None = None):  # noqa: D401
        t = table_name or self.table_name
        self._get_proxy(t).clear()
    def switch_table(self, new_table_name: str, schema: str | None = None):  # noqa: D401
        self.create_table(new_table_name, schema=schema)
        self.table_name = new_table_name
    def clear_db(self):  # noqa: D401
        cur = self._conn.cursor()
        for (n,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            cur.execute(f'DROP TABLE IF EXISTS "{n}"')
        cur.execute('VACUUM')
        self._proxy_cache.clear(); self._stmt_cache.clear()
        self.create_table('main')

    # -------- Transactions --------
    def begin(self): self._conn.cursor().execute('BEGIN IMMEDIATE')  # noqa: D401
    def commit(self): self._conn.cursor().execute('COMMIT')  # noqa: D401
    def rollback(self): self._conn.cursor().execute('ROLLBACK')  # noqa: D401
    begin_transaction = begin
    commit_transaction = commit
    rollback_transaction = rollback

    # -------- Execute --------
    def execute(self, sql: str, params: Sequence[Any] | None = None):  # noqa: D401
        cur = self._conn.cursor(); return list(cur.execute(sql, tuple(params) if params else ()))
    def execute_custom(self, sql: str, params: Sequence[Any] | None = None):  # noqa: D401
        return self.execute(sql, params)

    # -------- Misc --------
    def expiring_dict(self, expiration_time: int): return utils.ExpiringDict(expiration_time)  # noqa: D401
    def flush(self): pass  # noqa: D401 (無キュー)
    def close(self):  # noqa: D401
        if self._closed: return
        try: self._conn.close()
        except Exception: pass  # noqa: BLE001
        self._closed = True
    @property
    def backend(self) -> str: return 'apsw'  # noqa: D401
    @property
    def version(self): return self._config.version  # noqa: D401
    @property
    def storage_mode(self): return self._config.storage_mode  # noqa: D401

    # -------- Representation --------
    def __repr__(self):  # noqa: D401
        cls = self.__class__.__name__
        try:
            callers = []
            for f in inspect.stack():  # pragma: no cover (best effort)
                p = f.filename.replace('\\','/')
                if 'site-packages' not in p and 'importlib' not in p:
                    callers.append(os.path.basename(p))
            return f"{cls}(db='{self.db_name}', table='{self.table_name}', storage='{self.storage_mode}', aggr={self._use_aggr}, callers={callers[:3]})"
        except Exception:  # noqa: BLE001
            return f"{cls}(db='{self.db_name}', table='{self.table_name}')"

# ---------------- Async Wrapper -----------------
import asyncio
class AsyncFastDictSQLite:  # noqa: D401
    def __init__(self, *a, **kw):
        self._sync = FastDictSQLite(*a, **kw)
        self._closed = False
    def _ensure(self):
        if self._closed:
            raise RuntimeError('Database closed')
    async def _to_thread(self, fn, *args, **kwargs):  # noqa: D401
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
    # CRUD
    async def set(self, key, value): self._ensure(); await self._to_thread(self._sync.__setitem__, key, value)
    async def get(self, key, default=None):  # noqa: D401
        self._ensure()
        try: return await self._to_thread(self._sync.__getitem__, key)
        except KeyError: return default
    async def delete(self, key): self._ensure(); await self._to_thread(self._sync.__delitem__, key)
    async def has_key(self, key): self._ensure(); return await self._to_thread(lambda k: k in self._sync, key)
    async def contains(self, key): return await self.has_key(key)
    # Bulk / iteration
    async def bulk_set(self, items: Iterable[Tuple[str, Any]], *, use_transaction: bool = True): self._ensure(); return await self._to_thread(self._sync.bulk_set, items, None, use_transaction)
    async def keys(self, table_name: str | None = None): self._ensure(); return await self._to_thread(self._sync.keys, table_name)
    async def items(self, table_name: str | None = None):  # noqa: D401
        self._ensure(); return await self._to_thread(lambda t: self._sync._get_proxy(t).items(), table_name or self._sync.table_name)  # noqa: SLF001
    async def values(self, table_name: str | None = None): return [v for _,v in await self.items(table_name)]
    async def tables(self): self._ensure(); return await self._to_thread(self._sync.tables)
    # Maintenance
    async def clear_table(self, table_name: str | None = None): self._ensure(); await self._to_thread(self._sync.clear_table, table_name)
    async def clear(self): await self.clear_table()
    async def switch_table(self, name: str, schema: str | None = None): self._ensure(); await self._to_thread(self._sync.switch_table, name, schema)
    async def create_table(self, table_name: str | None = None, schema: str | None = None): self._ensure(); await self._to_thread(self._sync.create_table, table_name, schema)
    async def clear_db(self): self._ensure(); await self._to_thread(self._sync.clear_db)
    # Transactions
    async def begin(self): self._ensure(); await self._to_thread(self._sync.begin)
    async def commit(self): self._ensure(); await self._to_thread(self._sync.commit)
    async def rollback(self): self._ensure(); await self._to_thread(self._sync.rollback)
    async def begin_transaction(self): await self.begin()
    async def commit_transaction(self): await self.commit()
    async def rollback_transaction(self): await self.rollback()
    # Exec
    async def execute(self, sql: str, params: Sequence[Any] | None = None): self._ensure(); return await self._to_thread(self._sync.execute, sql, params)
    async def execute_custom(self, sql: str, params: Sequence[Any] | None = None): return await self.execute(sql, params)
    # Misc
    def expiring_dict(self, expiration_time: int): return self._sync.expiring_dict(expiration_time)
    async def flush(self): pass  # noqa: D401
    async def close(self):
        if self._closed: return
        await self._to_thread(self._sync.close)
        self._closed = True
    @property
    def backend(self): return self._sync.backend  # noqa: D401
    @property
    def version(self): return self._sync.version  # noqa: D401
    @property
    def storage_mode(self): return self._sync.storage_mode  # noqa: D401
    @property
    def table_name(self): return self._sync.table_name
    @table_name.setter
    def table_name(self, v): self._sync.table_name = v
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): await self.close()
    def __repr__(self): return f"AsyncFastDictSQLite(sync={self._sync!r})"  # noqa: D401
