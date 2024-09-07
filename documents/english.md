# DictSQLite

`DictSQLite` is a Python class that allows you to use an SQLite database as a dictionary. It is thread-safe and handles database operations and transactions through a queue.

## About Automatic Conflict Resolution

Automatic conflict resolution is deprecated due to its potential to significantly degrade performance. Implementing it required considerable time and effort. If a better solution becomes available, it will be considered.

Typically, issues do not arise if you use, open, and close the class instance properly with code like this:

```python
db = dict_sqlite.DictSQLite("db_path")
```

However, if you are accessing and writing to the database simultaneously from different Python code, automatic conflict resolution might be necessary. Nevertheless, due to the high speed of operations, the likelihood of conflicts is very low.

If you have significant concerns about conflicts, we recommend enabling automatic conflict resolution, even at the cost of reduced performance.

## Class `DictSQLite`

### Constructor

```python
DictSQLite(db_name: str, table_name: str = 'main', schema: bool = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None)
```

- **db_name**: Name of the database file
- **table_name**: Name of the table to use (default: 'main')
- **schema**: Table schema (default: `'(key TEXT PRIMARY KEY, value TEXT)'`)
- **conflict_resolver**: Whether to enable conflict resolution
- **journal_mode**: SQLite journal mode
- **lock_file**: Name of the lock file

### Methods

- `__setitem__(self, key, value)`: Add or update data.
- `__getitem__(self, key)`: Retrieve data.
- `__delitem__(self, key)`: Delete data.
- `__contains__(self, key)`: Check if a key exists.
- `__repr__(self)`: Represent the database contents as a dictionary.
- `keys(self)`: Get all keys.
- `begin_transaction(self)`: Begin a transaction.
- `commit_transaction(self)`: Commit a transaction.
- `rollback_transaction(self)`: Rollback a transaction.
- `switch_table(self, new_table_name, schema=None)`: Switch tables.
- `clear_db(self)`: Clear the entire database.
- `clear_table(self, table_name=None)`: Clear data from the current or specified table.
- `tables(self)`: Get a list of all table names.
- `close(self)`: Close the database connection.

## Usage

The following code snippet demonstrates the basic usage of the `DictSQLite` class:

```python
import dict_sqlite

def test_dict_sqlite():
    # Create an instance of DictSQLite
    db = dict_sqlite.DictSQLite("sample.db", journal_mode="WAL")
    
    # Add data
    db['name'] = 'Alice'
    db['age'] = '30'
    print("After adding data:", db)

    # Retrieve data
    print("Name:", db['name'])
    print("Age:", db['age'])

    # Check key existence
    print("Does 'name' key exist:", 'name' in db)
    print("Does 'address' key exist:", 'address' in db)

    # Delete data
    del db['age']
    print("After deleting data:", db)

    # Get all keys
    print("All keys:", db.keys())

    # Use transactions
    db.begin_transaction()
    db['transaction_key'] = 'transaction_value'
    print("During transaction state:", db)
    db.rollback_transaction()  # Rollback to cancel changes
    print("After rollback:", db)

    # Retry transaction and commit
    db.begin_transaction()
    db['transaction_key'] = 'transaction_value'
    print("During transaction state:", db)
    db.commit_transaction()  # Commit to save changes
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
    print("After clearing the current table's data:", db)

    # Clear data in a specific table
    db.switch_table('new_table')
    db['context_key'] = 'context_value'
    db.clear_table('new_table')
    print("After clearing specific table's data:", db)

    # Finally, close the database connection
    db.close()
    # Using as a context manager
    with dict_sqlite.DictSQLite("sample.db") as context_db:
        context_db['context_key'] = 'context_value'
        print("Data inside context manager:", context_db)

# Run the test
test_dict_sqlite()
```
