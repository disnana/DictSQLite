# DictSQLite

`DictSQLite` is a Python class that allows you to treat an SQLite database like a dictionary. It is thread-safe and handles transaction management and database operations via a queue.

## Automatic Conflict Resolution

Automatic conflict resolution is deprecated as it may significantly degrade performance. I spent a lot of time on its implementation and was concerned about it. If you have a better idea, I would like to implement that instead.

Normally, issues won't arise if you call the variable's class like this and use it properly by opening and closing it:

```python
db = dictsqlite.DictSQLite("db_path")
```

However, when accessing and writing to the database from different Python codes simultaneously, automatic conflict resolution might be necessary. That said, since the speed is very fast, the chances of a conflict are very low.

If you're genuinely concerned, I recommend enabling automatic conflict resolution at the cost of performance.

## Class `DictSQLite`

### Constructor

```python
DictSQLite(db_name: str, table_name: str = 'main', schema: bool = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None, password: str = None, publickey_path: str = "./public_keys.pem", privatekey_path: str = "./private_keys.pem", version: int = 1, key_create: bool = False)
```

- **db_name**: The name of the database file.
- **table_name**: The name of the table to use (default: 'main').
- **schema**: The schema of the table (default: `'(key TEXT PRIMARY KEY, value TEXT)'`).
- **conflict_resolver**: Whether the conflict resolution feature is enabled.
- **journal_mode**: The journal mode for SQLite.
- **lock_file**: The name of the lock file.
- **password**: The database password.
- **publickey_path**: The path to the public key.
- **privatekey_path**: The path to the private key.
- **version**: The database version.
- **key_create**: The flag to create a key.

### Methods

- `__setitem__(self, key, value)`: Adds or updates data.
- `__getitem__(self, key)`: Retrieves data.
- `__delitem__(self, key)`: Deletes data.
- `__contains__(self, key)`: Checks if the key exists.
- `__repr__(self)`: Displays the database content in dictionary format.
- `TableProxy(self, db, table_name)`: A table proxy class for version 2.
- `keys(self)`: Retrieves all the keys.
- `begin_transaction(self)`: Starts a transaction.
- `commit_transaction(self)`: Commits a transaction.
- `rollback_transaction(self)`: Rolls back a transaction.
- `switch_table(self, new_table_name, schema=None)`: Switches tables.
- `clear_db(self)`: Clears the entire database.
- `clear_table(self, table_name=None)`: Clears data from the current table or a specified table.
- `tables(self)`: Retrieves all table names.
- `close(self)`: Closes the database connection.

## Usage

The following code snippet demonstrates the basic usage of the `DictSQLite` (Version 2) class:

```python
import dictsqlite

def test_dict_sqlite_v2():
    # Create an instance of DictSQLite with version=2
    db = dictsqlite.DictSQLite("sample_v2.db", version=2, journal_mode="WAL")
    
    # Clear the database
    db.clear_db()
    print("Initial state:", db)
    
    # Create tables
    db.create_table("users")
    db.create_table("products")
    print("After creating tables:", db)
    
    # Add data to the users table
    db["users"]["user1"] = {"name": "Taro Tanaka", "age": 30, "email": "tanaka@example.com"}
    db["users"]["user2"] = {"name": "Hanako Sato", "age": 25, "email": "sato@example.com"}
    print("After adding user data:", db)
    
    # Add data to the products table
    db["products"]["product1"] = {"name": "Laptop", "price": 80000, "stock": 10}
    db["products"]["product2"] = {"name": "Smartphone", "price": 60000, "stock": 20}
    print("After adding product data:", db)
    
    # Display specific table contents
    print("Users table contents:", db["users"])
    print("Products table contents:", db["products"])
    
    # Retrieve specific data
    print("User1 info:", db["users"]["user1"])
    print("Product2 info:", db["products"]["product2"])
    
    # Check if a key exists
    print("Does user1 exist:", "user1" in db["users"])
    print("Does user3 exist:", "user3" in db["users"])
    
    # Delete data
    del db["users"]["user2"]
    print("After deleting user2 from users table:", db["users"])
    
    # Get all keys in a table
    print("All keys in users table:", db.keys("users"))
    
    # Using transactions
    db.begin_transaction()
    try:
        db["users"]["user3"] = {"name": "Jiro Yamada", "age": 40, "email": "yamada@example.com"}
        db["products"]["product3"] = {"name": "Tablet", "price": 40000, "stock": 15}
        print("State during transaction:", db)
        db.commit_transaction()
        print("After commit:", db)
    except Exception as e:
        db.rollback_transaction()
        print(f"Error occurred: {e}")
    
    # Demo of rollback
    db.begin_transaction()
    db["users"]["user4"] = {"name": "Ichiro Suzuki", "age": 35, "email": "suzuki@example.com"}
    print("Before rollback:", db["users"])
    db.rollback_transaction()
    print("After rollback:", db["users"])
    
    # Create and switch to a new table
    db.create_table("orders")
    db["orders"]["order1"] = {"user_id": "user1", "product_id": "product1", "quantity": 1}
    print("After creating orders table:", db["orders"])
    
    # Get a list of all tables in the database
    print("Table list:", db.tables())
    
    # Clear a specific table
    db.clear_table("products")
    print("After clearing products table:", db["products"])
    
    # Clear the entire database
    db.clear_db()
    print("After clearing entire database:", db)
    
    # Close the database connection
    db.close()
    
    # Using context manager
    with dictsqlite.DictSQLite("sample_v2.db", version=2) as context_db:
        context_db.create_table("context_table")
        context_db["context_table"]["key1"] = "value1"
        print("Data in context:", context_db)

# Run the test
test_dict_sqlite_v2()
```

The following code snippet demonstrates the basic usage of the `DictSQLite` (Version 1) class:

```python
import dictsqlite

def test_dict_sqlite():
    # Create an instance of DictSQLite
    db = dictsqlite.DictSQLite("sample.db", journal_mode="WAL")
    
    # Add data
    db['name'] = 'Alice'
    db['age'] = '30'
    print("After adding data:", db)

    # Retrieve data
    print("Name:", db['name'])
    print("Age:", db['age'])

    # Check if a key exists
    print("Does name key exist:", 'name' in db)
    print("Does address key exist:", 'address' in db)

    # Delete data
    del db['age']
    print("After deleting data:", db)

    # Get all keys
    print("All keys:", db.keys())

    # Using transactions
    db.begin_transaction()
    db['transaction_key'] = 'transaction_value'
    print("State during transaction:", db)
    db.rollback_transaction()  # Rollback and cancel the changes
    print("After rollback:", db)

    # Retry transaction and commit
    db.begin_transaction()
    db['transaction_key'] = 'transaction_value'
    print("State during transaction:", db)
    db.commit_transaction()  # Commit and save the changes
    print("After commit:", db)

    # Switch tables
    db.create_table('new_table')
    db.switch_table('new_table')
    db['another_key'] = 'another_value'
    print("Data in new table:", db)
    print("Table list:", db.tables())

    # Clear the entire database
    db.clear_db()
    print("After clearing the entire database:", db)
    db.clear_table()
    print("After clearing the current table:", db)

    # Clear specific table data
    db.switch_table('new_table')
    db['context_key'] = 'context_value'
    db.clear_table('new_table')
    print("After clearing data in specified table:", db)

    # Close the database connection
    db.close()

    # Using context manager
    with dictsqlite.DictSQLite("sample.db") as context_db:
        context_db['context_key'] = 'context_value'
        print("Data in context:", context_db)

# Run the test
test_dict_sqlite()
```