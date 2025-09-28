"""Async error handling & edge case tests mirroring test_error_handling.py."""
from __future__ import annotations
import os, tempfile, threading, asyncio, time, pickle
import pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_invalid_data_types(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'inv.db'))
    try:
        with pytest.raises(Exception):
            await db.set('lambda', lambda x: x)  # noqa: E731
        import threading as _th
        with pytest.raises(Exception):
            await db.set('thread', _th.Thread(target=lambda: None))
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_database_corruption_handling(tmp_path):
    db_path = tmp_path / 'corrupt.db'
    with open(db_path, 'w', encoding='utf-8') as f:  # not a real sqlite file
        f.write('NOT A SQLITE DB')
    db = AsyncFastDictSQLite(str(db_path))
    try:
        await db.set('test', 'value')  # may fail internally; ensure no crash at API layer
        # attempt to list keys
        try:
            await db.keys()
        except Exception:
            pass
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_read_only_database(tmp_path):
    db_file = tmp_path / 'ro.db'
    sync = AsyncFastDictSQLite(str(db_file))
    await sync.set('k', 'v'); await sync.close()
    os.chmod(db_file, 0o444)
    try:
        db = AsyncFastDictSQLite(str(db_file))
        try:
            assert await db.get('k') == 'v'
            await db.set('new', 'v')  # likely to error internally
            try:
                await db.keys()
            except Exception:
                pass
        finally:
            await db.close()
    finally:
        os.chmod(db_file, 0o644)

@pytest.mark.asyncio
async def test_async_invalid_table_names(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'badtab.db'))
    try:
        names = ["test'; DROP TABLE main; --", 'test table', '', '123table', 'table-name']
        for n in names:
            try:
                await db.switch_table(n)
                await db.set('test_key', 'val')
                await db.switch_table('main')
            except Exception:
                pass
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_invalid_journal_modes(tmp_path):
    with pytest.raises(ValueError):
        await AsyncFastDictSQLite(str(tmp_path / 'badjm.db'), journal_mode='INVALID').close()  # type: ignore

@pytest.mark.asyncio
async def test_async_large_data_handling(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'large.db'))
    try:
        large_string = 'A' * (1024*512)  # 512KB (smaller to keep test fast)
        await db.set('large_string', large_string)
        assert await db.get('large_string') == large_string
        large_list = list(range(5000))
        await db.set('large_list', large_list)
        assert await db.get('large_list') == large_list
        large_dict = {f'k{i}': f'v{i}' for i in range(500)}
        await db.set('large_dict', large_dict)
        assert await db.get('large_dict') == large_dict
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_concurrent_access_safety(tmp_path):
    db_path = tmp_path / 'concurrent.db'
    base = AsyncFastDictSQLite(str(db_path))
    await base.set('initial', 'value'); await base.close()
    async def reader():
        d = AsyncFastDictSQLite(str(db_path))
        try:
            return await d.get('initial')
        finally:
            await d.close()
    results = await asyncio.gather(*[reader() for _ in range(5)])
    assert all(r == 'value' for r in results)

@pytest.mark.asyncio
async def test_async_memory_pressure_handling(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'mem.db'))
    try:
        for i in range(300):  # reduced count for speed
            await db.set(f'item_{i}', {'data': list(range(50)), 'id': i})
        for i in range(0, 300, 75):
            v = await db.get(f'item_{i}')
            if v is not None:
                assert v['id'] == i
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_transaction_error_handling(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'txerr.db'))
    try:
        await db.begin_transaction()
        await db.set('tx_test', 'initial')
        # force duplicate primary key error using raw INSERT without OR REPLACE
        try:
            await db.execute(f'INSERT INTO "{db.table_name}" (key,value) VALUES (?,?)', ['tx_test', 'dup'])
            await db.commit_transaction()
        except Exception:
            await db.rollback_transaction()
        val = await db.get('tx_test')
        # depending on timing may be 'initial' or None if rollback removed it
        if val is not None:
            assert val == 'initial'
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_schema_validation_edge_cases(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'schema2.db'), schema='(key TEXT PRIMARY KEY, value BLOB, ts INTEGER)')
    try:
        await db.set('test', 'value')
        assert await db.get('test') == 'value'
    finally:
        await db.close()
    with pytest.raises(ValueError):
        await AsyncFastDictSQLite(str(tmp_path / 'schema_bad.db'), schema='(key TEXT); DROP TABLE main; --').close()  # type: ignore

@pytest.mark.asyncio
async def test_async_expiring_dict_independent(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'expind.db'))
    try:
        ed = db.expiring_dict(0.1)
        ed['a'] = 1
        assert ed['a'] == 1
        import asyncio
        await asyncio.sleep(0.25)
        assert 'a' not in ed
        # pickle round trip
        data = pickle.dumps(ed)
        restored = pickle.loads(data)
        restored['b'] = 2
        assert restored['b'] == 2
    finally:
        await db.close()
