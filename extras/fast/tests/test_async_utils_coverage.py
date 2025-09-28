"""Async variant of test_utils_coverage focusing on ExpiringDict + safe_pickle basic usage."""
from __future__ import annotations
import asyncio, pickle, pytest
from dictsqlite_fast import AsyncFastDictSQLite
from dictsqlite.modules import utils, safe_pickle

@pytest.mark.asyncio
async def test_async_expiring_dict_end_to_end(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'ucov.db'))
    try:
        ed = db.expiring_dict(0.05)
        ed['k'] = 'v'
        assert ed['k'] == 'v'
        await asyncio.sleep(0.15)
        assert 'k' not in ed
        # store expiring dict itself
        ed2 = utils.ExpiringDict(0.1); ed2['x']=1
        await db.set('ed', ed2)
        restored = await db.get('ed')
        # restored is mapping proxy -> convert to dict
        assert dict(restored)['x'] == 1
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_safe_pickle_roundtrip(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'ucov2.db'))
    try:
        data = {'a':[1,2], 'b':{'c':3}}
        dumped = pickle.dumps(data)
        loaded = safe_pickle.safe_loads(dumped)
        assert loaded == data
        await db.set('payload', data)
        got = await db.get('payload')
        assert got['a'][0] == 1
    finally:
        await db.close()

