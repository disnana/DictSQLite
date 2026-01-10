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


def test_prefix_mode_with_encryption():
    """Test prefix mode with encryption enabled"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_encryption.db")
        
        db = DictSQLiteV4(
            db_path, storage_mode="jsonb", table_mode="prefix",
            encryption_password="secret123"
        )
        
        users = db.table("users")
        users["alice"] = {"name": "Alice", "secret": "password123"}
        
        assert users["alice"]["secret"] == "password123"
        
        db.close()
        
        # Re-open with correct password
        db2 = DictSQLiteV4(
            db_path, storage_mode="jsonb", table_mode="prefix",
            encryption_password="secret123"
        )
        users2 = db2.table("users")
        assert users2["alice"]["secret"] == "password123"
        db2.close()
        
        print("✅ Prefix mode with encryption test passed")


def test_separate_mode_with_encryption():
    """Test separate mode with encryption enabled"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_encryption.db")
        
        db = DictSQLiteV4(
            db_path, storage_mode="jsonb", table_mode="separate",
            encryption_password="secret123"
        )
        
        users = db.table("users")
        users["alice"] = {"name": "Alice", "secret": "password123"}
        
        assert users["alice"]["secret"] == "password123"
        
        db.close()
        
        # Re-open with correct password
        db2 = DictSQLiteV4(
            db_path, storage_mode="jsonb", table_mode="separate",
            encryption_password="secret123"
        )
        users2 = db2.table("users")
        assert users2["alice"]["secret"] == "password123"
        db2.close()
        
        print("✅ Separate mode with encryption test passed")


def test_prefix_mode_all_storage_modes():
    """Test prefix mode with all storage modes"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    storage_modes = ["pickle", "json", "jsonb"]
    
    for mode in storage_modes:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_prefix_{mode}.db")
            
            db = DictSQLiteV4(db_path, storage_mode=mode, table_mode="prefix")
            users = db.table("users")
            
            users["alice"] = {"name": "Alice", "age": 30}
            assert users["alice"]["name"] == "Alice"
            assert users["alice"]["age"] == 30
            
            db.close()
            
            # Verify persistence
            db2 = DictSQLiteV4(db_path, storage_mode=mode, table_mode="prefix")
            users2 = db2.table("users")
            assert users2["alice"]["name"] == "Alice"
            db2.close()
    
    print("✅ Prefix mode with all storage modes test passed")


def test_separate_mode_all_storage_modes():
    """Test separate mode with all storage modes"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    storage_modes = ["pickle", "json", "jsonb"]
    
    for mode in storage_modes:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_separate_{mode}.db")
            
            db = DictSQLiteV4(db_path, storage_mode=mode, table_mode="separate")
            users = db.table("users")
            
            users["alice"] = {"name": "Alice", "age": 30}
            assert users["alice"]["name"] == "Alice"
            assert users["alice"]["age"] == 30
            
            db.close()
            
            # Verify persistence
            db2 = DictSQLiteV4(db_path, storage_mode=mode, table_mode="separate")
            users2 = db2.table("users")
            assert users2["alice"]["name"] == "Alice"
            db2.close()
    
    print("✅ Separate mode with all storage modes test passed")


def test_prefix_mode_all_persist_modes():
    """Test prefix mode with all persistence modes"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    persist_modes = ["memory", "lazy", "writethrough"]
    
    for mode in persist_modes:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_prefix_{mode}.db")
            
            db = DictSQLiteV4(db_path, storage_mode="jsonb", 
                            persist_mode=mode, table_mode="prefix")
            users = db.table("users")
            
            users["alice"] = {"name": "Alice"}
            assert users["alice"]["name"] == "Alice"
            
            if mode != "memory":
                db.flush()
            db.close()
    
    print("✅ Prefix mode with all persist modes test passed")


def test_separate_mode_all_persist_modes():
    """Test separate mode with all persistence modes"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    persist_modes = ["memory", "lazy", "writethrough"]
    
    for mode in persist_modes:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_separate_{mode}.db")
            
            db = DictSQLiteV4(db_path, storage_mode="jsonb", 
                            persist_mode=mode, table_mode="separate")
            users = db.table("users")
            
            users["alice"] = {"name": "Alice"}
            assert users["alice"]["name"] == "Alice"
            
            if mode != "memory":
                db.flush()
            db.close()
    
    print("✅ Separate mode with all persist modes test passed")


def test_prefix_mode_many_tables():
    """Test prefix mode with many tables"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_many_tables.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="prefix")
        
        # Create 20 tables
        for i in range(20):
            table = db.table(f"table_{i}")
            table[f"key_{i}"] = {"value": i}
        
        # Verify all tables
        for i in range(20):
            table = db.table(f"table_{i}")
            assert table[f"key_{i}"]["value"] == i
        
        db.close()
        print("✅ Prefix mode many tables test passed")


def test_separate_mode_many_tables():
    """Test separate mode with many tables"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_many_tables.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="separate")
        
        # Create 20 tables
        for i in range(20):
            table = db.table(f"table_{i}")
            table[f"key_{i}"] = {"value": i}
        
        # Verify all tables
        for i in range(20):
            table = db.table(f"table_{i}")
            assert table[f"key_{i}"]["value"] == i
        
        db.close()
        print("✅ Separate mode many tables test passed")


def test_prefix_mode_table_special_characters():
    """Test prefix mode with special characters in table names"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_special.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="prefix")
        
        # Use various table names
        table_names = ["users", "user_data", "users2", "my_table_123"]
        
        for name in table_names:
            table = db.table(name)
            table["key1"] = {"test": True}
            assert table["key1"]["test"] is True
        
        db.close()
        print("✅ Prefix mode special characters test passed")


def test_separate_mode_table_special_characters():
    """Test separate mode with special characters in table names"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_special.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="separate")
        
        # Use various table names (sanitized automatically)
        table_names = ["users", "user_data", "users2", "my_table_123"]
        
        for name in table_names:
            table = db.table(name)
            table["key1"] = {"test": True}
            assert table["key1"]["test"] is True
        
        db.close()
        print("✅ Separate mode special characters test passed")


def test_prefix_mode_large_data():
    """Test prefix mode with large data"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_large.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="prefix")
        users = db.table("users")
        
        # Add large data
        large_data = {"items": list(range(1000)), "nested": {"deep": {"value": "x" * 10000}}}
        users["large"] = large_data
        
        result = users["large"]
        assert len(result["items"]) == 1000
        assert len(result["nested"]["deep"]["value"]) == 10000
        
        db.close()
        print("✅ Prefix mode large data test passed")


def test_separate_mode_large_data():
    """Test separate mode with large data"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_large.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="separate")
        users = db.table("users")
        
        # Add large data
        large_data = {"items": list(range(1000)), "nested": {"deep": {"value": "x" * 10000}}}
        users["large"] = large_data
        
        result = users["large"]
        assert len(result["items"]) == 1000
        assert len(result["nested"]["deep"]["value"]) == 10000
        
        db.close()
        print("✅ Separate mode large data test passed")


def test_prefix_mode_update_operations():
    """Test prefix mode update operations"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_update.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="prefix")
        users = db.table("users")
        
        # Create
        users["alice"] = {"name": "Alice", "age": 30}
        assert users["alice"]["age"] == 30
        
        # Update
        users["alice"] = {"name": "Alice", "age": 31}
        assert users["alice"]["age"] == 31
        
        # Delete
        del users["alice"]
        assert "alice" not in users
        
        db.close()
        print("✅ Prefix mode update operations test passed")


def test_separate_mode_update_operations():
    """Test separate mode update operations"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_update.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="separate")
        users = db.table("users")
        
        # Create
        users["alice"] = {"name": "Alice", "age": 30}
        assert users["alice"]["age"] == 30
        
        # Update
        users["alice"] = {"name": "Alice", "age": 31}
        assert users["alice"]["age"] == 31
        
        # Delete
        del users["alice"]
        assert "alice" not in users
        
        db.close()
        print("✅ Separate mode update operations test passed")


def test_async_prefix_mode_comprehensive():
    """Test async operations with prefix mode comprehensively"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_prefix.db")
        
        db = AsyncDictSQLite(
            db_path, storage_mode="jsonb", table_mode="prefix"
        )
        
        users = db.table("users")
        products = db.table("products")
        
        # Add data to multiple tables
        users["user1"] = {"name": "Alice"}
        users["user2"] = {"name": "Bob"}
        products["prod1"] = {"name": "Laptop"}
        
        # Verify
        assert users["user1"]["name"] == "Alice"
        assert users["user2"]["name"] == "Bob"
        assert products["prod1"]["name"] == "Laptop"
        
        # Test keys
        assert len(users.keys()) == 2
        assert len(products.keys()) == 1
        
        db.close()
        print("✅ Async prefix mode comprehensive test passed")


def test_async_separate_mode_comprehensive():
    """Test async operations with separate mode comprehensively"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_separate_comp.db")
        
        db = AsyncDictSQLite(
            db_path, storage_mode="jsonb", table_mode="separate"
        )
        
        users = db.table("users")
        products = db.table("products")
        
        # Add data to multiple tables
        users["user1"] = {"name": "Alice"}
        users["user2"] = {"name": "Bob"}
        products["prod1"] = {"name": "Laptop"}
        
        # Verify
        assert users["user1"]["name"] == "Alice"
        assert users["user2"]["name"] == "Bob"
        assert products["prod1"]["name"] == "Laptop"
        
        # Test keys
        assert len(users.keys()) == 2
        assert len(products.keys()) == 1
        
        db.close()
        print("✅ Async separate mode comprehensive test passed")


def test_prefix_mode_table_items_values():
    """Test table items and values methods in prefix mode"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_prefix_items.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="prefix")
        users = db.table("users")
        
        users["alice"] = {"name": "Alice"}
        users["bob"] = {"name": "Bob"}
        
        # Test keys
        keys = list(users.keys())
        assert "alice" in keys
        assert "bob" in keys
        
        # Test values
        values = list(users.values())
        assert len(values) == 2
        
        # Test items
        items = list(users.items())
        assert len(items) == 2
        
        db.close()
        print("✅ Prefix mode items/values test passed")


def test_separate_mode_table_items_values():
    """Test table items and values methods in separate mode"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_separate_items.db")
        
        db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode="separate")
        users = db.table("users")
        
        users["alice"] = {"name": "Alice"}
        users["bob"] = {"name": "Bob"}
        
        # Test keys
        keys = list(users.keys())
        assert "alice" in keys
        assert "bob" in keys
        
        # Test values
        values = list(users.values())
        assert len(values) == 2
        
        # Test items
        items = list(users.items())
        assert len(items) == 2
        
        db.close()
        print("✅ Separate mode items/values test passed")


def test_prefix_mode_default_behavior():
    """Test that prefix mode is the default"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_default_mode.db")
        
        # Create without specifying table_mode (should default to prefix)
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        users = db.table("users")
        
        users["alice"] = {"name": "Alice"}
        assert users["alice"]["name"] == "Alice"
        
        db.close()
        print("✅ Prefix mode default behavior test passed")


def test_mode_backward_compatibility():
    """Test backward compatibility - existing code should work unchanged"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_backward_compat.db")
        
        # This is how users currently use the library (without table_mode)
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        # Direct dict operations
        db["key1"] = {"value": 1}
        assert db["key1"]["value"] == 1
        
        # Table operations
        users = db.table("users")
        users["alice"] = {"name": "Alice"}
        assert users["alice"]["name"] == "Alice"
        
        # All existing operations should work
        assert "key1" in db
        assert len(db) >= 1
        
        db.close()
        print("✅ Backward compatibility test passed")


# =============================================================================
# Comprehensive dict operation tests for TableProxy
# =============================================================================

def test_table_proxy_get_method():
    """Test TableProxy.get() method with default values"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_get_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Test .get() with existing key
            users["alice"] = {"name": "Alice", "age": 30}
            result = users.get("alice")
            assert result["name"] == "Alice"
            assert result["age"] == 30
            
            # Test .get() with non-existing key (returns None)
            result = users.get("nonexistent")
            assert result is None
            
            # Test .get() with default value
            result = users.get("nonexistent", {"default": True})
            assert result["default"] is True
            
            db.close()
    print("✅ TableProxy.get() test passed")


def test_table_proxy_pop_method():
    """Test TableProxy.pop() method"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_pop_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Add data
            users["alice"] = {"name": "Alice"}
            users["bob"] = {"name": "Bob"}
            assert len(users) == 2
            
            # Test .pop() with existing key
            result = users.pop("alice")
            assert result["name"] == "Alice"
            assert "alice" not in users
            assert len(users) == 1
            
            # Test .pop() with non-existing key and default
            result = users.pop("nonexistent", {"default": True})
            assert result["default"] is True
            
            # Test .pop() with non-existing key and no default (raises KeyError)
            with pytest.raises(KeyError):
                users.pop("nonexistent")
            
            db.close()
    print("✅ TableProxy.pop() test passed")


def test_table_proxy_setdefault_method():
    """Test TableProxy.setdefault() method"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_setdefault_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Test .setdefault() with non-existing key
            result = users.setdefault("alice", {"name": "Alice", "age": 30})
            assert result["name"] == "Alice"
            assert "alice" in users
            assert users["alice"]["age"] == 30
            
            # Test .setdefault() with existing key (should not change)
            result = users.setdefault("alice", {"name": "New Name", "age": 99})
            assert result["name"] == "Alice"  # Original value
            assert result["age"] == 30  # Original value
            
            # Test .setdefault() with None default
            result = users.setdefault("bob")
            assert result is None
            assert "bob" in users
            
            db.close()
    print("✅ TableProxy.setdefault() test passed")


def test_table_proxy_update_method():
    """Test TableProxy.update() method"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_update_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Test .update() with dict
            users.update({
                "alice": {"name": "Alice", "age": 30},
                "bob": {"name": "Bob", "age": 25}
            })
            
            assert len(users) == 2
            assert users["alice"]["name"] == "Alice"
            assert users["bob"]["age"] == 25
            
            # Test .update() overwrites existing keys
            users.update({"alice": {"name": "Alice Updated", "age": 31}})
            assert users["alice"]["name"] == "Alice Updated"
            assert users["alice"]["age"] == 31
            
            db.close()
    print("✅ TableProxy.update() test passed")


def test_table_proxy_iter_method():
    """Test TableProxy iteration (for key in table)"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_iter_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Add data
            users["alice"] = {"name": "Alice"}
            users["bob"] = {"name": "Bob"}
            users["charlie"] = {"name": "Charlie"}
            
            # Test iteration
            keys = []
            for key in users:
                keys.append(key)
            
            assert len(keys) == 3
            assert "alice" in keys
            assert "bob" in keys
            assert "charlie" in keys
            
            # Test list() on table
            key_list = list(users)
            assert len(key_list) == 3
            
            db.close()
    print("✅ TableProxy iteration test passed")


def test_table_proxy_delitem():
    """Test TableProxy del table[key]"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_delitem_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Add data
            users["alice"] = {"name": "Alice"}
            users["bob"] = {"name": "Bob"}
            assert len(users) == 2
            
            # Delete
            del users["alice"]
            assert "alice" not in users
            assert len(users) == 1
            
            # Delete non-existing key should not raise error (behavior may vary)
            # Just verify bob is still there
            assert "bob" in users
            
            db.close()
    print("✅ TableProxy del test passed")


def test_async_table_proxy_all_dict_ops():
    """Test AsyncTableProxy with all dict operations"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_async_all_{table_mode}.db")
            db = AsyncDictSQLite(db_path, storage_mode="jsonb", table_mode=table_mode)
            users = db.table("users")
            
            # Test __setitem__ and __getitem__
            users["alice"] = {"name": "Alice", "age": 30}
            assert users["alice"]["name"] == "Alice"
            
            # Test __contains__
            assert "alice" in users
            assert "nonexistent" not in users
            
            # Test __len__
            users["bob"] = {"name": "Bob"}
            assert len(users) == 2
            
            # Test keys()
            keys = users.keys()
            assert "alice" in keys
            assert "bob" in keys
            
            # Test values()
            values = users.values()
            assert len(values) == 2
            
            # Test items()
            items = users.items()
            assert len(items) == 2
            
            # Test get()
            assert users.get("alice")["name"] == "Alice"
            assert users.get("nonexistent") is None
            assert users.get("nonexistent", {"default": True})["default"] is True
            
            # Test pop()
            result = users.pop("bob")
            assert result["name"] == "Bob"
            assert "bob" not in users
            
            # Test setdefault()
            result = users.setdefault("charlie", {"name": "Charlie"})
            assert result["name"] == "Charlie"
            assert "charlie" in users
            
            # Test update()
            users.update({"dave": {"name": "Dave"}})
            assert users["dave"]["name"] == "Dave"
            
            # Test iteration
            keys = list(users)
            assert "alice" in keys
            assert "charlie" in keys
            assert "dave" in keys
            
            # Test __delitem__
            del users["dave"]
            assert "dave" not in users
            
            # Test clear()
            users.clear()
            assert len(users) == 0
            
            db.close()
    print("✅ AsyncTableProxy all dict ops test passed")


def test_table_proxy_bytes_mode():
    """Test TableProxy dict operations with bytes storage mode"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for table_mode in ["prefix", "separate"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_bytes_{table_mode}.db")
            db = DictSQLiteV4(db_path, storage_mode="bytes", table_mode=table_mode)
            data = db.table("data")
            
            # Test with bytes
            data["key1"] = b"value1"
            data["key2"] = b"value2"
            
            assert data["key1"] == b"value1"
            assert data.get("key1") == b"value1"
            assert data.get("nonexistent") is None
            
            result = data.pop("key1")
            assert result == b"value1"
            
            data.setdefault("key3", b"value3")
            assert data["key3"] == b"value3"
            
            data.update({"key4": b"value4", "key5": b"value5"})
            assert len(data) == 4
            
            keys = list(data)
            assert len(keys) == 4
            
            db.close()
    print("✅ TableProxy bytes mode test passed")


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
        test_prefix_mode_with_encryption()
        test_separate_mode_with_encryption()
        test_prefix_mode_all_storage_modes()
        test_separate_mode_all_storage_modes()
        test_prefix_mode_all_persist_modes()
        test_separate_mode_all_persist_modes()
        test_prefix_mode_many_tables()
        test_separate_mode_many_tables()
        test_prefix_mode_table_special_characters()
        test_separate_mode_table_special_characters()
        test_prefix_mode_large_data()
        test_separate_mode_large_data()
        test_prefix_mode_update_operations()
        test_separate_mode_update_operations()
        test_async_prefix_mode_comprehensive()
        test_async_separate_mode_comprehensive()
        test_prefix_mode_table_items_values()
        test_separate_mode_table_items_values()
        test_prefix_mode_default_behavior()
        test_mode_backward_compatibility()
        # New comprehensive dict operation tests
        test_table_proxy_get_method()
        test_table_proxy_pop_method()
        test_table_proxy_setdefault_method()
        test_table_proxy_update_method()
        test_table_proxy_iter_method()
        test_table_proxy_delitem()
        test_async_table_proxy_all_dict_ops()
        test_table_proxy_bytes_mode()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
