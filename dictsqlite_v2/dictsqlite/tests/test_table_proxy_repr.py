"""
Test TableProxy __repr__ and __str__ functionality for DictSQLite v4.2
"""
import os
import pytest
from .conftest import windows_safe_temp_dir


def test_table_proxy_repr_basic():
    """Test TableProxy __repr__ shows table name and contents"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_repr.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        # Create table proxy
        users = db.table("users")
        users["alice"] = {"name": "Alice", "role": "admin"}
        
        # Test __repr__
        repr_str = repr(users)
        assert "TableProxy" in repr_str
        assert "users" in repr_str
        assert "alice" in repr_str
        assert "Alice" in repr_str
        
        # Test __str__
        str_str = str(users)
        assert "TableProxy" in str_str
        assert "users" in str_str
        
        db.close()
        print("✅ TableProxy __repr__ basic test passed")


def test_table_proxy_repr_empty():
    """Test TableProxy __repr__ for empty table"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_repr_empty.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        # Create empty table proxy
        empty_table = db.table("empty")
        
        # Test __repr__ for empty table
        repr_str = repr(empty_table)
        assert "TableProxy" in repr_str
        assert "empty" in repr_str
        assert "{}" in repr_str
        
        db.close()
        print("✅ TableProxy __repr__ empty test passed")


def test_table_proxy_repr_multiple_items():
    """Test TableProxy __repr__ with multiple items"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_repr_multiple.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        # Create table with multiple items
        products = db.table("products")
        products["laptop"] = {"name": "Laptop", "price": 1000}
        products["mouse"] = {"name": "Mouse", "price": 50}
        
        # Test __repr__ contains all items
        repr_str = repr(products)
        assert "TableProxy" in repr_str
        assert "products" in repr_str
        assert "laptop" in repr_str
        assert "mouse" in repr_str
        
        db.close()
        print("✅ TableProxy __repr__ multiple items test passed")


def test_async_table_proxy_repr():
    """Test AsyncTableProxy __repr__ shows table name and contents"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_repr.db")
        
        db = AsyncDictSQLite(db_path, storage_mode="jsonb")
        
        # Create table proxy
        users = db.table("users")
        users["bob"] = {"name": "Bob", "role": "user"}
        
        # Test __repr__
        repr_str = repr(users)
        assert "TableProxy" in repr_str
        assert "users" in repr_str
        assert "bob" in repr_str
        assert "Bob" in repr_str
        
        db.close()
        print("✅ AsyncTableProxy __repr__ test passed")


def test_table_proxy_print():
    """Test that print(table_proxy) shows meaningful output"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_print.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        users = db.table("users")
        users["alice"] = {"name": "Alice", "role": "admin"}
        
        # Capture the printed output
        import io
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        print(users)
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Verify the output is not the default object representation
        assert "<builtins.TableProxy object at" not in output
        assert "TableProxy" in output
        assert "users" in output
        assert "alice" in output
        
        db.close()
        print("✅ TableProxy print test passed")


if __name__ == "__main__":
    print("Running TableProxy __repr__ tests...")
    
    try:
        test_table_proxy_repr_basic()
        test_table_proxy_repr_empty()
        test_table_proxy_repr_multiple_items()
        test_async_table_proxy_repr()
        test_table_proxy_print()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
