# Storage and Persistence

## `storage_mode`

- `pickle`: Supports broad Python objects. Safe Pickle is recommended.
- `jsonb`: MessagePack-style storage for JSON-compatible data.
- `json`: Human-readable JSON storage.
- `bytes`: Stores bytes as-is.

## `persist_mode`

- `memory`: In-process only. Fast, but data is not persisted after exit.
- `lazy`: Buffers writes and flushes them in batches. Best for throughput.
- `writethrough`: Persists every write immediately. Best for durability.

## Stability notes

Version 2.1.3 hardens failed-flush requeueing, prevents buffered writes from returning after delete/clear, and fixes lazy persistence for separate tables.
