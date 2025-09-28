"""AsyncFastDictSQLite 基本動作テスト。

高速 async ラッパの最小機能 (set/get/contains/clear/transaction/table) を検証する。
大規模性能は benchmark.py で別途計測。
"""
from __future__ import annotations

import pytest
import asyncio

from dictsqlite_fast import AsyncFastDictSQLite


@pytest.mark.asyncio
async def test_async_basic_crud(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'a.db'))
    try:
        await db.set('k1', 123)
        await db.set('k2', {'x': 1})
        assert await db.get('k1') == 123
        v = await db.get('k2')
        assert isinstance(v, dict) or hasattr(v, 'to_dict')
        assert (await db.get('missing')) is None
        assert await db.contains('k1') is True
        await db.delete('k1')
        assert await db.get('k1') is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_async_switch_and_clear(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'b.db'))
    try:
        await db.set('a', 1)
        await db.switch_table('t1')
        await db.set('b', 2)
        # main テーブルへ戻る
        await db.switch_table('main')
        assert await db.get('a') == 1
        # clear 現在テーブル(main)のみ
        await db.clear()
        assert await db.get('a') is None
        # t1 は残る
        await db.switch_table('t1')
        assert await db.get('b') == 2
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_async_transaction_bulk(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'c.db'))
    try:
        await db.transaction_bulk([(f'k{i}', i) for i in range(50)])
        # spot check
        assert await db.get('k0') == 0
        assert await db.get('k49') == 49
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_async_extended_api(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'ext.db'))
    try:
        await db.set('x', 1)
        assert await db.has_key('x') is True
        assert await db.contains('x') is True
        ks = await db.keys(); assert 'x' in ks
        its = await db.items(); assert ('x', 1) in its
        vals = await db.values(); assert 1 in vals
        # execute 経由で直接SQL
        res = await db.execute(f'SELECT key FROM "{db.table_name}" WHERE key=?', ['x'])
        assert res[0][0] == 'x'
        # transaction エイリアス
        await db.begin_transaction(); await db.set('y', 2); await db.commit_transaction()
        assert await db.get('y') == 2
        # clear_table 指定
        await db.clear_table(db.table_name)
        assert await db.get('x') is None and await db.get('y') is None
    finally:
        await db.close()
