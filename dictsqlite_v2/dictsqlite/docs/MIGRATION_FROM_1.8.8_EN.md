Migration guide: DictSQLite v1.8.8 -> current wrapper (internal 'v4' label) (English)

Purpose
-------
This document helps you migrate code and data written against DictSQLite v1.8.8 to the new current Python wrapper present in this tree. The goal is minimal friction: the current wrapper's defaults aim to be compatible with v1.8.8 when possible (default storage_mode is 'pickle').

Summary of important changes
----------------------------
- Python wrapper exposes `DictSQLite`. Examples that previously showed `DictSQLiteV4` should just `from dictsqlite import DictSQLite`.

    # Recommended (examples used in docs)
    from dictsqlite import DictSQLite

    # If your code (or examples) show DictSQLiteV4, treat it as the same implementation (optional alias):

    ```
    from dictsqlite import DictSQLiteV4 as DictSQLite
    ```

- Constructor parameter rename for encryption:
    - v1.8.8: `password='mypw'`
    - current wrapper: `encryption_password='mypw'`

- Default serialization (storage_mode) is `pickle`. This preserves behavior of storing Python objects without explicit pickle.dumps/loads in many cases.

- Async API changed to provide true awaitable methods on `AsyncDictSQLite`: `aget`, `aset`, `abatch_get`, `abatch_set`. The class also exposes backward-compatible synchronous wrappers `get`, `set`, `batch_get`, `batch_set`.

- The library provides Safe Pickle validation (optional): `enable_safe_pickle=True`, and `safe_pickle_allowed_modules` to restrict allowed module prefixes on unpickling.

- Bulk insert and buffering behavior improved; prefer `bulk_insert` or the async batch APIs for large numbers of items.

Detailed migration steps
------------------------
1) Import / class name
   - Replace any old import if needed. If your code uses `from dictsqlite import DictSQLite`, you likely need no change. If it imports `DictSQLiteV4`, replace with `DictSQLite` or alias it:

       # Old code (example)
       from dictsqlite import DictSQLite

       # New code (explicit v4 name is optional)
       from dictsqlite import DictSQLite  # recommended
       # or
       from dictsqlite import DictSQLiteV4 as DictSQLite  # preserves example names

2) Encryption parameter
   - If your v1.8.8 code used `password=...` when creating the DB, rename the parameter to `encryption_password`:

       # v1.8.8
       db = DictSQLite('secrets.db', password='my_password')

       # current wrapper
       db = DictSQLite('secrets.db', encryption_password='my_password')

   - Verify that `stats()['encryption_enabled']` returns True after opening.

3) Serialization / storage_mode
   - Default `storage_mode='pickle'` preserves many existing workflows. If your old code stored pickled bytes manually, be aware that:
     - When you used to store raw pickled bytes, the current wrapper may still return bytes; you can use `pickle.loads()` to decode.
     - If you rely on non-pickled JSONB formats, set `storage_mode='jsonb'` explicitly when opening.

4) Safe Pickle
   - If you want to enable safer decoding for untrusted data, set `enable_safe_pickle=True` and optionally set `safe_pickle_allowed_modules=['myapp']`.
   - When enabled, the current wrapper will validate pickled payloads and raise on suspicious objects.

5) Bulk operations and performance
   - For loops of db[key] = value still work and are buffered by default. For best throughput, use `bulk_insert(dict_or_iter)` which is optimized for large batches.
   - Example:

       data = {f'record:{i}': f'data_{i}' for i in range(10000)}
       db.bulk_insert(data)

6) Async migration
   - If you used older async helpers, move to the new awaitable API:

       # current wrapper
       from dictsqlite import AsyncDictSQLite
       async def main():
           db = AsyncDictSQLite(':memory:')
           await db.aset('k', {'x': 1})
           v = await db.aget('k')

   - If you have synchronous callsites that relied on older wrappers, the async class provided by the current wrapper still provides `get`/`set` sync wrappers, but migrating to awaitable methods is recommended.

7) Table / namespace usage
   - Use `db.table('other')` to access another table/namespace if your v1 code used multiple tables.

8) Stats and verification
   - After migrating, verify behavior with these checks:
       - `db['key'] = 'value'` -> ensure `db['key']` returns a str
       - Complex object roundtrip: `db['obj'] = {'a': 1}` and check `db['obj'] == {'a': 1}`
       - Encryption: `db = DictSQLite(path, encryption_password='pw')` then `db.stats()['encryption_enabled'] is True`
       - Bulk insert timings vs old approach

Edge cases and incompatibilities
--------------------------------
- If you have custom lower-level on-disk formats, or used direct SQL access into the underlying sqlite tables, verify table schema and storage_mode because v4 may format values differently (pickle vs raw bytes vs jsonb columns).
- If you used `password` for encryption and opened existing encrypted DBs, the rename to `encryption_password` is only a parameter name change — the underlying crypto is compatible if the same password is used.
- Safe Pickle: enabling it may reject objects that previously succeeded; update `safe_pickle_allowed_modules` or avoid enabling if you need full compatibility.

Building native extension (development)
--------------------------------------
If you see a RuntimeError about the native extension not being available, build it locally. The repository includes build instructions in examples. Typical steps (development machine):

    cd dictsqlite_v2/dictsqlite
    # build the native extension using maturin or project-supplied scripts
    maturin develop --release

Run tests and examples
----------------------
- Examples: `dictsqlite_v2/dictsqlite/examples/` includes migration samples (e.g. `v4.2_migration_example.py`). Run them to verify behavior.
- Tests: run pytest in the python wrapper directory to validate your environment. Example:

    cd dictsqlite_v2/dictsqlite/python
    pytest -q

Rollback / fallbacks
--------------------
- If you encounter unexpected behavior, re-open the DB with explicit `storage_mode` set to the format you expect (e.g., 'jsonb' or 'pickle'), or open a temp DB and re-export data in a controlled way.

Checklist before deploying
--------------------------
- [ ] Run unit/integration tests against the new wrapper on staging
- [ ] Confirm encryption/keys and stats
- [ ] Validate bulk write and read throughput
- [ ] Update any CI build steps to include building the native extension if using compiled wheel

Appendix: quick code map (old -> new)
------------------------------------
- Constructor
    v1.8.8: `DictSQLite(path, password='pw')`
    current wrapper:    `DictSQLite(path, encryption_password='pw')`

- Bulk writes
    v1.8.8: loop assignments
    current wrapper:    prefer `bulk_insert()` or async batch APIs

- Async API
    v1.x: helper/wrapper functions
    current wrapper: `AsyncDictSQLite` with `aget`/`aset` awaitable methods

If you want, I can also generate a small migration script that detects common patterns and prints suggested replacements for your codebase. Just tell me whether you'd like a draft script or more examples.
