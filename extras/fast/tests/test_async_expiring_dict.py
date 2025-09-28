"""Async variant of test_expiring_dict.py focusing on AsyncFastDictSQLite.expiring_dict.
"""
from __future__ import annotations
import time, pickle, pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_expiring_dict_basic(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'exp.db'))
    try:
        ed = db.expiring_dict(0.05)
        ed['a'] = 1
        assert 'a' in ed
        time.sleep(0.15)
        assert 'a' not in ed
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_expiring_dict_pickle_roundtrip(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'exp2.db'))
    try:
        ed = db.expiring_dict(0.1)
        ed['x'] = 10
        data = pickle.dumps(ed)
        restored = pickle.loads(data)
        assert restored['x'] == 10
        restored['y'] = 20
        time.sleep(0.25)
        assert 'y' not in restored
    finally:
        await db.close()

