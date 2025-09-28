"""DictSQLite の設定系とスキーマ検証テスト。"""
from __future__ import annotations

# pytest フィクスチャ名の再定義は意図的なため無効化
# pylint: disable=redefined-outer-name

import collections.abc
import pytest

from dictsqlite_fast import FastDictSQLite
from dictsqlite.modules import utils


@pytest.fixture()
def db_path(tmp_path):
    """一時DBファイルパスを提供するフィクスチャ。"""
    return tmp_path / "test_config_schema.db"


def test_journal_mode_valid_and_invalid(db_path):
    """journal_mode が妥当値では成功し、不正値では ValueError となる。"""
    # valid
    d = FastDictSQLite(str(db_path), journal_mode="WAL")
    try:
        d["x"] = 1
        assert d["x"] == 1
    finally:
        d.close()

    # invalid
    with pytest.raises(ValueError):
        FastDictSQLite(str(db_path), journal_mode="INVALID_MODE").close()


def test_schema_validation_blocks_injection(db_path):
    """スキーマ文字列のインジェクション（セミコロンなど）を弾く。"""
    d = FastDictSQLite(str(db_path))
    try:
        # セミコロンを含む不正なスキーマは拒否
        with pytest.raises(ValueError):
            d.create_table(table_name="bad", schema="(key TEXT); DROP TABLE main;")
    finally:
        d.close()


def test_expiring_dict_through_db_roundtrip(db_path):
    """ExpiringDict をDBへ保存・復元でき、内容が保持されることを確認。"""
    d = FastDictSQLite(str(db_path))
    try:
        ed = utils.ExpiringDict(1)
        ed["k"] = "v"
        d["ed"] = ed

        restored = d["ed"]
        # 戻りはテーブルのトップレベル値なのでRecursiveDict等のマッピングプロキシ
        assert isinstance(restored, collections.abc.MutableMapping)
        assert dict(restored)["k"] == "v"

        # 期限動作はユニットテストで検証済み。DB経由では常時再構築のためここでは不検証。
    finally:
        d.close()
