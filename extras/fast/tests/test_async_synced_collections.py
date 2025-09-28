"""Async variant of test_synced_collections.py for AsyncFastDictSQLite.

トップレベル list / set の自動同期挙動を非同期 API で検証。
"""
from __future__ import annotations
import pytest
from dictsqlite_fast import AsyncFastDictSQLite

@pytest.mark.asyncio
async def test_async_list_basic_operations(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'alist.db'))
    try:
        await db.set('test_list', [1,2,3])
        lst = await db.get('test_list')
        assert lst[0] == 1 and lst[2] == 3
        lst.append(4)
        lst.insert(1, 9)
        fresh = await db.get('test_list')
        assert fresh == [1,9,2,3,4]
        lst.pop(); lst.remove(9)
        fresh2 = await db.get('test_list')
        assert fresh2 == [1,2,3]
        lst.clear()
        assert await db.get('test_list') == []
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_list_slice_and_sort(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'alist2.db'))
    try:
        await db.set('nums', [5,4,3,2,1])
        nums = await db.get('nums')
        nums.reverse()
        assert await db.get('nums') == [1,2,3,4,5]
        nums.sort(reverse=True)
        assert await db.get('nums') == [5,4,3,2,1]
        nums[1:3] = [20,30]
        assert await db.get('nums') == [5,20,30,2,1]
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_set_basic_operations(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'aset.db'))
    try:
        await db.set('tags', {'a','b'})
        tags = await db.get('tags')
        tags.add('c')
        tags.discard('a')
        assert await db.get('tags') == {'b','c'}
        tags.update({'x','y'})
        assert {'b','c','x','y'} == await db.get('tags')
        tags.clear()
        assert await db.get('tags') == set()
    finally:
        await db.close()

