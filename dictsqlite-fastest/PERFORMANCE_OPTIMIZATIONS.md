# DictSQLite-Fastest Performance Optimizations

## Recent Enhancements (2025-10)

This document describes the recent performance optimizations added to DictSQLite-Fastest to improve memory utilization, WAL performance, and bulk operation speed.

## Memory and WAL Optimizations

### Enhanced PRAGMA Settings

The following PRAGMA settings have been added when `enable_memory_optimization=True`:

#### WAL Mode Optimizations
- **`locking_mode=EXCLUSIVE`**: Enables exclusive locking mode for WAL, reducing lock overhead and improving concurrent write performance
- **`journal_size_limit=64MB`**: Limits WAL file growth to 64MB to prevent excessive disk usage

#### Memory Optimizations
- **`secure_delete=OFF`**: Disables secure deletion for faster delete operations (data is marked as deleted rather than overwritten)
- **`read_uncommitted=ON`**: Allows reading uncommitted data for better read performance in single-writer scenarios
- **`cell_size_check=OFF`**: Disables cell size checking for reduced overhead
- **`PRAGMA optimize`**: Runs query planner optimization to update statistics

### Connection Pool Enhancements

The connection pool now applies the same memory optimizations to all pooled connections for consistent performance.

## Bulk Operation Improvements

### Optimized Chunk Sizes

All bulk operations now use optimized chunk sizes to maximize performance while staying within SQLite's parameter limits:

- **Previous**: 500 parameters per query
- **New**: 999 parameters per query (SQLite's maximum)

This change affects:
- `bulk_get()`: Now processes up to 999 keys per query
- `bulk_delete()`: Now deletes up to 999 keys per query
- `APSWBulkOperator.bulk_select_optimized()`: Increased from 500 to 999 keys
- `APSWBulkOperator.bulk_delete_optimized()`: Increased from 500 to 999 keys

### Improved Chunked Insert Performance

`bulk_insert_chunked()` now uses `executemany()` instead of individual `execute()` calls:

**Before**:
```python
for k, v in chunk:
    cursor.execute(self._insert_stmt, (k, v))
```

**After**:
```python
cursor.executemany(self._insert_stmt, chunk)
```

This reduces the number of statement preparations and executions, improving performance significantly.

### Optimized Auto-Selection Thresholds

`bulk_insert_optimized()` now uses better thresholds for automatic strategy selection:

| Item Count | Strategy | Previous | New |
|------------|----------|----------|-----|
| < 50 | Individual inserts | < 100 | < 50 |
| 50-499 | executemany | 100-999 | 50-499 |
| ≥ 500 | Chunked | ≥ 1000 | ≥ 500 |

**Chunk Size Calculation**:
- Previous: `min(1000, item_count // 10)`
- New: `min(2000, max(500, item_count // 20))`

This provides:
- Larger chunks for better memory utilization
- Minimum chunk size of 500 items
- Maximum chunk size of 2000 items

## Performance Benchmark Results

Based on our benchmarks with the new optimizations:

### Small Dataset (100 items)
- Insert: ~348,000 items/sec
- Read: ~360,000 items/sec
- Delete: ~557,000 items/sec

### Medium Dataset (1,000 items)
- Insert: ~448,000 items/sec
- Read: ~377,000 items/sec
- Delete: ~767,000 items/sec

### Large Dataset (5,000 items)
- Insert: ~434,000 items/sec
- Read: ~439,000 items/sec
- Delete: ~974,000 items/sec

## Usage Examples

### Enable All Optimizations

```python
from dictsqlite_fastest.main import DictSQLiteFastest

# Maximum performance configuration
db = DictSQLiteFastest(
    'high_performance.db',
    # Large memory cache
    cache_size=-128000,  # 128MB
    mmap_size=536870912,  # 512MB
    
    # Enable memory optimizations
    enable_memory_optimization=True,
    
    # WAL mode for best concurrent performance
    journal_mode='WAL',
    wal_autocheckpoint=2000,
    
    # Custom PRAGMA settings (optional)
    custom_pragma_settings={
        'page_size': 65536,  # 64KB pages
    }
)
```

### Bulk Operations

```python
# Efficient bulk insert
data = {f'key_{i}': f'value_{i}' for i in range(10000)}
db.bulk_insert_optimized(data)  # Automatically selects best strategy

# Efficient bulk read
keys = [f'key_{i}' for i in range(10000)]
results = db.bulk_get(keys)  # Processes in chunks of 999

# Efficient bulk delete
db.bulk_delete(keys)  # Processes in chunks of 999
```

## Trade-offs and Considerations

### Memory vs. Safety

Some optimizations prioritize performance over safety:

- **`secure_delete=OFF`**: Deleted data remains on disk until overwritten
- **`read_uncommitted=ON`**: May read uncommitted data in concurrent scenarios
- **`locking_mode=EXCLUSIVE`**: Single process access only

For applications requiring maximum data security or multi-process access, consider:

```python
db = DictSQLiteFastest(
    'secure.db',
    enable_memory_optimization=False,  # Disable aggressive optimizations
    custom_pragma_settings={
        'secure_delete': 'ON',
        'locking_mode': 'NORMAL',
    }
)
```

### WAL Mode Considerations

WAL mode with exclusive locking is best for:
- Single-process applications
- Write-heavy workloads
- Applications prioritizing speed over multi-process access

Consider disabling for:
- Multi-process concurrent access
- Applications requiring immediate durability
- Environments with limited disk space

## Compatibility

All optimizations maintain backward compatibility:
- Existing code continues to work without changes
- Optimizations can be selectively disabled
- Default behavior remains safe and conservative

## Future Improvements

Potential areas for further optimization:
- Prepared statement caching improvements
- Connection pooling enhancements
- Compression algorithm selection based on data characteristics
- Adaptive chunk size selection based on available memory
