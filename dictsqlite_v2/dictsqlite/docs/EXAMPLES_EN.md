DictSQLite v4 — Examples (English)

Import (two equivalent styles)
-----------------------------
Preferred public API name:

```python
from dictsqlite import DictSQLite
```

If your environment or examples use the implementation name, it is equivalent:

```python
from dictsqlite import DictSQLiteV4 as DictSQLite
```

Basic synchronous usage
-----------------------
```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')
# store a string
db['user:alice'] = 'Alice Smith'
# store a Python object (auto-pickled by default)
db['config'] = {'theme': 'dark', 'version': 2}

print(db['user:alice'])            # -> 'Alice Smith'
print(db.get('notfound', 'n/a'))   # -> 'n/a'

# iterate
for k in db.keys():
    print(k, db[k])

db.close()
```

Encryption example
------------------
```python
from dictsqlite import DictSQLite

# Use encryption_password to enable AES-256-GCM encrypted storage
db = DictSQLite('secure.db', encryption_password='my_password')

db['token'] = 'secret'
print(db.stats()['encryption_enabled'])  # True

db.close()

# reopen and read
db2 = DictSQLite('secure.db', encryption_password='my_password')
print(db2['token'])
db2.close()
```

Bulk insert example
-------------------
```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')
# prepare data
data = {f'record:{i}': f'value_{i}' for i in range(1000)}
# fast bulk insert
db.bulk_insert(data)

print('Inserted', len(list(db.keys())))

# clear
db.clear()
```

Asynchronous example
--------------------
```python
import asyncio
from dictsqlite import AsyncDictSQLite

async def async_demo():
    db = AsyncDictSQLite(':memory:')
    await db.aset('k', {'a': 1})
    v = await db.aget('k')
    print('async get:', v)

asyncio.run(async_demo())
```

Safe Pickle example
-------------------
```python
from dictsqlite import DictSQLite

# enable safe pickle to validate unpickling
db = DictSQLite(':memory:', enable_safe_pickle=True, safe_pickle_allowed_modules=['myapp'])

# If the value cannot be safely unpickled as allowed, an exception will be raised
# when writing or when Rust-side validation runs.

# Getting raw bytes
val = db.get('maybe_bytes')
if isinstance(val, (bytes, bytearray)):
    import pickle
    try:
        obj = pickle.loads(val)
    except Exception:
        # handle raw bytes
        pass

# Table proxy
other = db.table('other_table')
# many of the same APIs are available through the table proxy

# Stats and flush
print(db.stats())
db.flush()

# Close
db.close()
```

Notes
-----
- The examples assume the native extension is built and available. If you see a RuntimeError mentioning the native extension, follow the build instructions in the project root (maturin or supplied scripts).
