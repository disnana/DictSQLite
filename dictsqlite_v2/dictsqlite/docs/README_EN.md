# DictSQLite v2 — Quick Start (English)

## Overview

DictSQLite v2 is a high-performance library that provides a dict-like Python API backed by a Rust-powered native storage engine.

**Key Features:**
- **Ultra-fast**: 100M+ ops/sec with lock-free concurrent hashmap
- **AES-256-GCM Encryption**: Optional data encryption
- **Safe Pickle Validation**: Secure object serialization
- **SQL Injection Protection**: Parameterized queries for safety
- **v1.8.8 API Compatible**: Maintains compatibility with existing code

## Versioning

- **Package Version**: v2.0.7 (PyPI release version)
- **Internal Implementation**: v4 (internal architecture)

Internally, the implementation is labeled "v4", but this refers to the internal architecture. The package is published on PyPI as `dictsqlite 2.x.x`.

## Installation

```bash
pip install dictsqlite
```

## Import

**Recommended standard import:**

```python
from dictsqlite import DictSQLite
```

**Using internal implementation name (backward compatibility):**

```python
from dictsqlite import DictSQLiteV4  # Alias for DictSQLite
```

> **Note**: `DictSQLiteV4` is the internal implementation name. For new code, we recommend using `DictSQLite`.

## Basic Usage (Synchronous)

### Simple Example

```python
from dictsqlite import DictSQLite

# Initialize with memory database
db = DictSQLite(':memory:')

# Store strings
db['user:alice'] = 'Alice Smith'

# Store Python objects (automatically pickled)
db['config'] = {'theme': 'dark', 'version': 2}

# Retrieve values
print(db['user:alice'])                 # -> 'Alice Smith'
print(db.get('missing', 'default'))     # -> 'default'

# Check key existence
if 'user:alice' in db:
    print("User exists!")

# Iteration
for key in db.keys():
    print(key, db[key])

# Close
db.close()
```

### Context Manager

```python
from dictsqlite import DictSQLite

with DictSQLite('app.db') as db:
    db['a'] = 1
    db['b'] = {'nested': 'data'}
    print(db['a'])
# Automatically flushed and closed
```

## Asynchronous (Async/Await)

The `AsyncDictSQLite` class provides true asyncio support.

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # Awaitable methods
    await db.aset('key', 'value')
    value = await db.aget('key')
    print(value)  # -> 'value'
    
    # Batch operations
    await db.abatch_set([('key1', 'val1'), ('key2', 'val2')])
    values = await db.abatch_get(['key1', 'key2'])
    
    # Existence check
    exists = await db.acontains('key1')
    
    # Delete
    await db.adelete('key1')
    
    # Flush and close
    await db.aflush()
    await db.aclose()

asyncio.run(main())
```

### Async Context Manager

```python
async def main():
    async with AsyncDictSQLite('async.db') as db:
        await db.aset('test', 123)
        value = await db.aget('test')
```

### Awaitable Methods

- `await aget(key)` - Async get
- `await aset(key, value)` - Async set
- `await abatch_get(keys)` - Batch get
- `await abatch_set(items)` - Batch set
- `await acontains(key)` - Existence check
- `await adelete(key)` - Delete
- `await aflush()` - Flush
- `await aclose()` - Close

## Constructor Options

### DictSQLite

```python
DictSQLite(
    db_path,                            # str: Database file path or ':memory:'
    hot_capacity=1_000_000,             # int: Max entries in hot tier
    enable_async=True,                  # bool: Enable async background flush
    persist_mode="writethrough",        # str: Persistence mode
    storage_mode="pickle",              # str: Storage mode
    table_name="main",                  # str: Default table name
    encryption_password=None,           # str|None: AES-256-GCM encryption password
    enable_safe_pickle=False,           # bool: Enable Safe Pickle validation
    safe_pickle_allowed_modules=None,   # list|None: Safe Pickle allowed modules
    buffer_size=100,                    # int: Async buffer size
    encoding='utf-8',                   # str: Character encoding
    table_mode="prefix",                # str: Table isolation mode
    pool_size=20                        # int: SQLite connection pool size
)
```

#### Parameter Details

- **db_path**: Path to database file. Use `:memory:` for in-memory database.
- **hot_capacity**: Maximum number of entries in hot in-memory cache (default: 1,000,000)
- **enable_async**: Enable background async flush worker (default: True)
- **persist_mode**: Persistence mode
  - `"memory"`: Memory only, no persistence
  - `"lazy"`: Persist on flush/close
  - `"writethrough"`: Immediate persistence (default)
- **storage_mode**: Storage mode
  - `"pickle"`: Python pickle (default)
  - `"jsonb"`: PostgreSQL-compatible JSONB
  - `"json"`: Standard JSON
  - `"bytes"`: Binary data
- **table_name**: Table name to use (default: `"main"`)
- **encryption_password**: Encryption password (None to disable)
- **enable_safe_pickle**: Enable Safe Pickle validation (default: False)
- **safe_pickle_allowed_modules**: List of allowed module prefixes (e.g., `["myapp", "mylib"]`)
- **buffer_size**: Async buffer size (default: 100, automatically 1 for writethrough mode)
- **encoding**: String encoding (default: `'utf-8'`)
- **table_mode**: Table isolation mode
  - `"prefix"`: Key prefix isolation (default)
  - `"separate"`: Separate SQLite tables for complete isolation
- **pool_size**: SQLite connection pool size (default: 20)

### AsyncDictSQLite

```python
AsyncDictSQLite(
    db_path,                        # str: Database file path or ':memory:'
    capacity=1_000_000,             # int: Max cache entries
    persist_mode="lazy",            # str: Persistence mode
    storage_mode="pickle",          # str: Storage mode
    table_name="main",              # str: Default table name
    buffer_size=100,                # int: Write buffer size
    table_mode="prefix"             # str: Table isolation mode
)
```

## Storage Modes

### Pickle Mode (Default)

Automatically serializes/deserializes most Python objects.

```python
db = DictSQLite(':memory:', storage_mode="pickle")
db['data'] = {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
print(db['data'])  # -> {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
```

### JSONB Mode

PostgreSQL-compatible JSONB format. Suitable for JSON-compatible data.

```python
db = DictSQLite(':memory:', storage_mode="jsonb")
db['data'] = {'key': 'value', 'items': [1, 2, 3]}
```

### JSON Mode

Standard JSON serialization.

```python
db = DictSQLite(':memory:', storage_mode="json")
db['data'] = {'key': 'value'}
```

### Bytes Mode

Store binary data as-is.

```python
db = DictSQLite(':memory:', storage_mode="bytes")
db['data'] = b'binary data'
```

## Persistence Modes

### Memory Mode

Memory only, no persistence. Fast but data is lost.

```python
db = DictSQLite('temp.db', persist_mode="memory")
```

### Lazy Mode

Persist on flush or close.

```python
db = DictSQLite('data.db', persist_mode="lazy")
db['key'] = 'value'
db.flush()  # Persist here
```

### Writethrough Mode (Default)

Immediate persistence. Highest data durability.

```python
db = DictSQLite('data.db', persist_mode="writethrough")
db['key'] = 'value'  # Persisted immediately
```

## Encryption

Protect data using AES-256-GCM encryption.

```python
from dictsqlite import DictSQLite

# Enable encryption
db = DictSQLite('secure.db', encryption_password='my_secret_password')

db['secret_token'] = 'sensitive_data'
print(db.stats()['encryption_enabled'])  # -> True

db.close()

# Reopen (requires same password)
db2 = DictSQLite('secure.db', encryption_password='my_secret_password')
print(db2['secret_token'])  # -> 'sensitive_data'
db2.close()
```

## Safe Pickle

Use Safe Pickle to safely unpickle untrusted data.

```python
from dictsqlite import DictSQLite

# Enable Safe Pickle
db = DictSQLite(
    ':memory:', 
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "mylib"]
)

# Only objects from allowed modules can be stored
db['data'] = {'safe': 'data'}
```

## Table Functionality

Use multiple tables (namespaces) to separate data.

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# Main table
db['key1'] = 'value1'

# Use different tables
users = db.table('users')
users['alice'] = {'name': 'Alice', 'age': 30}
users['bob'] = {'name': 'Bob', 'age': 25}

settings = db.table('settings')
settings['theme'] = 'dark'

# Each table is independent
print(list(db.keys()))          # -> ['key1']
print(list(users.keys()))       # -> ['alice', 'bob']
print(list(settings.keys()))    # -> ['theme']
```

### Table Modes

- **prefix**: Key prefix isolation (fast, default)
- **separate**: Separate SQLite tables for complete isolation

```python
db = DictSQLite(':memory:', table_mode="separate")
```

## Bulk Operations

Efficiently insert large amounts of data.

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# Bulk insert from dict
data = {f'key{i}': f'value{i}' for i in range(1000)}
db.bulk_insert(data)

# Bulk insert from list
items = [(f'key{i}', f'value{i}') for i in range(1000)]
db.bulk_insert(items)
```

## Other Useful Methods

### Dictionary Methods

```python
# Get all keys
keys = db.keys()

# Get all values
values = db.values()

# Get key-value pairs
items = db.items()

# Get with default
value = db.get('key', 'default')

# Set default
db.setdefault('key', 'default_value')

# Pop (get and delete)
value = db.pop('key')
value = db.pop('key', 'default')  # Avoid KeyError

# Update
db.update({'key1': 'val1', 'key2': 'val2'})
db.update(key3='val3', key4='val4')

# Clear all
db.clear()

# Length
length = len(db)

# Iteration
for key in db:
    print(key, db[key])
```

### Statistics

```python
stats = db.stats()
print(stats)
# Example: {
#     'hot_tier_size': 1000,
#     'encryption_enabled': False,
#     'persist_mode': 'writethrough',
#     'storage_mode': 'pickle',
#     ...
# }
```

### Flush and Close

```python
# Flush hot tier to storage
db.flush()

# Close database (automatically flushes)
db.close()
```

## Migration from v1.8.8

### Key Changes

1. **Encryption Parameter Name Change**
   ```python
   # v1.8.8
   db = DictSQLite('db.db', password='secret')
   
   # v2.x.x
   db = DictSQLite('db.db', encryption_password='secret')
   ```

2. **Improved Default Behavior**
   - Automated pickle mode serialization
   - Faster performance
   - Improved error handling

3. **New Features**
   - Safe Pickle validation
   - Table modes (prefix/separate)
   - Adjustable connection pool size
   - Async awaitable API

See [MIGRATION_FROM_1.8.8_EN.md](MIGRATION_FROM_1.8.8_EN.md) for details.

## Troubleshooting

### Native Extension Not Found

```
RuntimeError: DictSQLite native extension not available.
```

**Solution:**

Build required in development environment:

```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

### Slow Performance

**Diagnosis:**

```python
stats = db.stats()
print(f"Hot tier size: {stats['hot_tier_size']}")
```

**Solutions:**

1. Increase `hot_capacity` (if memory allows)
2. Change to `persist_mode="lazy"` (if immediate persistence not required)
3. Increase `pool_size` (for high concurrent access)

## References

- [Examples (Japanese)](EXAMPLES_JP.md)
- [Examples (English)](EXAMPLES_EN.md)
- [Migration Guide (Japanese)](MIGRATION_FROM_1.8.8_JP.md)
- [Migration Guide (English)](MIGRATION_FROM_1.8.8_EN.md)
- [Documentation Index](INDEX.md)

## License

MIT License

## Support

- GitHub Issues: [https://github.com/disnana/DictSQLite](https://github.com/disnana/DictSQLite)
- Email: support@disnana.com
- Discord: [https://discord.gg/KzeHDrgwAz](https://discord.gg/KzeHDrgwAz)

