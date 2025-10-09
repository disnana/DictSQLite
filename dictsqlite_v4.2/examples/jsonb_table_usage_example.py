"""
Example usage of DictSQLite v4.2 with JSONB mode and table support
"""

# Note: This example requires building the module first with:
# cd /path/to/dictsqlite_v4.2
# maturin develop --release

try:
    from dictsqlite import DictSQLiteV4, AsyncDictSQLite
except ImportError:
    print("❌ Please build dictsqlite_v4 first with: maturin develop --release")
    exit(1)

import os
import tempfile

print("=" * 70)
print("DictSQLite v4.2 - JSONB Mode and Table Support Examples")
print("=" * 70)

# Create temporary directory for examples
tmpdir = tempfile.mkdtemp()
print(f"\nUsing temporary directory: {tmpdir}")

# ============================================================================
# Example 1: JSONB Mode (Binary JSON with MessagePack)
# ============================================================================
print("\n" + "=" * 70)
print("Example 1: JSONB Mode (Binary JSON with MessagePack)")
print("=" * 70)

db_jsonb = DictSQLiteV4(
    os.path.join(tmpdir, "example_jsonb.db"),
    storage_mode="jsonb"
)

# Store complex data structures
user_data = {
    "name": "田中太郎",
    "age": 30,
    "email": "tanaka@example.com",
    "hobbies": ["読書", "プログラミング", "旅行"],
    "address": {
        "city": "東京",
        "country": "日本",
        "postal_code": "100-0001"
    },
    "active": True
}

db_jsonb["user:tanaka"] = user_data
print("\n✓ Stored user data in JSONB format")

# Retrieve and display
retrieved = db_jsonb["user:tanaka"]
print(f"\n✓ Retrieved data:")
print(f"  Name: {retrieved['name']}")
print(f"  Age: {retrieved['age']}")
print(f"  Hobbies: {', '.join(retrieved['hobbies'])}")
print(f"  City: {retrieved['address']['city']}")

db_jsonb.close()

# ============================================================================
# Example 2: JSON Mode (Text JSON)
# ============================================================================
print("\n" + "=" * 70)
print("Example 2: JSON Mode (Human-readable Text JSON)")
print("=" * 70)

db_json = DictSQLiteV4(
    os.path.join(tmpdir, "example_json.db"),
    storage_mode="json"
)

config_data = {
    "theme": "dark",
    "language": "ja",
    "notifications": {
        "email": True,
        "push": False,
        "sms": False
    },
    "max_items": 100
}

db_json["app_config"] = config_data
print("\n✓ Stored config in JSON format (human-readable)")

retrieved_config = db_json["app_config"]
print(f"\n✓ Retrieved config:")
print(f"  Theme: {retrieved_config['theme']}")
print(f"  Language: {retrieved_config['language']}")
print(f"  Email notifications: {retrieved_config['notifications']['email']}")

db_json.close()

# ============================================================================
# Example 3: Table Support with JSONB
# ============================================================================
print("\n" + "=" * 70)
print("Example 3: Table Support (Multiple Tables in One DB)")
print("=" * 70)

db = DictSQLiteV4(
    os.path.join(tmpdir, "example_tables.db"),
    storage_mode="jsonb"
)

# Get table proxies
users = db.table("users")
products = db.table("products")
orders = db.table("orders")

# Add users
users["user001"] = {
    "name": "Alice",
    "email": "alice@example.com",
    "role": "admin"
}

users["user002"] = {
    "name": "Bob",
    "email": "bob@example.com",
    "role": "user"
}

print("\n✓ Added 2 users to 'users' table")

# Add products
products["prod001"] = {
    "name": "ノートPC",
    "price": 120000,
    "stock": 5
}

products["prod002"] = {
    "name": "マウス",
    "price": 2500,
    "stock": 50
}

print("✓ Added 2 products to 'products' table")

# Add orders
orders["order001"] = {
    "user_id": "user001",
    "product_id": "prod001",
    "quantity": 1,
    "total": 120000
}

print("✓ Added 1 order to 'orders' table")

# Display data from different tables
print("\n✓ Retrieving data from tables:")
print(f"  User 'user001': {users['user001']['name']} ({users['user001']['role']})")
print(f"  Product 'prod001': {products['prod001']['name']} - ¥{products['prod001']['price']:,}")
print(f"  Order 'order001': User {orders['order001']['user_id']} ordered {orders['order001']['quantity']} items")

# List keys in each table
print("\n✓ Keys in each table:")
print(f"  Users: {users.keys()}")
print(f"  Products: {products.keys()}")
print(f"  Orders: {orders.keys()}")

# Check table sizes
print("\n✓ Table sizes:")
print(f"  Users: {len(users)} entries")
print(f"  Products: {len(products)} entries")
print(f"  Orders: {len(orders)} entries")

# List all tables
print(f"\n✓ All tables in database: {db.tables()}")

db.close()

# ============================================================================
# Example 4: Default Table Name
# ============================================================================
print("\n" + "=" * 70)
print("Example 4: Using Default Table Name")
print("=" * 70)

# Create DB with custom default table name
users_db = DictSQLiteV4(
    os.path.join(tmpdir, "users_only.db"),
    storage_mode="jsonb",
    table_name="users"  # All operations will use "users" table by default
)

# Add data - automatically goes to "users" table
users_db["admin"] = {
    "name": "Administrator",
    "permissions": ["read", "write", "delete"]
}

users_db["guest"] = {
    "name": "Guest User",
    "permissions": ["read"]
}

print("\n✓ Added users to default 'users' table")
print(f"  Admin permissions: {users_db['admin']['permissions']}")
print(f"  Guest permissions: {users_db['guest']['permissions']}")

users_db.close()

# ============================================================================
# Example 5: Async Table Support
# ============================================================================
print("\n" + "=" * 70)
print("Example 5: Async Operations with Table Support")
print("=" * 70)

async_db = AsyncDictSQLite(
    os.path.join(tmpdir, "async_example.db"),
    storage_mode="jsonb"
)

# Get async table proxy
async_users = async_db.table("users")

# Add data
async_users["user1"] = {"name": "Charlie", "status": "active"}
async_users["user2"] = {"name": "Diana", "status": "active"}

print("\n✓ Added users via async table proxy")
print(f"  User1: {async_users['user1']['name']}")
print(f"  User2: {async_users['user2']['name']}")

async_db.close()

# ============================================================================
# Example 6: Comparison of Storage Modes
# ============================================================================
print("\n" + "=" * 70)
print("Example 6: Storage Mode Comparison")
print("=" * 70)

test_data = {
    "id": 123,
    "name": "テストデータ",
    "values": [1, 2, 3, 4, 5],
    "nested": {"key": "value"}
}

print("\n📊 Storage Mode Characteristics:")
print("-" * 70)

# Pickle mode (default)
print("\n1. Pickle Mode (default):")
print("   - Supports: ANY Python object")
print("   - Performance: Fast")
print("   - Size: Medium")
print("   - Readable: No (binary)")
print("   - Use case: General purpose, complex objects")

# JSON mode
print("\n2. JSON Mode:")
print("   - Supports: dict, list, str, int, float, bool, None")
print("   - Performance: Medium")
print("   - Size: Larger (text)")
print("   - Readable: Yes (human-readable text)")
print("   - Use case: Debugging, interoperability, simple data")

# JSONB mode (MessagePack)
print("\n3. JSONB Mode (MessagePack) ★ RECOMMENDED:")
print("   - Supports: dict, list, str, int, float, bool, None")
print("   - Performance: Very Fast (10-20% faster than JSON)")
print("   - Size: Smallest (binary, compact)")
print("   - Readable: No (binary)")
print("   - Use case: High-performance, large datasets, production")

# Bytes mode
print("\n4. Bytes Mode:")
print("   - Supports: Raw bytes only")
print("   - Performance: Fastest (no conversion)")
print("   - Size: As-is")
print("   - Readable: No (raw bytes)")
print("   - Use case: Binary data, custom serialization")

print("\n" + "=" * 70)
print("✅ All examples completed successfully!")
print("=" * 70)

# Cleanup
import shutil
shutil.rmtree(tmpdir)
print(f"\nCleaned up temporary directory: {tmpdir}")
