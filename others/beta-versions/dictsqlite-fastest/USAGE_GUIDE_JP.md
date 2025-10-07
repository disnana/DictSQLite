# DictSQLite-Fastest 完全使用ガイド

**DictSQLite-Fastestの詳細な使い方と実践的な活用方法**

## 📋 目次

1. [基本的な使い方](#基本的な使い方)
2. [高度な設定](#高度な設定)
3. [非同期操作](#非同期操作)
4. [パフォーマンス最適化](#パフォーマンス最適化)
5. [実践的な使用例](#実践的な使用例)
6. [エラーハンドリング](#エラーハンドリング)
7. [ベストプラクティス](#ベストプラクティス)

## 🚀 基本的な使い方

### インストールと初期設定

```python
# DictSQLite-Fastestのインポート
from dictsqlite_fastest import DictSQLiteFastest

# 基本的な使用方法
with DictSQLiteFastest('my_database.db') as db:
    # データの保存
    db['key1'] = 'value1'
    db['user_data'] = {'name': '田中太郎', 'age': 30}
    
    # データの取得
    print(db['key1'])           # 'value1'
    print(db['user_data'])      # {'name': '田中太郎', 'age': 30}
    
    # キーの存在確認
    if 'key1' in db:
        print("キーが存在します")
    
    # データの削除
    del db['key1']
```

### 辞書ライクな操作

```python
with DictSQLiteFastest('example.db') as db:
    # 複数データの一括設定
    db.update({
        'config': {'theme': 'dark', 'language': 'ja'},
        'users': ['alice', 'bob', 'charlie'],
        'settings': {'auto_save': True, 'timeout': 300}
    })
    
    # キー一覧の取得
    keys = list(db.keys())
    print(f"保存されているキー: {keys}")
    
    # 値一覧の取得
    values = list(db.values())
    
    # アイテム一覧の取得
    items = list(db.items())
    
    # データベースサイズの確認
    print(f"データ数: {len(db)}")
```

### データ型の対応

```python
with DictSQLiteFastest('datatypes.db') as db:
    # 基本データ型
    db['string'] = "文字列データ"
    db['integer'] = 42
    db['float'] = 3.14159
    db['boolean'] = True
    
    # コレクション型
    db['list'] = [1, 2, 3, 'mixed', True]
    db['dict'] = {'nested': {'data': 'value'}}
    db['tuple'] = (1, 2, 3)
    db['set'] = {1, 2, 3, 4, 5}
    
    # 複雑なオブジェクト
    import datetime
    db['datetime'] = datetime.datetime.now()
    db['date'] = datetime.date.today()
    
    # カスタムクラス（pickleで対応）
    class CustomClass:
        def __init__(self, value):
            self.value = value
    
    db['custom'] = CustomClass("カスタムデータ")
```

## ⚙️ 高度な設定

### データベース接続の詳細設定

```python
# 高性能設定でのデータベース作成
db = DictSQLiteFastest(
    'high_performance.db',
    journal_mode='WAL',           # WALモードで高速化
    cache_size=10000,             # キャッシュサイズを10MB
    synchronous='NORMAL',         # 安全性と速度のバランス
    temp_store='MEMORY',          # 一時ファイルをメモリに
    mmap_size=268435456,          # メモリマップサイズ (256MB)
    optimize_on_close=True        # 終了時に最適化
)

# 接続のウォームアップ（初回クエリ高速化）
db.warmup_connection()

# 使用後のクリーンアップ
db.close()
```

### ストレージモードの選択

```python
# JSONモード（人間が読める形式）
with DictSQLiteFastest('json_mode.db', storage_mode='json') as db:
    db['data'] = {'message': 'JSONで保存されます'}
    # ファイルを直接開いて読むことが可能

# Pickleモード（最高の互換性）
with DictSQLiteFastest('pickle_mode.db', storage_mode='pickle') as db:
    db['complex_data'] = CustomComplexObject()
    # 任意のPythonオブジェクトを保存可能
```

### テーブル操作

```python
with DictSQLiteFastest('multi_table.db') as db:
    # デフォルトテーブルの使用
    db['main_data'] = 'メインテーブルのデータ'
    
    # 新しいテーブルの作成と切り替え
    db.create_table('users')
    db.switch_table('users')
    db['user1'] = {'name': '山田花子', 'role': 'admin'}
    
    # 別のテーブルの作成
    db.create_table('products')
    db.switch_table('products')
    db['product1'] = {'name': 'ノートPC', 'price': 80000}
    
    # テーブル一覧の取得
    tables = db.tables()
    print(f"テーブル一覧: {tables}")
    
    # 元のテーブルに戻る
    db.switch_table('main')
    print(db['main_data'])  # 'メインテーブルのデータ'
```

## ⚡ 非同期操作

### 基本的な非同期操作

```python
import asyncio
from dictsqlite_fastest import AsyncDictSQLiteFastest

async def basic_async_operations():
    # 非同期データベースの作成
    db = AsyncDictSQLiteFastest('async_db.db')
    
    try:
        # 非同期でのデータ保存
        await db.aset('key1', 'async_value1')
        await db.aset('key2', {'async': 'data'})
        
        # 非同期でのデータ取得
        value1 = await db.aget('key1')
        value2 = await db.aget('key2')
        
        print(f"取得したデータ: {value1}, {value2}")
        
        # 非同期での存在確認
        exists = await db.acontains('key1')
        print(f"key1の存在: {exists}")
        
        # 非同期での削除
        await db.adelete('key1')
        
    finally:
        # 非同期でのクリーンアップ
        await db.aclose()

# 非同期関数の実行
asyncio.run(basic_async_operations())
```

### 大量並行処理

```python
async def concurrent_operations():
    db = AsyncDictSQLiteFastest('concurrent.db')
    
    try:
        # 大量の同時書き込み
        write_tasks = []
        for i in range(1000):
            task = db.aset(f'key_{i}', f'value_{i}')
            write_tasks.append(task)
        
        # すべての書き込みを並行実行
        await asyncio.gather(*write_tasks)
        print("1000個のデータを並行書き込み完了")
        
        # 大量の同時読み取り
        read_tasks = []
        for i in range(1000):
            task = db.aget(f'key_{i}')
            read_tasks.append(task)
        
        # すべての読み取りを並行実行
        values = await asyncio.gather(*read_tasks)
        print(f"1000個のデータを並行読み取り完了: {len(values)}個取得")
        
    finally:
        await db.aclose()

asyncio.run(concurrent_operations())
```

### セマフォによる同時実行数制御

```python
async def controlled_concurrent_operations():
    db = AsyncDictSQLiteFastest('controlled.db')
    
    # 同時実行数を10に制限
    semaphore = asyncio.Semaphore(10)
    
    async def limited_operation(key, value):
        async with semaphore:
            await db.aset(key, value)
            return await db.aget(key)
    
    try:
        # 制御された並行処理
        tasks = [
            limited_operation(f'key_{i}', f'value_{i}')
            for i in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        print(f"制御された並行処理完了: {len(results)}個処理")
        
    finally:
        await db.aclose()

asyncio.run(controlled_concurrent_operations())
```

## 🎯 パフォーマンス最適化

### バルク操作による高速化

```python
with DictSQLiteFastest('bulk_ops.db') as db:
    # 大量データの効率的な挿入
    bulk_data = {
        f'user_{i}': {
            'id': i,
            'name': f'ユーザー{i}',
            'created_at': datetime.datetime.now().isoformat()
        }
        for i in range(10000)
    }
    
    # バルク挿入（最適化された方法）
    start_time = time.time()
    db.bulk_insert_optimized(bulk_data)
    bulk_time = time.time() - start_time
    print(f"バルク挿入（10000件）: {bulk_time:.4f}秒")
    
    # 通常の挿入と比較
    start_time = time.time()
    for key, value in list(bulk_data.items())[:100]:
        db[key + '_normal'] = value
    normal_time = time.time() - start_time
    print(f"通常挿入（100件）: {normal_time:.4f}秒")
    
    # バルク読み取り
    keys_to_read = [f'user_{i}' for i in range(0, 1000, 10)]
    start_time = time.time()
    values = db.bulk_get(keys_to_read)
    read_time = time.time() - start_time
    print(f"バルク読み取り（100件）: {read_time:.4f}秒")
```

### トランザクション制御

```python
with DictSQLiteFastest('transaction.db') as db:
    try:
        # トランザクション開始
        db.begin_transaction()
        
        # 複数の操作を一括実行
        for i in range(1000):
            db[f'tx_key_{i}'] = f'tx_value_{i}'
        
        # 条件によってコミットまたはロールバック
        if len(db) > 500:
            db.commit_transaction()
            print("トランザクションをコミットしました")
        else:
            db.rollback_transaction()
            print("トランザクションをロールバックしました")
            
    except Exception as e:
        # エラー時は自動的にロールバック
        db.rollback_transaction()
        print(f"エラーが発生しました: {e}")
```

### キャッシュとプリフェッチ

```python
with DictSQLiteFastest('cached.db', cache_size=20000) as db:
    # データの事前ロード
    prefetch_keys = [f'key_{i}' for i in range(100)]
    
    # データが存在しない場合は作成
    for key in prefetch_keys:
        if key not in db:
            db[key] = f'データ_{key}'
    
    # プリフェッチでキャッシュにロード
    db.prefetch_keys(prefetch_keys)
    
    # 高速アクセス（キャッシュから取得）
    start_time = time.time()
    for key in prefetch_keys:
        value = db[key]
    cached_time = time.time() - start_time
    print(f"キャッシュアクセス時間: {cached_time:.4f}秒")
```

## 💡 実践的な使用例

### Webアプリケーションのセッション管理

```python
import json
import time
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, db_path='sessions.db'):
        self.db = DictSQLiteFastest(
            db_path,
            journal_mode='WAL',
            cache_size=5000
        )
        self.db.warmup_connection()
    
    def create_session(self, user_id, session_data=None):
        session_id = f"session_{user_id}_{int(time.time())}"
        session_info = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'data': session_data or {}
        }
        self.db[session_id] = session_info
        return session_id
    
    def get_session(self, session_id):
        if session_id in self.db:
            session = self.db[session_id]
            # アクセス時間を更新
            session['last_accessed'] = datetime.now().isoformat()
            self.db[session_id] = session
            return session
        return None
    
    def update_session(self, session_id, data):
        if session_id in self.db:
            session = self.db[session_id]
            session['data'].update(data)
            session['last_accessed'] = datetime.now().isoformat()
            self.db[session_id] = session
            return True
        return False
    
    def cleanup_expired_sessions(self, hours=24):
        """期限切れセッションのクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        expired_sessions = []
        
        for session_id in self.db.keys():
            session = self.db[session_id]
            last_accessed = datetime.fromisoformat(session['last_accessed'])
            if last_accessed < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.db[session_id]
        
        return len(expired_sessions)
    
    def close(self):
        self.db.close()

# 使用例
session_mgr = SessionManager()
session_id = session_mgr.create_session('user123', {'theme': 'dark'})
session_mgr.update_session(session_id, {'language': 'ja'})
session_data = session_mgr.get_session(session_id)
print(f"セッションデータ: {session_data}")
```

### 設定管理システム

```python
class ConfigManager:
    def __init__(self, config_file='app_config.db'):
        self.db = DictSQLiteFastest(
            config_file,
            storage_mode='json',  # 設定は人間が読める形式で
            journal_mode='WAL'
        )
        self._load_defaults()
    
    def _load_defaults(self):
        """デフォルト設定の読み込み"""
        defaults = {
            'app': {
                'name': 'My Application',
                'version': '1.0.0',
                'debug': False
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'timeout': 30
            },
            'ui': {
                'theme': 'light',
                'language': 'en',
                'items_per_page': 20
            }
        }
        
        for category, settings in defaults.items():
            if category not in self.db:
                self.db[category] = settings
    
    def get(self, category, key=None, default=None):
        """設定値の取得"""
        if category in self.db:
            config = self.db[category]
            if key is None:
                return config
            return config.get(key, default)
        return default
    
    def set(self, category, key, value):
        """設定値の変更"""
        if category in self.db:
            config = self.db[category]
            config[key] = value
            self.db[category] = config
        else:
            self.db[category] = {key: value}
    
    def set_category(self, category, settings):
        """カテゴリ全体の設定"""
        self.db[category] = settings
    
    def reset_category(self, category):
        """カテゴリの設定をリセット"""
        if category in self.db:
            del self.db[category]
            self._load_defaults()
    
    def export_config(self):
        """設定の全エクスポート"""
        return dict(self.db.items())
    
    def import_config(self, config_dict):
        """設定の全インポート"""
        for category, settings in config_dict.items():
            self.db[category] = settings

# 使用例
config = ConfigManager()
config.set('ui', 'theme', 'dark')
config.set('ui', 'language', 'ja')
theme = config.get('ui', 'theme')
print(f"現在のテーマ: {theme}")
```

### キャッシュシステム

```python
import hashlib
import pickle
from datetime import datetime, timedelta

class CacheSystem:
    def __init__(self, cache_file='cache.db', default_ttl=3600):
        self.db = DictSQLiteFastest(
            cache_file,
            journal_mode='WAL',
            cache_size=10000
        )
        self.default_ttl = default_ttl
    
    def _make_key(self, key):
        """キーのハッシュ化"""
        if isinstance(key, str):
            return f"cache_{hashlib.md5(key.encode()).hexdigest()}"
        else:
            return f"cache_{hashlib.md5(pickle.dumps(key)).hexdigest()}"
    
    def set(self, key, value, ttl=None):
        """キャッシュに値を設定"""
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        expire_time = datetime.now() + timedelta(seconds=ttl)
        
        cache_entry = {
            'value': value,
            'expire_time': expire_time.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        self.db[cache_key] = cache_entry
    
    def get(self, key, default=None):
        """キャッシュから値を取得"""
        cache_key = self._make_key(key)
        
        if cache_key in self.db:
            entry = self.db[cache_key]
            expire_time = datetime.fromisoformat(entry['expire_time'])
            
            if datetime.now() < expire_time:
                return entry['value']
            else:
                # 期限切れなので削除
                del self.db[cache_key]
        
        return default
    
    def delete(self, key):
        """キャッシュエントリを削除"""
        cache_key = self._make_key(key)
        if cache_key in self.db:
            del self.db[cache_key]
            return True
        return False
    
    def cleanup_expired(self):
        """期限切れエントリのクリーンアップ"""
        now = datetime.now()
        expired_keys = []
        
        for cache_key in self.db.keys():
            if cache_key.startswith('cache_'):
                entry = self.db[cache_key]
                expire_time = datetime.fromisoformat(entry['expire_time'])
                if now >= expire_time:
                    expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.db[key]
        
        return len(expired_keys)
    
    def clear_all(self):
        """全キャッシュのクリア"""
        cache_keys = [k for k in self.db.keys() if k.startswith('cache_')]
        for key in cache_keys:
            del self.db[key]
        return len(cache_keys)
    
    def stats(self):
        """キャッシュ統計の取得"""
        cache_keys = [k for k in self.db.keys() if k.startswith('cache_')]
        total_entries = len(cache_keys)
        
        now = datetime.now()
        expired_count = 0
        
        for key in cache_keys:
            entry = self.db[key]
            expire_time = datetime.fromisoformat(entry['expire_time'])
            if now >= expire_time:
                expired_count += 1
        
        return {
            'total_entries': total_entries,
            'valid_entries': total_entries - expired_count,
            'expired_entries': expired_count
        }

# 使用例
cache = CacheSystem(default_ttl=300)  # 5分のTTL

# データの保存
cache.set('user_profile_123', {'name': '田中太郎', 'email': 'tanaka@example.com'})
cache.set('expensive_calculation', 42, ttl=1800)  # 30分のTTL

# データの取得
profile = cache.get('user_profile_123')
print(f"キャッシュされたプロフィール: {profile}")

# 統計の確認
stats = cache.stats()
print(f"キャッシュ統計: {stats}")
```

## 🛡️ エラーハンドリング

### 基本的なエラーハンドリング

```python
from dictsqlite_fastest import DictSQLiteFastest, DictSQLiteError

def safe_database_operations():
    try:
        with DictSQLiteFastest('safe_db.db') as db:
            # データベース操作
            db['test_key'] = 'test_value'
            value = db['test_key']
            print(f"取得した値: {value}")
            
    except DictSQLiteError as e:
        print(f"DictSQLiteエラー: {e}")
    except KeyError as e:
        print(f"キーが見つかりません: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")

safe_database_operations()
```

### 非同期エラーハンドリング

```python
async def safe_async_operations():
    db = None
    try:
        db = AsyncDictSQLiteFastest('async_safe.db')
        
        # 非同期操作
        await db.aset('key1', 'value1')
        value = await db.aget('key1')
        print(f"非同期で取得: {value}")
        
        # 存在しないキーへのアクセス
        try:
            missing_value = await db.aget('non_existent_key')
        except KeyError:
            print("キーが存在しません（予期された動作）")
        
    except Exception as e:
        print(f"非同期操作エラー: {e}")
    finally:
        if db:
            await db.aclose()

asyncio.run(safe_async_operations())
```

### リトライ機能付きエラーハンドリング

```python
import time
import random

def retry_operation(func, max_retries=3, delay=1):
    """リトライ機能付き関数実行"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"リトライ {attempt + 1}/{max_retries}: {e}")
            time.sleep(delay * (2 ** attempt))  # 指数バックオフ

def unreliable_operation():
    """不安定な操作のシミュレーション"""
    with DictSQLiteFastest('retry_db.db') as db:
        if random.random() < 0.7:  # 70%の確率で失敗
            raise Exception("一時的なエラー")
        
        db['success'] = True
        return db['success']

# リトライ付きで実行
try:
    result = retry_operation(unreliable_operation)
    print(f"操作成功: {result}")
except Exception as e:
    print(f"最終的に失敗: {e}")
```

## 🏆 ベストプラクティス

### 1. リソース管理

```python
# 推奨: コンテキストマネージャーの使用
with DictSQLiteFastest('database.db') as db:
    db['key'] = 'value'
    # 自動的にクリーンアップされる

# 非推奨: 手動管理
db = DictSQLiteFastest('database.db')
try:
    db['key'] = 'value'
finally:
    db.close()  # 忘れやすい
```

### 2. バッチ処理の活用

```python
# 推奨: バッチ処理
data_to_insert = {f'key_{i}': f'value_{i}' for i in range(1000)}
with DictSQLiteFastest('batch.db') as db:
    db.bulk_insert_optimized(data_to_insert)

# 非推奨: 個別処理
with DictSQLiteFastest('individual.db') as db:
    for i in range(1000):
        db[f'key_{i}'] = f'value_{i}'  # 遅い
```

### 3. 適切な設定の選択

```python
# 高性能アプリケーション向け
high_perf_db = DictSQLiteFastest(
    'high_perf.db',
    journal_mode='WAL',
    synchronous='NORMAL',
    cache_size=10000,
    temp_store='MEMORY'
)

# 安全性重視アプリケーション向け
safe_db = DictSQLiteFastest(
    'safe.db',
    journal_mode='DELETE',
    synchronous='FULL',
    cache_size=2000
)
```

### 4. 非同期処理での同時実行制御

```python
async def controlled_async_processing():
    db = AsyncDictSQLiteFastest('controlled.db')
    
    # セマフォで同時実行数を制御
    semaphore = asyncio.Semaphore(10)  # 最大10個の同時実行
    
    async def process_item(key, value):
        async with semaphore:
            await db.aset(key, value)
            return await db.aget(key)
    
    try:
        # 効率的な並行処理
        tasks = [
            process_item(f'key_{i}', f'value_{i}')
            for i in range(1000)
        ]
        results = await asyncio.gather(*tasks)
        print(f"処理完了: {len(results)}件")
    finally:
        await db.aclose()
```

### 5. メモリ効率の最適化

```python
# 大量データ処理時のメモリ効率化
def process_large_dataset(data_source, batch_size=1000):
    with DictSQLiteFastest('large_data.db', cache_size=20000) as db:
        batch = {}
        count = 0
        
        for key, value in data_source:
            batch[key] = value
            count += 1
            
            # バッチサイズに達したら一括処理
            if count >= batch_size:
                db.bulk_insert_optimized(batch)
                batch.clear()
                count = 0
        
        # 残りのデータを処理
        if batch:
            db.bulk_insert_optimized(batch)
```

### 6. 定期的なメンテナンス

```python
def maintenance_routine(db_path):
    """定期メンテナンスルーチン"""
    with DictSQLiteFastest(db_path) as db:
        # データベースの最適化
        db.vacuum()
        
        # 統計情報の更新
        db.analyze()
        
        # パフォーマンス統計の取得
        stats = db.get_performance_stats()
        print(f"パフォーマンス統計: {stats}")
        
        return stats

# 定期実行（例：毎日深夜）
maintenance_routine('production.db')
```

---

**このガイドにより、DictSQLite-Fastestを効率的かつ安全に活用することができます。用途に応じて適切な設定と使用方法を選択し、高性能なアプリケーションを構築してください。**