# DictSQLite-Fastest

A high-performance alternative to DictSQLite using APSW (Another Python SQLite Wrapper) for maximum speed while maintaining full compatibility with the original DictSQLite API.

## Performance Summary

Based on comprehensive benchmarks, DictSQLite-Fastest provides significant performance improvements:

- **Average Speedup: 8.03x**
- **Maximum Speedup: 17.23x** (bulk insert operations)
- **100% of tests show performance improvements**

### Detailed Performance Results

| Operation | Original Time | Fastest Time | Speedup |
|-----------|---------------|---------------|---------|
| Bulk Insert (100 items) | 0.0801s | 0.0064s | **12.46x** |
| Bulk Read (100 items) | 0.0063s | 0.0022s | **2.84x** |
| Complex Data (10 items) | 0.0079s | 0.0025s | **3.16x** |
| Bulk Insert (500 items) | 0.3162s | 0.0184s | **17.23x** |
| Bulk Read (500 items) | 0.0308s | 0.0090s | **3.41x** |
| Complex Data (50 items) | 0.0372s | 0.0037s | **10.03x** |
| Bulk Insert (1000 items) | 0.3138s | 0.0304s | **10.34x** |
| Bulk Read (1000 items) | 0.0615s | 0.0178s | **3.46x** |
| Complex Data (100 items) | 0.0533s | 0.0057s | **9.31x** |

## Key Features

### 🚀 Performance Optimizations

- **APSW Backend**: Uses APSW instead of sqlite3 for maximum performance
- **Thread-Local Connections**: Each thread gets its own optimized connection
- **WAL Mode Default**: Write-Ahead Logging enabled by default for better concurrency
- **Optimized PRAGMA Settings**: Tuned for high performance
  - `synchronous=NORMAL` for balanced safety/speed
  - 64MB cache size
  - Memory-based temporary storage
  - 256MB memory-mapped I/O

### 🔄 Full Compatibility

- **100% API Compatible**: Drop-in replacement for DictSQLite
- **Same Data Format**: Can read/write databases created by original DictSQLite
- **All Features Supported**:
  - Encryption (RSA + AES)
  - Safe pickle loading
  - JSON storage mode
  - Synced collections (lists, sets)
  - Recursive dictionaries
  - Multiple table support (v2 API)

### ⚡ Async Support

- **Native Async Operations**: Built-in async support with proper connection handling
- **Concurrent Operations**: Optimized for high-concurrency scenarios
- **Connection Pool Management**: Automatic connection lifecycle management

## Installation

```bash
# Install APSW (required dependency)
pip install apsw

# Then use the module (no separate installation needed)
```

## Usage

### Basic Usage (Synchronous)

```python
from dictsqlite_fastest import DictSQLiteFastest

# Drop-in replacement for DictSQLite
with DictSQLiteFastest('fastest.db') as db:
    db['key1'] = 'value1'
    db['key2'] = {'nested': 'data'}
    db['list'] = [1, 2, 3]
    
    print(db['key1'])  # 'value1'
    
    # Auto-synced collections
    db['list'].append(4)  # Automatically saved to DB
    print(db['list'])  # [1, 2, 3, 4]
```

### Async Usage

```python
import asyncio
from dictsqlite_fastest import AsyncDictSQLiteFastest

async def main():
    async with AsyncDictSQLiteFastest('async_fastest.db') as db:
        # Async operations
        await db.aset('key1', 'value1')
        value = await db.aget('key1')
        
        # Concurrent operations
        tasks = [
            db.aset(f'key_{i}', f'value_{i}')
            for i in range(100)
        ]
        await asyncio.gather(*tasks)
        
        keys = await db.akeys()
        print(f"Stored {len(keys)} keys")

asyncio.run(main())
```

### Migration from DictSQLite

Simply replace the import - no other changes needed:

```python
# Before
from dictsqlite import DictSQLite

# After  
from dictsqlite_fastest import DictSQLiteFastest as DictSQLite

# All existing code works unchanged!
```

## Configuration Options

All original DictSQLite options are supported:

```python
db = DictSQLiteFastest(
    'database.db',
    table_name='custom_table',
    journal_mode='WAL',  # Default, optimized for performance
    storage_mode='pickle',  # or 'json'
    password='encryption_password',
    publickey_path='./public_keys.pem',
    privatekey_path='./private_keys.pem',
    safe_pickle_policy=custom_policy
)
```

## Performance Optimization Tips

### 1. Use WAL Mode (Default)
```python
# WAL mode is default and recommended for best performance
db = DictSQLiteFastest('db.db', journal_mode='WAL')
```

### 2. Batch Operations
```python
# Batch multiple operations for maximum speed
with DictSQLiteFastest('db.db') as db:
    for i in range(1000):
        db[f'key_{i}'] = f'value_{i}'  # Very fast with APSW
```

### 3. Async for Concurrency
```python
# Use async for concurrent operations
async with AsyncDictSQLiteFastest('db.db') as db:
    tasks = [db.aset(f'key_{i}', data) for i in range(1000)]
    await asyncio.gather(*tasks)  # Concurrent execution
```

## Benchmarking

Run the included benchmark to compare performance on your system:

```bash
cd dictsqlite-fastest
python benchmark.py
```

## Testing

Comprehensive test suites ensure compatibility and performance:

```bash
# Basic functionality tests
pytest tests/test_basic.py

# Performance comparison tests  
pytest tests/test_performance_comparison.py

# Compatibility tests
pytest tests/test_compatibility.py

# Advanced performance tests
pytest tests/test_advanced_performance.py
```

## Architecture

### Thread Safety
- Each thread gets its own APSW connection via `threading.local()`
- Thread-safe connection management with proper locking
- No shared state between threads

### Connection Optimization
- Automatic connection reuse within threads
- Optimized PRAGMA settings applied per connection
- Proper connection cleanup on thread exit

### Async Implementation
- Uses `ThreadPoolExecutor` with connection-per-operation model
- Semaphore-based concurrency limiting
- Automatic connection lifecycle management

## Compatibility Notes

- **100% API compatible** with original DictSQLite
- **Database format compatible** - can read/write same files
- **Feature complete** - all encryption, safety, and advanced features supported
- **Behavior identical** - matches original behavior exactly (including edge cases)

## Performance vs Original

| Metric | DictSQLite | DictSQLite-Fastest | Improvement |
|--------|------------|-------------------|-------------|
| Bulk Insert | Slow | **17x faster** | Massive |
| Bulk Read | Moderate | **3-4x faster** | Significant |
| Complex Operations | Slow | **9-10x faster** | Excellent |
| Memory Usage | Higher | Lower | Better |
| Concurrent Access | Limited | Excellent | Much better |

## Requirements

- Python 3.9+
- APSW (pip install apsw)
- All original DictSQLite dependencies (portalocker, cryptography)

## License

Same as original DictSQLite - MIT License

## Contributing

This module is designed to be a high-performance, drop-in replacement for DictSQLite. When contributing:

1. Maintain 100% API compatibility
2. Ensure all tests pass
3. Add performance benchmarks for new features
4. Follow the existing code style

## Future Enhancements

- [ ] Connection pooling for even better async performance
- [ ] Prepared statement caching optimization
- [ ] Bulk operation APIs for maximum efficiency
- [ ] Custom APSW extensions for specialized operations
- [ ] Memory-mapped file optimizations
- [ ] Compression support for large values