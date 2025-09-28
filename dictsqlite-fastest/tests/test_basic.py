"""Basic tests for DictSQLite-Fastest."""

import pytest
import asyncio
from pathlib import Path

from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_fastest.db"


@pytest.fixture()
def db(db_path):
    d = DictSQLiteFastest(str(db_path))
    yield d
    d.close()


@pytest.fixture()
async def async_db(db_path):
    d = AsyncDictSQLiteFastest(str(db_path))
    yield d
    await d.aclose()


def test_basic_crud(db: DictSQLiteFastest):
    """基本的なCRUD操作のテスト"""
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

    # 削除
    del db["a"]
    assert ("a" in db) is False


def test_synced_collections(db: DictSQLiteFastest):
    """同期コレクションのテスト"""
    # リスト
    db["mylist"] = [1, 2, 3]
    db["mylist"].append(4)
    assert db["mylist"] == [1, 2, 3, 4]

    # セット
    db["myset"] = {1, 2, 3}
    db["myset"].add(4)
    assert 4 in db["myset"]


def test_recursive_dict(db: DictSQLiteFastest):
    """再帰辞書のテスト"""
    db["nested"] = {"x": 1, "inner": {"y": 2}}
    
    # ネストされた値の取得
    assert db["nested"]["x"] == 1
    assert db["nested"]["inner"]["y"] == 2
    
    # ネストされた値の更新
    db["nested"]["inner"]["y"] = 42
    assert db["nested"]["inner"]["y"] == 42


@pytest.mark.asyncio
async def test_async_basic_crud():
    """非同期基本CRUD操作のテスト"""
    import tempfile
    import os
    
    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        async with AsyncDictSQLiteFastest(db_path) as db:
            await db.aset("a", 1)
            await db.aset("b", "text")
            
            assert await db.aget("a") == 1
            assert await db.aget("b") == "text"
            assert await db.ahas_key("a") is True
            assert await db.__acontains__("b") is True
            
            keys = await db.akeys()
            assert "a" in keys
            assert "b" in keys
            
            await db.adelete("a")
            assert await db.__acontains__("a") is False
    finally:
        # 一時ファイルを削除
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_performance_optimizations(db: DictSQLiteFastest):
    """パフォーマンス最適化の確認"""
    # APSWの設定が適用されているか確認
    assert db.conn.pragma("synchronous") in [0, 1, 2]  # NORMALまたは設定値
    assert db.conn.pragma("cache_size") < 0  # negative means KB
    assert db.conn.pragma("temp_store") == 2  # MEMORY
    
    # Prepared statementsが設定されているか確認
    assert hasattr(db, '_insert_stmt')
    assert hasattr(db, '_select_stmt')
    assert hasattr(db, '_delete_stmt')


def test_json_mode(db_path):
    """JSONモードのテスト"""
    with DictSQLiteFastest(str(db_path), storage_mode='json') as db:
        db["list"] = [1, 2, 3]
        db["dict"] = {"a": 1, "b": 2}
        db["set"] = {1, 2, 3}
        
        assert db["list"] == [1, 2, 3]
        assert db["dict"] == {"a": 1, "b": 2}
        assert db["set"] == {1, 2, 3}


def test_context_manager(db_path):
    """コンテキストマネージャーのテスト"""
    with DictSQLiteFastest(str(db_path)) as db:
        db["test"] = "value"
        assert db["test"] == "value"
    
    # 接続が閉じられているかは直接確認できないが、エラーが出ないことを確認
    # 新しい接続で値が残っているか確認
    with DictSQLiteFastest(str(db_path)) as db2:
        assert db2["test"] == "value"