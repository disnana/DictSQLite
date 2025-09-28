"""Async tests: transactions & table management for AsyncFastDictSQLite.

同期版 test_transactions_and_tables.py に対応。
"""
from __future__ import annotations
import pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_transactions_commit_and_rollback(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'tx.db'))
    try:
        await db.begin_transaction()
        await db.set('k1', 'v1')
        await db.set('k2', 'v2')
        await db.commit_transaction()
        assert await db.get('k1') == 'v1'
        assert await db.get('k2') == 'v2'

        await db.begin_transaction()
        await db.set('k3', 'v3')
        await db.rollback_transaction()
        assert await db.get('k3') is None
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_switch_table_and_clear(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'tables.db'))
    try:
        await db.set('main_k', 1)
        await db.switch_table('t1')
        await db.set('t1_k', 2)
        await db.switch_table('main')
        assert await db.get('main_k') == 1
        await db.switch_table('t1')
        assert await db.get('t1_k') == 2
        await db.clear_table('t1')
        assert await db.keys('t1') == []
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_version2_multi_tables(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'v2.db'), version=2)
    try:
        # 明示テーブル作成
        await db.create_table(table_name='alpha')
        await db.create_table(table_name='beta')
        # (key, table)
        await db.set(('k1','alpha'), 100)
        await db.set(('k2','beta'), 200)
        alpha = await db.get('alpha')  # TableProxy ではなく version2 では TableProxy が返る -> sync proxy
        beta = await db.get('beta')
        assert alpha['k1'] == 100
        assert beta['k2'] == 200
        assert 'alpha' in (await db.tables()) and 'beta' in (await db.tables())
    finally:
        await db.close()

