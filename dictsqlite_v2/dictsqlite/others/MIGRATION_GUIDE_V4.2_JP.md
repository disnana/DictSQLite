# DictSQLite v4.2 移行ガイド

**オリジナル版 v1.8.8 から DictSQLite v4.2 への完全移行ガイド**

## 📋 目次

1. [移行概要](#移行概要)
2. [v1.8.8とv4.2の主な違い](#v188とv42の主な違い)
3. [互換性について](#互換性について)
4. [移行手順](#移行手順)
5. [API比較表](#api比較表)
6. [コード移行例](#コード移行例)
7. [パフォーマンス最適化方法](#パフォーマンス最適化方法)
8. [よくある移行問題と解決策](#よくある移行問題と解決策)
9. [移行チェックリスト](#移行チェックリスト)

---

## 🎯 移行概要

### なぜ v4.2 に移行するのか？

DictSQLite v4.2は、Rust実装により大幅なパフォーマンス向上とメモリ効率の改善を実現したバージョンです。

| 改善項目 | 効果 |
|---------|------|
| **非同期書き込み** | 最大300倍の高速化 |
| **同期WriteThrough書き込み** | 最大43倍の高速化 |
| **バッチ読み込み** | 5-10倍の高速化 |
| **メモリ管理** | LRUキャッシュによる効率的なメモリ使用 |
| **暗号化** | AES-256-GCM による強力な暗号化 |
| **Safe Pickle** | 安全なデシリアライゼーション |

### 移行の利点とリスク

**✅ 利点:**
- 大幅なパフォーマンス向上
- より効率的なメモリ使用
- 組み込みの暗号化サポート
- Safe Pickleによるセキュリティ強化
- ホットデータのメモリキャッシュ
- 非同期処理のサポート

**⚠️ 注意点:**
- APIの変更が必要（辞書ライクAPIから明示的なメソッド呼び出しへ）
- Rustネイティブモジュールのビルドが必要
- データ型の扱いが異なる（bytes型中心）
- ピュアPythonではない（配布時の考慮が必要）

---

## 📊 v1.8.8とv4.2の主な違い

### アーキテクチャの違い

**v1.8.8 (Python実装)**
```
Python (sqlite3) → SQLiteファイル
- ピュアPython実装
- 辞書ライクAPI
- 自動型変換（pickle/JSON）
- シングルスレッド最適化
```

**v4.2 (Rust実装)**
```
Python → Rust (PyO3) → SQLiteファイル
           ↓
      LRUキャッシュ
      バッファリング
      暗号化層
- Rust実装による高速化
- 明示的なメソッド呼び出し
- bytes型中心の設計
- 非同期処理サポート
- ホットデータキャッシュ
```

### 主な機能比較

| 機能 | v1.8.8 | v4.2 |
|-----|--------|------|
| **基本操作** | `db['key'] = value` | `db['key'] = value` (文字列自動変換) |
| **データ型** | 自動pickle変換 | 文字列は自動UTF-8変換、オブジェクトは自動pickle |
| **暗号化** | オプション機能 | ネイティブサポート (AES-256-GCM) |
| **非同期** | 非サポート | AsyncDictSQLite クラス |
| **キャッシュ** | なし | LRUホットティア |
| **バッファリング** | なし | 書き込みバッファ (v4.2) |
| **Safe Pickle** | 基本サポート | 完全サポート |
| **パフォーマンス** | 標準 | 5-300倍高速 |

---

## 🔄 互換性について

### データベースファイルの互換性

✅ **v1.8.8のデータベースファイルは読み込み可能ですが、以下の条件があります:**

1. **Pickle形式のデータ**: そのまま読み込み可能
2. **JSON形式のデータ**: pickleとしてデコードされるため注意が必要
3. **暗号化データ**: v1.8.8とv4.2で暗号化方式が異なるため直接移行不可

### API互換性

✅ **高いAPI互換性:**

- 基本的な辞書ライクAPI（`db['key']`）は完全互換
- 文字列は自動的にUTF-8エンコード（手動エンコード不要）
- オブジェクトは自動的にpickle化（v1.8.8と同様）
- 読み込み時はbytes型が返る（必要に応じてdecode）

**エンコーディングのカスタマイズ:**
```python
# デフォルトはUTF-8
db = DictSQLiteV4('app.db')

# カスタムエンコーディング（例：Shift-JIS）
db = DictSQLiteV4('app.db', encoding='shift-jis')
```

---

## 🚀 移行手順

### ステップ1: 環境準備

#### 1.1 Rustツールチェーンのインストール

```bash
# Rustのインストール
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# バージョン確認
rustc --version
cargo --version
```

#### 1.2 Maturinのインストール

```bash
# Maturinのインストール
pip install maturin

# バージョン確認
maturin --version
```

### ステップ2: DictSQLite v4.2のビルド

```bash
# v4.2ディレクトリに移動
cd others/beta-versions/dictsqlite_v4.2

# リリースモードでビルド
maturin develop --release

# ビルド確認
python -c "from dictsqlite_v4 import DictSQLiteV4; print('Build successful!')"
```

### ステップ3: データ移行

#### 3.1 非暗号化データの移行

```python
# v1.8.8でデータをエクスポート
from dictsqlite import DictSQLite
import pickle

# 既存のデータベースを開く
old_db = DictSQLite('old_database.db')

# データをエクスポート
export_data = {}
for key in old_db.keys():
    export_data[key] = old_db[key]

# pickle形式で保存
with open('export_data.pkl', 'wb') as f:
    pickle.dump(export_data, f)

old_db.close()
```

```python
# v4.2でデータをインポート
from dictsqlite_v4 import DictSQLiteV4
import pickle

# エクスポートしたデータを読み込み
with open('export_data.pkl', 'rb') as f:
    import_data = pickle.load(f)

# 新しいデータベースに保存
new_db = DictSQLiteV4('new_database.db')

for key, value in import_data.items():
    # v4.2は文字列、bytes、オブジェクトをすべて自動処理
    new_db[key] = value  # 文字列は自動UTF-8変換、オブジェクトは自動pickle化

new_db.close()
print(f"移行完了: {len(import_data)} アイテム")
```

#### 3.2 暗号化データの移行

v1.8.8とv4.2は異なる暗号化方式を使用しているため、以下の手順で移行します：

```python
# 1. v1.8.8で復号化してエクスポート
from dictsqlite import DictSQLite
import pickle

old_db = DictSQLite('old_encrypted.db', password='old_password')
export_data = {key: old_db[key] for key in old_db.keys()}
old_db.close()

with open('decrypted_export.pkl', 'wb') as f:
    pickle.dump(export_data, f)

# 2. v4.2で新しい暗号化方式でインポート
from dictsqlite_v4 import DictSQLiteV4
import pickle

with open('decrypted_export.pkl', 'rb') as f:
    import_data = pickle.load(f)

new_db = DictSQLiteV4(
    'new_encrypted.db',
    encryption_password='new_password'  # 新しいパスワード
)

for key, value in import_data.items():
    # v4.2は自動的に型を変換
    new_db[key] = value  # 文字列、bytes、オブジェクトすべて対応

new_db.close()
print(f"暗号化移行完了: {len(import_data)} アイテム")
```

### ステップ4: コードの更新

移行例は[コード移行例](#コード移行例)セクションを参照してください。

---

## 📋 API比較表

### 初期化

| 操作 | v1.8.8 | v4.2 |
|-----|--------|------|
| 基本初期化 | `DictSQLite('db.db')` | `DictSQLiteV4('db.db')` |
| テーブル指定 | `DictSQLite('db.db', table_name='users')` | ❌ サポートなし（単一テーブル） |
| 暗号化 | `DictSQLite('db.db', password='pass')` | `DictSQLiteV4('db.db', encryption_password='pass')` |
| JSON モード | `DictSQLite('db.db', storage_mode='json')` | ❌ サポートなし（bytes/pickle） |
| Safe Pickle | `DictSQLite('db.db', safe_pickle_policy=...)` | `DictSQLiteV4('db.db', enable_safe_pickle=True, safe_pickle_allowed_modules=[...])` |

### 基本操作

| 操作 | v1.8.8 | v4.2 |
|-----|--------|------|
| **書き込み** | `db['key'] = 'value'` | `db['key'] = 'value'` (文字列は自動UTF-8変換) |
| **読み込み** | `value = db['key']` (自動型変換) | `value = db['key']` (bytes) → 必要に応じて`value.decode()` |
| **削除** | `del db['key']` | `del db['key']` |
| **存在確認** | `'key' in db` | `'key' in db` |
| **キー取得** | `db.keys()` | `list(db.keys())` |
| **値取得** | `db.values()` | ❌ サポートなし |
| **アイテム取得** | `db.items()` | ❌ サポートなし |
| **クリア** | `db.clear()` | `db.clear()` |

### 高度な機能

| 機能 | v1.8.8 | v4.2 |
|-----|--------|------|
| **一括挿入** | なし | `db.bulk_insert({...})` |
| **統計情報** | なし | `db.stats()` |
| **フラッシュ** | なし | `db.flush()` |
| **コンテキストマネージャ** | `with DictSQLite(...) as db:` | `with DictSQLiteV4(...) as db:` |
| **非同期** | ❌ サポートなし | `AsyncDictSQLite(...)` |

### v4.2 固有のパラメータ

```python
DictSQLiteV4(
    db_path,                        # データベースパス
    hot_capacity=1_000_000,         # ホットティアの最大サイズ（エントリ数）
    enable_async=True,              # 非同期フラッシュの有効化
    persist_mode="writethrough",    # "memory", "lazy", "writethrough"
    encryption_password=None,       # 暗号化パスワード
    enable_safe_pickle=False,       # Safe Pickle有効化
    safe_pickle_allowed_modules=None,  # 許可するモジュール
    buffer_size=100                 # v4.2: 書き込みバッファサイズ
)
```

---

## 💻 コード移行例

### 例1: 基本的な使用

#### v1.8.8 のコード

```python
from dictsqlite import DictSQLite

# 初期化
db = DictSQLite('users.db', table_name='users')

# 文字列を保存（自動pickle化）
db['user:alice'] = 'Alice Smith'
db['user:bob'] = 'Bob Jones'

# 読み込み（自動的に文字列に戻る）
alice = db['user:alice']
print(f"Alice: {alice}")  # Alice: Alice Smith

# 辞書を保存（自動pickle化）
db['config'] = {'theme': 'dark', 'lang': 'ja'}
config = db['config']
print(f"Theme: {config['theme']}")  # Theme: dark

db.close()
```

#### v4.2 への移行

```python
from dictsqlite_v4 import DictSQLiteV4

# 初期化（テーブル名は指定不可）
db = DictSQLiteV4('users.db')

# 文字列を保存（自動的にUTF-8エンコードされる）
db['user:alice'] = 'Alice Smith'  # 自動変換
db['user:bob'] = 'Bob Jones'

# 読み込み（bytes型が返る）
alice_bytes = db['user:alice']
alice = alice_bytes.decode('utf-8')
print(f"Alice: {alice}")  # Alice: Alice Smith

# 辞書を保存（自動的にpickle化される）
db['config'] = {'theme': 'dark', 'lang': 'ja'}  # 自動pickle化
# 読み込み（bytes型が返るので、必要に応じてunpickle）
import pickle
config = pickle.loads(db['config'])
print(f"Theme: {config['theme']}")  # Theme: dark

db.close()
```

**注**: v4.2のPythonラッパーは文字列とオブジェクトを自動変換します。手動でエンコードやpickle化する必要はありません。

### 例2: 暗号化の使用

#### v1.8.8 のコード

```python
from dictsqlite import DictSQLite

# 暗号化データベース
db = DictSQLite('secrets.db', password='my_password')

# 機密データを保存
db['api_key'] = 'sk-1234567890'
db['token'] = 'eyJhbGciOiJIUzI1NiIs...'

# 読み込み
api_key = db['api_key']
print(f"API Key: {api_key[:10]}...")

db.close()
```

#### v4.2 への移行

```python
from dictsqlite_v4 import DictSQLiteV4

# 暗号化データベース（パラメータ名が変更）
db = DictSQLiteV4('secrets.db', encryption_password='my_password')

# 機密データを保存（bytes型に変換）
db['api_key'] = b'sk-1234567890'
db['token'] = 'eyJhbGciOiJIUzI1NiIs...'.encode('utf-8')

# 読み込み（bytes型が返る）
api_key_bytes = db['api_key']
api_key = api_key_bytes.decode('utf-8')
print(f"API Key: {api_key[:10]}...")

db.close()
```

### 例3: Safe Pickle

#### v1.8.8 のコード

```python
from dictsqlite import DictSQLite, SafePolicy

# Safe Pickleポリシーの設定
policy = SafePolicy(
    allowed_module_prefixes=('myapp', 'mylib'),
    allowed_builtins={'list', 'dict', 'tuple'}
)

db = DictSQLite('data.db', safe_pickle_policy=policy)

# オブジェクトを保存
from myapp.models import User
user = User(name='Alice', age=30)
db['user:alice'] = user

# 読み込み（Safe Pickleで検証される）
loaded_user = db['user:alice']
print(loaded_user.name)

db.close()
```

#### v4.2への移行

```python
from dictsqlite_v4 import DictSQLiteV4

# Safe Pickle設定（パラメータ名が変更）
db = DictSQLiteV4(
    'data.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp', 'mylib']
)

# オブジェクトを保存（自動的にpickle化される）
from myapp.models import User
user = User(name='Alice', age=30)
db['user:alice'] = user  # 自動pickle化

# 読み込み（Safe Pickleで検証される）
loaded_user_bytes = db['user:alice']
loaded_user = pickle.loads(loaded_user_bytes)
print(loaded_user.name)

db.close()
```

**注**: オブジェクトは自動的にpickle化されます。手動pickle化は不要です。

### 例4: 一括操作

#### v1.8.8 のコード

```python
from dictsqlite import DictSQLite

db = DictSQLite('bulk.db')

# 一括書き込み（forループ）
users = {
    f'user:{i}': f'User {i}' 
    for i in range(1000)
}

for key, value in users.items():
    db[key] = value

db.close()
```

#### v4.2 への移行（最適化）

```python
from dictsqlite_v4 import DictSQLiteV4

db = DictSQLiteV4('bulk.db', buffer_size=500)

# 一括書き込み（bulk_insertを使用）
users = {
    f'user:{i}': f'User {i}'.encode('utf-8')
    for i in range(1000)
}

# 方法1: bulk_insertを使用（最速）
db.bulk_insert(users)

# 方法2: 通常の書き込み（バッファリングで自動最適化）
# for key, value in users.items():
#     db[key] = value

db.close()
```

### 例5: コンテキストマネージャ

#### v1.8.8 と v4.2（同じ使い方）

```python
# v1.8.8
from dictsqlite import DictSQLite

with DictSQLite('temp.db') as db:
    db['key'] = 'value'
    print(db['key'])
# 自動的にcloseされる
```

```python
# v4.2
from dictsqlite_v4 import DictSQLiteV4

with DictSQLiteV4('temp.db') as db:
    db['key'] = b'value'
    print(db['key'])
# 自動的にflushされてcloseされる
```

---

## ⚡ パフォーマンス最適化方法

### 1. buffer_size の最適化

v4.2の最大の特徴は書き込みバッファリングです。`buffer_size`パラメータを適切に設定することで、パフォーマンスを大幅に向上できます。

#### buffer_size の選び方

| buffer_size | 使用ケース | メモリ | レイテンシ | スループット |
|------------|----------|--------|----------|------------|
| 50-100 | リアルタイム処理、低レイテンシ重視 | 低 | 低 | 中 |
| 100-500 | **推奨デフォルト**、バランス重視 | 中 | 中 | 高 |
| 500-1000 | バッチ処理、最高スループット重視 | 高 | 高 | 最高 |

#### 例: リアルタイム処理

```python
# リアルタイムデータ更新（低レイテンシ重視）
db = DictSQLiteV4('realtime.db', buffer_size=50)

# データが50件溜まるごとに自動フラッシュ
for i in range(200):
    db[f'sensor:{i}'] = f'data_{i}'.encode('utf-8')
    # 50, 100, 150, 200件目でフラッシュされる
```

#### 例: バッチ処理

```python
# バッチ処理（スループット重視）
db = DictSQLiteV4('batch.db', buffer_size=1000)

# 大量データを高速書き込み
for i in range(10000):
    db[f'record:{i}'] = f'data_{i}'.encode('utf-8')
    # 1000件ごとにまとめてフラッシュ（I/O回数削減）

# 最後に残りをフラッシュ
db.flush()
db.close()
```

### 2. hot_capacity の最適化

`hot_capacity`はメモリキャッシュのサイズを制御します。頻繁にアクセスするデータ量に応じて設定します。

```python
# 小規模データセット（10,000エントリ未満）
db = DictSQLiteV4('small.db', hot_capacity=10_000)

# 中規模データセット（100,000エントリ未満）
db = DictSQLiteV4('medium.db', hot_capacity=100_000)

# 大規模データセット（1,000,000エントリ）
db = DictSQLiteV4('large.db', hot_capacity=1_000_000)
```

### 3. persist_mode の選択

| モード | 説明 | 使用ケース |
|--------|------|-----------|
| `"memory"` | メモリのみ、永続化なし | テスト、一時データ |
| `"lazy"` | 遅延書き込み、flush時に永続化 | 高速書き込み、バッチ処理 |
| `"writethrough"` | 即座に永続化（バッファリング付き） | データ保証重視 |

```python
# メモリモード（最速、永続化なし）
db_mem = DictSQLiteV4(':memory:', persist_mode='memory')

# 遅延モード（高速、手動flush必要）
db_lazy = DictSQLiteV4('lazy.db', persist_mode='lazy')
# ... データ書き込み ...
db_lazy.flush()  # 手動でフラッシュ

# ライトスルーモード（バッファリング付き即座永続化）
db_wt = DictSQLiteV4('writethrough.db', persist_mode='writethrough', buffer_size=500)
# バッファサイズまで溜まると自動フラッシュ
```

### 4. bulk_insert の活用

大量データの一括挿入には`bulk_insert`を使用します。

```python
db = DictSQLiteV4('bulk.db')

# 100,000件のデータ
data = {
    f'key:{i}': f'value_{i}'.encode('utf-8')
    for i in range(100_000)
}

# bulk_insertで一括挿入（最速）
import time
start = time.time()
db.bulk_insert(data)
elapsed = time.time() - start
print(f"100,000件を {elapsed:.2f}秒で挿入")

db.close()
```

### 5. 非同期処理の活用

高負荷環境では`AsyncDictSQLite`を使用します。

```python
from dictsqlite_v4 import AsyncDictSQLite

# 非同期データベース
async_db = AsyncDictSQLite('async.db', buffer_size=500)

# 非同期書き込み（バックグラウンドでフラッシュ）
for i in range(10000):
    async_db.set_async(f'key:{i}', f'value_{i}'.encode('utf-8'))

# ノンブロッキングで高速書き込み可能

# 終了時は明示的にフラッシュ
async_db.flush()
async_db.close()
```

### 6. パフォーマンス測定

```python
from dictsqlite_v4 import DictSQLiteV4
import time

db = DictSQLiteV4('perf.db', buffer_size=500)

# 書き込みパフォーマンス測定
start = time.time()
for i in range(10000):
    db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
write_time = time.time() - start

# 統計情報を取得
stats = db.stats()
print(f"書き込み: {10000 / write_time:.0f} ops/sec")
print(f"ホットティアサイズ: {stats['hot_tier_size']}")
print(f"暗号化: {stats['encryption_enabled']}")

# 読み込みパフォーマンス測定
start = time.time()
for i in range(10000):
    _ = db[f'key:{i}']
read_time = time.time() - start
print(f"読み込み: {10000 / read_time:.0f} ops/sec")

db.close()
```

### 7. ベストプラクティス

```python
# ✅ 推奨: パフォーマンスとデータ保証のバランス
db = DictSQLiteV4(
    'production.db',
    hot_capacity=100_000,      # アクティブなデータ量に応じて調整
    buffer_size=200,           # 適度なバッファリング
    persist_mode='writethrough',  # データ保証
    enable_async=True,         # バックグラウンドフラッシュ
    encryption_password='...'  # 機密データには暗号化
)

# データ書き込み
for key, value in data.items():
    db[key] = value

# コンテキストマネージャで確実にフラッシュ
with DictSQLiteV4('safe.db', buffer_size=500) as db:
    for i in range(1000):
        db[f'key:{i}'] = f'value_{i}'.encode('utf-8')
# 自動的にflush()とclose()が呼ばれる
```

---

## ❓ よくある移行問題と解決策

### 問題1: 型エラー - 自動変換について

**質問:**
```python
db['key'] = 'value'  # これは動作しますか？
```

**回答:**
はい、v4.2のPythonラッパーは文字列を自動的にUTF-8エンコードします。

```python
# すべて有効な書き方
db['key'] = 'value'              # 自動UTF-8エンコード
db['key'] = 'value'.encode()     # 明示的エンコード（どちらでもOK）
db['key'] = b'value'             # bytes直接指定
```

読み込み時はbytes型が返されるため、必要に応じてデコードします：

```python
value_bytes = db['key']
value = value_bytes.decode('utf-8')  # 文字列に変換
```

### 問題2: 読み込み時にbytes型が返る

**問題:**
```python
value = db['key']
print(value)  # b'value' （bytes型）
```

**解決策:**
```python
# bytes型をstrに変換
value_bytes = db['key']
value = value_bytes.decode('utf-8')
print(value)  # 'value' （str型）

# または辞書に保存する場合（自動pickle化される）
db['data'] = {'key': 'value'}  # 自動でpickle化
data = pickle.loads(db['data'])  # unpickleして取得
```

**注**: 書き込みは自動変換されますが、読み込みはbytes型なので必要に応じてデコードが必要です。

### 問題3: テーブル名を指定できない

**v1.8.8:**
```python
db = DictSQLite('app.db', table_name='users')
```

**v4.2（自動変換）:**
```python
db = DictSQLiteV4('app.db')
db['users:alice'] = 'Alice data'  # 自動UTF-8エンコード
db['posts:1'] = 'Post content'
```

### 問題4: JSON モードがない

**v1.8.8:**
```python
db = DictSQLite('data.db', storage_mode='json')
db['config'] = {'theme': 'dark'}
```

**v4.2（自動変換使用）:**
```python
db = DictSQLiteV4('data.db')

# 方法1: 辞書を直接保存（自動pickle化）
config = {'theme': 'dark'}
db['config'] = config  # 自動でpickle化される

# 読み込み
import pickle
config = pickle.loads(db['config'])

# 方法2: JSON文字列として保存
import json
config = {'theme': 'dark'}
db['config'] = json.dumps(config)  # 自動でUTF-8エンコード

# 読み込み
config_str = db['config'].decode('utf-8')
config = json.loads(config_str)
```

### 問題5: ビルドエラー

**エラー:**
```
error: could not compile `dictsqlite-v4`
```

**解決策:**

```bash
# Rustツールチェーンを最新化
rustup update

# 依存関係をクリーン
cd others/beta-versions/dictsqlite_v4.2
cargo clean

# 再ビルド
maturin develop --release

# それでも失敗する場合、依存パッケージを確認
pip install --upgrade pip maturin
```

### 問題6: 暗号化データベースが開けない

**問題:**
```python
# v1.8.8で暗号化したDBをv4.2で開けない
db = DictSQLiteV4('old_encrypted.db', encryption_password='password')
# Error: Decryption failed
```

**解決策:**

v1.8.8とv4.2は異なる暗号化方式のため、[データ移行](#32-暗号化データの移行)セクションの手順で移行が必要です。

### 問題7: パフォーマンスが期待より遅い

**チェックポイント:**

```python
# 1. buffer_sizeを確認
db = DictSQLiteV4('slow.db', buffer_size=500)  # デフォルトは100

# 2. persist_modeを確認
db = DictSQLiteV4('slow.db', persist_mode='lazy')  # lazyが最速

# 3. bulk_insertを使用
db.bulk_insert(large_data)  # forループより高速

# 4. hot_capacityを増やす
db = DictSQLiteV4('slow.db', hot_capacity=1_000_000)

# 5. 統計情報を確認
stats = db.stats()
print(stats)  # キャッシュヒット率などを確認
```

---

## ✅ 移行チェックリスト

### 環境準備
- [ ] Rustツールチェーンをインストール
- [ ] Maturinをインストール
- [ ] DictSQLite v4.2をビルド
- [ ] インポートテストが成功

### データ移行
- [ ] 既存データをバックアップ
- [ ] 非暗号化データのエクスポート
- [ ] v4.2への移行スクリプト作成
- [ ] 移行スクリプトのテスト
- [ ] 本番データの移行
- [ ] データ整合性の確認

### コード移行
- [ ] インポート文を更新
- [ ] 文字列→bytes変換を追加
- [ ] 辞書/オブジェクト→pickle変換を追加
- [ ] テーブル名使用箇所を修正
- [ ] Safe Pickleパラメータを更新
- [ ] 暗号化パラメータ名を更新
- [ ] エラーハンドリングを確認

### 最適化
- [ ] buffer_sizeを最適化
- [ ] hot_capacityを調整
- [ ] persist_modeを選択
- [ ] bulk_insertを活用
- [ ] パフォーマンステストを実施

### テスト
- [ ] ユニットテストを更新
- [ ] 統合テストを実施
- [ ] パフォーマンステストを実施
- [ ] 本番環境でのスモークテスト

### ドキュメント
- [ ] READMEを更新
- [ ] APIドキュメントを更新
- [ ] 移行ガイドをチーム共有
- [ ] トラブルシューティング手順を文書化

---

## 📚 参考資料

- [README_V4.2_JP.md](./README_V4.2_JP.md) - v4.2の完全ガイド
- [PERFORMANCE_OPTIMIZATION_GUIDE_JP.md](./PERFORMANCE_OPTIMIZATION_GUIDE_JP.md) - パフォーマンス最適化の詳細ガイド
- [DEVELOPER_GUIDE_JP.md](./DEVELOPER_GUIDE_JP.md) - 開発者向け詳細ドキュメント
- [examples/](./examples/) - 実践的なサンプルコード
  - [v4.2_basic_usage.py](./examples/v4.2_basic_usage.py) - 基本的な使い方
  - [v4.2_migration_example.py](./examples/v4.2_migration_example.py) - 移行例
  - [v4.2_performance_examples.py](./examples/v4.2_performance_examples.py) - パフォーマンス最適化
  - [v4.2_advanced_examples.py](./examples/v4.2_advanced_examples.py) - 高度な機能
- [V4.2_IMPLEMENTATION_SUMMARY.md](./V4.2_IMPLEMENTATION_SUMMARY.md) - 実装詳細

---

## 📝 まとめ

DictSQLite v4.2への移行は、以下のステップで実施できます：

1. **環境準備**: Rust、Maturinのインストールとビルド
2. **データ移行**: pickle形式でのエクスポート/インポート
3. **コード更新**: bytes型への対応、パラメータ名の変更
4. **最適化**: buffer_size、hot_capacityの調整
5. **テスト**: 十分なテストの実施

移行により、**5〜300倍**のパフォーマンス向上が期待できます。

ご不明な点がありましたら、[Issue](https://github.com/disnana/DictSQLite/issues)でお気軽にお問い合わせください。
