# DictSQLite v4.2 Usage Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Security Features](#security-features)
5. [Performance Modes](#performance-modes)
6. [Advanced Usage](#advanced-usage)
7. [API Reference](#api-reference)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

DictSQLite v4.2 is an ultra-fast SQLite database wrapper that works like a Python dictionary.

### Key Features

- **🚀 Ultra Fast**: 100M+ ops/sec with lock-free concurrent access
- **🔒 Security**: AES-256-GCM encryption and Safe Pickle validation
- **💾 Flexible Persistence**: Memory, lazy, and write-through modes
- **🔄 Compatibility**: Full backward compatibility with DictSQLite v1/v2/v3
- **⚡ Rust Implementation**: Native performance via PyO3

### What's New in v4.2

- **Auto Unpickle**: Automatic data restoration when Safe Pickle is enabled
- **Enhanced Security**: Dangerous functions blocked by default
- **Buffering Optimization**: Batch processing in WriteThrough mode

---

## Installation

### From PyPI

```bash
pip install dictsqlite-v4
```

### Build from Source

```bash
# Rust toolchain required
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Clone the project
git clone https://github.com/yourusername/dictsqlite.git
cd dictsqlite/others/beta-versions/dictsqlite_v4.2

# Build & Install
maturin build --release
pip install target/wheels/dictsqlite_v4-*.whl
```

### Requirements

- Python 3.9+
- 64-bit OS (Windows, macOS, Linux)

---

## Basic Usage

### Quick Start

```python
from dictsqlite_v4 import DictSQLiteV4

# Create database
db = DictSQLiteV4("mydata.db")

# Use like a dictionary
db["user:1"] = b"Alice"
db["user:2"] = b"Bob"

# Read data
print(db["user:1"])  # b"Alice"

# Check existence
if "user:1" in db:
    print("User 1 exists!")

# Get all keys
for key in db.keys():
    print(key, db[key])

# Close database
db.close()
```

### Context Manager

```python
with DictSQLiteV4("mydata.db") as db:
    db["key"] = b"value"
    # Automatically closed
```

### In-Memory Mode

```python
# No persistence, fastest
db = DictSQLiteV4(":memory:")
```

---

## Security Features

### AES-256-GCM Encryption

Encrypt sensitive data at rest.

```python
# Enable encryption
db = DictSQLiteV4(
    "encrypted.db",
    encryption_password="your_secure_password_here"
)

# Data is automatically encrypted/decrypted
db["api_key"] = b"sk-1234567890abcdef"
db["password"] = b"super_secret"

# Auto-decryption on read
api_key = db["api_key"]  # Automatically decrypted
```

**Important Notes:**

- Lost passwords cannot be recovered
- Use environment variables in production
- Use strong, complex passwords

```python
import os

# Recommended: Load from environment
password = os.getenv("DB_PASSWORD")
if not password:
    raise ValueError("DB_PASSWORD environment variable not set")

db = DictSQLiteV4("secure.db", encryption_password=password)
```

### Safe Pickle

Protect your system from untrusted data.

```python
import pickle

# Enable Safe Pickle
db = DictSQLiteV4(
    "safe.db",
    enable_safe_pickle=True
)

# Safe data types (dict, list, int, str, etc.) are allowed
user_data = {
    "id": 1,
    "name": "Alice",
    "hobbies": ["reading", "coding"]
}
db["user:1"] = pickle.dumps(user_data)

# Automatically unpickled safely
restored = db["user:1"]  # Returns dict
print(restored["name"])  # "Alice"

# Dangerous functions (__import__, os.system, etc.) are blocked
try:
    dangerous = pickle.dumps(__import__)
    db["danger"] = dangerous  # Raises exception!
except Exception as e:
    print(f"Blocked: {e}")
```

#### Allow Custom Modules

To use your own classes:

```python
# Allow specific module prefixes
db = DictSQLiteV4(
    "custom.db",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "mylib"]
)

# Now myapp.* and mylib.* classes are allowed
from myapp.models import User

user = User(name="Alice", age=30)
db["user:1"] = pickle.dumps(user)
restored_user = db["user:1"]  # User object returned
```

### Encryption + Safe Pickle (Maximum Security)

Combine both for maximum security:

```python
db = DictSQLiteV4(
    "ultra_secure.db",
    encryption_password="ultra_secure_password",
    enable_safe_pickle=True
)

# Data is encrypted AND pickle-validated
sensitive_data = {
    "user_id": 1,
    "credit_card": "1234-5678-9012-3456",
    "balance": 100000
}
db["user:1"] = pickle.dumps(sensitive_data)

# On read: decrypt → unpickle validation → data retrieval
user = db["user:1"]
```

---

## Performance Modes

### 1. Memory Mode (Fastest)

```python
db = DictSQLiteV4(
    ":memory:",
    persist_mode="memory"
)

# No persistence, all in memory
# Fastest but data lost on process exit
```

**Use Cases:**
- Temporary cache
- Session data
- Test environments

### 2. Lazy Persistence Mode (Fast + Persistent)

```python
db = DictSQLiteV4(
    "data.db",
    persist_mode="lazy"
)

# Writes are buffered in memory
# Manual or automatic flush to disk
db["key1"] = b"value1"
db["key2"] = b"value2"

# Explicitly save to disk
db.flush()

# With context manager, auto-flush on exit
with DictSQLiteV4("data.db", persist_mode="lazy") as db:
    db["key"] = b"value"
    # Automatically flushed on exit
```

**Use Cases:**
- Batch processing
- Log collection
- High-speed writes needed

### 3. Write-Through Mode (Most Safe)

```python
db = DictSQLiteV4(
    "critical.db",
    persist_mode="writethrough"
)

# All writes immediately saved to disk
db["important"] = b"critical data"
# ↑ Immediately written to disk
```

**Use Cases:**
- Mission-critical data
- Transaction processing
- Zero data loss tolerance

### Buffer Size Tuning

Leverage buffering in WriteThrough mode:

```python
db = DictSQLiteV4(
    "buffered.db",
    persist_mode="writethrough",
    buffer_size=500  # Flush every 500 entries
)

# Buffered until threshold reached
for i in range(1000):
    db[f"key_{i}"] = f"value_{i}".encode()
    # Auto-flush every 500 entries
```

---

## Advanced Usage

### Hot Tier Capacity Tuning

```python
# Set hot tier (memory cache) size
db = DictSQLiteV4(
    "large.db",
    hot_capacity=10_000_000  # Keep up to 10M entries in memory
)
```

**Recommended Values:**
- Small: 100,000
- Medium: 1,000,000 (default)
- Large: 10,000,000+

### Table Name Specification

```python
# Use different tables
db_users = DictSQLiteV4("app.db", table_name="users")
db_products = DictSQLiteV4("app.db", table_name="products")

db_users["user:1"] = b"Alice"
db_products["product:1"] = b"Laptop"

# Same DB file, separate tables
```

### JSONB Storage Mode

Efficiently store JSON data:

```python
db = DictSQLiteV4(
    "json.db",
    storage_mode="jsonb"  # MessagePack format
)

# Store Python objects directly
data = {
    "id": 1,
    "name": "Alice",
    "tags": ["admin", "active"]
}
db["user:1"] = data  # Auto-serialized

# Auto-deserialized
user = db["user:1"]  # Returns dict
```

### Statistics

```python
stats = db.stats()
print(stats)

# Example output:
# {
#     'hot_tier_size': 1000,
#     'hot_tier_capacity': 1000000,
#     'num_shards': 32,
#     'encryption_enabled': True,
#     'safe_pickle_enabled': True,
#     'persist_mode': 'WriteThrough'
# }
```

### Dictionary Operations

```python
# Length
print(len(db))

# Key existence
if "user:1" in db:
    print("Exists")

# Get with default
value = db.get("maybe_missing", default=b"default value")

# Update
db.update({
    "key1": b"value1",
    "key2": b"value2"
})

# Setdefault
value = db.setdefault("key", b"default")

# Iteration
for key in db.keys():
    print(key)

for value in db.values():
    print(value)

for key, value in db.items():
    print(key, value)

# Delete
del db["key"]

# Clear all
db.clear()
```

---

## API Reference

### DictSQLiteV4 Class

#### Constructor

```python
DictSQLiteV4(
    db_path: str,
    hot_capacity: int = 1_000_000,
    enable_async: bool = True,
    persist_mode: str = "writethrough",
    storage_mode: str = "pickle",
    table_name: str = "main",
    encryption_password: Optional[str] = None,
    enable_safe_pickle: bool = False,
    safe_pickle_allowed_modules: Optional[List[str]] = None,
    buffer_size: int = 100,
    encoding: str = 'utf-8'
)
```

**Parameters:**

- `db_path`: Database file path (`:memory:` for in-memory)
- `hot_capacity`: Max entries in hot tier (memory cache)
- `enable_async`: Enable async background processing (future expansion)
- `persist_mode`: Persistence mode
  - `"memory"`: No persistence
  - `"lazy"`: Lazy persistence
  - `"writethrough"`: Immediate persistence (default)
- `storage_mode`: Storage format
  - `"pickle"`: Python pickle (default)
  - `"jsonb"`: MessagePack (JSON-compatible)
  - `"json"`: JSON string
  - `"bytes"`: Raw bytes
- `table_name`: Table name to use (default: "main")
- `encryption_password`: Encryption password (None for no encryption)
- `enable_safe_pickle`: Enable Safe Pickle validation
- `safe_pickle_allowed_modules`: List of allowed module prefixes
- `buffer_size`: Buffer size for WriteThrough mode
- `encoding`: String encoding (default: 'utf-8')

#### Methods

##### `__setitem__(key, value)`
```python
db["key"] = value
```
Set a value.

##### `__getitem__(key)`
```python
value = db["key"]
```
Get a value. Raises `KeyError` if key doesn't exist.

##### `__delitem__(key)`
```python
del db["key"]
```
Delete a key-value pair.

##### `__contains__(key)`
```python
if "key" in db:
    ...
```
Check if key exists.

##### `__len__()`
```python
size = len(db)
```
Return number of stored entries.

##### `get(key, default=None)`
```python
value = db.get("key", default=b"default")
```
Get value with default.

##### `keys()`
```python
for key in db.keys():
    print(key)
```
Return iterator of all keys.

##### `values()`
```python
for value in db.values():
    print(value)
```
Return iterator of all values.

##### `items()`
```python
for key, value in db.items():
    print(key, value)
```
Return iterator of all key-value pairs.

##### `update(other)`
```python
db.update({"key1": b"value1", "key2": b"value2"})
```
Update from dict or another DictSQLite.

##### `setdefault(key, default)`
```python
value = db.setdefault("key", b"default")
```
Set default value only if key doesn't exist.

##### `clear()`
```python
db.clear()
```
Remove all entries.

##### `flush()`
```python
db.flush()
```
Write buffered data to disk (used in lazy mode).

##### `stats()`
```python
stats = db.stats()
```
Return statistics as dict.

##### `close()`
```python
db.close()
```
Close database (automatic with context manager).

---

## Best Practices

### 1. Security

```python
# ✅ Good: Load from environment
import os
password = os.getenv("DB_PASSWORD")
db = DictSQLiteV4("secure.db", encryption_password=password)

# ❌ Bad: Hardcoded
db = DictSQLiteV4("secure.db", encryption_password="hardcoded_password")
```

### 2. Resource Management

```python
# ✅ Good: Context manager
with DictSQLiteV4("data.db") as db:
    db["key"] = b"value"
    # Auto-closed

# ❌ Bad: Manual (easy to forget)
db = DictSQLiteV4("data.db")
db["key"] = b"value"
# Easy to forget close()
```

### 3. Performance

```python
# ✅ Good: Lazy mode for batch processing
with DictSQLiteV4("batch.db", persist_mode="lazy") as db:
    for i in range(100000):
        db[f"key_{i}"] = f"value_{i}".encode()
    # Bulk save on exit

# ❌ Bad: Write-through for bulk writes
db = DictSQLiteV4("batch.db", persist_mode="writethrough")
for i in range(100000):
    db[f"key_{i}"] = f"value_{i}".encode()
    # Disk I/O every time → slow
```

### 4. Error Handling

```python
# ✅ Good: Proper exception handling
try:
    value = db["key"]
except KeyError:
    value = b"default"

# Or use get()
value = db.get("key", b"default")
```

### 5. Data Types

```python
# ✅ Good: Use bytes
db["key"] = b"value"

# Or use pickle
import pickle
db["user"] = pickle.dumps({"name": "Alice", "age": 30})
user = db["user"]  # Auto-converted to dict

# ⚠️ Note: Strings are auto-converted to bytes,
# but explicit bytes are clearer
```

### 6. Untrusted Data

```python
# ✅ Good: Use Safe Pickle
db = DictSQLiteV4(
    "untrusted.db",
    enable_safe_pickle=True
)

# Safe even with external data
user_input = get_user_pickle_data()
db["user_data"] = user_input  # Dangerous functions blocked

# ❌ Bad: No Safe Pickle with external data
db = DictSQLiteV4("unsafe.db")
db["user_data"] = user_input  # Dangerous!
```

---

## Troubleshooting

### Q: I forgot my password

**A:** Unfortunately, encrypted data cannot be recovered without the password. Use a password manager.

### Q: Getting "forbidden global" error

**A:** Safe Pickle is blocking dangerous functions. Allow them if needed via `safe_pickle_allowed_modules`.

```python
# Allow custom classes
db = DictSQLiteV4(
    "data.db",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp"]
)
```

### Q: Performance is slow

**A:** Check the following:

1. **Persistence mode**: Use `lazy` for bulk writes
2. **Hot capacity**: Increase `hot_capacity`
3. **Buffer size**: Adjust `buffer_size`
4. **Encryption**: Disable if not needed

```python
# Performance tuning
db = DictSQLiteV4(
    "fast.db",
    hot_capacity=10_000_000,
    persist_mode="lazy",
    buffer_size=1000,
    encryption_password=None  # No encryption
)
```

### Q: High memory usage

**A:** Reduce `hot_capacity`:

```python
db = DictSQLiteV4(
    "low_memory.db",
    hot_capacity=10_000  # Reduced from default 1,000,000
)
```

### Q: Data not persisting

**A:** Check:

1. Not using memory mode (`:memory:`)
2. Calling `flush()` in `lazy` mode
3. Using context manager or `close()`

```python
# Ensure persistence
with DictSQLiteV4("data.db", persist_mode="lazy") as db:
    db["key"] = b"value"
    db.flush()  # Explicit flush
# Auto-flush on exit
```

### Q: Can multiple processes access the same DB?

**A:** Yes. SQLite supports multiple readers and properly locked writes. However, be cautious with heavy concurrent writes.

### Q: Is it thread-safe?

**A:** Yes. Uses lock-free DashMap internally, safe for multi-threaded environments.

---

## Performance Benchmarks

### Test Environment
- CPU: Intel Core i7
- RAM: 16GB
- OS: Windows 11

### Results

| Operation | Speed | Mode |
|-----------|-------|------|
| Write | 100M+ ops/sec | Memory |
| Read | 150M+ ops/sec | Memory |
| Encrypted Write | 12K ops/sec | WriteThrough + Encryption |
| Safe Pickle | 10K ops/sec | WriteThrough + Safe Pickle |
| Both | 8K ops/sec | WriteThrough + Both |

---

## Version History

### v4.2.0 (2025-10-08)
- ✨ Auto unpickle when Safe Pickle enabled
- 🔒 DEFAULT_DENY applied by default
- ⚡ WriteThrough buffering optimization
- 🐛 Pickle validation fixes

### v4.1.0
- 🔒 Safe Pickle feature added
- 🔐 AES-256-GCM encryption added

### v4.0.0
- 🚀 Complete Rust rewrite
- ⚡ 100M+ ops/sec performance
- 💾 Three persistence modes

---

## License

MIT License

---

## Support

If you encounter issues:

1. [GitHub Issues](https://github.com/disnana/DictSQLite/issues)
2. Check documentation
3. Review example code

---

## Related Links

- [GitHub Repository](https://github.com/disnana/DictSQLite)
- [PyPI Package](https://pypi.org/project/dictsqlite-v4/)
- [Example Code](examples/)

---

**Happy Coding! 🎉**
