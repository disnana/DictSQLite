# DictSQLite v4.1 開発者ガイド（日本語）

## 目次

1. [概要](#概要)
2. [クイックスタート](#クイックスタート)
3. [同期API詳細](#同期api詳細)
4. [非同期API詳細](#非同期api詳細)
5. [永続化モード選択ガイド](#永続化モード選択ガイド)
6. [パフォーマンス最適化](#パフォーマンス最適化)
7. [セキュリティ機能](#セキュリティ機能)
8. [ベストプラクティス](#ベストプラクティス)
9. [トラブルシューティング](#トラブルシューティング)
10. [実践例](#実践例)

---

## 概要

DictSQLite v4.1は、Pythonの辞書ライクなインターフェースでSQLiteを操作できる高性能ライブラリです。Rustで実装され、以下の特徴があります:

### 主要機能

- ✅ **高速**: 平均 1.2M ops/sec、最大 4.6M ops/sec
- ✅ **3層アーキテクチャ**: Hot Tier (メモリ) → Warm Tier → Cold Tier (SQLite)
- ✅ **LRU自動管理**: メモリ使用量を自動制御
- ✅ **3つの永続化モード**: Memory / Lazy / WriteThrough
- ✅ **暗号化対応**: AES-256-GCM
- ✅ **辞書互換API**: Python標準辞書と同じインターフェース
- ✅ **非同期サポート**: AsyncDictSQLite で高速並行処理

### パフォーマンス概要

| 操作 | 速度 (ops/sec) | 用途 |
|------|----------------|------|
| 基本的な読み書き | 1.2M - 2.4M | 一般的な用途 |
| 削除操作 | 4.6M | 高速クリーンアップ |
| バルク操作 | 2.3M - 2.5M | 大量データ処理 |
| 暗号化操作 | 600K - 1.7M | セキュアなデータ保存 |

---

## クイックスタート

### インストール

```bash
# Rustツールチェーンをインストール
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# プロジェクトをビルド
cd others/beta-versions/dictsqlite_v4.1
cargo build --release
maturin develop --release
```

### 最もシンプルな使い方

```python
from dictsqlite_v4 import DictSQLiteV4

# 基本的な使い方
db = DictSQLiteV4('data.db')

# 書き込み
db['key'] = 'value'
db['user:1'] = {'name': 'Alice', 'age': 30}

# 読み込み
print(db['key'])  # 'value'
print(db['user:1'])  # {'name': 'Alice', 'age': 30}

# 削除
del db['key']

# クローズ
db.close()
```

---

## 同期API詳細

### 初期化パラメータ

```python
DictSQLiteV4(
    db_path: str,                           # データベースファイルパス
    hot_capacity: int = 1_000_000,          # Hot Tierの容量
    enable_async: bool = True,              # 非同期フラッシュの有効化
    persist_mode: str = "writethrough",     # 永続化モード
    encryption_password: str = None,        # 暗号化パスワード
    enable_safe_pickle: bool = False,       # Safe Pickle検証
    safe_pickle_allowed_modules: list = None  # 許可するモジュールリスト
)
```

#### パラメータ詳細

**db_path**
- データベースファイルのパス
- 存在しない場合は自動作成
- 例: `'data.db'`, `'/tmp/cache.db'`, `':memory:'`

**hot_capacity**
- メモリ上に保持する最大アイテム数
- LRUエビクションの閾値
- 推奨値:
  - 小規模: 10,000
  - 中規模: 100,000
  - 大規模: 1,000,000

**enable_async**
- バックグラウンド非同期フラッシュを有効化
- `True`: パフォーマンス優先（推奨）
- `False`: データ一貫性優先

**persist_mode**
- `"memory"`: メモリのみ（永続化なし、最速）
- `"lazy"`: 遅延書き込み（高速、定期的にフラッシュ必要）
- `"writethrough"`: 即座に永続化（安全、やや低速）

**encryption_password**
- AES-256-GCM暗号化のパスワード
- `None`: 暗号化なし
- 文字列: 暗号化有効

### 基本操作

#### 辞書ライクな操作

```python
db = DictSQLiteV4('data.db')

# 書き込み
db['key1'] = 'value1'
db['key2'] = {'nested': 'data'}
db['key3'] = [1, 2, 3, 4, 5]

# 読み込み
value = db['key1']              # 'value1'
value = db.get('key1')          # 'value1'
value = db.get('missing', 42)   # 42 (デフォルト値)

# 存在チェック
if 'key1' in db:
    print('存在します')

# 削除
del db['key1']

# サイズ
count = len(db)

# キー一覧
keys = db.keys()        # すべてのキー
items = db.items()      # (key, value) のペア
values = db.values()    # すべての値
```

#### 高度な操作

```python
# setdefault: キーが存在しなければ設定
value = db.setdefault('counter', 0)  # 初回は0を設定して返す

# pop: 削除して値を返す
value = db.pop('key1', None)  # キーを削除して値を返す

# update: 複数のキーを一括更新
db.update({
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3'
})

# clear: すべてクリア
db.clear()
```

#### バルク操作（高速）

```python
# bulk_insert: 大量データを高速挿入
data = {f'key_{i}': f'value_{i}' for i in range(10000)}
db.bulk_insert(data)  # 2.3M ops/sec

# バッチ読み込み
keys = [f'key_{i}' for i in range(1000)]
for key in keys:
    value = db.get(key)
```

### 永続化制御

```python
# Lazyモードでの明示的フラッシュ
db = DictSQLiteV4('data.db', persist_mode='lazy')
db['key'] = 'value'
db.flush()  # ディスクに書き込み

# 安全なクローズ（自動フラッシュ）
db.close()

# コンテキストマネージャー（推奨）
with DictSQLiteV4('data.db') as db:
    db['key'] = 'value'
# 自動的にflush()とclose()が呼ばれる
```

### パフォーマンス測定

```python
import time

db = DictSQLiteV4('benchmark.db', persist_mode='memory')

# 書き込みベンチマーク
start = time.perf_counter()
for i in range(10000):
    db[f'key_{i}'] = f'value_{i}'
elapsed = time.perf_counter() - start
ops_per_sec = 10000 / elapsed
print(f'Write: {ops_per_sec:,.0f} ops/sec')

# 読み込みベンチマーク
start = time.perf_counter()
for i in range(10000):
    _ = db[f'key_{i}']
elapsed = time.perf_counter() - start
ops_per_sec = 10000 / elapsed
print(f'Read: {ops_per_sec:,.0f} ops/sec')

db.close()
```

---

## 非同期API詳細

### 基本的な使い方

```python
import asyncio
from dictsqlite_v4 import AsyncDictSQLite

async def main():
    # 初期化
    db = AsyncDictSQLite('async_data.db', persist_mode='lazy')
    
    # 非同期書き込み
    await db.set_async('key1', 'value1')
    
    # 非同期読み込み
    value = await db.get_async('key1')
    print(value)  # 'value1'
    
    # フラッシュとクローズ
    await db.flush()
    await db.close()

# 実行
asyncio.run(main())
```

### 並行処理（高性能）

```python
import asyncio
from dictsqlite_v4 import AsyncDictSQLite

async def main():
    db = AsyncDictSQLite('concurrent.db', persist_mode='lazy')
    
    # 並行書き込み（高速）
    tasks = [
        db.set_async(f'key_{i}', f'value_{i}')
        for i in range(1000)
    ]
    await asyncio.gather(*tasks)  # すべて並行実行
    
    # 並行読み込み（高速）
    tasks = [
        db.get_async(f'key_{i}')
        for i in range(1000)
    ]
    results = await asyncio.gather(*tasks)
    
    await db.flush()
    await db.close()

asyncio.run(main())
```

### セマフォによる同時実行制御

```python
import asyncio
from dictsqlite_v4 import AsyncDictSQLite

async def main():
    db = AsyncDictSQLite('controlled.db', persist_mode='lazy')
    
    # 同時実行数を制限
    semaphore = asyncio.Semaphore(10)  # 最大10並行
    
    async def limited_write(key, value):
        async with semaphore:
            await db.set_async(key, value)
    
    # 大量のタスクを制御された並行数で実行
    tasks = [
        limited_write(f'key_{i}', f'value_{i}')
        for i in range(10000)
    ]
    await asyncio.gather(*tasks)
    
    await db.flush()
    await db.close()

asyncio.run(main())
```

### バッチ処理のベストプラクティス

```python
async def batch_process(db, data_chunks):
    """大量データを効率的に処理"""
    
    for chunk in data_chunks:
        # チャンクごとに並行書き込み
        tasks = [
            db.set_async(key, value)
            for key, value in chunk.items()
        ]
        await asyncio.gather(*tasks)
        
        # チャンクごとにフラッシュ（メモリ管理）
        await db.flush()

# 使用例
async def main():
    db = AsyncDictSQLite('batch.db', persist_mode='lazy')
    
    # データを1000アイテムずつのチャンクに分割
    all_data = {f'key_{i}': f'value_{i}' for i in range(100000)}
    chunk_size = 1000
    chunks = [
        dict(list(all_data.items())[i:i+chunk_size])
        for i in range(0, len(all_data), chunk_size)
    ]
    
    await batch_process(db, chunks)
    await db.close()

asyncio.run(main())
```

---

## 永続化モード選択ガイド

### モード比較表

| モード | 速度 | 永続性 | メモリ | 用途 |
|--------|------|--------|--------|------|
| **Memory** | ⚡⚡⚡ 最速 (1.4M ops/sec) | ❌ なし | 💾💾 大 | 一時キャッシュ、テスト |
| **Lazy** | ⚡⚡ 高速 (1.3M ops/sec) | ✅ 定期的 | 💾 中 | 通常のアプリケーション（推奨） |
| **WriteThrough** | ⚡ 低速 (20K ops/sec) | ✅✅ 即座 | 💾 小 | 金融、ログ、重要データ |

### Memory モード

**特徴:**
- データは一切ディスクに保存されない
- プロセス終了時にデータ消失
- 最高速度: 1,378,988 ops/sec

**推奨用途:**
```python
# セッションキャッシュ
session_cache = DictSQLiteV4(':memory:', persist_mode='memory')
session_cache[f'user_{user_id}'] = user_data

# 一時的な計算結果
temp_results = DictSQLiteV4('temp.db', persist_mode='memory')
for result in compute_intensive_task():
    temp_results[result.id] = result.data
```

**注意点:**
- データは永続化されない
- アプリケーション再起動後はデータなし

### Lazy モード（推奨）

**特徴:**
- 書き込みはメモリに保持、定期的にディスクへフラッシュ
- 高速: 1,316,355 ops/sec
- バランスの取れた性能と信頼性

**推奨用途:**
```python
# Webアプリケーションのキャッシュ
cache = DictSQLiteV4('app_cache.db', persist_mode='lazy', hot_capacity=100000)
cache[f'api_response_{key}'] = response_data

# 定期的にフラッシュ
import threading
def periodic_flush():
    while True:
        time.sleep(300)  # 5分ごと
        cache.flush()

threading.Thread(target=periodic_flush, daemon=True).start()
```

**フラッシュタイミング:**
```python
# 手動フラッシュ
db.flush()

# アプリケーション終了時
import atexit
atexit.register(db.flush)

# 定期的なフラッシュ（推奨）
import schedule
schedule.every(5).minutes.do(db.flush)
```

### WriteThrough モード

**特徴:**
- 各書き込みを即座にディスクへ永続化
- データ損失リスク最小
- 低速: 20,400 ops/sec

**推奨用途:**
```python
# 金融取引ログ
transaction_log = DictSQLiteV4(
    'transactions.db',
    persist_mode='writethrough'
)
transaction_log[transaction_id] = {
    'amount': 1000.00,
    'timestamp': time.time(),
    'status': 'completed'
}
# 即座にディスクに保存される

# 監査ログ
audit_log = DictSQLiteV4('audit.db', persist_mode='writethrough')
audit_log[f'event_{event_id}'] = audit_event
```

**最適化:**
```python
# バルク操作を使用（WriteThroughでも高速化）
transactions = {
    f'tx_{i}': {'amount': i * 100, 'status': 'pending'}
    for i in range(1000)
}
transaction_log.bulk_insert(transactions)  # 一括挿入は高速
```

---

## パフォーマンス最適化

### 1. 適切なhot_capacity設定

```python
# データ量に応じて調整
small_db = DictSQLiteV4('small.db', hot_capacity=10_000)      # < 10K items
medium_db = DictSQLiteV4('medium.db', hot_capacity=100_000)   # < 100K items
large_db = DictSQLiteV4('large.db', hot_capacity=1_000_000)   # < 1M items
```

**計算式:**
```python
# 推奨容量 = 予想データ量 * 0.2（20%をホットに保持）
estimated_items = 500_000
hot_capacity = int(estimated_items * 0.2)
db = DictSQLiteV4('data.db', hot_capacity=hot_capacity)
```

### 2. バルク操作の活用

```python
# 🐌 遅い: ループで個別挿入
for i in range(10000):
    db[f'key_{i}'] = f'value_{i}'  # 1.2M ops/sec

# ⚡ 高速: バルク挿入
data = {f'key_{i}': f'value_{i}' for i in range(10000)}
db.bulk_insert(data)  # 2.3M ops/sec（約2倍高速）
```

### 3. 適切なモード選択

```python
# 読み込み頻度が高い場合
read_heavy_db = DictSQLiteV4(
    'read_heavy.db',
    persist_mode='lazy',      # 高速読み込み
    hot_capacity=500_000      # 大きめのキャッシュ
)

# 書き込み頻度が高い場合
write_heavy_db = DictSQLiteV4(
    'write_heavy.db',
    persist_mode='lazy',      # 高速書き込み
    enable_async=True         # 非同期フラッシュ
)

# データ損失が許容できない場合
critical_db = DictSQLiteV4(
    'critical.db',
    persist_mode='writethrough'  # 安全性優先
)
```

### 4. 非同期処理の活用

```python
import asyncio

async def fast_batch_write():
    db = AsyncDictSQLite('async.db', persist_mode='lazy')
    
    # 並行書き込み（高速）
    tasks = [db.set_async(f'key_{i}', f'value_{i}') for i in range(10000)]
    await asyncio.gather(*tasks)
    
    await db.flush()
    await db.close()

# 同期版より高速
asyncio.run(fast_batch_write())
```

### 5. LRUエビクションの理解

```python
# LRUエビクションが発生する場合
db = DictSQLiteV4('data.db', hot_capacity=1000)

# 1000アイテムまでは高速（メモリから）
for i in range(1000):
    db[f'key_{i}'] = f'value_{i}'  # 超高速

# 1001個目からエビクション発生
db['key_1000'] = 'value_1000'  # やや低速（古いデータをディスクへ）

# 読み込みは透過的（自動的にディスクから取得）
value = db['key_0']  # エビクションされていても取得可能
```

### 6. メモリ効率化

```python
# Pickle処理のオーバーヘッドを避ける
# ✅ 良い: シンプルな型
db['key'] = 'string'
db['key'] = 12345
db['key'] = [1, 2, 3]
db['key'] = {'simple': 'dict'}

# ⚠️ 注意: 複雑なオブジェクトは遅い
class ComplexObject:
    def __init__(self):
        self.data = [i for i in range(10000)]

db['key'] = ComplexObject()  # Pickle化のオーバーヘッド
```

---

## セキュリティ機能

### AES-256-GCM暗号化

```python
# 暗号化を有効化
secure_db = DictSQLiteV4(
    'secure.db',
    encryption_password='my_secure_password_123'
)

# 通常通り使用（透過的に暗号化）
secure_db['secret_key'] = 'confidential_data'
value = secure_db['secret_key']  # 自動的に復号化

secure_db.close()
```

**パフォーマンス:**
- 暗号化書き込み: 600K ops/sec（暗号化なしの約50%）
- 暗号化読み込み: 1.7M ops/sec（暗号化なしの約72%）

**推奨用途:**
```python
# ユーザー認証情報
auth_db = DictSQLiteV4(
    'auth.db',
    encryption_password=os.environ['DB_PASSWORD'],
    persist_mode='writethrough'  # 安全性優先
)
auth_db[f'user_{user_id}'] = {
    'password_hash': hash_password(password),
    'salt': salt,
    'mfa_secret': mfa_secret
}

# 機密ログ
audit_db = DictSQLiteV4(
    'audit.db',
    encryption_password=config['audit_password'],
    persist_mode='writethrough'
)
```

### Safe Pickle検証

```python
# Pickle検証を有効化
safe_db = DictSQLiteV4(
    'safe.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['datetime', 'decimal', 'myapp.models']
)

# 許可されたモジュールのみデシリアライズ可能
from datetime import datetime
safe_db['timestamp'] = datetime.now()  # ✅ OK

# 不正なモジュールは拒否
import pickle
malicious_data = pickle.dumps(eval)  # ⚠️ 危険
# safe_db['bad'] = malicious_data  # ❌ エラー
```

### パスワード管理のベストプラクティス

```python
import os
from getpass import getpass

# 環境変数から取得（推奨）
password = os.environ.get('DB_PASSWORD')
if not password:
    password = getpass('Enter database password: ')

db = DictSQLiteV4('secure.db', encryption_password=password)

# パスワードを変数から削除
password = None
```

---

## ベストプラクティス

### 1. コンテキストマネージャーの使用

```python
# ✅ 推奨: 自動的にクローズ
with DictSQLiteV4('data.db') as db:
    db['key'] = 'value'
# 自動的にflush()とclose()

# ❌ 非推奨: 手動クローズ
db = DictSQLiteV4('data.db')
db['key'] = 'value'
db.close()  # 忘れやすい
```

### 2. 例外処理

```python
from dictsqlite_v4 import DictSQLiteV4

try:
    with DictSQLiteV4('data.db') as db:
        value = db['nonexistent_key']
except KeyError:
    print('キーが存在しません')
except Exception as e:
    print(f'エラー: {e}')
```

### 3. 大量データの処理

```python
def process_large_dataset(data_source):
    with DictSQLiteV4('large.db', persist_mode='lazy', hot_capacity=100000) as db:
        batch = {}
        batch_size = 1000
        
        for i, item in enumerate(data_source):
            batch[item.id] = item.data
            
            # 1000件ごとにバルク挿入
            if len(batch) >= batch_size:
                db.bulk_insert(batch)
                batch.clear()
                
                # 10000件ごとにフラッシュ
                if i % 10000 == 0:
                    db.flush()
                    print(f'Processed {i} items')
        
        # 残りを挿入
        if batch:
            db.bulk_insert(batch)
        
        db.flush()
```

### 4. マルチプロセス対応

```python
from multiprocessing import Process
import time

def worker(worker_id, db_path):
    """各ワーカーは独自のDBインスタンスを持つ"""
    db = DictSQLiteV4(db_path, persist_mode='lazy')
    
    for i in range(1000):
        db[f'worker_{worker_id}_item_{i}'] = f'data_{i}'
    
    db.flush()
    db.close()

# 複数ワーカーで並行処理
processes = []
for i in range(4):
    p = Process(target=worker, args=(i, f'worker_{i}.db'))
    p.start()
    processes.append(p)

for p in processes:
    p.join()
```

### 5. ログ記録

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with DictSQLiteV4('data.db') as db:
    logger.info(f'Database opened with {len(db)} items')
    
    db['new_key'] = 'new_value'
    logger.info('Item added')
    
    db.flush()
    logger.info('Database flushed')
```

### 6. 定期的なメンテナンス

```python
import schedule
import time

def maintain_database():
    with DictSQLiteV4('data.db') as db:
        # 古いデータを削除
        current_time = time.time()
        expired_keys = [
            key for key in db.keys()
            if key.startswith('cache_') and is_expired(db[key], current_time)
        ]
        
        for key in expired_keys:
            del db[key]
        
        db.flush()
        print(f'Removed {len(expired_keys)} expired items')

# 1時間ごとにメンテナンス
schedule.every(1).hour.do(maintain_database)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## トラブルシューティング

### よくある問題と解決策

#### 1. メモリ不足エラー

**問題:**
```python
db = DictSQLiteV4('huge.db', hot_capacity=10_000_000)  # 大きすぎる
# MemoryError
```

**解決策:**
```python
# hot_capacityを減らす
db = DictSQLiteV4('huge.db', hot_capacity=500_000)

# またはLRUエビクションに任せる
db = DictSQLiteV4('huge.db', hot_capacity=100_000)  # 自動的にディスクへ退避
```

#### 2. パフォーマンスが遅い

**問題:**
```python
# WriteThroughモードで大量書き込み
db = DictSQLiteV4('data.db', persist_mode='writethrough')
for i in range(100000):
    db[f'key_{i}'] = f'value_{i}'  # 遅い: 20K ops/sec
```

**解決策:**
```python
# Lazyモードに変更
db = DictSQLiteV4('data.db', persist_mode='lazy')
for i in range(100000):
    db[f'key_{i}'] = f'value_{i}'  # 高速: 1.3M ops/sec
db.flush()

# またはバルク操作を使用
data = {f'key_{i}': f'value_{i}' for i in range(100000)}
db.bulk_insert(data)  # さらに高速: 2.3M ops/sec
```

#### 3. データ損失

**問題:**
```python
db = DictSQLiteV4('data.db', persist_mode='lazy')
db['important'] = 'data'
# プログラムがクラッシュ → データ損失
```

**解決策:**
```python
# 重要なデータはWriteThroughモード
critical_db = DictSQLiteV4('critical.db', persist_mode='writethrough')
critical_db['important'] = 'data'  # 即座に保存

# またはLazyモードで定期的にフラッシュ
db = DictSQLiteV4('data.db', persist_mode='lazy')
db['important'] = 'data'
db.flush()  # 明示的にフラッシュ
```

#### 4. 暗号化が遅い

**問題:**
```python
db = DictSQLiteV4('data.db', encryption_password='pass')
# 暗号化のオーバーヘッドで遅い
```

**解決策:**
```python
# 本当に暗号化が必要か検討
# 不要なら暗号化なしで使用
fast_db = DictSQLiteV4('data.db')  # 暗号化なし

# または機密データのみ暗号化
normal_db = DictSQLiteV4('normal.db')  # 通常データ
secure_db = DictSQLiteV4('secure.db', encryption_password='pass')  # 機密データ
```

#### 5. KeyError

**問題:**
```python
value = db['nonexistent_key']  # KeyError
```

**解決策:**
```python
# get()メソッドを使用
value = db.get('nonexistent_key', 'default_value')

# または存在チェック
if 'key' in db:
    value = db['key']

# または例外処理
try:
    value = db['key']
except KeyError:
    value = 'default_value'
```

---

## 実践例

### 例1: Webアプリケーションキャッシュ

```python
from dictsqlite_v4 import DictSQLiteV4
import time
import hashlib

class APICache:
    def __init__(self, cache_file='api_cache.db', ttl=3600):
        self.db = DictSQLiteV4(
            cache_file,
            persist_mode='lazy',
            hot_capacity=50000
        )
        self.ttl = ttl
    
    def get_cache_key(self, endpoint, params):
        """キャッシュキーを生成"""
        key_str = f"{endpoint}:{str(sorted(params.items()))}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, endpoint, params):
        """キャッシュから取得"""
        key = self.get_cache_key(endpoint, params)
        
        if key in self.db:
            cached = self.db[key]
            if time.time() - cached['timestamp'] < self.ttl:
                return cached['data']
        
        return None
    
    def set(self, endpoint, params, data):
        """キャッシュに保存"""
        key = self.get_cache_key(endpoint, params)
        self.db[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def cleanup(self):
        """期限切れキャッシュを削除"""
        current_time = time.time()
        expired = []
        
        for key in self.db.keys():
            cached = self.db[key]
            if current_time - cached['timestamp'] >= self.ttl:
                expired.append(key)
        
        for key in expired:
            del self.db[key]
        
        self.db.flush()
        return len(expired)
    
    def close(self):
        self.db.close()

# 使用例
cache = APICache(ttl=3600)  # 1時間のTTL

# APIレスポンスをキャッシュ
def fetch_user_data(user_id):
    endpoint = '/api/users'
    params = {'id': user_id}
    
    # キャッシュをチェック
    cached = cache.get(endpoint, params)
    if cached:
        print('Cache hit!')
        return cached
    
    # キャッシュミス: APIを呼び出し
    print('Cache miss, fetching from API...')
    data = call_external_api(endpoint, params)
    
    # キャッシュに保存
    cache.set(endpoint, params, data)
    return data

# 定期的なクリーンアップ
import schedule
schedule.every(1).hour.do(cache.cleanup)
```

### 例2: セッション管理

```python
from dictsqlite_v4 import DictSQLiteV4
import uuid
import time

class SessionManager:
    def __init__(self, session_file='sessions.db', timeout=1800):
        self.db = DictSQLiteV4(
            session_file,
            persist_mode='lazy',
            hot_capacity=10000
        )
        self.timeout = timeout
    
    def create_session(self, user_id, user_data):
        """新しいセッションを作成"""
        session_id = str(uuid.uuid4())
        self.db[session_id] = {
            'user_id': user_id,
            'user_data': user_data,
            'created_at': time.time(),
            'last_accessed': time.time()
        }
        return session_id
    
    def get_session(self, session_id):
        """セッションを取得"""
        if session_id not in self.db:
            return None
        
        session = self.db[session_id]
        
        # タイムアウトチェック
        if time.time() - session['last_accessed'] > self.timeout:
            del self.db[session_id]
            return None
        
        # アクセス時刻を更新
        session['last_accessed'] = time.time()
        self.db[session_id] = session
        
        return session
    
    def update_session(self, session_id, user_data):
        """セッションデータを更新"""
        if session_id in self.db:
            session = self.db[session_id]
            session['user_data'] = user_data
            session['last_accessed'] = time.time()
            self.db[session_id] = session
    
    def delete_session(self, session_id):
        """セッションを削除"""
        if session_id in self.db:
            del self.db[session_id]
    
    def cleanup_expired(self):
        """期限切れセッションを削除"""
        current_time = time.time()
        expired = []
        
        for session_id in self.db.keys():
            session = self.db[session_id]
            if current_time - session['last_accessed'] > self.timeout:
                expired.append(session_id)
        
        for session_id in expired:
            del self.db[session_id]
        
        self.db.flush()
        return len(expired)
    
    def close(self):
        self.db.flush()
        self.db.close()

# 使用例
sessions = SessionManager(timeout=1800)  # 30分タイムアウト

# セッション作成
session_id = sessions.create_session(
    user_id=123,
    user_data={'username': 'alice', 'role': 'admin'}
)

# セッション取得
session = sessions.get_session(session_id)
if session:
    print(f"User: {session['user_data']['username']}")

# セッション更新
sessions.update_session(session_id, {'username': 'alice', 'role': 'superadmin'})

# クリーンアップ（定期的に実行）
import schedule
schedule.every(10).minutes.do(sessions.cleanup_expired)
```

### 例3: ジョブキュー

```python
import asyncio
from dictsqlite_v4 import AsyncDictSQLite
import time
import uuid

class AsyncJobQueue:
    def __init__(self, queue_file='jobs.db'):
        self.db = AsyncDictSQLite(queue_file, persist_mode='lazy')
    
    async def enqueue(self, job_type, job_data, priority=5):
        """ジョブをキューに追加"""
        job_id = str(uuid.uuid4())
        await self.db.set_async(job_id, {
            'type': job_type,
            'data': job_data,
            'priority': priority,
            'status': 'pending',
            'created_at': time.time(),
            'attempts': 0
        })
        return job_id
    
    async def dequeue(self):
        """最優先ジョブを取得"""
        # すべてのpendingジョブを取得
        all_jobs = {}
        for key in await self.db.keys_async():
            job = await self.db.get_async(key)
            if job['status'] == 'pending':
                all_jobs[key] = job
        
        if not all_jobs:
            return None, None
        
        # 優先度でソート
        sorted_jobs = sorted(
            all_jobs.items(),
            key=lambda x: (x[1]['priority'], x[1]['created_at']),
            reverse=True
        )
        
        job_id, job = sorted_jobs[0]
        
        # ステータスを処理中に更新
        job['status'] = 'processing'
        job['started_at'] = time.time()
        await self.db.set_async(job_id, job)
        
        return job_id, job
    
    async def complete(self, job_id):
        """ジョブを完了としてマーク"""
        job = await self.db.get_async(job_id)
        if job:
            job['status'] = 'completed'
            job['completed_at'] = time.time()
            await self.db.set_async(job_id, job)
        await self.db.flush()
    
    async def fail(self, job_id, error_message, max_retries=3):
        """ジョブを失敗としてマーク"""
        job = await self.db.get_async(job_id)
        if job:
            job['attempts'] += 1
            
            if job['attempts'] >= max_retries:
                job['status'] = 'failed'
                job['error'] = error_message
            else:
                job['status'] = 'pending'  # リトライ
            
            await self.db.set_async(job_id, job)
        await self.db.flush()
    
    async def close(self):
        await self.db.flush()
        await self.db.close()

# 使用例
async def worker(queue):
    """ジョブを処理するワーカー"""
    while True:
        job_id, job = await queue.dequeue()
        
        if not job:
            await asyncio.sleep(1)
            continue
        
        try:
            print(f"Processing job {job_id}: {job['type']}")
            
            # ジョブ処理（例）
            if job['type'] == 'send_email':
                await send_email(job['data'])
            elif job['type'] == 'generate_report':
                await generate_report(job['data'])
            
            await queue.complete(job_id)
            print(f"Job {job_id} completed")
            
        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            await queue.fail(job_id, str(e))

async def main():
    queue = AsyncJobQueue()
    
    # ジョブを追加
    await queue.enqueue('send_email', {'to': 'user@example.com'}, priority=10)
    await queue.enqueue('generate_report', {'report_id': 123}, priority=5)
    
    # ワーカーを起動
    workers = [worker(queue) for _ in range(3)]  # 3並行ワーカー
    await asyncio.gather(*workers)
    
    await queue.close()

# asyncio.run(main())
```

### 例4: 高速カウンター

```python
from dictsqlite_v4 import DictSQLiteV4
import threading

class AtomicCounter:
    def __init__(self, db_file='counters.db'):
        self.db = DictSQLiteV4(db_file, persist_mode='lazy')
        self.lock = threading.Lock()
    
    def increment(self, key, amount=1):
        """カウンターを増加"""
        with self.lock:
            current = self.db.get(key, 0)
            new_value = current + amount
            self.db[key] = new_value
            return new_value
    
    def decrement(self, key, amount=1):
        """カウンターを減少"""
        return self.increment(key, -amount)
    
    def get(self, key):
        """現在の値を取得"""
        return self.db.get(key, 0)
    
    def reset(self, key):
        """カウンターをリセット"""
        with self.lock:
            self.db[key] = 0
    
    def flush(self):
        """ディスクに保存"""
        self.db.flush()
    
    def close(self):
        self.db.flush()
        self.db.close()

# 使用例
counter = AtomicCounter()

# マルチスレッドで安全にカウント
def worker():
    for _ in range(1000):
        counter.increment('total_requests')
        counter.increment('worker_count')

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Total requests: {counter.get('total_requests')}")
print(f"Worker count: {counter.get('worker_count')}")

counter.flush()
counter.close()
```

---

## まとめ

### クイックリファレンス

**最速設定:**
```python
db = DictSQLiteV4('data.db', persist_mode='memory', hot_capacity=1_000_000)
```

**バランス設定（推奨）:**
```python
db = DictSQLiteV4('data.db', persist_mode='lazy', hot_capacity=100_000)
```

**安全性優先:**
```python
db = DictSQLiteV4('data.db', persist_mode='writethrough', encryption_password='pass')
```

### 性能目標

| 操作 | 目標速度 |
|------|----------|
| 基本操作（get/set） | > 1M ops/sec |
| バルク操作 | > 2M ops/sec |
| 暗号化操作 | > 600K ops/sec |
| LRU読み込み | > 2M ops/sec |

### サポート

- GitHub Issues: [DictSQLite Issues](https://github.com/disnana/DictSQLite/issues)
- ベンチマーク結果: `BENCHMARK_RESULTS_JP.md`
- テストドキュメント: `TESTING_DOCUMENTATION_JP.md`

---

**最終更新**: 2024年12月  
**バージョン**: DictSQLite v4.1  
**著者**: DictSQLite Development Team
