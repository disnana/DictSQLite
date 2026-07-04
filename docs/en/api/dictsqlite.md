---
outline: [2, 3]
---

# API Reference

Use `DictSQLite` for normal code, `AsyncDictSQLite` for asyncio, and `table()` / `TableProxy` for namespaces.

## `DictSQLite`

```python
from dictsqlite import DictSQLite

db = DictSQLite(
    "data.db",
    storage_mode="pickle",
    persist_mode="lazy",
    table_mode="prefix",
    safe_pickle=True,
)
```

| Operation | Description |
|---|---|
| `db[key] = value` / `db.set(key, value)` | Store a value. |
| `db[key]` / `db.get(key, default=None)` | Read a value. |
| `del db[key]` / `db.delete(key)` | Delete a key. |
| `db.batch_set(dict)` | Write many keys at once. |
| `db.batch_get(keys)` | Read many keys at once. |
| `db.clear()` | Remove all entries. |
| `db.flush()` | Flush lazy writes to storage. |
| `db.close()` | Flush and close resources. |

## `AsyncDictSQLite`

```python
from dictsqlite import AsyncDictSQLite

db = AsyncDictSQLite("data.db")
await db.set("key", "value")
value = await db.get("key")
await db.close()
```

The async API is designed for asyncio workloads. Batch reads use bulk storage reads to reduce SQLite round trips on cache misses.

## `TableProxy`

```python
users = db.table("users")
users["alice"] = {"role": "admin"}
```

Tables provide namespaced access. `prefix` mode stores prefixed keys, while `separate` mode uses separate SQLite tables.

## Key options

| Option | Values |
|---|---|
| `storage_mode` | `pickle`, `jsonb`, `json`, `bytes` |
| `persist_mode` | `memory`, `lazy`, `writethrough` |
| `table_mode` | `prefix`, `separate` |
| `safe_pickle` | `True` / `False` |
| `encryption_password` | `str` / `None` |
| `compression` | Enabled through configuration |
