# AsyncDictSQLite v4.2 - True Asyncio Support

## Overview

DictSQLite v4.2 now provides **true Python asyncio support** with awaitable methods. The AsyncDictSQLite class can now be used with Python's `async/await` syntax, allowing for non-blocking I/O operations and better integration with async frameworks like FastAPI, aiohttp, and Sanic.

## What's New

### True Async/Await Support

Previously, AsyncDictSQLite had "async" in the name but methods like `get_async()` and `set_async()` were **not actually awaitable**. 

**Before (v4.1)**:
```python
db = AsyncDictSQLite("mydb.db")
db.set_async("key", b"value")  # ❌ Cannot await!
value = db.get_async("key")     # ❌ Cannot await!
```

**Now (v4.2)**:
```python
db = AsyncDictSQLite("mydb.db")
await db.aset("key", b"value")  # ✅ Truly awaitable!
value = await db.aget("key")     # ✅ Truly awaitable!
```

### New Awaitable Methods

- `async aget(key)` - Asynchronously get a value
- `async aset(key, value)` - Asynchronously set a value
- `async abatch_get(keys)` - Asynchronously get multiple values
- `async abatch_set(items)` - Asynchronously set multiple values

### Backward Compatibility

All existing synchronous methods are still available for backward compatibility:

- `get(key)` - Synchronous get
- `set(key, value)` - Synchronous set
- `batch_get(keys)` - Synchronous batch get
- `batch_set(items)` - Synchronous batch set

## Installation

Build and install the native extension:

```bash
cd dictsqlite_v4.2
maturin build --release
pip install target/wheels/dictsqlite_v4-*.whl
```

## Usage Examples

### Basic Async Operations

```python
import asyncio
from dictsqlite_v4.2 import AsyncDictSQLite

async def main():
    async with AsyncDictSQLite("mydb.db", persist_mode="lazy") as db:
        # Set values
        await db.aset("user:1", b"Alice")
        await db.aset("user:2", b"Bob")
        
        # Get values
        user1 = await db.aget("user:1")
        print(f"User 1: {user1}")  # Output: User 1: b'Alice'
        
        # Get missing key
        missing = await db.aget("nonexistent")
        print(f"Missing: {missing}")  # Output: Missing: None

asyncio.run(main())
```

### Concurrent Operations

The real power of async comes with concurrent operations:

```python
async def concurrent_example():
    async with AsyncDictSQLite("mydb.db") as db:
        # Write 100 records concurrently
        write_tasks = [
            db.aset(f"key_{i}", f"value_{i}".encode())
            for i in range(100)
        ]
        await asyncio.gather(*write_tasks)
        print("✓ Wrote 100 records concurrently")
        
        # Read them back concurrently
        read_tasks = [
            db.aget(f"key_{i}")
            for i in range(100)
        ]
        results = await asyncio.gather(*read_tasks)
        print(f"✓ Read {len(results)} records concurrently")
```

### Batch Operations

```python
async def batch_example():
    async with AsyncDictSQLite("mydb.db") as db:
        # Batch set
        items = [
            (f"product:{i}", f"Product {i}".encode())
            for i in range(50)
        ]
        await db.abatch_set(items)
        print("✓ Batch set 50 items")
        
        # Batch get
        keys = [f"product:{i}" for i in range(50)]
        values = await db.abatch_get(keys)
        print(f"✓ Batch retrieved {len(values)} items")
```

### Integration with Web Frameworks

#### FastAPI Example

```python
from fastapi import FastAPI
from dictsqlite_v4.2 import AsyncDictSQLite

app = FastAPI()
db = AsyncDictSQLite("cache.db", persist_mode="writethrough")

@app.get("/user/{user_id}")
async def get_user(user_id: str):
    user_data = await db.aget(f"user:{user_id}")
    if user_data is None:
        return {"error": "User not found"}
    return {"user_id": user_id, "data": user_data.decode()}

@app.post("/user/{user_id}")
async def create_user(user_id: str, data: dict):
    await db.aset(f"user:{user_id}", str(data).encode())
    return {"status": "created", "user_id": user_id}
```

#### aiohttp Example

```python
from aiohttp import web
from dictsqlite_v4.2 import AsyncDictSQLite

db = AsyncDictSQLite("sessions.db", persist_mode="writethrough")

async def handle_get(request):
    key = request.match_info['key']
    value = await db.aget(key)
    if value is None:
        return web.Response(status=404, text="Not found")
    return web.Response(text=value.decode())

async def handle_set(request):
    key = request.match_info['key']
    value = await request.text()
    await db.aset(key, value.encode())
    return web.Response(text="OK")

app = web.Application()
app.add_routes([
    web.get('/cache/{key}', handle_get),
    web.post('/cache/{key}', handle_set),
])

web.run_app(app)
```

## Technical Details

### Implementation

The async support is implemented using:

1. **pyo3 0.24.x** with the `experimental-async` feature
2. **Tokio runtime** for executing async operations
3. **Native Rust async/await** for non-blocking I/O

The async methods use `spawn_blocking` to offload I/O operations to a thread pool, ensuring that the event loop is never blocked.

### Performance Characteristics

- **Cache operations**: Nearly instant (lock-free concurrent hashmap)
- **Storage operations**: Non-blocking (offloaded to thread pool)
- **Concurrent operations**: Excellent scalability with multiple concurrent tasks

### GIL Handling

The async methods properly release the Python GIL during I/O operations, allowing true parallelism even with Python's Global Interpreter Lock.

## Configuration Options

All AsyncDictSQLite options from v4.2 are still available:

```python
db = AsyncDictSQLite(
    db_path="mydb.db",
    capacity=1_000_000,          # Cache capacity
    persist_mode="lazy",          # "memory", "lazy", or "writethrough"
    storage_mode="pickle",        # "pickle", "json", "jsonb", or "bytes"
    table_name="main",            # Table name for multi-table support
    buffer_size=100               # Write buffer size for batching
)
```

## Migration Guide

### From v4.1 to v4.2

If you were using the pseudo-async methods:

```python
# v4.1 (pseudo-async)
db = AsyncDictSQLite("mydb.db")
db.set_async("key", b"value")
value = db.get_async("key")
```

You have two options:

**Option 1**: Use new async methods (recommended)
```python
# v4.2 (true async)
db = AsyncDictSQLite("mydb.db")
await db.aset("key", b"value")
value = await db.aget("key")
```

**Option 2**: Keep using synchronous methods (backward compatible)
```python
# v4.2 (backward compatible)
db = AsyncDictSQLite("mydb.db")
db.set("key", b"value")  # Renamed from set_async
value = db.get("key")     # Renamed from get_async
```

## Testing

Run the test suite:

```bash
python tests/test_async_awaitable.py
```

Run the example:

```bash
python examples/async_await_example.py
```

## Performance Improvements

v4.2 includes significant performance improvements:

- **300x faster writes** in WriteThrough mode (through write buffering)
- **43x faster batch operations** (through batched SQL transactions)
- **Lock-free cache access** for read-heavy workloads
- **Parallel batch processing** with Rayon

## Known Limitations

- Requires Python 3.9 or higher
- pyo3 experimental-async feature is still experimental
- Async methods cannot be used in synchronous code (must use `asyncio.run()` or similar)

## Future Enhancements

Planned for v4.3:

- Async iterators for large datasets
- Streaming support for large values
- Connection pooling for multi-database scenarios
- Query builder for complex operations

## License

MIT License - Same as DictSQLite project

## Credits

- Built with PyO3 for Rust-Python bindings
- Uses Tokio for async runtime
- DashMap for lock-free concurrent hashmap
- SQLite for persistent storage
