"""
Test table_mode feature for DictSQLite v4.2

This module tests the new table_mode parameter that allows choosing between:
- "prefix": Use key prefixes for table isolation (default, backward compatible)
- "separate": Use separate SQLite tables for complete isolation
"""
import os
import pytest
from .conftest import windows_safe_temp_dir


def test_prefix_mode_basic():
    """Test basic prefix mode functionality (default behavior)"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_mode.db")
        
        # Create DB with prefix mode (default)
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="prefix")
        
        # Get table proxies
        users = db.table("users")
        products = db.table("products")
        
        # Add data to users table
        users["user1"] = {"name": "Alice", "age": 30}
        users["user2"] = {"name": "Bob", "age": 25}
        
        # Add data to products table
        products["prod1"] = {"name": "Laptop", "price": 80000}
        products["prod2"] = {"name": "Mouse", "price": 1500}
        
        # Verify users table
        assert users["user1"]["name"] == "Alice"
        assert users["user2"]["age"] == 25
        
        # Verify products table
        assert products["prod1"]["price"] == 80000
        assert products["prod2"]["name"] == "Mouse"
        
        # Check keys
        user_keys = users.keys()
        assert "user1" in user_keys
        assert "user2" in user_keys
        
        product_keys = products.keys()
        assert "prod1" in product_keys
        assert "prod2" in product_keys
        
        # Test __contains__
        assert "user1" in users
        assert "prod1" in products
        assert "user999" not in users
        
        # Test len
        assert len(users) == 2
        assert len(products) == 2
        
        db.close()
        print("✅ Prefix mode basic test passed")


def test_separate_mode_basic():
    """Test basic separate mode functionality"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_mode.db")
        
        # Create DB with separate mode
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="separate")
        
        # Get table proxies
        users = db.table("users")
        products = db.table("products")
        
        # Add data to users table
        users["user1"] = {"name": "Alice", "age": 30}
        users["user2"] = {"name": "Bob", "age": 25}
        
        # Add data to products table
        products["prod1"] = {"name": "Laptop", "price": 80000}
        products["prod2"] = {"name": "Mouse", "price": 1500}
        
        # Verify users table
        assert users["user1"]["name"] == "Alice"
        assert users["user2"]["age"] == 25
        
        # Verify products table
        assert products["prod1"]["price"] == 80000
        assert products["prod2"]["name"] == "Mouse"
        
        # Check keys
        user_keys = users.keys()
        assert "user1" in user_keys
        assert "user2" in user_keys
        
        product_keys = products.keys()
        assert "prod1" in product_keys
        assert "prod2" in product_keys
        
        # Test __contains__
        assert "user1" in users
        assert "prod1" in products
        assert "user999" not in users
        
        # Test len
        assert len(users) == 2
        assert len(products) == 2
        
        db.close()
        print("✅ Separate mode basic test passed")


def test_separate_mode_persistence():
    """Test that separate mode data persists correctly across sessions"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_persist.db")
        
        # Session 1: Write data
        db1 = DictSQLiteV4(
            db_path, storage_mode="jsonb", 
            persist_mode="writethrough", table_mode="separate"
        )
        users = db1.table("users")
        products = db1.table("products")
        
        users["alice"] = {"name": "Alice", "role": "admin"}
        products["laptop"] = {"name": "Laptop", "price": 1000}
        
        db1.flush()
        db1.close()
        
        # Session 2: Read data
        db2 = DictSQLiteV4(
            db_path, storage_mode="jsonb", table_mode="separate"
        )
        users2 = db2.table("users")
        products2 = db2.table("products")
        
        # Verify data persisted
        assert users2["alice"]["name"] == "Alice"
        assert users2["alice"]["role"] == "admin"
        assert products2["laptop"]["price"] == 1000
        
        db2.close()
        print("✅ Separate mode persistence test passed")


def test_separate_mode_isolation():
    """Test that separate mode provides complete table isolation"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_isolation.db")
        
        db = DictSQLiteV4(
            db_path, storage_mode="jsonb",
            persist_mode="writethrough", table_mode="separate"
        )
        
        # Create tables with same keys
        users = db.table("users")
        admins = db.table("admins")
        
        # Same key in different tables
        users["alice"] = {"type": "user", "level": 1}
        admins["alice"] = {"type": "admin", "level": 10}
        
        # Verify isolation
        assert users["alice"]["type"] == "user"
        assert users["alice"]["level"] == 1
        assert admins["alice"]["type"] == "admin"
        assert admins["alice"]["level"] == 10
        
        # Delete from one table shouldn't affect the other
        del users["alice"]
        assert "alice" not in users
        assert "alice" in admins
        assert admins["alice"]["type"] == "admin"
        
        db.close()
        print("✅ Separate mode isolation test passed")


def test_separate_mode_clear_table():
    """Test clearing a table in separate mode"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_clear.db")
        
        db = DictSQLiteV4(
            db_path, storage_mode="jsonb",
            persist_mode="writethrough", table_mode="separate"
        )
        
        users = db.table("users")
        products = db.table("products")
        
        users["user1"] = {"name": "Alice"}
        users["user2"] = {"name": "Bob"}
        products["prod1"] = {"name": "Laptop"}
        products["prod2"] = {"name": "Mouse"}
        
        # Clear users table
        users.clear()
        
        # Verify users is empty
        assert len(users) == 0
        assert "user1" not in users
        
        # Verify products is unaffected
        assert len(products) == 2
        assert "prod1" in products
        assert "prod2" in products
        
        db.close()
        print("✅ Separate mode clear table test passed")


def test_async_separate_mode():
    """Test async operations with separate mode"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_separate.db")
        
        # Create async DB with separate mode
        db = AsyncDictSQLite(
            db_path, storage_mode="jsonb", table_mode="separate"
        )
        
        # Get table proxy
        users = db.table("users")
        products = db.table("products")
        
        # Add data
        users["user1"] = {"name": "Alice", "age": 30}
        products["prod1"] = {"name": "Laptop", "price": 1000}
        
        # Verify
        assert users["user1"]["name"] == "Alice"
        assert products["prod1"]["price"] == 1000
        
        # Test __contains__
        assert "user1" in users
        assert "prod1" in products
        
        db.close()
        print("✅ Async separate mode test passed")


def test_modes_constants():
    """Test that Modes constants are available"""
    try:
        from dictsqlite import Modes
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    # Verify table mode constants
    assert Modes.TABLE_PREFIX == "prefix"
    assert Modes.TABLE_SEPARATE == "separate"
    
    print("✅ Modes constants test passed")


def test_invalid_table_mode():
    """Test that invalid table_mode raises an error"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_invalid.db")
        
        with pytest.raises(ValueError):
            DictSQLiteV4(db_path, table_mode="invalid_mode")
        
        print("✅ Invalid table_mode test passed")


if __name__ == "__main__":
    print("Running table_mode tests...")
    
    try:
        test_prefix_mode_basic()
        test_separate_mode_basic()
        test_separate_mode_persistence()
        test_separate_mode_isolation()
        test_separate_mode_clear_table()
        test_async_separate_mode()
        test_modes_constants()
        test_invalid_table_mode()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
