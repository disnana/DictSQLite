"""Async JSON mode tests mirroring test_json_mode.py."""
from __future__ import annotations
import pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_json_basic_store_and_load(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aj_basic.db'), storage_mode='json')
    try:
        await db.set('int', 123)
        await db.set('str', 'hello')
        await db.set('list', [1,2,3])
        await db.set('dict', {'a':1,'b':2})
        await db.set('set', {'x','y'})
        assert await db.get('int') == 123
        assert await db.get('str') == 'hello'
        assert await db.get('list') == [1,2,3]
        d = await db.get('dict'); assert d['a']==1 and d['b']==2
        assert await db.get('set') == {'x','y'}
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_json_nested_dict_updates(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aj_nested.db'), storage_mode='json')
    try:
        await db.set('conf', {"section": {"k":1}, 'list':[10,20]})
        conf = await db.get('conf')
        conf['section']['k'] = 2
        conf['section']['new'] = 99
        conf['list'][0] = 11  # not auto-synced (nested list)
        conf2 = await db.get('conf')
        assert conf2['section']['k'] == 2
        assert conf2['section']['new'] == 99
        assert conf2['list'][0] == 10
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_json_not_serializable_raises(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aj_err.db'), storage_mode='json')
    class X:  # pylint: disable=too-few-public-methods
        pass
    try:
        with pytest.raises(TypeError):
            await db.set('x', X())
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_json_mode_with_encryption(tmp_path):
    pub = tmp_path / 'pub.pem'; priv = tmp_path / 'priv.pem'
    db = AsyncFastDictSQLite(str(tmp_path / 'aj_enc.db'), storage_mode='json', password='pw', key_create=True,
                             publickey_path=str(pub), privatekey_path=str(priv))
    try:
        await db.set('secure', {'v':42, 's': {'a','b'}})
        sec = await db.get('secure')
        assert sec['v'] == 42
        assert sec['s'] == {'a','b'}
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_json_mode_type_error_under_encryption(tmp_path):
    pub = tmp_path / 'pub2.pem'; priv = tmp_path / 'priv2.pem'
    db = AsyncFastDictSQLite(str(tmp_path / 'aj_enc_err.db'), storage_mode='json', password='pw', key_create=True,
                             publickey_path=str(pub), privatekey_path=str(priv))
    try:
        with pytest.raises(TypeError):
            await db.set('bad', lambda x: x)  # noqa: E731
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_json_basic_store_and_load_v2(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aj_v2.db'), version=2, storage_mode='json')
    try:
        await db.create_table()  # main
        await db.set(('k','main'), {'n':1})
        main_proxy = await db.get('main')
        assert main_proxy['k']['n'] == 1
    finally:
        await db.close()

