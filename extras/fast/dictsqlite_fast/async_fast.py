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

    互換性方針:
      - DictSQLite / FastDictSQLite の主要API名称をほぼ踏襲 (has_key / clear_table / switch_table / execute など)
      - dict 風シンタックス (__getitem__) は Python の仕様上 await 対応できないため get/set を使用
      - 追加で items / values は全キー列挙 -> 個別取得 (大量データ時はコスト大: 注意書き)
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

    async def has_key(self, key) -> bool:  # noqa: D401  # 互換 alias
        return await self.contains(key)

    async def delete(self, key):  # noqa: D401
        await self._run(self._sync.__delitem__, key)

    # ---- bulk / iteration helpers ----
    async def keys(self, table_name: str | None = None):  # noqa: D401
        return await self._run(self._sync.keys, table_name)

    async def items(self, table_name: str | None = None):  # noqa: D401
        ks = await self.keys(table_name)
        out = []
        for k in ks:
            v = await self.get(k)
            out.append((k, v))
        return out

    async def values(self, table_name: str | None = None):  # noqa: D401
        return [v for _, v in await self.items(table_name)]

    async def tables(self):  # noqa: D401
        return await self._run(self._sync.tables)

    # ---- maintenance ----
    async def clear(self):  # noqa: D401  # 現在テーブル
        await self._run(self._sync.clear_table)

    async def clear_table(self, table_name: str | None = None):  # noqa: D401
        if table_name is None:
            await self.clear()
        else:
            await self._run(self._sync.clear_table, table_name)

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

    # 互換エイリアス
    async def begin_transaction(self):  # noqa: D401
        await self.begin()
    async def commit_transaction(self):  # noqa: D401
        await self.commit()
    async def rollback_transaction(self):  # noqa: D401
        await self.rollback()

    async def transaction_bulk(self, items: Iterable[tuple]):  # noqa: D401
        await self.begin()
        try:
            for k, v in items:
                await self.set(k, v)
            await self.commit()
        except Exception:  # noqa: BLE001
            await self.rollback()
            raise

    # ---- exec / helpers ----
    async def execute(self, sql: str, params: Iterable[Any] | None = None):  # noqa: D401
        return await self._run(self._sync.execute, sql, params)
    async def execute_custom(self, sql: str, params: Iterable[Any] | None = None):  # noqa: D401
        return await self.execute(sql, params)
    def expiring_dict(self, expiration_time: int):  # noqa: D401
        return self._sync.expiring_dict(expiration_time)

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

    @property
    def table_name(self):  # noqa: D401
        return self._sync.table_name
    @table_name.setter
    def table_name(self, value):  # noqa: D401
        self._sync.table_name = value

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

