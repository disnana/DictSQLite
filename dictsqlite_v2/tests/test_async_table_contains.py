"""
Test AsyncTableProxy __contains__ implementation
"""
import os
import pytest
from .conftest import windows_safe_temp_dir


def test_async_table_contains_basic():
    """Test basic __contains__ functionality for AsyncTableProxy"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_contains.db")
        
        # Create async DB with JSONB mode
        db = AsyncDictSQLite(db_path, storage_mode="jsonb")
        
        # Get table proxy
        users = db.table("users")
        
        # Initially should not contain any keys
        assert "user1" not in users
        assert "user2" not in users
        
        # Add data
        users["user1"] = {"name": "Alice", "age": 30}
        
        # Now should contain user1
        assert "user1" in users
        assert "user2" not in users
        
        # Add another user
        users["user2"] = {"name": "Bob", "age": 25}
        
        # Now should contain both
        assert "user1" in users
        assert "user2" in users
        assert "user3" not in users
        
        db.close()
        print("✅ Async table contains basic test passed")


def test_async_table_contains_with_different_storage_modes():
    """Test __contains__ with different storage modes"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    for storage_mode in ["pickle", "json", "jsonb"]:
        with windows_safe_temp_dir() as tmpdir:
            db_path = os.path.join(tmpdir, f"test_contains_{storage_mode}.db")
            
            db = AsyncDictSQLite(db_path, storage_mode=storage_mode)
            products = db.table("products")
            
            # Test contains before adding
            assert "p1" not in products
            
            # Add item
            if storage_mode == "pickle":
                products["p1"] = b"product1"
            else:
                products["p1"] = {"name": "Product1", "price": 100}
            
            # Test contains after adding
            assert "p1" in products
            assert "p2" not in products
            
            db.close()
    
    print(f"✅ Async table contains with different storage modes test passed")


def test_async_table_contains_multiple_tables():
    """Test __contains__ with multiple tables to ensure proper isolation"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_multi_table_contains.db")
        
        db = AsyncDictSQLite(db_path, storage_mode="jsonb")
        
        # Create multiple tables
        users = db.table("users")
        products = db.table("products")
        orders = db.table("orders")
        
        # Add data to different tables
        users["u1"] = {"name": "Alice"}
        products["p1"] = {"name": "Laptop"}
        orders["o1"] = {"user": "u1", "product": "p1"}
        
        # Test isolation - each table should only contain its own keys
        assert "u1" in users
        assert "p1" not in users
        assert "o1" not in users
        
        assert "p1" in products
        assert "u1" not in products
        assert "o1" not in products
        
        assert "o1" in orders
        assert "u1" not in orders
        assert "p1" not in orders
        
        db.close()
        print("✅ Async table contains multiple tables test passed")


if __name__ == "__main__":
    test_async_table_contains_basic()
    test_async_table_contains_with_different_storage_modes()
    test_async_table_contains_multiple_tables()
    print("\n✅ All AsyncTableProxy __contains__ tests passed!")
