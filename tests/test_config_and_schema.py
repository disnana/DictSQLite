"""DictSQLite の設定系とスキーマ検証テスト。"""
from __future__ import annotations

import sqlite3
import time
import pickle
import pytest

from dictsqlite.main import DictSQLite
from dictsqlite.modules import utils


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_config_schema.db"


def test_journal_mode_valid_and_invalid(db_path):
    # valid
    d = DictSQLite(str(db_path), journal_mode="WAL")
    try:
        d["x"] = 1
        assert d["x"] == 1
    finally:
        d.close()

    # invalid
    with pytest.raises(ValueError):
        DictSQLite(str(db_path), journal_mode="INVALID_MODE").close()


def test_schema_validation_blocks_injection(db_path):
    d = DictSQLite(str(db_path))
    try:
        # セミコロンを含む不正なスキーマは拒否
        with pytest.raises(ValueError):
            d.create_table(table_name="bad", schema="(key TEXT); DROP TABLE main;")
    finally:
        d.close()


def test_expiring_dict_through_db_roundtrip(db_path):
    d = DictSQLite(str(db_path))
    try:
        ed = utils.ExpiringDict(0.1)
        ed["k"] = "v"
        d["ed"] = ed

        restored = d["ed"]
        # 戻りはテーブルのトップレベル値なのでRecursiveDict等のマッピングプロキシ
        import collections.abc
        assert isinstance(restored, collections.abc.MutableMapping)
        assert dict(restored.items())["k"] == "v"

        # 期限動作はユニットテストで検証済み。DB経由では常時再構築のためここでは不検証。
    finally:
        d.close()
