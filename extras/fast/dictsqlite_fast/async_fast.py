"""AsyncFastDictSQLite: FastDictSQLite の asyncio ラッパー実装

目的:
  - 既存 FastDictSQLite (同期) を内部に保持し、async API(set/get/contains/clear/transaction_bulk/close/switch_table) を提供
  - benchmark.py / 今後の利用コードが期待するメソッドシグネチャを満たす
  - KeyError を get では None にマッピング (benchmark の baseline wrapper と整合)
  - 任意の同時呼び出しは run_in_executor() でスレッドプールへ委譲 (内部 FastDictSQLite 自体はキューで直列化)
  - async context manager (__aenter__/__aexit__) 対応

注意:
  - 高スループット用途では run_in_executor オーバーヘッドがある。apsw の asyncio サポート導入時に最適化余地あり。
  - set/get 以外の将来拡張 (scan, prefix search など) は容易に追加可能。
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable

from .fast import FastDictSQLite

__all__ = ["AsyncFastDictSQLite"]


class AsyncFastDictSQLite:
    """FastDictSQLite の単純 async ラッパー。

    推奨利用パターン:
        async with AsyncFastDictSQLite('file.db') as db:
            await db.set('k', 1)
            v = await db.get('k')

    Methods provided:
      - set(key, value)
      - get(key) -> value | None
      - contains(key) -> bool
      - clear()
      - switch_table(name, schema=None)
      - transaction_bulk(iterable_of_pairs)
      - begin / commit / rollback (仮想, FastDictSQLite の queue 経由)
      - tables() / keys()
      - close()
    """

    def __init__(self, *a, **kw):  # noqa: D401
        self._sync = FastDictSQLite(*a, **kw)
        self._closed = False

    # ---- 内部 util ----
    async def _run(self, fn, *args, **kwargs):  # noqa: D401
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    # ---- CRUD ----
    async def set(self, key, value):  # noqa: D401
        await self._run(self._sync.__setitem__, key, value)

    async def get(self, key, default=None):  # noqa: D401
        try:
            return await self._run(self._sync.__getitem__, key)
        except KeyError:
            return default

    async def contains(self, key) -> bool:  # noqa: D401
        return await self._run(lambda k: k in self._sync, key)

    async def delete(self, key):  # noqa: D401
        await self._run(self._sync.__delitem__, key)

    # ---- bulk / iteration helpers ----
    async def keys(self, table_name: str | None = None):  # noqa: D401
        return await self._run(self._sync.keys, table_name)

    async def tables(self):  # noqa: D401
        return await self._run(self._sync.tables)

    # ---- maintenance ----
    async def clear(self):  # noqa: D401
        await self._run(self._sync.clear_table)

    async def switch_table(self, name: str, schema: str | None = None):  # noqa: D401
        await self._run(self._sync.switch_table, name, schema)

    async def clear_db(self):  # noqa: D401
        await self._run(self._sync.clear_db)

    # ---- transactions ----
    async def begin(self):  # noqa: D401
        await self._run(self._sync.begin)
    async def commit(self):  # noqa: D401
        await self._run(self._sync.commit)
    async def rollback(self):  # noqa: D401
        await self._run(self._sync.rollback)

    async def transaction_bulk(self, items: Iterable[tuple]):  # noqa: D401
        await self.begin()
        try:
            for k, v in items:
                await self.set(k, v)
            await self.commit()
        except Exception:  # noqa: BLE001
            await self.rollback()
            raise

    # ---- misc ----
    @property
    def backend(self) -> str:  # noqa: D401
        return self._sync.backend

    @property
    def version(self):  # noqa: D401
        return self._sync.version

    @property
    def storage_mode(self):  # noqa: D401
        return self._sync.storage_mode

    async def flush(self):  # noqa: D401
        await self._run(self._sync.flush)

    async def close(self):  # noqa: D401
        if self._closed:
            return
        await self.flush()
        await self._run(self._sync.close)
        self._closed = True

    # ---- context manager ----
    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        await self.close()

    # ---- representation ----
    def __repr__(self):  # noqa: D401
        return f"AsyncFastDictSQLite(sync={self._sync!r})"

