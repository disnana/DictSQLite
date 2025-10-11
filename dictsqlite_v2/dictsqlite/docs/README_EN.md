DictSQLite v4 — Quick Start (English)

Overview
--------
DictSQLite exposes a dict-like Python API backed by a high-performance native store. The package provides both synchronous and asynchronous variants. It aims to be backwards-compatible with earlier DictSQLite versions while adding performance, encryption, and safety features.

Note about versioning
---------------------
This package contains an internal implementation version labeled "v4". That is an internal versioning detail — when releasing this package it is published as version "v2". In documentation and examples you may see `DictSQLiteV4`; the "V4" suffix is an implementation name and is optional. The recommended public import is:

```python
from dictsqlite import DictSQLite
```

If you encounter examples that mention `DictSQLiteV4`, treat it as an implementation name; you can import it directly if present, or simply use the public `DictSQLite` exported by the package. (Avoid relying on `DictSQLiteV4` unless your installation exposes that symbol.)

Quick usage (synchronous)
-------------------------
```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')
# store a string
db['user:alice'] = 'Alice Smith'
# store a Python object (auto-pickled by default)
db['config'] = {'theme': 'dark'}

print(db['user:alice'])                 # -> 'Alice Smith'
print(db.get('missing', 'default'))     # -> 'default'

db.close()
```

Context manager
---------------
```python
from dictsqlite import DictSQLite

with DictSQLite('app.db') as db:
    db['a'] = 1
    print(db['a'])
```

Async usage (awaitable)
-----------------------
```python
# If your installation exposes AsyncDictSQLite, import it. Some examples show
# implementation-level names; the public `DictSQLite` class is the recommended import.
# from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    # Use AsyncDictSQLite if available in your environment
    db = AsyncDictSQLite(':memory:')
    await db.aset('k', 'value')
    v = await db.aget('k')

asyncio.run(main())
```

Important constructor options
-----------------------------
- `db_path` (str): Path to DB file or ':memory:'
- `hot_capacity` (int): Size of in-memory hot tier cache (default: 1_000_000)
- `enable_async` (bool): Enable background async flush worker (True by default)
- `persist_mode` (str): 'memory', 'lazy', or 'writethrough'
- `storage_mode` (str): 'pickle' (default) or 'jsonb'
- `table_name` (str): Table to use for storage (default 'main')
- `encryption_password` (str|None): AES-256-GCM password; if provided, storage is encrypted
- `enable_safe_pickle` (bool): When True, perform safe pickle validation
- `safe_pickle_allowed_modules` (list): Allowed module prefixes for safe pickle validation
- `buffer_size` (int): Buffer size for async batching
- `encoding` (str): Encoding used to decode bytes to str when appropriate (default 'utf-8')

Serialization behavior
----------------------
- Default `storage_mode` is 'pickle', so most Python objects are automatically serialized/deserialized.
- Strings are preserved and returned as Python `str` when possible.
- If you manually store raw bytes or use `jsonb`, the wrapper may return raw bytes; use `pickle.loads` or `.decode()` as appropriate.

Safe Pickle
-----------
Enable `enable_safe_pickle=True` to activate additional validation on pickled data. You can restrict allowed modules via `safe_pickle_allowed_modules`.

Bulk operations
---------------
- `bulk_insert(items)`: Fast way to insert many items. Accepts a `dict` or iterable of `(key, value)` pairs.

Other useful methods
--------------------
- `keys()`, `values()`, `items()` — iterate the database
- `table(name)` — access a different table/namespace
- `stats()` — return performance and configuration statistics (e.g. `encryption_enabled`, `hot_tier_size`)
- `flush()` — flush hot tier to storage
- `clear()` — remove all entries

Migration notes
---------------
- v1.x used the parameter `password=` for encryption; v4 uses `encryption_password=`. See the migration guide for details.
- Default pickle-mode aims to be compatible with v1.8.8 so most objects should continue to work without manual `pickle.dumps`/`loads`.

Troubleshooting: native extension not found
------------------------------------------
If you get an error about the native extension not being available, build it first. The Python wrapper will raise a RuntimeError pointing to build instructions.

Typical development build (example):
```cmd
cd dictsqlite_v2\dictsqlite
maturin develop --release
```

Further reading
---------------
See `docs/` for migration guides and examples. The docs include English and Japanese README, examples, and detailed migration instructions.
