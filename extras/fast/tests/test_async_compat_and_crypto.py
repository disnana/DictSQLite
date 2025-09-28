"""Async variant of test_compat_and_crypto.py."""
from __future__ import annotations
import json, sqlite3, pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_json_compatibility_read(tmp_path):
    db_path = tmp_path / 'ac_compat.db'
    con = sqlite3.connect(str(db_path)); cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS main (key TEXT PRIMARY KEY, value TEXT)')
    payload = {"a":1, "b":{"__type__":"set","value":[2,3]}, "c":[1,2,3]}
    cur.execute('INSERT OR REPLACE INTO main (key,value) VALUES (?,?)', ('kjson', json.dumps(payload)))
    con.commit(); con.close()
    db = AsyncFastDictSQLite(str(db_path))
    try:
        v = await db.get('kjson')
        assert v['a'] == 1
        assert set(v['b']) == {2,3}
        assert v['c'] == [1,2,3]
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_encryption_roundtrip(tmp_path):
    pytest.importorskip('cryptography')
    from dictsqlite.modules import crypto  # type: ignore
    pub = tmp_path / 'pub.pem'; priv = tmp_path / 'priv.pem'
    crypto.key_create(password='pw', pubkey_path=str(pub), private_key_path=str(priv))
    db = AsyncFastDictSQLite(str(tmp_path / 'enc.db'), password='pw', publickey_path=str(pub), privatekey_path=str(priv))
    try:
        await db.set('num', 42)
        await db.set('text', 'hello')
        await db.set('arr', [1,2,3])
        await db.set('obj', {'x':1,'y':2})
        await db.set('set', {1,2})
        assert await db.get('num') == 42
        assert await db.get('text') == 'hello'
        arr = await db.get('arr'); assert arr == [1,2,3]
        obj = await db.get('obj'); assert obj['x'] == 1
        st = await db.get('set'); assert st == {1,2}
        con = sqlite3.connect(str(tmp_path / 'enc.db')); cur = con.cursor(); cur.execute('SELECT value FROM main WHERE key=?', ('text',)); raw = cur.fetchone()[0]; con.close()
        assert isinstance(raw, (bytes, bytearray))
    finally:
        await db.close()

