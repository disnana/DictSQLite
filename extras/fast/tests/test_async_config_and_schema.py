"""Async tests mirroring test_config_and_schema (journal_mode, schema, expiring_dict)."""
from __future__ import annotations
import pytest
from dictsqlite_fast import AsyncFastDictSQLite
from dictsqlite.modules import utils

@pytest.mark.asyncio
async def test_async_journal_mode_valid_and_invalid(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'jm.db'), journal_mode='WAL')
    try:
        await db.set('x', 1)
        assert await db.get('x') == 1
    finally:
        await db.close()
    with pytest.raises(ValueError):
        await AsyncFastDictSQLite(str(tmp_path / 'bad.db'), journal_mode='INVALID').close()  # type: ignore

@pytest.mark.asyncio
async def test_async_schema_validation_blocks_injection(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'schema.db'))
    try:
        with pytest.raises(ValueError):
            await db.create_table(table_name='bad', schema='(key TEXT); DROP TABLE main;')
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_async_expiring_dict_through_db_roundtrip(tmp_path):
    db = AsyncFastDictSQLite(str(tmp_path / 'exp.db'))
    try:
        ed = utils.ExpiringDict(1)
        ed['k'] = 'v'
        await db.set('ed', ed)
        restored = await db.get('ed')
        # restored は RecursiveDict 相当
        assert dict(restored)['k'] == 'v'
    finally:
        await db.close()

