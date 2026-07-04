# Guide

DictSQLite is a fast persistent dictionary backed by SQLite. Version 2 is implemented with Rust/PyO3 and provides both sync and async APIs.

<div class="quick-grid">
  <a class="quick-card" href="./api">
    <strong>API reference</strong>
    <span>Operations for DictSQLite, AsyncDictSQLite, and TableProxy</span>
  </a>
  <a class="quick-card" href="./storage">
    <strong>Choose modes</strong>
    <span>Pick pickle/jsonb/json/bytes and lazy/writethrough modes</span>
  </a>
  <a class="quick-card" href="./async">
    <strong>Use async</strong>
    <span>set/get/batch/flush for asyncio workloads</span>
  </a>
  <a class="quick-card" href="./performance">
    <strong>Read benchmarks</strong>
    <span>Measurements by size, count, batch, and storage format</span>
  </a>
</div>

## Installation

```bash
pip install dictsqlite
```

## Minimal example

```python
from dictsqlite import DictSQLite

db = DictSQLite("cache.db")
db["user:1"] = {"name": "Alice", "score": 42}

print(db["user:1"])
db.close()
```

## Async API

```python
import asyncio
from dictsqlite import AsyncDictSQLite

async def main():
    db = AsyncDictSQLite("cache.db")
    await db.set("job:1", {"status": "queued"})
    print(await db.get("job:1"))
    await db.close()

asyncio.run(main())
```

## Storage and persistence modes

- `storage_mode`: `pickle`, `jsonb`, `json`, `bytes`
- `persist_mode`: `memory`, `lazy`, `writethrough`
- `table_mode`: `prefix`, `separate`

Use Safe Pickle and encryption according to your trust boundary. `lazy` is useful for heavy write throughput, while `writethrough` is best when each write must be persisted immediately.

## Common setups

| Use case | Recommended setup |
|---|---|
| Temporary cache | `persist_mode="memory"` |
| Fast persistent cache | `persist_mode="lazy", storage_mode="jsonb"` |
| Durability after every write | `persist_mode="writethrough"` |
| Binary data | `storage_mode="bytes"` |
| Separated tables | `table_mode="separate"` |
