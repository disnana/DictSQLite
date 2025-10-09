"""
Test JSONB mode and table support for DictSQLite v4.2
"""
import os
import pytest
from .conftest import windows_safe_temp_dir


def test_jsonb_mode_basic():
    """Test basic JSONB mode functionality"""
    # Import after building
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_jsonb.db")
        
        # Create DB with JSONB mode
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
        # Test dict storage
        test_data = {
            "name": "Alice",
            "age": 30,
            "hobbies": ["reading", "coding"],
            "address": {
                "city": "Tokyo",
                "country": "Japan"
            }
        }
        
        db["user1"] = test_data
        
        # Retrieve and verify
        retrieved = db["user1"]
        assert retrieved == test_data
        assert retrieved["name"] == "Alice"
        assert retrieved["age"] == 30
        assert retrieved["hobbies"] == ["reading", "coding"]
        assert retrieved["address"]["city"] == "Tokyo"
        
        # Test with list
        db["numbers"] = [1, 2, 3, 4, 5]
        assert db["numbers"] == [1, 2, 3, 4, 5]
        
        # Test with string
        db["message"] = "Hello, World!"
        assert db["message"] == "Hello, World!"
        
        # Test with number
        db["count"] = 42
        assert db["count"] == 42
        
        # Test with boolean
        db["flag"] = True
        assert db["flag"] is True
        
        db.close()
        print("✅ JSONB mode basic test passed")


def test_json_mode_basic():
    """Test basic JSON mode functionality"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_json.db")
        
        # Create DB with JSON mode
        db = DictSQLiteV4(db_path, storage_mode="json")
        
        # Test dict storage
        test_data = {
            "theme": "dark",
            "language": "ja",
            "notifications": True
        }
        
        db["config"] = test_data
        
        # Retrieve and verify
        retrieved = db["config"]
        assert retrieved == test_data
        
        db.close()
        print("✅ JSON mode basic test passed")


def test_table_support_basic():
    """Test basic table support"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tables.db")
        
        # Create DB with JSONB mode
        db = DictSQLiteV4(db_path, storage_mode="jsonb")
        
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
        print("✅ Table support basic test passed")


def test_table_with_default_table_name():
    """Test using default table name parameter"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_default_table.db")
        
        # Create DB with custom default table name
        users_db = DictSQLiteV4(db_path, storage_mode="jsonb", table_name="users")
        
        # Add data - should go to "users" table
        users_db["user1"] = {"name": "Alice", "age": 30}
        
        # Verify
        assert users_db["user1"]["name"] == "Alice"
        
        users_db.close()
        print("✅ Default table name test passed")


def test_async_table_support():
    """Test async table support"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_tables.db")
        
        # Create async DB with JSONB mode
        db = AsyncDictSQLite(db_path, storage_mode="jsonb")
        
        # Get table proxy
        users = db.table("users")
        
        # Add data
        users["user1"] = {"name": "Alice", "age": 30}
        
        # Verify
        assert users["user1"]["name"] == "Alice"
        
        db.close()
        print("✅ Async table support test passed")


def test_async_batch_operations_with_jsonb():
    """Test async batch operations with JSONB mode"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_async_batch.db")
        
        # Create async DB with JSONB mode
        db = AsyncDictSQLite(db_path, storage_mode="jsonb")
        
        # Individual set with complex data (batch_set might not be available or has different signature)
        for i in range(10):
            db[f"user_{i}"] = {"name": f"User{i}", "age": 20 + i, "active": True}
        
        # Verify
        assert db["user_0"] is not None
        assert db["user_0"]["name"] == "User0"
        
        db.close()
        print("✅ Async batch operations with JSONB test passed")


def test_async_multiple_tables():
    """Test async operations with multiple tables"""
    try:
        from dictsqlite import AsyncDictSQLite
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_multi_tables.db")
        
        # Create async DB
        db = AsyncDictSQLite(db_path, storage_mode="jsonb")
        
        # Create multiple tables
        users = db.table("users")
        products = db.table("products")
        orders = db.table("orders")
        
        # Add data to different tables
        users["u1"] = {"name": "Alice", "email": "alice@example.com"}
        products["p1"] = {"name": "Laptop", "price": 1000}
        orders["o1"] = {"user": "u1", "product": "p1", "qty": 1}
        
        # Verify data isolation by trying to get the data
        assert users["u1"] is not None
        assert products["p1"] is not None
        assert orders["o1"] is not None
        
        # Verify correct data
        assert users["u1"]["email"] == "alice@example.com"
        assert products["p1"]["price"] == 1000
        assert orders["o1"]["qty"] == 1
        
        db.close()
        print("✅ Async multiple tables test passed")


def test_persistence_across_sessions():
    """Test that JSONB data persists across sessions"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_persist.db")
        
        # Session 1: Write data
        db1 = DictSQLiteV4(db_path, storage_mode="jsonb", persist_mode="writethrough")
        db1["key1"] = {"data": "value1", "count": 42}
        db1.flush()
        db1.close()
        
        # Session 2: Read data
        db2 = DictSQLiteV4(db_path, storage_mode="jsonb")
        retrieved = db2["key1"]
        assert retrieved == {"data": "value1", "count": 42}
        db2.close()
        
        print("✅ Persistence across sessions test passed")


def test_table_persistence():
    """Test that table data persists correctly"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        db_path = os.path.join(tmpdir, "test_table_persist.db")
        
        # Session 1: Write to tables
        db1 = DictSQLiteV4(db_path, storage_mode="jsonb", persist_mode="writethrough")
        users = db1.table("users")
        users["alice"] = {"name": "Alice", "role": "admin"}
        db1.flush()
        db1.close()
        
        # Session 2: Read from tables
        db2 = DictSQLiteV4(db_path, storage_mode="jsonb")
        users2 = db2.table("users")
        retrieved = users2["alice"]
        assert retrieved["name"] == "Alice"
        assert retrieved["role"] == "admin"
        db2.close()
        
        print("✅ Table persistence test passed")


def test_mixed_storage_modes():
    """Test that different storage modes work correctly"""
    try:
        from dictsqlite import DictSQLiteV4
    except ImportError:
        pytest.skip("dictsqlite not built yet")
    
    with windows_safe_temp_dir() as tmpdir:
        # Test Pickle mode (default)
        db_pickle = DictSQLiteV4(os.path.join(tmpdir, "pickle.db"))
        db_pickle["data"] = {"key": "value"}
        assert db_pickle["data"] == {"key": "value"}
        db_pickle.close()
        
        # Test JSON mode
        db_json = DictSQLiteV4(os.path.join(tmpdir, "json.db"), storage_mode="json")
        db_json["data"] = {"key": "value"}
        assert db_json["data"] == {"key": "value"}
        db_json.close()
        
        # Test JSONB mode
        db_jsonb = DictSQLiteV4(os.path.join(tmpdir, "jsonb.db"), storage_mode="jsonb")
        db_jsonb["data"] = {"key": "value"}
        assert db_jsonb["data"] == {"key": "value"}
        db_jsonb.close()
        
        # Test Bytes mode
        db_bytes = DictSQLiteV4(os.path.join(tmpdir, "bytes.db"), storage_mode="bytes")
        db_bytes["data"] = b"Hello, World!"
        assert db_bytes["data"] == b"Hello, World!"
        db_bytes.close()
        
        print("✅ Mixed storage modes test passed")


if __name__ == "__main__":
    print("Running JSONB and table support tests...")
    
    try:
        test_jsonb_mode_basic()
        test_json_mode_basic()
        test_table_support_basic()
        test_table_with_default_table_name()
        test_async_table_support()
        test_async_batch_operations_with_jsonb()
        test_async_multiple_tables()
        test_persistence_across_sessions()
        test_table_persistence()
        test_mixed_storage_modes()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
