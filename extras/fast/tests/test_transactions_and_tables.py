"""Tests for transactions and table management in DictSQLite."""
# pylint: disable=redefined-outer-name

import pytest

from dictsqlite_fast import FastDictSQLite


@pytest.fixture()
def db_path(tmp_path):
    """Provide a path to a temporary database file."""
    return tmp_path / "test.db"


@pytest.fixture()
def db(db_path):
    """Provide a FastDictSQLite instance."""
    d = FastDictSQLite(str(db_path))
    yield d
    d.close()


def test_transactions_commit_and_rollback(db: FastDictSQLite):
    """Test commit and rollback functionality."""
    # BEGIN -> write -> COMMIT
    db.begin_transaction()
    db["k1"] = "v1"
    db["k2"] = "v2"
    db.commit_transaction()
    # 待機
    db.operation_queue.join()

    assert db["k1"] == "v1"
    assert db["k2"] == "v2"

    # BEGIN -> write -> ROLLBACK
    db.begin_transaction()
    db["k3"] = "v3"
    db.rollback_transaction()
    db.operation_queue.join()

    assert ("k3" in db) is False


def test_switch_table_and_clear(db: FastDictSQLite):
    """Test switching tables and clearing them."""
    db["main_k"] = 1
    # 別テーブルへスイッチ
    db.switch_table("t1")
    db["t1_k"] = 2

    # main に戻す
    db.switch_table("main")
    assert db["main_k"] == 1

    # t1 に存在する
    db.switch_table("t1")
    assert db["t1_k"] == 2

    # clear_table 対象のみクリア
    db.clear_table("t1")
    db.operation_queue.join()

    assert db.keys("t1") == []


def test_version2_multi_tables(db_path):
    """Test multiple tables feature in version 2."""
    db = FastDictSQLite(str(db_path), version=2)
    try:
        # 先にテーブル作成（version=2は自動作成しない設計）
        db.create_table(table_name="alpha")
        db.create_table(table_name="beta")
        db.operation_queue.join()

        # (key, table) で書き込み
        db[("k1", "alpha")] = 100
        db[("k2", "beta")] = 200
        db.operation_queue.join()

        # 読み取り（テーブルプロキシ）
        alpha = db["alpha"]
        beta = db["beta"]

        assert alpha["k1"] == 100
        assert beta["k2"] == 200

        # contains on proxy
        assert ("k1" in alpha) is True
        assert ("kX" in alpha) is False

        # 反復で (key, value) が得られる
        items = dict(iter(alpha))
        assert items == {"k1": 100}

        # __repr__ が全テーブルを含む
        r = repr(db)
        assert "alpha" in r and "beta" in r
    finally:
        db.close()
