# Async API

```python
from dictsqlite import AsyncDictSQLite

db = AsyncDictSQLite("async.db", persist_mode="lazy")
await db.set("k", "v")
value = await db.get("k")
await db.flush()
await db.close()
```

## Batch operations

```python
await db.batch_set({"a": 1, "b": 2})
values = await db.batch_get(["a", "b", "missing"])
```

Version 2.1.3 routes batch-get cache misses through bulk reads, reducing small SQLite round trips.

## Shutdown

Call `flush()` or `close()` in `lazy` mode. If a flush fails, pending writes are restored so they can be retried.
