# DictSQLite

`DictSQLite` is a Python library that provides a dictionary-like interface for an SQLite database. It is designed to be thread-safe, handling transactions and database operations through a background queue.

## How It Works

DictSQLite provides a dictionary-like interface on top of an SQLite database. Understanding how it handles data internally can help you use it more effectively.

### Data Storage and Serialization

When you assign a Python object as a value to a key, DictSQLite does not store the object directly. Instead, it performs the following steps:

1.  **Serialization**: The Python object (e.g., a `dict`, `list`, `set`, or custom object) is serialized into a binary format using Python's `pickle` module.
2.  **Encoding**: The resulting binary data is then encoded into a text string using `Base64`.
3.  **Storage**: This Base64 string is stored in the `value` column of the SQLite table, which is defined as `TEXT` by default.

This process allows you to store almost any Python object in the database. When you retrieve the data, the reverse process occurs: the text is decoded from Base64, and then deserialized with `pickle` to reconstruct the original Python object.

### Table Schema

By default, every table in DictSQLite is created with a simple key-value schema:

```sql
CREATE TABLE table_name (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

-   `key`: A unique `TEXT` string that acts as the primary key.
-   `value`: A `TEXT` column that stores the Base64-encoded, pickled Python object.

You can also specify a custom schema when creating a `DictSQLite` instance or when creating a new table. However, to use the dictionary-style access (`db['key'] = value`), the schema **must** include `key` and `value` columns.

### Keys, Indexes, and Data Types

-   **Primary Key**: The `key` column serves as the primary key, ensuring fast lookups.
-   **Indexes**: In the default schema, the only index is on the primary key. If you need custom indexes, you must define them as part of a custom schema.
-   **Data Types**: The `key` is typically a string, but can be other types like `INTEGER` if a custom schema is used. The `value` can be any pickle-able Python object. The library also provides special proxy objects, `DBSyncedList` and `DBSyncedSet`, which automatically write back to the database when they are modified.

## Class `DictSQLite`

### Constructor

```python
DictSQLite(db_name: str, table_name: str = 'main', schema: str = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None, password: str = None, publickey_path: str = "./public_keys.pem", privatekey_path: str = "./private_keys.pem", version: int = 1, key_create: bool = False)
```

- **db_name**: The name of the database file.
- **table_name**: The name of the table to use (default: 'main').
- **schema**: The schema of the table. Defaults to `'(key TEXT PRIMARY KEY, value TEXT)'`. You can provide a string with a custom SQL schema for the table. The library will validate the schema before creating the table.
- **conflict_resolver**: Deprecated. This feature may be removed in future versions.
- **journal_mode**: The journal mode for SQLite (e.g., "WAL").
- **lock_file**: The name of the lock file for conflict resolution.
- **password**: The password for encrypting data.
- **publickey_path**: The path to the public key for encryption.
- **privatekey_path**: The path to the private key for encryption.
- **version**: The database version (1 or 2). Version 2 allows managing multiple tables more easily.
- **key_create**: If `True`, new encryption keys will be generated.

### Methods

- `__setitem__(self, key, value)`: Adds or updates data.
- `__getitem__(self, key)`: Retrieves data.
- `__delitem__(self, key)`: Deletes data.
- `__contains__(self, key)`: Checks if the key exists.
- `__repr__(self)`: Displays the database content in dictionary format.
- `keys(self)`: Retrieves all the keys.
- `begin_transaction(self)`: Starts a transaction.
- `commit_transaction(self)`: Commits a transaction.
- `rollback_transaction(self)`: Rolls back a transaction.
- `switch_table(self, new_table_name, schema=None)`: Switches the active table.
- `create_table(self, table_name, schema=None)`: Creates a new table.
- `clear_db(self)`: Clears the entire database by dropping all tables.
- `clear_table(self, table_name=None)`: Clears all data from a table.
- `tables(self)`: Retrieves a list of all table names.
- `close(self)`: Closes the database connection.
- `execute_custom(self, query, params=())`: Executes a custom SQL query.

## Usage

### Basic Usage (v1)

```python
import dictsqlite

# Create an instance of DictSQLite
with dictsqlite.DictSQLite("sample.db", journal_mode="WAL") as db:
    # Add data
    db['name'] = 'Alice'
    db['age'] = 30
    db['items'] = ['book', 'pen']
    print("After adding data:", db)

    # Retrieve data
    print("Name:", db['name'])
    
    # Modify a mutable object
    # The change is not automatically saved
    items = db['items']
    items.append('notebook')
    
    # To save the change, you must reassign it
    db['items'] = items
    print("After modifying items:", db)

    # Check if a key exists
    print("Does 'age' exist:", 'age' in db)

    # Delete data
    del db['age']
    print("After deleting 'age':", db)
```

### Multi-Table Usage (v2)

```python
import dictsqlite

with dictsqlite.DictSQLite("sample_v2.db", version=2, journal_mode="WAL") as db:
    db.clear_db()
    
    # Create tables
    db.create_table("users")
    db.create_table("products")
    
    # Add data to the 'users' table
    users = db["users"]
    users["user1"] = {"name": "Taro Tanaka", "age": 30}
    users["user2"] = {"name": "Hanako Sato", "age": 25}
    
    # Add data to the 'products' table
    products = db["products"]
    products["prod1"] = {"name": "Laptop", "price": 80000}
    
    print("All database contents:", db)
    print("Users table:", db["users"])
    
    # Delete data
    del db["users"]["user2"]
    print("Users table after deletion:", db["users"])
```

### Custom Schema Usage

You can define a custom schema. However, to use the standard dictionary-style access (`db['key'] = value`), the schema must include `key` and `value` columns. This example changes the key's data type to `INTEGER`.

```python
import dictsqlite

# The schema must be a single string containing the column definitions.
custom_schema = '(key INTEGER PRIMARY KEY, value TEXT)'

with dictsqlite.DictSQLite("custom_int.db", schema=custom_schema) as db:
    db.clear_db()
    
    # Now you can use integers as keys
    db[100] = {"product": "Laptop", "stock": 20}
    db[200] = {"product": "Mouse", "stock": 150}

    print("Database content with integer keys:", db)
    print("Value for key 100:", db[100])

    # The keys are retrieved as integers
    print("Keys in the table:", db.keys())
```
