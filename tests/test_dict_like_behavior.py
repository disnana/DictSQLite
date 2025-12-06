"""Tests for dict-like behavior in DictSQLite and TableProxy.

このテストファイルは、DictSQLiteとTableProxyが通常のPython辞書と同様に
振る舞うことを確認するテストを含んでいます。これはモジュールの存在意義である
「通常のdictと同じように扱える」ことを保証するためのテストです。
"""
# pylint: disable=missing-function-docstring,redefined-outer-name

import pytest

from dictsqlite.main import DictSQLite


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_dict_like.db"


@pytest.fixture()
def db(db_path):
    d = DictSQLite(str(db_path))
    yield d
    d.close()


class TestDictSQLiteDictLikeBehavior:
    """Tests for DictSQLite dict-like behavior."""

    def test_empty_db_equals_empty_dict(self, db_path):
        """空のデータベースが空の辞書と等しいことをテスト"""
        with DictSQLite(str(db_path)) as db:
            # Testing __eq__ explicitly, not boolean truthiness
            assert db == {}  # pylint: disable=use-implicit-booleaness-not-comparison

    def test_db_equals_dict_with_values(self, db: DictSQLite):
        """値を持つデータベースが対応する辞書と等しいことをテスト"""
        db["key1"] = "value1"
        db["key2"] = "value2"
        db.operation_queue.join()

        assert db == {"key1": "value1", "key2": "value2"}

    def test_db_not_equals_different_dict(self, db: DictSQLite):
        """データベースが異なる辞書と等しくないことをテスト"""
        db["key1"] = "value1"
        db.operation_queue.join()

        assert db != {"key1": "wrong_value"}
        assert db != {"different_key": "value1"}
        assert db != {"key1": "value1", "extra": "value"}

    def test_keys_method(self, db: DictSQLite):
        """keys()メソッドが正しく動作することをテスト"""
        db["a"] = 1
        db["b"] = 2
        db["c"] = 3
        db.operation_queue.join()

        keys = db.keys()
        assert set(keys) == {"a", "b", "c"}
        assert len(keys) == 3

    def test_get_method(self, db: DictSQLite):
        """get()メソッドが辞書と同様に動作することをテスト"""
        db["existing"] = "value"
        db.operation_queue.join()

        assert db.get("existing") == "value"
        assert db.get("non_existing") is None
        assert db.get("non_existing", "default") == "default"

    def test_contains_operator(self, db: DictSQLite):
        """in演算子が正しく動作することをテスト"""
        db["key"] = "value"
        db.operation_queue.join()

        assert "key" in db
        assert "non_existing" not in db


class TestTableProxyDictLikeBehavior:
    """Tests for TableProxy dict-like behavior."""

    def test_table_method_creates_table_proxy(self, db: DictSQLite):
        """table()メソッドがTableProxyを返すことをテスト"""
        table = db.table("test_table")
        assert table is not None
        assert table.table_name == "test_table"

    def test_table_proxy_equals_dict(self, db: DictSQLite):
        """TableProxyが辞書との等価比較をサポートすることをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        db.operation_queue.join()

        assert table == {"key1": "value1"}

    def test_table_proxy_not_equals_different_dict(self, db: DictSQLite):
        """TableProxyが異なる辞書と等しくないことをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        db.operation_queue.join()

        assert table != {"key1": "wrong_value"}
        assert table != {"different_key": "value1"}

    def test_table_proxy_keys(self, db: DictSQLite):
        """TableProxyのkeys()メソッドをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        table["key2"] = "value2"
        db.operation_queue.join()

        keys = table.keys()
        assert set(keys) == {"key1", "key2"}
        assert len(keys) == 2

    def test_table_proxy_values(self, db: DictSQLite):
        """TableProxyのvalues()メソッドをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        table["key2"] = "value2"
        db.operation_queue.join()

        values = table.values()
        assert set(values) == {"value1", "value2"}
        assert len(values) == 2

    def test_table_proxy_items(self, db: DictSQLite):
        """TableProxyのitems()メソッドをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        table["key2"] = "value2"
        db.operation_queue.join()

        items = table.items()
        assert set(items) == {("key1", "value1"), ("key2", "value2")}
        assert len(items) == 2

    def test_table_proxy_len(self, db: DictSQLite):
        """TableProxyの__len__メソッドをテスト"""
        table = db.table("table1")
        assert len(table) == 0

        table["key1"] = "value1"
        db.operation_queue.join()
        assert len(table) == 1

        table["key2"] = "value2"
        db.operation_queue.join()
        assert len(table) == 2

    def test_table_proxy_iter(self, db: DictSQLite):
        """TableProxyの__iter__が辞書と同様にキーをイテレートすることをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        table["key2"] = "value2"
        db.operation_queue.join()

        # iter()はキーのみを返す（辞書と同じ）
        keys_from_iter = list(table)
        assert set(keys_from_iter) == {"key1", "key2"}

    def test_table_proxy_get(self, db: DictSQLite):
        """TableProxyのget()メソッドをテスト"""
        table = db.table("table1")
        table["existing"] = "value"
        db.operation_queue.join()

        assert table.get("existing") == "value"
        assert table.get("non_existing") is None
        assert table.get("non_existing", "default") == "default"

    def test_table_proxy_contains(self, db: DictSQLite):
        """TableProxyのin演算子をテスト"""
        table = db.table("table1")
        table["key"] = "value"
        db.operation_queue.join()

        assert "key" in table
        assert "non_existing" not in table

    def test_table_proxy_repr(self, db: DictSQLite):
        """TableProxyの__repr__が辞書形式の文字列を返すことをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        db.operation_queue.join()

        rep = repr(table)
        assert rep.startswith("{") and rep.endswith("}")
        assert "key1" in rep
        assert "value1" in rep


class TestMultipleTablesScenario:
    """Tests for multiple tables scenario from the issue."""

    def test_issue_scenario(self, db_path):
        """Issue #XXX で報告されたシナリオをテスト"""
        with DictSQLite(str(db_path)) as db:
            # 空のDBは空の辞書と等しい (testing __eq__ explicitly)
            assert db == {}  # pylint: disable=use-implicit-booleaness-not-comparison

            # メインテーブルに値を設定
            db['key1'] = 'value1'
            db['key2'] = 'value2'
            db.operation_queue.join()

            # 値の取得をテスト
            assert db['key1'] == 'value1'
            assert db['key2'] == 'value2'

            # get()メソッドのテスト
            assert db.get('key1') == 'value1'

            # テーブル1を作成して値を設定
            table1 = db.table('table1')
            table1['tkey1'] = 'tvalue1'
            db.operation_queue.join()

            assert table1['tkey1'] == 'tvalue1'

            # テーブル2を作成して値を設定
            table2 = db.table('table2')
            table2['tkey2'] = 'tvalue2'
            db.operation_queue.join()

            assert table2['tkey2'] == 'tvalue2'

            # keys()メソッドのテスト（順序は保証されないのでsetで比較）
            assert set(table1.keys()) == {'tkey1'}
            assert set(table2.keys()) == {'tkey2'}

            # 辞書との等価比較テスト
            assert table1 == {"tkey1": 'tvalue1'}
            assert table2 == {"tkey2": 'tvalue2'}

    def test_table_does_not_affect_main_table(self, db: DictSQLite):
        """table()メソッドがメインテーブルに影響しないことをテスト"""
        db["main_key"] = "main_value"
        db.operation_queue.join()

        table1 = db.table("table1")
        table1["table_key"] = "table_value"
        db.operation_queue.join()

        # メインテーブルの値は影響を受けない
        assert db["main_key"] == "main_value"
        assert "table_key" not in db
        assert db.keys() == ["main_key"]

        # テーブル1には新しい値がある
        assert table1["table_key"] == "table_value"
        assert table1.keys() == ["table_key"]


class TestDictConversion:
    """Tests for dict conversion."""

    def test_dict_from_table_proxy_items(self, db: DictSQLite):
        """dict()でTableProxyを辞書に変換できることをテスト"""
        table = db.table("table1")
        table["key1"] = "value1"
        table["key2"] = "value2"
        db.operation_queue.join()

        d = dict(table.items())
        assert d == {"key1": "value1", "key2": "value2"}

    def test_dict_from_dict_sqlite_items(self, db: DictSQLite):
        """DictSQLiteからitems()を使って辞書を作成できることをテスト"""
        db["key1"] = "value1"
        db["key2"] = "value2"
        db.operation_queue.join()

        proxy = db.table(db.table_name)
        d = dict(proxy.items())
        assert d == {"key1": "value1", "key2": "value2"}
