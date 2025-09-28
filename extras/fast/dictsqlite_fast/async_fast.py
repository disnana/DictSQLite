"""AsyncFastDictSQLite: FastDictSQLite の asyncio ラッパー実装

パフォーマンス改善:
  - 非ブロッキング操作(set / delete / begin / commit / rollback) は直接呼び出し (以前は run_in_executor 経由で不要なオーバーヘッド)。
  - items()/values() はキーを列挙して個別 get する N+1 クエリを避け、内部 TableProxy.get_all_rows を一括取得 -> 逆シリアライズ。
  - _run -> _run_blocking に名称変更し、明示的にブロッキング操作のみ executor 利用。
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable, List, Tuple

from .fast import FastDictSQLite

__all__ = ["AsyncFastDictSQLite"]


class AsyncFastDictSQLite:
    """FastDictSQLite の単純 async ラッパー (軽量化版)。"""

    def __init__(self, *a, **kw):  # noqa: D401
        self._sync = FastDictSQLite(*a, **kw)
        self._closed = False

    # ---- 内部 util ----
    async def _run_blocking(self, fn, *args, **kwargs):  # noqa: D401
        """ブロッキング (結果待ち) 操作を executor へ委譲."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    def _ensure_open(self):  # noqa: D401
        if self._closed:
            raise RuntimeError("Database already closed")

    # ---- CRUD ----
    async def set(self, key, value):  # noqa: D401
        self._ensure_open()
        # 非ブロッキング (enqueue のみ)
        self._sync.__setitem__(key, value)
        await asyncio.sleep(0)  # 協調的に制御を返す

    async def get(self, key, default=None):  # noqa: D401
        self._ensure_open()
        try:
            return await self._run_blocking(self._sync.__getitem__, key)
        except KeyError:
            return default

    async def contains(self, key) -> bool:  # noqa: D401
        self._ensure_open(); return await self._run_blocking(lambda k: k in self._sync, key)

    async def has_key(self, key) -> bool:  # noqa: D401
        return await self.contains(key)

    async def delete(self, key):  # noqa: D401
        self._ensure_open(); self._sync.__delitem__(key); await asyncio.sleep(0)

    # ---- bulk / iteration helpers ----
    async def keys(self, table_name: str | None = None):  # noqa: D401
        self._ensure_open()
        return await self._run_blocking(self._sync.keys, table_name)

    async def items(self, table_name: str | None = None):  # noqa: D401
        self._ensure_open()
        # 高速化: 単一 SELECT で取得
        def _all() -> List[Tuple[Any, Any]]:
            tname = table_name or self._sync.table_name
            proxy = self._sync.TableProxy(self._sync, tname)
            rows = proxy.get_all_rows()  # [(key, blob), ...]
            out: List[Tuple[Any, Any]] = []
            for k, blob in rows:
                val = self._sync._deserialize(blob)  # noqa: SLF001
                wrapped = self._sync.wrap_in_proxy(k, proxy, val)
                out.append((k, wrapped))
            return out
        return await self._run_blocking(_all)

    async def values(self, table_name: str | None = None):  # noqa: D401
        return [v for _, v in await self.items(table_name)]

    async def tables(self):  # noqa: D401
        self._ensure_open(); return await self._run_blocking(self._sync.tables)

    # ---- maintenance ----
    async def clear(self):  # noqa: D401
        self._ensure_open(); await self._run_blocking(self._sync.clear_table)

    async def clear_table(self, table_name: str | None = None):  # noqa: D401
        self._ensure_open()
        if table_name is None:
            await self.clear()
        else:
            await self._run_blocking(self._sync.clear_table, table_name)

    async def switch_table(self, name: str, schema: str | None = None):  # noqa: D401
        self._ensure_open(); await self._run_blocking(self._sync.switch_table, name, schema)

    async def create_table(self, table_name: str | None = None, schema: str | None = None):  # noqa: D401
        self._ensure_open(); await self._run_blocking(self._sync.create_table, table_name, schema)

    async def clear_db(self):  # noqa: D401
        self._ensure_open(); await self._run_blocking(self._sync.clear_db)

    # ---- transactions ----
    async def begin(self):  # noqa: D401
        self._ensure_open(); self._sync.begin(); await asyncio.sleep(0)
    async def commit(self):  # noqa: D401
        self._ensure_open(); self._sync.commit(); await asyncio.sleep(0)
    async def rollback(self):  # noqa: D401
        self._ensure_open(); self._sync.rollback(); await asyncio.sleep(0)

    async def begin_transaction(self):  # noqa: D401
        await self.begin()
    async def commit_transaction(self):  # noqa: D401
        await self.commit()
    async def rollback_transaction(self):  # noqa: D401
        await self.rollback()

    async def transaction_bulk(self, items: Iterable[tuple]):  # noqa: D401
        self._ensure_open(); await self.begin()
        try:
            for k, v in items:
                await self.set(k, v)
            await self.commit()
        except Exception:  # noqa: BLE001
            await self.rollback(); raise

    # ---- exec / helpers ----
    async def execute(self, sql: str, params: Iterable[Any] | None = None):  # noqa: D401
        self._ensure_open(); return await self._run_blocking(self._sync.execute, sql, params)
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
        self._ensure_open(); await self._run_blocking(self._sync.flush)

    async def close(self):  # noqa: D401
        if self._closed:
            return
        await self.flush()
        await self._run_blocking(self._sync.close)
        self._closed = True

    # ---- context manager ----
    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        await self.close()

    # ---- representation ----
    def __repr__(self):  # noqa: D401
        return f"AsyncFastDictSQLite(sync={self._sync!r})"

