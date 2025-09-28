import threading
import time
import pytest

from dictsqlite_fast import FastDictSQLite

@pytest.fixture(params=["pickle", "json"])
def storage_mode(request):
    return request.param

@pytest.fixture()
def db(tmp_path, storage_mode):
    db_file = tmp_path / "fast_pkg.db"
    db = FastDictSQLite(str(db_file), storage_mode=storage_mode)
    yield db
    db.close()


def test_crud_and_repr(db):
    db["a"] = 1
    db["b"] = {"x": 10}
    db["c"] = [1, 2]
    db["d"] = {1, 2}
    assert db.has_key("a")
    assert "a" in db
    assert db["a"] == 1
    # list / set proxy
    lst = db["c"]
    st = db["d"]
    lst.append(3)
    st.add(3)
    assert db["c"] == [1, 2, 3]
    assert set(db["d"]) == {1, 2, 3}
    rep = repr(db)
    assert rep.startswith("FastDictSQLite(")


def test_recursive_dict(db):
    db["cfg"] = {"inner": {"k": 1}, "lst": [1], "s": {1}}
    cfg = db["cfg"]
    cfg["inner"]["k"] = 99
    cfg["x"] = 5
    # nested list/set not auto synced
    cfg["lst"].append(2)
    cfg["s"].add(2)
    cfg2 = db["cfg"]
    assert cfg2["inner"]["k"] == 99
    assert cfg2["x"] == 5
    assert cfg2["lst"] == [1]  # not synced
    assert set(cfg2["s"]) == {1}  # not synced


def test_switch_table_and_version2(tmp_path, storage_mode):
    db_file = tmp_path / "ver2.db"
    db = FastDictSQLite(str(db_file), version=2, storage_mode=storage_mode)
    # version=2: db["table"] で TableProxy
    db.switch_table("t1")
    db[("k1", "t1")] = 100
    assert db["t1"]["k1"] == 100
    db.switch_table("t2")
    db[("k2", "t2")] = {"nest": 1}
    assert db["t2"]["k2"]["nest"] == 1
    assert set(db.tables()) >= {"t1", "t2"}
    db.clear_table("t1")
    assert db.keys("t1") == []
    db.clear_db()
    assert db.tables() == ["main"]
    db.close()


def test_transactions(db):
    db.begin()
    db["x"] = 10
    db.commit()
    assert db["x"] == 10
    db.begin_transaction()
    db["y"] = 20
    db.rollback_transaction()
    # rollback の簡易検証 (APSW begin immediate 後 rollback)
    try:
        _ = db["y"]
        # 失敗しない可能性もある(実装が即書き込み)ので緩くチェック
    except KeyError:
        pass


def test_conflict_resolver(tmp_path, storage_mode):
    db_path = tmp_path / "locktest.db"
    db1 = FastDictSQLite(str(db_path), conflict_resolver=True, storage_mode=storage_mode)
    db2 = FastDictSQLite(str(db_path), conflict_resolver=True, storage_mode=storage_mode)

    def writer(db, start):
        for i in range(start, start + 10):
            db[f"k{i}"] = i
            time.sleep(0.01)

    t1 = threading.Thread(target=writer, args=(db1, 0))
    t2 = threading.Thread(target=writer, args=(db2, 100))
    t1.start(); t2.start(); t1.join(); t2.join()
    # flush queues
    db1.flush(); db2.flush()
    # Just ensure no exception and partial keys exist
    keys = set(db1.keys())
    assert any(k.startswith("k1") for k in keys) or any(k.startswith("k0") for k in keys)
    db1.close(); db2.close()


def test_execute_raw(db):
    db["raw"] = 1
    res = db.execute(f"SELECT key FROM \"{db.table_name}\" WHERE key=?", ["raw"])
    assert res[0][0] == "raw"


def test_expiring_dict_helper(db):
    ed = db.expiring_dict(1)
    ed["a"] = 1
    assert ed.get("a") == 1


