# Migration Guide from DictSQLite v1.8.8 to v2.0.7

This guide explains how to migrate from DictSQLite v1.8.8 to v2.0.7 (internal version v4).

## Table of Contents

1. [Overview](#overview)
2. [Key Changes](#key-changes)
3. [Breaking Changes](#breaking-changes)
4. [New Features](#new-features)
5. [Migration Steps](#migration-steps)
6. [Code Examples](#code-examples)
7. [Troubleshooting](#troubleshooting)

## Overview

### Version Information

- **v1.8.8**: Old version (Python implementation)
- **v2.0.7**: New version (Rust + Python, PyPI release version)
- **v4**: Internal implementation version name (architecture label)

### Compatibility

DictSQLite v2 is designed with **API compatibility** with v1.8.8 in mind. Most code will work with minimal changes.

## Key Changes

### 1. Parameter Name Changes

#### Encryption Parameter

```python
# v1.8.8
db = DictSQLite('db.db', password='secret')

# v2.0.7
db = DictSQLite('db.db', encryption_password='secret')
```

**Reason**: Clearer naming makes the parameter's purpose explicit.

### 2. Import Names

**Recommended import:**

```python
# v1.8.8
from dictsqlite import DictSQLite

# v2.0.7 (same)
from dictsqlite import DictSQLite
```

**Internal implementation name (optional):**

```python
# v2.0.7 also supports internal implementation name
from dictsqlite import DictSQLiteV4  # Alias for DictSQLite
```

> **Note**: For new code, we recommend using `DictSQLite`. `DictSQLiteV4` is provided for backward compatibility.

### 3. Improved Default Behavior

#### Automated Pickle Mode

```python
# v1.8.8 (manual serialization sometimes needed)
import pickle
db['key'] = pickle.dumps({'data': 'value'})
value = pickle.loads(db['key'])

# v2.0.7 (automated)
db['key'] = {'data': 'value'}
value = db['key']  # Automatically deserialized
```

### 4. Significant Performance Improvement

- **v1.8.8**: Python implementation, ~1M ops/sec
- **v2.0.7**: Rust implementation, 100M+ ops/sec (100x+ faster)

### 5. New Constructor Parameters

Parameters added in v2.0.7:

```python
DictSQLite(
    db_path,
    hot_capacity=1_000_000,         # New: Hot cache size
    enable_async=True,              # New: Async flush
    persist_mode="writethrough",    # Existing (improved)
    storage_mode="pickle",          # Existing (improved)
    table_name="main",              # Existing
    encryption_password=None,       # Changed: password → encryption_password
    enable_safe_pickle=False,       # New: Safe Pickle validation
    safe_pickle_allowed_modules=None,  # New: Allowed modules
    buffer_size=100,                # New: Buffer size
    encoding='utf-8',               # New: Encoding
    table_mode="prefix",            # New: Table mode
    pool_size=20                    # New: Connection pool size
)
```

## Breaking Changes

### 1. Encryption Parameter Name Change (Required)

**Impact**: All code using encryption

**Before migration (v1.8.8):**
```python
db = DictSQLite('secure.db', password='my_password')
```

**After migration (v2.0.7):**
```python
db = DictSQLite('secure.db', encryption_password='my_password')
```

### 2. Native Extension Build (Development Only)

**Impact**: When developing from source

**Required action:**
```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

**Note**: Not required when installing from PyPI.

### 3. Python Version Requirement

- **v1.8.8**: Python 3.7+
- **v2.0.7**: Python 3.9+

## New Features

### 1. Safe Pickle Validation

Secure deserialization of untrusted data:

```python
db = DictSQLite(
    'db.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp', 'mylib']
)
```

### 2. Table Modes

#### Prefix Mode (Default, Fast)

```python
db = DictSQLite(':memory:', table_mode='prefix')
users = db.table('users')
settings = db.table('settings')
```

#### Separate Mode (Complete Isolation)

```python
db = DictSQLite(':memory:', table_mode='separate')
# Each table is created as a separate SQLite table
```

### 3. Async Awaitable API

True asyncio integration:

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    await db.aset('key', 'value')
    value = await db.aget('key')
    
    await db.aclose()

asyncio.run(main())
```

### 4. Adjustable Connection Pool Size

Optimize concurrent access:

```python
db = DictSQLite('db.db', pool_size=50)  # For high concurrency
```

### 5. Adjustable Hot Capacity

Control memory cache size:

```python
db = DictSQLite('db.db', hot_capacity=10_000_000)  # 10 million entries
```

## Migration Steps

### Step 1: Install Package

```bash
pip install --upgrade dictsqlite
```

### Step 2: Verify Imports

Check import statements in code (usually no change needed):

```python
from dictsqlite import DictSQLite  # No change needed
```

### Step 3: Update Parameter Names

If using encryption, update parameter name:

```python
# Before migration
db = DictSQLite('db.db', password='secret')

# After migration
db = DictSQLite('db.db', encryption_password='secret')
```

### Step 4: Run Tests

Run existing test suite to verify functionality:

```bash
python -m pytest tests/
```

### Step 5: Verify Performance

Check statistics to measure performance:

```python
stats = db.stats()
print(stats)
```

## Code Examples

### Example 1: Basic Migration

**v1.8.8 code:**
```python
from dictsqlite import DictSQLite

# Basic usage
db = DictSQLite('myapp.db')
db['user:1'] = {'name': 'Alice', 'age': 30}
user = db['user:1']
db.close()

# Encryption
secure_db = DictSQLite('secure.db', password='secret123')
secure_db['token'] = 'abc123'
secure_db.close()
```

**Migration to v2.0.7:**
```python
from dictsqlite import DictSQLite

# Basic usage (no change)
db = DictSQLite('myapp.db')
db['user:1'] = {'name': 'Alice', 'age': 30}
user = db['user:1']
db.close()

# Encryption (parameter name changed)
secure_db = DictSQLite('secure.db', encryption_password='secret123')
secure_db['token'] = 'abc123'
secure_db.close()
```

### Example 2: Utilizing New Features

```python
from dictsqlite import DictSQLite

# Enable Safe Pickle
db = DictSQLite(
    'db.db',
    encryption_password='secret',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp']
)

# Table functionality
users = db.table('users')
users['alice'] = {'name': 'Alice', 'role': 'admin'}

settings = db.table('settings')
settings['theme'] = 'dark'

db.close()
```

### Example 3: Migration to Async

**v1.8.8 (sync only):**
```python
from dictsqlite import DictSQLite

db = DictSQLite('db.db')

for i in range(1000):
    db[f'key_{i}'] = f'value_{i}'

db.close()
```

**v2.0.7 (async):**
```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite('db.db')
    
    # Faster with batch operations
    items = [(f'key_{i}', f'value_{i}') for i in range(1000)]
    await db.abatch_set(items)
    
    await db.aclose()

asyncio.run(main())
```

### Example 4: Performance Optimization

```python
from dictsqlite import DictSQLite

# v1.8.8 default settings
db_old = DictSQLite('db.db')

# v2.0.7 optimized settings
db_new = DictSQLite(
    'db.db',
    hot_capacity=10_000_000,  # Larger cache
    persist_mode='lazy',       # Lazy write
    pool_size=50,              # Larger connection pool
    buffer_size=1000           # Larger buffer
)
```

## Troubleshooting

### Issue 1: RuntimeError: DictSQLite native extension not available

**Cause**: Native extension not built (development only)

**Solution:**
```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

**Note**: This issue doesn't occur when installing from PyPI.

### Issue 2: KeyError or TypeError after migration

**Cause**: Encryption parameter name change

**Solution:**
```python
# Wrong
db = DictSQLite('db.db', password='secret')

# Correct
db = DictSQLite('db.db', encryption_password='secret')
```

### Issue 3: Pickle-related errors

**Cause**: Pickle handling may differ between v1.8.8 and v2.0.7

**Solution:**

Enable Safe Pickle:
```python
db = DictSQLite(
    'db.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['your_module']
)
```

Or change storage mode:
```python
db = DictSQLite('db.db', storage_mode='jsonb')
```

### Issue 4: Cannot read existing database

**Cause**: Encryption password mismatch

**Solution:**

Specify exact password used in v1.8.8:
```python
# Saved in v1.8.8
# db = DictSQLite('db.db', password='old_password')

# Read in v2.0.7
db = DictSQLite('db.db', encryption_password='old_password')
```

### Issue 5: Performance slower than expected

**Diagnosis:**
```python
stats = db.stats()
print(f"Hot tier size: {stats['hot_tier_size']}")
print(f"Persist mode: {stats['persist_mode']}")
```

**Solution:**

Adjust parameters:
```python
db = DictSQLite(
    'db.db',
    hot_capacity=10_000_000,  # Increase
    persist_mode='lazy',       # Change
    pool_size=50               # Increase
)
```

## Database File Compatibility

### Using v1.8.8 Database in v2.0.7

**Without encryption:**
```python
# Can open v1.8.8 database directly
db = DictSQLite('old_v1.8.8.db')
```

**With encryption:**
```python
# Just change parameter name
# v1.8.8: password='secret'
# v2.0.7: encryption_password='secret'
db = DictSQLite('encrypted_v1.8.8.db', encryption_password='secret')
```

### Using v2.0.7 Database in v1.8.8

Generally compatible, but v2.0.7 features (Safe Pickle, table modes, etc.) may not work correctly in v1.8.8.

## Checklist

Verify the following before migration:

- [ ] Python 3.9+ is installed
- [ ] Ran `pip install --upgrade dictsqlite`
- [ ] Changed `password=` to `encryption_password=`
- [ ] Test suite passes
- [ ] Verified performance improvements
- [ ] Considered new features (Safe Pickle, table modes, etc.)

## Recommended Migration Strategies

### Strategy 1: Gradual Migration (Recommended)

1. First, migrate in test environment
2. Update parameter names
3. Run tests and verify functionality
4. Deploy to production

### Strategy 2: Parallel Operation

1. Run v1.8.8 and v2.0.7 in parallel
2. Implement new features in v2.0.7
3. Gradually migrate to v2.0.7
4. Deprecate v1.8.8

## References

- [README_EN.md](README_EN.md) - v2.0.7 quick start
- [EXAMPLES_EN.md](EXAMPLES_EN.md) - Practical examples
- [README_JP.md](README_JP.md) - Japanese documentation
- [EXAMPLES_JP.md](EXAMPLES_JP.md) - Japanese examples

## Support

For migration questions or support:

- **GitHub Issues**: [https://github.com/disnana/DictSQLite/issues](https://github.com/disnana/DictSQLite/issues)
- **Email**: support@disnana.com
- **Discord**: [https://discord.gg/KzeHDrgwAz](https://discord.gg/KzeHDrgwAz)

---

**Last Updated**: December 7, 2025  
**Target Versions**: v1.8.8 → v2.0.7 (internal version v4)

