import json
import time
import sqlite3
import pytest

from dictsqlite.main import DictSQLite


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_basic.db"


@pytest.fixture()
def db(db_path):
    d = DictSQLite(str(db_path))
    yield d
    d.close()


def test_basic_crud_and_repr(db: DictSQLite):
    db["a"] = 1
    db["b"] = "text"
    db["c"] = 3.14
    db["d"] = True
    db["e"] = None
    db["f"] = b"bytes"

    assert db.has_key("a") is True
    assert "a" in db

    assert db["a"] == 1
    assert db["b"] == "text"
    assert db["c"] == 3.14
    assert db["d"] is True
    assert db["e"] is None
    assert db["f"] == b"bytes"

    keys = set(db.keys())
    for k in ["a", "b", "c", "d", "e", "f"]:
        assert k in keys

    # __repr__ は辞書風の表現
    rep = repr(db)
    assert rep.startswith("{") and rep.endswith("}")

    # 削除
    del db["a"]
    assert ("a" in db) is False


def test_top_level_synced_list_and_set(db: DictSQLite):
    db["lst"] = [1, 2]
    db["st"] = {1, 2}

    lst = db["lst"]
    st = db["st"]

    # top-level list は同期される
    lst.append(3)
    assert db["lst"] == [1, 2, 3]

    # top-level set は同期される
    st.add(3)
    assert set(db["st"]) == {1, 2, 3}


@pytest.mark.parametrize("initial", [
    {"x": 1, "inner": {"y": 2}, "l": [1], "s": {1}},
    {"inner": {"y": 0}},
])
def test_recursive_dict_and_nested_behavior(db: DictSQLite, initial):
    db["cfg"] = initial

    cfg = db["cfg"]  # RecursiveDict のはず
    # top-level dict の更新
    cfg["x"] = 10

    # ネスト辞書の更新は自動保存される
    if "inner" in cfg:
        cfg["inner"]["y"] = 20

    # items()/values() のラップ確認（値側のプロキシを介して更新できる）
    for k, v in cfg.items():
        if k == "inner" and isinstance(v, dict) or hasattr(v, "__getitem__"):
            try:
                v["z"] = 99
            except Exception:
                pass

    # nested list は同期されない（再読込で反映されない）
    if "l" in cfg:
        lst = cfg["l"]
        if isinstance(lst, list):
            lst.append(2)

    # nested set も同期されない
    if "s" in cfg:
        s = cfg["s"]
        if isinstance(s, set):
            s.add(2)

    # 再取得して検証
    cfg2 = db["cfg"]
    assert cfg2.get("x") == 10
    if "inner" in initial:
        assert cfg2["inner"]["y"] == 20
        # items()からの更新が効いていれば z=99 が存在する
        assert ("z" in cfg2["inner"]) is True
    if "l" in initial:
        assert cfg2["l"] == [1]  # 同期されない
    if "s" in initial:
        assert set(cfg2["s"]) == {1}  # 同期されない


def test_contains_keys_and_clear_table(db: DictSQLite):
    db["k1"] = "v1"
    db["k2"] = "v2"
    assert db.has_key("k1")
    assert set(db.keys()) >= {"k1", "k2"}

    db.clear_table()
    # テーブルクリア後は空
    assert db.keys() == []


