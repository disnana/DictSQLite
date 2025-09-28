"""AsyncFastDictSQLite root package copy.

Mirrors extras/fast/dictsqlite_fast/async_fast.py so that installing DictSQLite with
extras `[fast]` exposes async API directly from `dictsqlite_fast`.
"""
from __future__ import annotations
import asyncio
from typing import Any, Iterable
from .fast import FastDictSQLite

__all__ = ["AsyncFastDictSQLite"]

class AsyncFastDictSQLite:
    def __init__(self, *a, **kw):  # noqa: D401
        self._sync = FastDictSQLite(*a, **kw)
        self._closed = False
    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
    async def set(self, key, value): await self._run(self._sync.__setitem__, key, value)
    async def get(self, key, default=None):
        try: return await self._run(self._sync.__getitem__, key)
        except KeyError: return default
    async def contains(self, key) -> bool: return await self._run(lambda k: k in self._sync, key)
    async def has_key(self, key) -> bool: return await self.contains(key)
    async def delete(self, key): await self._run(self._sync.__delitem__, key)
    async def keys(self, table_name: str | None = None): return await self._run(self._sync.keys, table_name)
    async def items(self, table_name: str | None = None):
        ks = await self.keys(table_name); out=[]
        for k in ks: out.append((k, await self.get(k)))
        return out
    async def values(self, table_name: str | None = None): return [v for _,v in await self.items(table_name)]
    async def tables(self): return await self._run(self._sync.tables)
    async def clear(self): await self._run(self._sync.clear_table)
    async def clear_table(self, table_name: str | None = None):
        if table_name is None: await self.clear()
        else: await self._run(self._sync.clear_table, table_name)
    async def switch_table(self, name: str, schema: str | None = None): await self._run(self._sync.switch_table, name, schema)
    async def create_table(self, table_name: str | None = None, schema: str | None = None): await self._run(self._sync.create_table, table_name, schema)
    async def clear_db(self): await self._run(self._sync.clear_db)
    async def begin(self): await self._run(self._sync.begin)
    async def commit(self): await self._run(self._sync.commit)
    async def rollback(self): await self._run(self._sync.rollback)
    async def begin_transaction(self): await self.begin()
    async def commit_transaction(self): await self.commit()
    async def rollback_transaction(self): await self.rollback()
    async def transaction_bulk(self, items: Iterable[tuple]):
        await self.begin();
        try:
            for k,v in items: await self.set(k,v)
            await self.commit()
        except Exception:  # noqa: BLE001
            await self.rollback(); raise
    async def execute(self, sql: str, params: Iterable[Any] | None = None): return await self._run(self._sync.execute, sql, params)
    async def execute_custom(self, sql: str, params: Iterable[Any] | None = None): return await self.execute(sql, params)
    def expiring_dict(self, expiration_time: int): return self._sync.expiring_dict(expiration_time)
    @property
    def backend(self) -> str: return self._sync.backend
    @property
    def version(self): return self._sync.version
    @property
    def storage_mode(self): return self._sync.storage_mode
    @property
    def table_name(self): return self._sync.table_name
    @table_name.setter
    def table_name(self, v): self._sync.table_name = v
    async def flush(self): await self._run(self._sync.flush)
    async def close(self):
        if self._closed: return
        await self.flush(); await self._run(self._sync.close); self._closed=True
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): await self.close()
    def __repr__(self): return f"AsyncFastDictSQLite(sync={self._sync!r})"

