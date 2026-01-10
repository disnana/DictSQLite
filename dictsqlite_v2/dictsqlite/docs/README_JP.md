# DictSQLite v2 — クイックスタート（日本語）

## 概要

DictSQLite v2 は、Rust製の高性能ネイティブストレージをバックエンドに持つ、辞書ライクな Python API を提供するライブラリです。

**主な特徴:**
- **超高速**: ロックフリー並行ハッシュマップで 100M+ ops/sec
- **AES-256-GCM暗号化**: オプショナルなデータ暗号化
- **Safe Pickle検証**: 安全なオブジェクトシリアライゼーション
- **SQLインジェクション対策**: パラメータ化クエリによる保護
- **v1.8.8 API互換**: 既存コードとの互換性を維持

## バージョンについて

- **パッケージバージョン**: v2.0.7（PyPIでの公開バージョン）
- **内部実装バージョン**: v4（内部アーキテクチャ）

内部的には「v4」という実装名が使用されていますが、これは内部アーキテクチャのバージョンです。PyPIでは `dictsqlite 2.x.x` として公開されています。

## インストール

```bash
pip install dictsqlite
```

## インポート方法

**推奨される標準的なインポート:**

```python
from dictsqlite import DictSQLite
```

**内部実装名を使用する場合（後方互換性）:**

```python
from dictsqlite import DictSQLiteV4  # DictSQLite のエイリアス
```

> **注意**: `DictSQLiteV4` は内部実装名です。新しいコードでは `DictSQLite` の使用を推奨します。

## 基本的な使い方（同期）

### シンプルな例

```python
from dictsqlite import DictSQLite

# メモリDBで初期化
db = DictSQLite(':memory:')

# 文字列を保存
db['user:alice'] = 'Alice Smith'

# Pythonオブジェクトを保存（自動的にpickleされる）
db['config'] = {'theme': 'dark', 'version': 2}

# 値の取得
print(db['user:alice'])                 # -> 'Alice Smith'
print(db.get('missing', 'default'))     # -> 'default'

# キーの存在確認
if 'user:alice' in db:
    print("User exists!")

# イテレーション
for key in db.keys():
    print(key, db[key])

# 閉じる
db.close()
```

### コンテキストマネージャ

```python
from dictsqlite import DictSQLite

with DictSQLite('app.db') as db:
    db['a'] = 1
    db['b'] = {'nested': 'data'}
    print(db['a'])
# 自動的にフラッシュしてクローズ
```

## 非同期（Async/Await）

`AsyncDictSQLite` クラスは、真の asyncio サポートを提供します。

```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite(':memory:')
    
    # awaitableメソッド
    await db.aset('key', 'value')
    value = await db.aget('key')
    print(value)  # -> 'value'
    
    # バッチ操作
    await db.abatch_set([('key1', 'val1'), ('key2', 'val2')])
    values = await db.abatch_get(['key1', 'key2'])
    
    # 存在確認
    exists = await db.acontains('key1')
    
    # 削除
    await db.adelete('key1')
    
    # フラッシュとクローズ
    await db.aflush()
    await db.aclose()

asyncio.run(main())
```

### 非同期コンテキストマネージャ

```python
async def main():
    async with AsyncDictSQLite('async.db') as db:
        await db.aset('test', 123)
        value = await db.aget('test')
```

### Awaitableメソッド一覧

- `await aget(key)` - 非同期取得
- `await aset(key, value)` - 非同期設定
- `await abatch_get(keys)` - バッチ取得
- `await abatch_set(items)` - バッチ設定
- `await acontains(key)` - 存在確認
- `await adelete(key)` - 削除
- `await aflush()` - フラッシュ
- `await aclose()` - クローズ

## コンストラクタオプション

### DictSQLite

```python
DictSQLite(
    db_path,                            # str: データベースファイルパスまたは ':memory:'
    hot_capacity=1_000_000,             # int: ホットティアの最大エントリ数
    enable_async=True,                  # bool: 非同期バックグラウンドフラッシュ
    persist_mode="writethrough",        # str: 永続化モード
    storage_mode="pickle",              # str: ストレージモード
    table_name="main",                  # str: デフォルトテーブル名
    encryption_password=None,           # str|None: AES-256-GCM暗号化パスワード
    enable_safe_pickle=False,           # bool: Safe Pickle検証を有効化
    safe_pickle_allowed_modules=None,   # list|None: Safe Pickle許可モジュール
    buffer_size=100,                    # int: 非同期バッファサイズ
    encoding='utf-8',                   # str: 文字エンコーディング
    table_mode="prefix",                # str: テーブル分離モード
    pool_size=20                        # int: SQLite接続プールサイズ
)
```

#### パラメータ詳細

- **db_path**: データベースファイルのパス。`:memory:` でメモリDB。
- **hot_capacity**: メモリ内のホットキャッシュの最大エントリ数（デフォルト: 1,000,000）
- **enable_async**: バックグラウンドの非同期フラッシュワーカーを有効化（デフォルト: True）
- **persist_mode**: 永続化モード
  - `"memory"`: メモリのみ、永続化なし
  - `"lazy"`: フラッシュ/クローズ時に永続化
  - `"writethrough"`: 即座に永続化（デフォルト）
- **storage_mode**: ストレージモード
  - `"pickle"`: Python pickle（デフォルト）
  - `"jsonb"`: PostgreSQL互換JSONB
  - `"json"`: 標準JSON
  - `"bytes"`: バイナリデータ
- **table_name**: 使用するテーブル名（デフォルト: `"main"`）
- **encryption_password**: 暗号化パスワード（Noneで無効）
- **enable_safe_pickle**: Safe Pickle検証を有効化（デフォルト: False）
- **safe_pickle_allowed_modules**: 許可するモジュールプレフィックスのリスト（例: `["myapp", "mylib"]`）
- **buffer_size**: 非同期バッファサイズ（デフォルト: 100、writethroughモードでは自動的に1）
- **encoding**: 文字列エンコーディング（デフォルト: `'utf-8'`）
- **table_mode**: テーブル分離モード
  - `"prefix"`: キープレフィックスによる分離（デフォルト）
  - `"separate"`: 個別のSQLiteテーブルによる完全分離
- **pool_size**: SQLite接続プールサイズ（デフォルト: 20）

### AsyncDictSQLite

```python
AsyncDictSQLite(
    db_path,                        # str: データベースファイルパスまたは ':memory:'
    capacity=1_000_000,             # int: キャッシュの最大エントリ数
    persist_mode="lazy",            # str: 永続化モード
    storage_mode="pickle",          # str: ストレージモード
    table_name="main",              # str: デフォルトテーブル名
    buffer_size=100,                # int: 書き込みバッファサイズ
    table_mode="prefix"             # str: テーブル分離モード
)
```

## ストレージモード

### Pickleモード（デフォルト）

ほとんどのPythonオブジェクトを自動的にシリアライズ/デシリアライズします。

```python
db = DictSQLite(':memory:', storage_mode="pickle")
db['data'] = {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
print(db['data'])  # -> {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
```

### JSONBモード

PostgreSQL互換のJSONBフォーマット。JSON互換のデータに適しています。

```python
db = DictSQLite(':memory:', storage_mode="jsonb")
db['data'] = {'key': 'value', 'items': [1, 2, 3]}
```

### JSONモード

標準JSONシリアライゼーション。

```python
db = DictSQLite(':memory:', storage_mode="json")
db['data'] = {'key': 'value'}
```

### Bytesモード

バイナリデータをそのまま保存。

```python
db = DictSQLite(':memory:', storage_mode="bytes")
db['data'] = b'binary data'
```

## 永続化モード

### Memorモード

メモリのみ、永続化なし。高速ですがデータは失われます。

```python
db = DictSQLite('temp.db', persist_mode="memory")
```

### Lazyモード

フラッシュまたはクローズ時に永続化。

```python
db = DictSQLite('data.db', persist_mode="lazy")
db['key'] = 'value'
db.flush()  # ここで永続化
```

### Writethroughモード（デフォルト）

即座に永続化。データの耐久性が最も高い。

```python
db = DictSQLite('data.db', persist_mode="writethrough")
db['key'] = 'value'  # 即座に永続化
```

## 暗号化

AES-256-GCM暗号化を使用してデータを保護できます。

```python
from dictsqlite import DictSQLite

# 暗号化を有効化
db = DictSQLite('secure.db', encryption_password='my_secret_password')

db['secret_token'] = 'sensitive_data'
print(db.stats()['encryption_enabled'])  # -> True

db.close()

# 再度開く（同じパスワードが必要）
db2 = DictSQLite('secure.db', encryption_password='my_secret_password')
print(db2['secret_token'])  # -> 'sensitive_data'
db2.close()
```

## Safe Pickle

Safe Pickle機能を使用して、信頼できないデータのunpickleを安全に行えます。

```python
from dictsqlite import DictSQLite

# Safe Pickleを有効化
db = DictSQLite(
    ':memory:', 
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "mylib"]
)

# 許可されたモジュールのオブジェクトのみ保存可能
db['data'] = {'safe': 'data'}
```

## テーブル機能

複数のテーブル（名前空間）を使用してデータを分離できます。

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# メインテーブル
db['key1'] = 'value1'

# 別のテーブルを使用
users = db.table('users')
users['alice'] = {'name': 'Alice', 'age': 30}
users['bob'] = {'name': 'Bob', 'age': 25}

settings = db.table('settings')
settings['theme'] = 'dark'

# 各テーブルは独立している
print(list(db.keys()))          # -> ['key1']
print(list(users.keys()))       # -> ['alice', 'bob']
print(list(settings.keys()))    # -> ['theme']
```

### テーブルモード

- **prefix**: キープレフィックスによる分離（高速、デフォルト）
- **separate**: 個別のSQLiteテーブルによる完全分離

```python
db = DictSQLite(':memory:', table_mode="separate")
```

## 一括操作

大量のデータを効率的に挿入できます。

```python
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')

# 辞書から一括挿入
data = {f'key{i}': f'value{i}' for i in range(1000)}
db.bulk_insert(data)

# リストから一括挿入
items = [(f'key{i}', f'value{i}') for i in range(1000)]
db.bulk_insert(items)
```

## その他の便利なメソッド

### 辞書メソッド

```python
# キー一覧
keys = db.keys()

# 値一覧
values = db.values()

# キーと値のペア
items = db.items()

# デフォルト値付き取得
value = db.get('key', 'default')

# デフォルト値を設定
db.setdefault('key', 'default_value')

# 取得して削除
value = db.pop('key')
value = db.pop('key', 'default')  # KeyErrorを避ける

# 更新
db.update({'key1': 'val1', 'key2': 'val2'})
db.update(key3='val3', key4='val4')

# 全削除
db.clear()

# 長さ
length = len(db)

# イテレーション
for key in db:
    print(key, db[key])
```

### 統計情報

```python
stats = db.stats()
print(stats)
# 例: {
#     'hot_tier_size': 1000,
#     'encryption_enabled': False,
#     'persist_mode': 'writethrough',
#     'storage_mode': 'pickle',
#     ...
# }
```

### フラッシュとクローズ

```python
# ホットティアをストレージへフラッシュ
db.flush()

# データベースをクローズ（自動的にフラッシュ）
db.close()
```

## v1.8.8からの移行

### 主な変更点

1. **暗号化パラメータ名の変更**
   ```python
   # v1.8.8
   db = DictSQLite('db.db', password='secret')
   
   # v2.x.x
   db = DictSQLite('db.db', encryption_password='secret')
   ```

2. **デフォルト動作の改善**
   - Pickleモードのシリアライゼーションが自動化
   - より高速なパフォーマンス
   - 改善されたエラーハンドリング

3. **新機能**
   - Safe Pickle検証
   - テーブルモード（prefix/separate）
   - 接続プールサイズの調整
   - 非同期awaitable API

詳細は [MIGRATION_FROM_1.8.8_JP.md](MIGRATION_FROM_1.8.8_JP.md) を参照してください。

## トラブルシューティング

### ネイティブ拡張が見つからない

```
RuntimeError: DictSQLite native extension not available.
```

**解決方法:**

開発環境でビルドが必要です：

```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

### パフォーマンスが遅い

**診断:**

```python
stats = db.stats()
print(f"Hot tier size: {stats['hot_tier_size']}")
```

**解決策:**

1. `hot_capacity` を増やす（メモリに余裕がある場合）
2. `persist_mode="lazy"` に変更（即座の永続化が不要な場合）
3. `pool_size` を増やす（並行アクセスが多い場合）

## 参考資料

- [使用例（日本語）](EXAMPLES_JP.md)
- [使用例（英語）](EXAMPLES_EN.md)
- [移行ガイド（日本語）](MIGRATION_FROM_1.8.8_JP.md)
- [移行ガイド（英語）](MIGRATION_FROM_1.8.8_EN.md)
- [ドキュメント目次](INDEX.md)

## ライセンス

MIT License

## サポート

- GitHub Issues: [https://github.com/disnana/DictSQLite](https://github.com/disnana/DictSQLite)
- Email: support@disnana.com
- Discord: [https://discord.gg/KzeHDrgwAz](https://discord.gg/KzeHDrgwAz)

