"""Async variant of test_pickle_security.py."""
from __future__ import annotations
import os, sys, tempfile, time, pickle, pytest
from dictsqlite_fast import AsyncFastDictSQLite
from dictsqlite.main import randomstrings, safe_pickle as _safe_pickle

class Evil:  # pylint: disable=too-few-public-methods
    def __reduce__(self):
        tmp = os.path.join(tempfile.gettempdir(), 'dictsqlite_rce_test_async.txt')
        cmd = f'"{sys.executable}" -c "open(\"{tmp}\",\"w\").write(\"PWNED\")"'
        return (os.system, (cmd,))

@pytest.mark.asyncio
async def test_async_evil_payload_not_executed(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'rce.db'))
    try:
        marker = os.path.join(tempfile.gettempdir(), 'dictsqlite_rce_test_async.txt')
        if os.path.exists(marker): os.remove(marker)
        await db.set('evil', Evil())
        val = await db.get('evil')
        assert isinstance(val, str)
        time.sleep(0.05)
        assert not os.path.exists(marker)
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_mixed_payload_blocked(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'mix.db'))
    try:
        await db.set('mixed', {'safe':1, 'evil': Evil()})
        val = await db.get('mixed')
        assert isinstance(val, str)
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_safe_pickle_allows_safe_builtins():
    safe_data = {'a':[1,2,3], 'b':(1,2)}
    dumped = pickle.dumps(safe_data)
    restored = _safe_pickle.safe_loads(dumped)
    assert restored == safe_data

@pytest.mark.asyncio
async def test_async_policy_allows_project_function(tmp_path):
    kwargs = { 'safe_pickle_policy': _safe_pickle.SafePolicy.for_package('dictsqlite', allow_functions_from_prefixes=True)}
    db = AsyncFastDictSQLite(str(tmp_path / 'func.db'), **kwargs)
    try:
        await db.set('func', randomstrings)
        func = await db.get('func')
        s = getattr(func, '__call__')(5)
        assert isinstance(s, str) and len(s) == 5
    finally:
        await db.close()

