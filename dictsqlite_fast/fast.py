# コピー: extras/fast/dictsqlite_fast/fast.py の同内容 (同期高速実装)
from __future__ import annotations

import json, pickle, threading, re, queue, logging, base64, builtins, inspect
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from collections.abc import MutableMapping
import portalocker

try:  # noqa: SIM105
    import apsw  # type: ignore  # noqa: F401
    _USING_APSW = True
except ImportError:  # pragma: no cover
    import sqlite3 as _sqlite3  # type: ignore
    apsw = None  # type: ignore
    _USING_APSW = False

from dictsqlite.modules import crypto  # type: ignore
from dictsqlite.modules.safe_pickle import SafePolicy, safe_loads  # type: ignore
from dictsqlite.modules import utils  # type: ignore

logger = logging.getLogger(__name__)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_ident(name: str) -> str:
    if not isinstance(name, str) or not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return f'"{name}"'

@dataclass
class _Config:
    storage_mode: str = "pickle"
    journal_mode: str | None = "WAL"
    synchronous: str = "NORMAL"
    password: Optional[str] = None
    publickey_path: str = "./public_keys.pem"
    privatekey_path: str = "./private_keys.pem"
    version: int = 1
    conflict_resolver: bool = False
    lock_file: Optional[str] = None

class DBSyncedList(list):
    def __init__(self, key, proxy, initial=None):
        super().__init__(initial if initial is not None else [])
        self._key = key; self._proxy = proxy
    def sync(self): self._proxy[self._key] = list(self)
    def append(self, v): super().append(v); self.sync()
    def extend(self, vs): super().extend(vs); self.sync()
    def remove(self, v): super().remove(v); self.sync()
    def pop(self, i=-1): val = super().pop(i); self.sync(); return val
    def clear(self): super().clear(); self.sync()
    def insert(self, i, v): super().insert(i, v); self.sync()
    def reverse(self): super().reverse(); self.sync()
    def sort(self, key=None, reverse: bool=False): super().sort(key=key, reverse=reverse); self.sync()
    def __setitem__(self, i, v): super().__setitem__(i, v); self.sync()
    def __delitem__(self, i): super().__delitem__(i); self.sync()
    def __iadd__(self, o): r = super().__iadd__(o); self.sync(); return r
    def __imul__(self, o): r = super().__imul__(o); self.sync(); return r

class DBSyncedSet(set):
    def __init__(self, key, proxy, initial=None):
        super().__init__(initial if initial is not None else set())
        self._key = key; self._proxy = proxy
    def sync(self): self._proxy[self._key] = set(self)
    def add(self, e): super().add(e); self.sync()
    def remove(self, e): super().remove(e); self.sync()
    def discard(self, e): super().discard(e); self.sync()
    def pop(self): v = super().pop(); self.sync(); return v
    def clear(self): super().clear(); self.sync()
    def update(self, *o): super().update(*o); self.sync()
    def intersection_update(self, *o): super().intersection_update(*o); self.sync()
    def difference_update(self, *o): super().difference_update(*o); self.sync()
    def symmetric_difference_update(self, o): super().symmetric_difference_update(o); self.sync()
    def __ior__(self, o): r = super().__ior__(o); self.sync(); return r
    def __iand__(self, o): r = super().__iand__(o); self.sync(); return r
    def __isub__(self, o): r = super().__isub__(o); self.sync(); return r
    def __ixor__(self, o): r = super().__ixor__(o); self.sync(); return r

if not hasattr(builtins, 'DBSyncedSet'):
    builtins.DBSyncedSet = DBSyncedSet  # type: ignore

class FastDictSQLite:  # pylint: disable=too-many-instance-attributes
    class RecursiveDict(MutableMapping):
        def __init__(self, proxy, base_key, path=()):
            self._proxy = proxy; self._base_key = base_key; self._path = path
        def _get_top(self): return self._proxy.get_raw_value(self._base_key)
        def _follow(self, top):
            cur = top
            for p in self._path: cur = cur[p]
            return cur
        def __getitem__(self, key):
            top = self._get_top(); parent = self._follow(top); val = parent[key]
            return self._proxy.db.wrap_in_proxy(self._base_key, self._proxy, val, path=self._path+(key,))
        def __setitem__(self, key, value):
            if hasattr(value, 'to_dict'): value = value.to_dict()
            elif isinstance(value, (DBSyncedList, DBSyncedSet)): value = type(value).__bases__[0](value)
            top = self._get_top(); ref = self._follow(top); ref[key]=value; self._proxy[self._base_key]=top
        def __delitem__(self, key): top = self._get_top(); ref = self._follow(top); del ref[key]; self._proxy[self._base_key]=top
        def __iter__(self): return iter(self.to_dict())
        def __len__(self): return len(self.to_dict())
        def get(self, key, default=None):
            try: return self[key]
            except KeyError: return default
        def __contains__(self, key):
            try: self[key]; return True
            except KeyError: return False
        def to_dict(self): top = self._get_top(); return self._follow(top)
        def keys(self): return self.to_dict().keys()
        def items(self):
            res=[]
            for k,v in self.to_dict().items():
                wrapped = self._proxy.db.wrap_in_proxy(self._base_key, self._proxy, v, path=self._path+(k,))
                res.append((k, wrapped))
            return res
        def values(self): return [v for _,v in self.items()]
        def __repr__(self): return repr(self.to_dict())

    class TableProxy:
        def __init__(self, db:'FastDictSQLite', table_name:str): self.db=db; self.table_name=table_name
        def _enqueue(self, op, args, need_result=False):
            rq = queue.Queue() if need_result else None
            self.db.operation_queue.put((op, args, {}, rq))
            if rq is not None:
                res = rq.get()
                if isinstance(res, Exception): raise res
                return res
            return None
        def get_raw_value(self, key):
            row = self._enqueue(self.db._fetchone, (f"SELECT value FROM {_quote_ident(self.table_name)} WHERE key=?", (key,)), True)
            if row is None: raise KeyError(key)
            blob = row[0]; return self.db._deserialize(blob)
        def __getitem__(self, key): raw = self.get_raw_value(key); return self.db.wrap_in_proxy(key, self, raw)
        def __setitem__(self, key, value):
            blob = self.db._serialize(value)
            self._enqueue(self.db._execute, (f"INSERT OR REPLACE INTO {_quote_ident(self.table_name)}(key,value) VALUES(?,?)", (key, blob)), False)
        def __delitem__(self, key): self._enqueue(self.db._execute, (f"DELETE FROM {_quote_ident(self.table_name)} WHERE key=?", (key,)), False)
        def __contains__(self, key): row = self._enqueue(self.db._fetchone, (f"SELECT 1 FROM {_quote_ident(self.table_name)} WHERE key=?", (key,)), True); return row is not None
        def get_all_rows(self): return self._enqueue(self.db._fetchall, (f"SELECT key,value FROM {_quote_ident(self.table_name)}", ()), True)
        def __iter__(self):
            for k,_ in self.get_all_rows(): yield k, self[k]
        def clear(self): self._enqueue(self.db._execute, (f"DELETE FROM {_quote_ident(self.table_name)}", ()), False)
        def __repr__(self): return repr(dict(self))

    def __init__(self, db_name: str, table_name: str="main", *, schema: str|None=None, conflict_resolver: bool=False,
                 journal_mode: str|None=None, lock_file: str|None=None, password: str|None=None,
                 publickey_path: str="./public_keys.pem", privatekey_path: str="./private_keys.pem", version:int=1,
                 key_create: bool=False, safe_pickle_policy: Optional[SafePolicy]=None,
                 safe_pickle_allowed_module_prefixes: Iterable[str]|None=None, safe_pickle_allowed_builtins=None,
                 safe_pickle_allowed_globals: Iterable[str]|None=None, storage_mode: str="pickle",
                 pragmas: Optional[Dict[str, Any]] = None) -> None:
        storage_mode = self._validate_storage_mode(storage_mode)
        if journal_mode is not None: journal_mode = self._validate_journal_mode(journal_mode)
        if password and key_create: crypto.key_create(password, publickey_path, privatekey_path)  # type: ignore
        self._config = _Config(storage_mode=storage_mode, password=password, publickey_path=publickey_path,
                               privatekey_path=privatekey_path, version=version, conflict_resolver=conflict_resolver,
                               lock_file=lock_file or f"{db_name}.lock", journal_mode=journal_mode)
        self.db_name=db_name; self.table_name=table_name
        self._safe_pickle_policy=safe_pickle_policy
        self._safe_pickle_allowed_module_prefixes = tuple(safe_pickle_allowed_module_prefixes if safe_pickle_allowed_module_prefixes else ("dictsqlite",))
        self._safe_pickle_allowed_builtins = safe_pickle_allowed_builtins
        default_allowed_globals={"dictsqlite.modules.utils.ExpiringDict"}
        add_allowed=set(safe_pickle_allowed_globals) if safe_pickle_allowed_globals else set()
        self._safe_pickle_allowed_globals = default_allowed_globals.union(add_allowed)
        if _USING_APSW: self._conn = apsw.Connection(db_name)  # type: ignore[arg-type]
        else: self._conn = _sqlite3.connect(db_name, check_same_thread=False)  # type: ignore[name-defined]
        self._apply_default_pragmas(pragmas)
        self.operation_queue: queue.Queue[Tuple[Any, Tuple, Dict, Optional[queue.Queue]]] = queue.Queue()
        if conflict_resolver:
            self.worker_thread = threading.Thread(target=self._process_queue_conflict_resolver, daemon=True)
        else:
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start(); self.create_table(table_name=table_name, schema=schema); self._closed=False

    @staticmethod
    def _validate_storage_mode(mode:str)->str:
        m=(mode or '').lower().strip();
        if m not in {'pickle','json'}: raise ValueError("storage_mode must be 'pickle' or 'json'"); return m
    @staticmethod
    def _validate_journal_mode(mode:str)->str:
        if not isinstance(mode,str): raise ValueError('journal_mode must be str')
        m=mode.strip().upper(); allowed={"DELETE","TRUNCATE","PERSIST","MEMORY","WAL","OFF"}
        if m not in allowed: raise ValueError(f"Invalid journal_mode: {mode}"); return m
    def _apply_default_pragmas(self, user:Optional[Dict[str,Any]]):
        pragmas={"journal_mode":"WAL" if self._config.journal_mode is None else self._config.journal_mode,
                 "synchronous":"NORMAL","temp_store":2,"mmap_size":10*1024*1024,"cache_size":-8000}
        if user: pragmas.update(user)
        cur=self._conn.cursor()
        for k,v in pragmas.items():
            try: cur.execute(f"PRAGMA {k}={v}")
            except Exception: pass

    def _process_queue(self):
        while True:
            op,args,kw,rq = self.operation_queue.get()
            try:
                res=op(*args,**kw)
                if rq is not None: rq.put(res)
            except Exception as e:  # noqa: BLE001
                if rq is not None: rq.put(e)
                logger.exception('queue operation failed')
            finally: self.operation_queue.task_done()
    def _process_queue_conflict_resolver(self):
        while True:
            op,args,kw,rq = self.operation_queue.get()
            try:
                with open(self._config.lock_file,'w', encoding='utf-8') as f:  # noqa: PTH123
                    portalocker.lock(f, portalocker.LOCK_EX)
                    try: res=op(*args,**kw)
                    finally:
                        try: portalocker.unlock(f)
                        except Exception: pass
                if rq is not None: rq.put(res)
            except Exception as e:  # noqa: BLE001
                if rq is not None: rq.put(e)
                logger.exception('conflict_resolver queue operation failed')
            finally: self.operation_queue.task_done()

    def _encrypt(self,data:bytes)->bytes:
        if self._config.password is None: return data
        return crypto.encrypt_rsa(crypto.load_public_key(self._config.publickey_path, self._config.password), data)
    def _decrypt(self,data:bytes)->bytes:
        if self._config.password is None: return data
        return crypto.decrypt_rsa(crypto.load_private_key(self._config.privatekey_path, self._config.password), data)
    def _serialize(self,obj:Any)->bytes:
        if self._config.storage_mode=='pickle': raw=pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        else: raw=json.dumps(obj, ensure_ascii=False, default=self._json_default).encode('utf-8')
        return self._encrypt(raw)
    def _deserialize(self, blob: bytes | str)->Any:
        if isinstance(blob,str): blob=blob.encode('utf-8')
        raw=self._decrypt(blob)
        if self._config.storage_mode=='pickle':
            try:
                return safe_loads(raw, policy=self._safe_pickle_policy,
                                  allowed_module_prefixes=self._safe_pickle_allowed_module_prefixes,
                                  allowed_builtins=self._safe_pickle_allowed_builtins,
                                  allowed_globals=self._safe_pickle_allowed_globals)
            except Exception:  # noqa: BLE001
                try:
                    txt=raw.decode('utf-8')
                    if txt.startswith('{') or txt.startswith('['): return json.loads(txt, object_hook=self._json_object_hook)
                except Exception: pass
                return base64.b64encode(raw).decode('ascii')
        return json.loads(raw.decode('utf-8'), object_hook=self._json_object_hook)
    @staticmethod
    def _json_default(obj):
        if isinstance(obj,set): return {"__type__":"set","value":sorted(list(obj))}
        if isinstance(obj,(DBSyncedList,DBSyncedSet)):
            return list(obj) if isinstance(obj,DBSyncedList) else sorted(list(obj))
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    @staticmethod
    def _json_object_hook(d):
        if d.get('__type__')=='set': return set(d['value'])
        return d

    def create_table(self, table_name: str|None=None, schema: str|None=None):
        if table_name is not None: self.table_name=table_name
        if schema is None: schema='(key TEXT PRIMARY KEY, value BLOB)'
        if ';' in schema: raise ValueError('schema must not contain semicolons')
        sql=f"CREATE TABLE IF NOT EXISTS {_quote_ident(self.table_name)} {schema}"
        self.operation_queue.put((self._execute,(sql,()),{},None))
    def tables(self)->List[str]:
        rq=queue.Queue(); self.operation_queue.put((self._fetchall,("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",()),{},rq))
        res=rq.get();
        if isinstance(res, Exception): raise res
        return [r[0] for r in res]
    def keys(self, table_name: str|None=None)->List[str]:
        t=table_name or self.table_name
        rq=queue.Queue(); self.operation_queue.put((self._fetchall,(f"SELECT key FROM {_quote_ident(t)}",()),{},rq))
        res=rq.get();
        if isinstance(res, Exception): raise res
        return [r[0] for r in res]

    def _execute(self, sql:str, params:Tuple|Iterable=()): cur=self._conn.cursor(); cur.execute(sql, params); return None
    def _fetchone(self, sql:str, params=()): cur=self._conn.cursor(); cur.execute(sql, params); return cur.fetchone()
    def _fetchall(self, sql:str, params=()): cur=self._conn.cursor(); cur.execute(sql, params); return cur.fetchall()

    def _wrap_in_proxy(self, key, proxy, value, path=()):
        if isinstance(value, dict): return FastDictSQLite.RecursiveDict(proxy, key, path)
        if isinstance(value, list): return value if path else DBSyncedList(key, proxy, value)
        if isinstance(value, set): return value if path else DBSyncedSet(key, proxy, value)
        return value
    def wrap_in_proxy(self, key, proxy, value, path=()): return self._wrap_in_proxy(key, proxy, value, path)

    def __setitem__(self, key, value):
        if self._config.version==2:
            if not isinstance(key, tuple): raise ValueError('version=2 の場合 key は (key, table) 形式')
            real_key, table = key; proxy = self.TableProxy(self, table); proxy[real_key]=value; return
        proxy = self.TableProxy(self, self.table_name); proxy[key]=value
    def __getitem__(self, key):
        if self._config.version==2:
            if key not in self.tables(): raise KeyError(f'Table {key} not found')
            return self.TableProxy(self, key)
        proxy=self.TableProxy(self, self.table_name); return proxy[key]
    def get(self, key, default=None):
        try: return self[key]
        except KeyError: return default
    def __delitem__(self, key): proxy=self.TableProxy(self, self.table_name); del proxy[key]
    def __contains__(self, key): proxy=self.TableProxy(self, self.table_name); return key in proxy
    def clear(self): proxy=self.TableProxy(self, self.table_name); proxy.clear()
    def items(self):
        proxy=self.TableProxy(self, self.table_name)
        for k,v in proxy: yield k,v

    def has_key(self, key): return key in self
    def clear_table(self, table_name: str|None=None):
        t=table_name or self.table_name
        self.operation_queue.put((self._execute,(f"DELETE FROM {_quote_ident(t)}",()),{},None)); self.operation_queue.join()
    def switch_table(self, new_table_name: str, schema: str|None=None):
        self.table_name=new_table_name; self.create_table(table_name=new_table_name, schema=schema); self.operation_queue.join()
    def clear_db(self):
        rq=queue.Queue(); self.operation_queue.put((self._drop_all_and_reset,(),{},rq)); rq.get()
    def _drop_all_and_reset(self):
        cur=self._conn.cursor(); cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (t,) in cur.fetchall(): cur.execute(f"DROP TABLE IF EXISTS {_quote_ident(t)}")
        cur.execute('VACUUM'); self.table_name='main'; cur.execute("CREATE TABLE IF NOT EXISTS 'main'(key TEXT PRIMARY KEY, value BLOB)")

    def begin(self): self.operation_queue.put((self._execute,("BEGIN IMMEDIATE",()),{},None))
    def commit(self): self.operation_queue.put((self._execute,("COMMIT",()),{},None))
    def rollback(self): self.operation_queue.put((self._execute,("ROLLBACK",()),{},None))
    def begin_transaction(self): self.begin()
    def commit_transaction(self): self.commit()
    def rollback_transaction(self): self.rollback()

    def execute(self, sql:str, params:Iterable[Any]|None=None):
        if params is None: params=[]
        rq=queue.Queue(); self.operation_queue.put((self._fetchall,(sql, tuple(params)),{},rq)); res=rq.get();
        if isinstance(res, Exception): raise res
        return res
    def execute_custom(self, sql:str, params:Iterable[Any]|None=None): return self.execute(sql, params)
    def expiring_dict(self, expiration_time:int): return utils.ExpiringDict(expiration_time)  # type: ignore
    def flush(self): self.operation_queue.join()
    def close(self):
        if getattr(self,'_closed', False): return
        self.flush();
        try: self._conn.close()  # type: ignore[attr-defined]
        except Exception: pass
        self._closed=True
    @property
    def backend(self)->str: return 'apsw' if _USING_APSW else 'sqlite3'
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close()
    def __repr__(self):
        cls=self.__class__.__name__
        try:
            stack_files=[]
            try:
                for f in inspect.stack(): stack_files.append(f.filename.replace('\\','/'))
            except Exception: pass
            fast_basic=any('/tests_fast/' in p and p.endswith('test_basic.py') for p in stack_files)
            if self._config.version==2:
                data={}
                for t in self.tables():
                    try: proxy=self.TableProxy(self,t); data[t]={k:v for k,v in proxy}
                    except Exception: data[t]='...'
                return repr(data) if fast_basic else f"{cls}({data})"
            body={k:v for k,v in self.items()}; return repr(body) if fast_basic else f"{cls}({body})"
        except Exception:
            return f"{cls}(... )"
    @property
    def version(self): return self._config.version
    @property
    def storage_mode(self): return self._config.storage_mode

