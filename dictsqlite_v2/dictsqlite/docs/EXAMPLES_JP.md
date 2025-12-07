# DictSQLite v2 — 使用例（日本語）

このドキュメントでは、DictSQLite v2の実践的な使用例を紹介します。

## 目次

1. [基本的な使い方](#基本的な使い方)
2. [暗号化](#暗号化)
3. [Safe Pickle](#safe-pickle)
4. [テーブル機能](#テーブル機能)
5. [一括操作](#一括操作)
6. [非同期操作](#非同期操作)
7. [ストレージモード](#ストレージモード)
8. [永続化モード](#永続化モード)
9. [実践的な例](#実践的な例)

## 基本的な使い方

### インポート

```python
# 推奨：標準的なインポート
from dictsqlite import DictSQLite

# 内部実装名を使う場合（後方互換性）
from dictsqlite import DictSQLiteV4
```

### シンプルな例

```python
from dictsqlite import DictSQLite

# メモリDBを作成
db = DictSQLite(':memory:')

# 文字列を保存
db['user:alice'] = 'Alice Smith'
db['user:bob'] = 'Bob Johnson'

# Pythonオブジェクトを保存（自動的にpickleされる）
db['config'] = {
    'theme': 'dark',
    'language': 'ja',
    'notifications': True
}

# 値を取得
print(db['user:alice'])        # -> 'Alice Smith'
print(db['config']['theme'])   # -> 'dark'

# デフォルト値付き取得
print(db.get('missing', 'default'))  # -> 'default'

# キーの存在確認
if 'user:alice' in db:
    print("Alice exists!")

# イテレーション
for key in db.keys():
    print(f"{key}: {db[key]}")

db.close()
```

### コンテキストマネージャ

```python
from dictsqlite import DictSQLite

# 自動的にクローズされる
with DictSQLite('myapp.db') as db:
    db['setting1'] = 'value1'
    db['setting2'] = 'value2'
    
    # 処理...
    
# ここで自動的にフラッシュしてクローズ
```

### ファイルDBと永続化

```python
from dictsqlite import DictSQLite

# ファイルDBを作成
db = DictSQLite('data.db', persist_mode="writethrough")

# データを保存（即座に永続化）
db['persistent_data'] = {'important': 'information'}

db.close()

# 再度開いてデータを読み込む
db = DictSQLite('data.db')
print(db['persistent_data'])  # -> {'important': 'information'}
db.close()
```

## 暗号化

### 基本的な暗号化

```python
from dictsqlite import DictSQLite

# 暗号化を有効化
db = DictSQLite(
    'secure.db',
    encryption_password='my_secret_password_123'
)

# 機密データを保存
db['api_key'] = 'sk-1234567890abcdef'
db['user_token'] = {'token': 'xyz', 'expires': '2025-12-31'}

# 暗号化が有効か確認
stats = db.stats()
print(f"Encryption enabled: {stats['encryption_enabled']}")  # -> True

db.close()
```

### 暗号化されたDBを開く

```python
from dictsqlite import DictSQLite

# 同じパスワードで開く
db = DictSQLite(
    'secure.db',
    encryption_password='my_secret_password_123'
)

# データにアクセス
print(db['api_key'])  # -> 'sk-1234567890abcdef'

db.close()
```

### 暗号化 + JSONBモード

```python
from dictsqlite import DictSQLite

db = DictSQLite(
    'encrypted_json.db',
    encryption_password='password',
    storage_mode='jsonb'
)

# JSON互換データを暗号化して保存
db['user_data'] = {
    'name': 'Alice',
    'email': 'alice@example.com',
    'ssn': '123-45-6789'
}

db.close()
```

## Safe Pickle

### Safe Pickleを有効化

```python
from dictsqlite import DictSQLite

# Safe Pickleを有効化
db = DictSQLite(
    ':memory:',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp', 'mylib']
)

# 安全なデータを保存
db['data'] = {
    'numbers': [1, 2, 3],
    'text': 'Hello',
    'nested': {'key': 'value'}
}

# 許可されていないモジュールのオブジェクトは拒否される
```

### カスタムクラスとSafe Pickle

```python
from dictsqlite import DictSQLite

# myapp.modelsモジュールのクラスを許可
db = DictSQLite(
    ':memory:',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp.models']
)

# これは許可される（myapp.modelsのクラス）
# from myapp.models import User
# db['user'] = User(name='Alice', age=30)

# これは拒否される（os.systemなどの危険な関数）
```

## テーブル機能

### 複数のテーブルを使用

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# メインテーブル
db['global_setting'] = 'value'

# ユーザーテーブル
users = db.table('users')
users['alice'] = {'name': 'Alice Smith', 'age': 30, 'email': 'alice@example.com'}
users['bob'] = {'name': 'Bob Johnson', 'age': 25, 'email': 'bob@example.com'}

# 設定テーブル
settings = db.table('settings')
settings['theme'] = 'dark'
settings['language'] = 'ja'
settings['notifications'] = True

# 各テーブルは独立している
print(list(db.keys()))          # -> ['global_setting']
print(list(users.keys()))       # -> ['alice', 'bob']
print(list(settings.keys()))    # -> ['theme', 'language', 'notifications']

# テーブルごとに操作
for key in users.keys():
    user = users[key]
    print(f"{user['name']}: {user['email']}")

db.close()
```

### Separateテーブルモード

```python
from dictsqlite import DictSQLite

# 完全に分離されたSQLiteテーブルを使用
db = DictSQLite(':memory:', table_mode='separate')

# 各テーブルは個別のSQLiteテーブルとして作成される
products = db.table('products')
products['p001'] = {'name': 'Product A', 'price': 1000}
products['p002'] = {'name': 'Product B', 'price': 2000}

orders = db.table('orders')
orders['o001'] = {'product_id': 'p001', 'quantity': 5}

db.close()
```

## 一括操作

### 辞書から一括挿入

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# 大量のデータを準備
data = {}
for i in range(10000):
    data[f'key_{i}'] = f'value_{i}'

# 一括挿入（高速）
db.bulk_insert(data)

print(f"Inserted {len(db)} items")

db.close()
```

### リストから一括挿入

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# (key, value)タプルのリスト
items = [(f'key_{i}', {'id': i, 'data': f'value_{i}'}) for i in range(1000)]

# 一括挿入
db.bulk_insert(items)

db.close()
```

## 非同期操作

### 基本的な非同期操作

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # 非同期で設定
    await db.aset('key1', 'value1')
    await db.aset('key2', {'nested': 'data'})
    
    # 非同期で取得
    value1 = await db.aget('key1')
    value2 = await db.aget('key2')
    
    print(value1)  # -> 'value1'
    print(value2)  # -> {'nested': 'data'}
    
    # 存在確認
    exists = await db.acontains('key1')
    print(exists)  # -> True
    
    # 削除
    await db.adelete('key1')
    
    # フラッシュとクローズ
    await db.aflush()
    await db.aclose()

asyncio.run(main())
```

### バッチ操作

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # バッチ設定
    items = [
        ('user1', {'name': 'Alice'}),
        ('user2', {'name': 'Bob'}),
        ('user3', {'name': 'Charlie'})
    ]
    await db.abatch_set(items)
    
    # バッチ取得
    keys = ['user1', 'user2', 'user3']
    values = await db.abatch_get(keys)
    
    for key, value in zip(keys, values):
        if value:
            print(f"{key}: {value}")
    
    await db.aclose()

asyncio.run(main())
```

### 非同期コンテキストマネージャ

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    async with AsyncDictSQLite('async_data.db') as db:
        await db.aset('test', {'data': 'value'})
        result = await db.aget('test')
        print(result)
    # 自動的にクローズ

asyncio.run(main())
```

### 並行操作

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def write_data(db, key, value):
    await db.aset(key, value)

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # 複数の書き込みを並行実行
    tasks = []
    for i in range(100):
        task = write_data(db, f'key_{i}', f'value_{i}')
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    print(f"Wrote {len(tasks)} items concurrently")
    
    await db.aclose()

asyncio.run(main())
```

## ストレージモード

### Pickleモード（デフォルト）

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='pickle')

# 複雑なPythonオブジェクトを保存
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

# そのまま取得できる
data = db['data']
print(data['list'])   # -> [1, 2, 3, 4, 5]
print(data['tuple'])  # -> (10, 20, 30)

db.close()
```

### JSONBモード

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='jsonb')

# JSON互換データを保存
db['user'] = {
    'name': 'Alice',
    'age': 30,
    'tags': ['python', 'rust', 'database'],
    'active': True
}

print(db['user'])

db.close()
```

### JSONモード

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='json')

# 標準JSON
db['config'] = {
    'version': '2.0.7',
    'features': ['encryption', 'async', 'safe_pickle']
}

db.close()
```

### Bytesモード

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:', storage_mode='bytes')

# バイナリデータを保存
db['binary'] = b'\x00\x01\x02\x03\x04'
db['image'] = b'PNG\x89...'  # 画像データなど

# そのまま取得
binary_data = db['binary']
print(type(binary_data))  # -> <class 'bytes'>

db.close()
```

## 永続化モード

### Memoryモード

```python
from dictsqlite import DictSQLite

# メモリのみ、永続化なし（最速）
db = DictSQLite('temp.db', persist_mode='memory')

db['temp_data'] = 'This will not be persisted'

db.close()
# データは失われる
```

### Lazyモード

```python
from dictsqlite import DictSQLite

# フラッシュ時に永続化
db = DictSQLite('lazy.db', persist_mode='lazy')

# メモリに保存（まだ永続化されない）
for i in range(1000):
    db[f'key_{i}'] = f'value_{i}'

# 手動でフラッシュ
db.flush()  # ここで永続化

db.close()  # クローズ時も自動的にフラッシュ
```

### Writethroughモード（デフォルト）

```python
from dictsqlite import DictSQLite

# 即座に永続化（最も安全）
db = DictSQLite('writethrough.db', persist_mode='writethrough')

# 各書き込みが即座に永続化される
db['important'] = 'This is immediately persisted'

# プログラムがクラッシュしてもデータは安全

db.close()
```

## 実践的な例

### セッション管理

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

# 使用例
manager = SessionManager()
session_id = manager.create_session('user_123')
print(f"Created session: {session_id}")

session = manager.get_session(session_id)
print(f"Session data: {session}")

manager.close()
```

### キャッシュシステム

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
        
        # TTLチェック
        if time.time() - data['timestamp'] > self.ttl:
            del self.cache[key]
            return None
        
        return data['value']
    
    def clear(self):
        self.cache.clear()
    
    def close(self):
        self.db.close()

# 使用例
cache = Cache(ttl=60)
cache.set('user:123', {'name': 'Alice', 'role': 'admin'})

user = cache.get('user:123')
print(user)  # -> {'name': 'Alice', 'role': 'admin'}

cache.close()
```

### 設定管理

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

# 使用例
config = ConfigManager()
print(config.get('app_name'))  # -> 'MyApp'
config.set('debug', True)
print(config.get_all())

config.close()
```

### 非同期ログシステム

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

# 使用例
async def main():
    async with AsyncLogger() as logger:
        await logger.info('Application started')
        await logger.warning('Low memory warning')
        await logger.error('Database connection failed')

asyncio.run(main())
```

## まとめ

DictSQLite v2は、シンプルな辞書インターフェースで高度な機能を提供します：

- ✅ 高速な読み書き
- ✅ 暗号化によるセキュリティ
- ✅ Safe Pickleによる安全性
- ✅ 柔軟なストレージモード
- ✅ 非同期サポート
- ✅ 複数テーブル機能

より詳しい情報は、[README_JP.md](README_JP.md)を参照してください。

