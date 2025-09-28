"""Tests for compatibility and cryptography features of DictSQLite."""
# pylint: disable=redefined-outer-name

import collections.abc
import json
import sqlite3
import pytest
from dictsqlite_fast import FastDictSQLite


@pytest.fixture()
def db_path(tmp_path):
    """Provide a path to a temporary database file."""
    return tmp_path / "test_compat.db"


@pytest.fixture()
def db(db_path):
    """Provide a DictSQLite instance."""
    d = FastDictSQLite(str(db_path))
    yield d
    d.close()


def test_json_compatibility_read(db_path):
    """Test reading data from a database with old JSON format."""
    # 手動で旧JSON形式のデータを挿入し、APIで正しく読めることを確認
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS main (key TEXT PRIMARY KEY, value TEXT)")

    # set は {"__type__":"set","value":[...]} として保存
    payload = {"a": 1, "b": {"__type__": "set", "value": [2, 3]}, "c": [1, 2, 3]}
    cur.execute("INSERT OR REPLACE INTO main (key, value) VALUES (?, ?)", (
        "kjson",
        json.dumps(payload),
    ))
    conn.commit()
    conn.close()

    db_conn = FastDictSQLite(str(db_path))
    try:
        v = db_conn["kjson"]
        assert isinstance(v, collections.abc.Mapping)
        assert v["a"] == 1
        assert set(v["b"]) == {2, 3}
        assert v["c"] == [1, 2, 3]
    finally:
        db_conn.close()


def test_encryption_roundtrip(tmp_path):
    """Test the full encryption and decryption roundtrip."""
    # cryptography が無い場合はスキップ
    pytest.importorskip("cryptography", reason="cryptography not installed")
    # pylint: disable=import-outside-toplevel
    from dictsqlite.modules import crypto

    pub_path = tmp_path / "pub.pem"
    priv_path = tmp_path / "priv.pem"
    password = "pw123"

    crypto.key_create(
        password=password,
        pubkey_path=str(pub_path),
        private_key_path=str(priv_path),
    )

    db_path = tmp_path / "enc.db"
    db_conn = FastDictSQLite(
        str(db_path),
        password=password,
        publickey_path=str(pub_path),
        privatekey_path=str(priv_path),
    )
    try:
        db_conn["num"] = 42
        db_conn["text"] = "hello"
        db_conn["arr"] = [1, 2, 3]
        db_conn["obj"] = {"x": 1, "y": 2}
        db_conn["set"] = {1, 2}

        assert db_conn["num"] == 42
        assert db_conn["text"] == "hello"
        assert db_conn["arr"] == [1, 2, 3]
        assert db_conn["obj"]["x"] == 1
        assert set(db_conn["set"]) == {1, 2}

        # DB内部が暗号化されていることを確認（復号なしではプレーンテキストは見えない=bytesで存在）
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute("SELECT value FROM main WHERE key = ?", ("text",))
        raw = cur.fetchone()[0]
        con.close()
        assert isinstance(raw, (bytes, bytearray))
    finally:
        db_conn.close()
