"""
Test TableProxy __eq__ functionality for DictSQLite

This tests that TableProxy instances can be compared with dictionaries
using the == operator, similar to how Python dicts work.
"""
import os
import pytest
from .conftest import windows_safe_temp_dir


def test_table_proxy_eq_with_dict():
    """Test TableProxy equality comparison with dict"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eq.db")
        
        db = DictSQLiteV4(db_path, storage_mode="pickle")
        
        # Create table proxy
        table = db.table("test_table")
        table["key1"] = "value1"
        
        # Test equality with matching dict
        assert table == {"key1": "value1"}
        
        # Test inequality with non-matching dict
        assert not (table == {"key1": "value2"})
        assert not (table == {"key2": "value1"})
        assert not (table == {"key1": "value1", "key2": "value2"})
        
        db.close()
        print("✅ TableProxy __eq__ with dict test passed")


def test_table_proxy_eq_with_empty_dict():
    """Test TableProxy equality comparison with empty dict"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eq_empty.db")
        
        db = DictSQLiteV4(db_path, storage_mode="pickle")
        
        # Create empty table proxy
        empty_table = db.table("empty")
        
        # Empty table should equal empty dict
        assert empty_table == {}
        
        # Empty table should not equal non-empty dict
        assert not (empty_table == {"key": "value"})
        
        db.close()
        print("✅ TableProxy __eq__ with empty dict test passed")


def test_table_proxy_eq_multiple_items():
    """Test TableProxy equality comparison with multiple items"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eq_multiple.db")
        
        db = DictSQLiteV4(db_path, storage_mode="pickle")
        
        # Create table with multiple items
        table = db.table("multi")
        table["key1"] = "value1"
        table["key2"] = "value2"
        table["key3"] = "value3"
        
        # Test equality with matching dict
        assert table == {"key1": "value1", "key2": "value2", "key3": "value3"}
        
        # Test inequality with missing key
        assert not (table == {"key1": "value1", "key2": "value2"})
        
        # Test inequality with extra key
        assert not (table == {"key1": "value1", "key2": "value2", "key3": "value3", "key4": "value4"})
        
        db.close()
        print("✅ TableProxy __eq__ with multiple items test passed")


def test_table_proxy_eq_with_non_dict():
    """Test TableProxy equality comparison with non-dict types"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eq_non_dict.db")
        
        db = DictSQLiteV4(db_path, storage_mode="pickle")
        
        # Create table proxy
        table = db.table("test")
        table["key1"] = "value1"
        
        # Table should not equal non-dict types
        assert not (table == "not a dict")
        assert not (table == 123)
        assert not (table == ["key1", "value1"])
        assert not (table == None)  # noqa: E711 - Testing equality operator, not identity
        
        db.close()
        print("✅ TableProxy __eq__ with non-dict types test passed")


def test_table_proxy_eq_with_another_table():
    """Test TableProxy equality comparison with another TableProxy"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eq_tables.db")
        
        db = DictSQLiteV4(db_path, storage_mode="pickle")
        
        # Create two tables with same content
        table1 = db.table("table1")
        table1["key1"] = "value1"
        
        table2 = db.table("table2")
        table2["key1"] = "value1"
        
        # Two tables with same content should be equal
        assert table1 == table2
        
        # Modify one table
        table2["key2"] = "value2"
        
        # Now they should not be equal
        assert not (table1 == table2)
        
        db.close()
        print("✅ TableProxy __eq__ with another TableProxy test passed")


def test_table_proxy_eq_jsonb_mode():
    """Test TableProxy equality in JSONB storage mode"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_eq_jsonb.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        # Create table with complex value
        table = db.table("jsonb_table")
        table["user"] = {"name": "Alice", "age": 30}
        
        # Test equality with matching dict
        assert table == {"user": {"name": "Alice", "age": 30}}
        
        db.close()
        print("✅ TableProxy __eq__ in JSONB mode test passed")


def test_issue_reproduction():
    """Test the exact scenario from the GitHub issue"""
    try:
        from dictsqlite import DictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        db = DictSQLite(db_path)
        
        # Reproduce the issue scenario
        if not db == {}:
            raise Exception("データベースが空ではありません。")
        
        db['key1'] = 'value1'
        db['key2'] = 'value2'
        
        table1 = db.table('table1')
        table1['tkey1'] = 'tvalue1'
        
        table2 = db.table('table2')
        table2['tkey2'] = 'tvalue2'
        
        # These are the key assertions from the issue
        if table1 == {"tkey1": 'tvalue1'}:
            print("table1の内容は正しいです。")
        else:
            raise Exception("table1の内容が正しくありません。")
        
        if table2 == {"tkey2": 'tvalue2'}:
            print("table2の内容は正しいです。")
        else:
            raise Exception("table2の内容が正しくありません。")
        
        db.close()
        print("✅ Issue reproduction test passed")


def test_async_table_proxy_eq_with_dict():
    """Test AsyncTableProxy equality comparison with dict"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_eq.db")
        
        db = AsyncDictSQLite(db_path, storage_mode="pickle")
        
        # Create async table proxy
        table = db.table("test_table")
        table["key1"] = "value1"
        
        # Test equality with matching dict
        assert table == {"key1": "value1"}
        
        # Test inequality with non-matching dict
        assert not (table == {"key1": "value2"})
        assert not (table == {"key2": "value1"})
        
        db.close()
        print("✅ AsyncTableProxy __eq__ with dict test passed")


def test_async_table_proxy_eq_with_empty_dict():
    """Test AsyncTableProxy equality comparison with empty dict"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_eq_empty.db")
        
        db = AsyncDictSQLite(db_path, storage_mode="pickle")
        
        # Create empty async table proxy
        empty_table = db.table("empty")
        
        # Empty table should equal empty dict
        assert empty_table == {}
        
        # Empty table should not equal non-empty dict
        assert not (empty_table == {"key": "value"})
        
        db.close()
        print("✅ AsyncTableProxy __eq__ with empty dict test passed")


def test_async_table_proxy_eq_multiple_items():
    """Test AsyncTableProxy equality comparison with multiple items"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_eq_multiple.db")
        
        db = AsyncDictSQLite(db_path, storage_mode="pickle")
        
        # Create table with multiple items
        table = db.table("multi")
        table["key1"] = "value1"
        table["key2"] = "value2"
        table["key3"] = "value3"
        
        # Test equality with matching dict
        assert table == {"key1": "value1", "key2": "value2", "key3": "value3"}
        
        # Test inequality with missing key
        assert not (table == {"key1": "value1", "key2": "value2"})
        
        db.close()
        print("✅ AsyncTableProxy __eq__ with multiple items test passed")


if __name__ == "__main__":
    print("Running TableProxy __eq__ tests...")
    
    try:
        test_table_proxy_eq_with_dict()
        test_table_proxy_eq_with_empty_dict()
        test_table_proxy_eq_multiple_items()
        test_table_proxy_eq_with_non_dict()
        test_table_proxy_eq_with_another_table()
        test_table_proxy_eq_jsonb_mode()
        test_issue_reproduction()
        test_async_table_proxy_eq_with_dict()
        test_async_table_proxy_eq_with_empty_dict()
        test_async_table_proxy_eq_multiple_items()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
