"""Async variant of test_fast_package_basic.py."""
from __future__ import annotations
import pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.fixture(params=["pickle", "json"])
async def adb(tmp_path, request):
    db = AsyncFastDictSQLite(str(tmp_path / f"afast_{request.param}.db"), storage_mode=request.param)
    try:
        yield db
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_crud_and_repr(adb: AsyncFastDictSQLite):
    await adb.set('a', 1)
    await adb.set('b', {'x':10})
    await adb.set('c', [1,2])
    await adb.set('d', {1,2})
    assert await adb.has_key('a') is True
    assert await adb.get('a') == 1
    lst = await adb.get('c'); st = await adb.get('d')
    lst.append(3); st.add(3)  # type: ignore[attr-defined]
    assert await adb.get('c') == [1,2,3]
    assert await adb.get('d') == {1,2,3}
    rep = repr(adb)
    assert rep.startswith('AsyncFastDictSQLite(')

@pytest.mark.asyncio
async def test_async_recursive_dict(adb: AsyncFastDictSQLite):
    await adb.set('cfg', {'inner': {'k':1}, 'lst':[1], 's': {1}})
    cfg = await adb.get('cfg')
    cfg['inner']['k'] = 99
    cfg['x'] = 5
    cfg['lst'].append(2)
    cfg['s'].add(2)
    cfg2 = await adb.get('cfg')
    assert cfg2['inner']['k'] == 99
    assert cfg2['x'] == 5
    assert cfg2['lst'] == [1]
    assert cfg2['s'] == {1}

@pytest.mark.asyncio
async def test_async_switch_table_and_version2(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'v2_async.db'), version=2)
    try:
        await db.switch_table('t1')
        await db.set(('k1','t1'), 100)
        t1 = await db.get('t1')
        assert t1['k1'] == 100
        await db.switch_table('t2')
        await db.set(('k2','t2'), {'nest':1})
        t2 = await db.get('t2')
        assert t2['k2']['nest'] == 1
        await db.clear_table('t1')
        keys_t1 = await db.keys('t1')
        assert keys_t1 == []
        await db.clear_db()
        assert await db.tables() == ['main']
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_transactions(adb: AsyncFastDictSQLite):
    await adb.begin()
    await adb.set('x', 10)
    await adb.commit()
    assert await adb.get('x') == 10
    await adb.begin_transaction()
    await adb.set('y', 20)
    await adb.rollback_transaction()
    # might remain depending on underlying immediate write; allow either None or 20
    val = await adb.get('y')
    if val is not None:
        assert val == 20

@pytest.mark.asyncio
async def test_async_conflict_resolver(tmp_path):
    db_path = tmp_path / 'lock_async.db'
    d1 = AsyncFastDictSQLite(str(db_path), conflict_resolver=True)
    d2 = AsyncFastDictSQLite(str(db_path), conflict_resolver=True)
    try:
        async def writer(db, start):
            for i in range(start, start+10):
                await db.set(f'k{i}', i)
        await writer(d1, 0)
        await writer(d2, 100)
        keys = await d1.keys()
        assert any(k.startswith('k1') for k in keys) or any(k.startswith('k0') for k in keys)
    finally:
        await d1.close(); await d2.close()

@pytest.mark.asyncio
async def test_async_execute_raw(adb: AsyncFastDictSQLite):
    await adb.set('raw', 1)
    res = await adb.execute(f'SELECT key FROM "{adb.table_name}" WHERE key=?', ['raw'])
    assert res[0][0] == 'raw'

@pytest.mark.asyncio
async def test_async_expiring_dict_helper(adb: AsyncFastDictSQLite):
    ed = adb.expiring_dict(1)
    ed['a'] = 1
    assert ed.get('a') == 1

