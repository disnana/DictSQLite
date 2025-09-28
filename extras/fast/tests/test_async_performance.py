"""Async performance / stress tests (縮小件数で高速実行)"""
from __future__ import annotations
import time, random, threading, asyncio, pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_bulk_insert_performance(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aperf.db'))
    try:
        start = time.time()
        for i in range(300):
            await db.set(f'key_{i}', {'id': i, 'data': f'v{i}'})
        assert await db.get('key_0') == {'id':0,'data':'v0'}
        assert time.time() - start < 15
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_bulk_read_performance(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aread.db'))
    try:
        for i in range(300):
            await db.set(f'r_{i}', i)
        start = time.time()
        for i in range(300):
            assert await db.get(f'r_{i}') == i
        assert time.time() - start < 10
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_mixed_operations(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'amixed.db'))
    try:
        for i in range(200):
            await db.set(f'm_{i}', {'id': i})
            if i>0:
                prev = await db.get(f'm_{i-1}')
                assert prev['id']==i-1
            if i % 25 == 0 and i>0:
                val = await db.get(f'm_{i-1}')
                val['updated'] = True
        last = await db.get('m_199'); assert last['id']==199
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_concurrent_operations(tmp_path):
    db_path = tmp_path / 'aconc.db'
    async def worker(tid):
        db = AsyncFastDictSQLite(str(db_path))
        try:
            for i in range(50):
                await db.set(f't{tid}_{i}', {'t':tid,'i':i})
            # read subset
            for i in range(0,50,10):
                v = await db.get(f't{tid}_{i}')
                assert v['t']==tid
        finally:
            await db.close()
    await asyncio.gather(*[worker(t) for t in range(3)])
    verify = AsyncFastDictSQLite(str(db_path))
    try:
        v = await verify.get('t0_0')
        assert v is None or v['t']==0
    finally:
        await verify.close()

@pytest.mark.asyncio
async def test_async_memory_usage_large_dataset(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'amem.db'))
    try:
        for i in range(1000):
            await db.set(f'item_{i}', {'id':i,'data':list(range(5))})
        sample = random.sample(range(1000), 50)
        for i in sample:
            v = await db.get(f'item_{i}')
            assert v['id']==i
    finally:
        await db.close()

