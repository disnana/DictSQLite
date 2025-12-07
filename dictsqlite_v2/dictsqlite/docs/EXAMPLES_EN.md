# DictSQLite v2 — Examples (English)

This document provides practical examples of using DictSQLite v2.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Encryption](#encryption)
3. [Safe Pickle](#safe-pickle)
4. [Table Functionality](#table-functionality)
5. [Bulk Operations](#bulk-operations)
6. [Async Operations](#async-operations)
7. [Storage Modes](#storage-modes)
8. [Persistence Modes](#persistence-modes)
9. [Practical Examples](#practical-examples)

## Basic Usage

### Import

```python
# Recommended: Standard import
from dictsqlite import DictSQLite

# Using internal implementation name (backward compatibility)
from dictsqlite import DictSQLiteV4
```

### Simple Example

```python
from dictsqlite import DictSQLite

# Create memory database
db = DictSQLite(':memory:')

# Store strings
db['user:alice'] = 'Alice Smith'
db['user:bob'] = 'Bob Johnson'

# Store Python objects (automatically pickled)
db['config'] = {
    'theme': 'dark',
    'language': 'en',
    'notifications': True
}

# Retrieve values
print(db['user:alice'])        # -> 'Alice Smith'
print(db['config']['theme'])   # -> 'dark'

# Get with default
print(db.get('missing', 'default'))  # -> 'default'

# Check key existence
if 'user:alice' in db:
    print("Alice exists!")

# Iteration
for key in db.keys():
    print(f"{key}: {db[key]}")

db.close()
```

### Context Manager

```python
from dictsqlite import DictSQLite

# Automatically closed
with DictSQLite('myapp.db') as db:
    db['setting1'] = 'value1'
    db['setting2'] = 'value2'
    
    # Processing...
    
# Automatically flushed and closed here
```

### File Database and Persistence

```python
from dictsqlite import DictSQLite

# Create file database
db = DictSQLite('data.db', persist_mode="writethrough")

# Save data (immediately persisted)
db['persistent_data'] = {'important': 'information'}

db.close()

# Reopen and read data
db = DictSQLite('data.db')
print(db['persistent_data'])  # -> {'important': 'information'}
db.close()
```

## Encryption

### Basic Encryption

```python
from dictsqlite import DictSQLite

# Enable encryption
db = DictSQLite(
    'secure.db',
    encryption_password='my_secret_password_123'
)

# Store sensitive data
db['api_key'] = 'sk-1234567890abcdef'
db['user_token'] = {'token': 'xyz', 'expires': '2025-12-31'}

# Check if encryption is enabled
stats = db.stats()
print(f"Encryption enabled: {stats['encryption_enabled']}")  # -> True

db.close()
```

### Opening Encrypted Database

```python
from dictsqlite import DictSQLite

# Open with same password
db = DictSQLite(
    'secure.db',
    encryption_password='my_secret_password_123'
)

# Access data
print(db['api_key'])  # -> 'sk-1234567890abcdef'

db.close()
```

### Encryption + JSONB Mode

```python
from dictsqlite import DictSQLite

db = DictSQLite(
    'encrypted_json.db',
    encryption_password='password',
    storage_mode='jsonb'
)

# Store JSON-compatible data encrypted
db['user_data'] = {
    'name': 'Alice',
    'email': 'alice@example.com',
    'ssn': '123-45-6789'
}

db.close()
```

## Safe Pickle

### Enable Safe Pickle

```python
from dictsqlite import DictSQLite

# Enable Safe Pickle
db = DictSQLite(
    ':memory:',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp', 'mylib']
)

# Store safe data
db['data'] = {
    'numbers': [1, 2, 3],
    'text': 'Hello',
    'nested': {'key': 'value'}
}

# Objects from disallowed modules are rejected
```

### Custom Classes with Safe Pickle

```python
from dictsqlite import DictSQLite

# Allow classes from myapp.models module
db = DictSQLite(
    ':memory:',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp.models']
)

# This is allowed (myapp.models class)
# from myapp.models import User
# db['user'] = User(name='Alice', age=30)

# This is rejected (dangerous functions like os.system)
```

## Table Functionality

### Using Multiple Tables

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# Main table
db['global_setting'] = 'value'

# Users table
users = db.table('users')
users['alice'] = {'name': 'Alice Smith', 'age': 30, 'email': 'alice@example.com'}
users['bob'] = {'name': 'Bob Johnson', 'age': 25, 'email': 'bob@example.com'}

# Settings table
settings = db.table('settings')
settings['theme'] = 'dark'
settings['language'] = 'en'
settings['notifications'] = True

# Each table is independent
print(list(db.keys()))          # -> ['global_setting']
print(list(users.keys()))       # -> ['alice', 'bob']
print(list(settings.keys()))    # -> ['theme', 'language', 'notifications']

# Operate per table
for key in users.keys():
    user = users[key]
    print(f"{user['name']}: {user['email']}")

db.close()
```

### Separate Table Mode

```python
from dictsqlite import DictSQLite

# Use completely separated SQLite tables
db = DictSQLite(':memory:', table_mode='separate')

# Each table is created as a separate SQLite table
products = db.table('products')
products['p001'] = {'name': 'Product A', 'price': 1000}
products['p002'] = {'name': 'Product B', 'price': 2000}

orders = db.table('orders')
orders['o001'] = {'product_id': 'p001', 'quantity': 5}

db.close()
```

## Bulk Operations

### Bulk Insert from Dictionary

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# Prepare large amount of data
data = {}
for i in range(10000):
    data[f'key_{i}'] = f'value_{i}'

# Bulk insert (fast)
db.bulk_insert(data)

print(f"Inserted {len(db)} items")

db.close()
```

### Bulk Insert from List

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# List of (key, value) tuples
items = [(f'key_{i}', {'id': i, 'data': f'value_{i}'}) for i in range(1000)]

# Bulk insert
db.bulk_insert(items)

db.close()
```

## Async Operations

### Basic Async Operations

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # Async set
    await db.aset('key1', 'value1')
    await db.aset('key2', {'nested': 'data'})
    
    # Async get
    value1 = await db.aget('key1')
    value2 = await db.aget('key2')
    
    print(value1)  # -> 'value1'
    print(value2)  # -> {'nested': 'data'}
    
    # Check existence
    exists = await db.acontains('key1')
    print(exists)  # -> True
    
    # Delete
    await db.adelete('key1')
    
    # Flush and close
    await db.aflush()
    await db.aclose()

asyncio.run(main())
```

### Batch Operations

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # Batch set
    items = [
        ('user1', {'name': 'Alice'}),
        ('user2', {'name': 'Bob'}),
        ('user3', {'name': 'Charlie'})
    ]
    await db.abatch_set(items)
    
    # Batch get
    keys = ['user1', 'user2', 'user3']
    values = await db.abatch_get(keys)
    
    for key, value in zip(keys, values):
        if value:
            print(f"{key}: {value}")
    
    await db.aclose()

asyncio.run(main())
```

### Async Context Manager

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    async with AsyncDictSQLite('async_data.db') as db:
        await db.aset('test', {'data': 'value'})
        result = await db.aget('test')
        print(result)
    # Automatically closed

asyncio.run(main())
```

### Concurrent Operations

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def write_data(db, key, value):
    await db.aset(key, value)

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # Execute multiple writes concurrently
    tasks = []
    for i in range(100):
        task = write_data(db, f'key_{i}', f'value_{i}')
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    print(f"Wrote {len(tasks)} items concurrently")
    
    await db.aclose()

asyncio.run(main())
```

## Storage Modes

### Pickle Mode (Default)

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='pickle')

# Store complex Python objects
db['data'] = {
    'list': [1, 2, 3, 4, 5],
    'tuple': (10, 20, 30),
    'set': {100, 200, 300},
    'nested': {
        'deep': {
            'structure': 'value'
        }
    }
}

# Retrieve as-is
data = db['data']
print(data['list'])   # -> [1, 2, 3, 4, 5]
print(data['tuple'])  # -> (10, 20, 30)

db.close()
```

### JSONB Mode

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='jsonb')

# Store JSON-compatible data
db['user'] = {
    'name': 'Alice',
    'age': 30,
    'tags': ['python', 'rust', 'database'],
    'active': True
}

print(db['user'])

db.close()
```

### JSON Mode

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='json')

# Standard JSON
db['config'] = {
    'version': '2.0.7',
    'features': ['encryption', 'async', 'safe_pickle']
}

db.close()
```

### Bytes Mode

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='bytes')

# Store binary data
db['binary'] = b'\x00\x01\x02\x03\x04'
db['image'] = b'PNG\x89...'  # Image data, etc.

# Retrieve as-is
binary_data = db['binary']
print(type(binary_data))  # -> <class 'bytes'>

db.close()
```

## Persistence Modes

### Memory Mode

```python
from dictsqlite import DictSQLite

# Memory only, no persistence (fastest)
db = DictSQLite('temp.db', persist_mode='memory')

db['temp_data'] = 'This will not be persisted'

db.close()
# Data is lost
```

### Lazy Mode

```python
from dictsqlite import DictSQLite

# Persist on flush
db = DictSQLite('lazy.db', persist_mode='lazy')

# Save to memory (not persisted yet)
for i in range(1000):
    db[f'key_{i}'] = f'value_{i}'

# Manual flush
db.flush()  # Persisted here

db.close()  # Also automatically flushes on close
```

### Writethrough Mode (Default)

```python
from dictsqlite import DictSQLite

# Immediate persistence (safest)
db = DictSQLite('writethrough.db', persist_mode='writethrough')

# Each write is immediately persisted
db['important'] = 'This is immediately persisted'

# Data is safe even if program crashes

db.close()
```

## Practical Examples

### Session Management

```python
from dictsqlite import DictSQLite
import uuid
import datetime

class SessionManager:
    def __init__(self, db_path='sessions.db'):
        self.db = DictSQLite(
            db_path,
            encryption_password='session_secret_key',
            persist_mode='writethrough'
        )
        self.sessions = self.db.table('sessions')
    
    def create_session(self, user_id):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.datetime.now().isoformat(),
            'last_access': datetime.datetime.now().isoformat()
        }
        return session_id
    
    def get_session(self, session_id):
        return self.sessions.get(session_id)
    
    def update_access(self, session_id):
        session = self.sessions.get(session_id)
        if session:
            session['last_access'] = datetime.datetime.now().isoformat()
            self.sessions[session_id] = session
    
    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def close(self):
        self.db.close()

# Usage
manager = SessionManager()
session_id = manager.create_session('user_123')
print(f"Created session: {session_id}")

session = manager.get_session(session_id)
print(f"Session data: {session}")

manager.close()
```

### Cache System

```python
from dictsqlite import DictSQLite
import time

class Cache:
    def __init__(self, ttl=3600):
        self.db = DictSQLite(':memory:', hot_capacity=10000)
        self.cache = self.db.table('cache')
        self.ttl = ttl
    
    def set(self, key, value):
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def get(self, key):
        data = self.cache.get(key)
        if data is None:
            return None
        
        # TTL check
        if time.time() - data['timestamp'] > self.ttl:
            del self.cache[key]
            return None
        
        return data['value']
    
    def clear(self):
        self.cache.clear()
    
    def close(self):
        self.db.close()

# Usage
cache = Cache(ttl=60)
cache.set('user:123', {'name': 'Alice', 'role': 'admin'})

user = cache.get('user:123')
print(user)  # -> {'name': 'Alice', 'role': 'admin'}

cache.close()
```

### Configuration Management

```python
from dictsqlite import DictSQLite

class ConfigManager:
    def __init__(self, config_file='config.db'):
        self.db = DictSQLite(
            config_file,
            persist_mode='writethrough',
            storage_mode='jsonb'
        )
        self.config = self.db.table('config')
        self._load_defaults()
    
    def _load_defaults(self):
        defaults = {
            'app_name': 'MyApp',
            'version': '1.0.0',
            'debug': False,
            'max_connections': 100,
            'timeout': 30
        }
        
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
    
    def get_all(self):
        return dict(self.config.items())
    
    def close(self):
        self.db.close()

# Usage
config = ConfigManager()
print(config.get('app_name'))  # -> 'MyApp'
config.set('debug', True)
print(config.get_all())

config.close()
```

### Async Logging System

```python
from dictsqlite import AsyncDictSQLite
import asyncio
import datetime

class AsyncLogger:
    def __init__(self, log_file='logs.db'):
        self.db = None
        self.log_file = log_file
    
    async def __aenter__(self):
        self.db = AsyncDictSQLite(self.log_file, buffer_size=1000)
        self.logs = self.db.table('logs')
        return self
    
    async def __aexit__(self, *args):
        await self.db.aclose()
    
    async def log(self, level, message):
        timestamp = datetime.datetime.now().isoformat()
        log_id = f"{timestamp}_{level}"
        
        await self.db.aset(log_id, {
            'level': level,
            'message': message,
            'timestamp': timestamp
        })
    
    async def info(self, message):
        await self.log('INFO', message)
    
    async def error(self, message):
        await self.log('ERROR', message)
    
    async def warning(self, message):
        await self.log('WARNING', message)

# Usage
async def main():
    async with AsyncLogger() as logger:
        await logger.info('Application started')
        await logger.warning('Low memory warning')
        await logger.error('Database connection failed')

asyncio.run(main())
```

## Summary

DictSQLite v2 provides advanced features through a simple dictionary interface:

- ✅ Fast read/write operations
- ✅ Security through encryption
- ✅ Safety through Safe Pickle
- ✅ Flexible storage modes
- ✅ Async support
- ✅ Multi-table functionality

For more detailed information, see [README_EN.md](README_EN.md).

