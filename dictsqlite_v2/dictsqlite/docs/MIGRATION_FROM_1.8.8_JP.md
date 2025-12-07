# DictSQLite v1.8.8 から v2.0.7 への移行ガイド

このガイドでは、DictSQLite v1.8.8 から v2.0.7（内部バージョン v4）への移行方法を説明します。

## 目次

1. [概要](#概要)
2. [主な変更点](#主な変更点)
3. [破壊的変更](#破壊的変更)
4. [新機能](#新機能)
5. [移行手順](#移行手順)
6. [コード例](#コード例)
7. [トラブルシューティング](#トラブルシューティング)

## 概要

### バージョン情報

- **v1.8.8**: 旧バージョン（Python実装）
- **v2.0.7**: 新バージョン（Rust + Python、PyPI公開バージョン）
- **v4**: 内部実装バージョン名（アーキテクチャラベル）

### 互換性

DictSQLite v2は、v1.8.8との**API互換性**を重視して設計されています。ほとんどのコードは最小限の変更で動作します。

## 主な変更点

### 1. パラメータ名の変更

#### 暗号化パラメータ

```python
# v1.8.8
db = DictSQLite('db.db', password='secret')

# v2.0.7
db = DictSQLite('db.db', encryption_password='secret')
```

**理由**: より明確な命名により、パラメータの目的が明確になります。

### 2. インポート名

**推奨されるインポート:**

```python
# v1.8.8
from dictsqlite import DictSQLite

# v2.0.7（同じ）
from dictsqlite import DictSQLite
```

**内部実装名（オプション）:**

```python
# v2.0.7では内部実装名も使用可能
from dictsqlite import DictSQLiteV4  # DictSQLite のエイリアス
```

> **注意**: 新しいコードでは `DictSQLite` の使用を推奨します。`DictSQLiteV4` は後方互換性のために提供されています。

### 3. デフォルト動作の改善

#### Pickleモードの自動化

```python
# v1.8.8（手動シリアライゼーションが必要な場合があった）
import pickle
db['key'] = pickle.dumps({'data': 'value'})
value = pickle.loads(db['key'])

# v2.0.7（自動化）
db['key'] = {'data': 'value'}
value = db['key']  # 自動的にデシリアライズ
```

### 4. パフォーマンスの大幅向上

- **v1.8.8**: Python実装、~1M ops/sec
- **v2.0.7**: Rust実装、100M+ ops/sec（100倍以上高速）

### 5. 新しいコンストラクタパラメータ

v2.0.7で追加されたパラメータ:

```python
DictSQLite(
    db_path,
    hot_capacity=1_000_000,         # 新規: ホットキャッシュサイズ
    enable_async=True,              # 新規: 非同期フラッシュ
    persist_mode="writethrough",    # 既存（改善）
    storage_mode="pickle",          # 既存（改善）
    table_name="main",              # 既存
    encryption_password=None,       # 変更: password → encryption_password
    enable_safe_pickle=False,       # 新規: Safe Pickle検証
    safe_pickle_allowed_modules=None,  # 新規: 許可モジュール
    buffer_size=100,                # 新規: バッファサイズ
    encoding='utf-8',               # 新規: エンコーディング
    table_mode="prefix",            # 新規: テーブルモード
    pool_size=20                    # 新規: 接続プールサイズ
)
```

## 破壊的変更

### 1. 暗号化パラメータ名の変更（必須）

**影響**: 暗号化を使用しているすべてのコード

**移行前（v1.8.8）:**
```python
db = DictSQLite('secure.db', password='my_password')
```

**移行後（v2.0.7）:**
```python
db = DictSQLite('secure.db', encryption_password='my_password')
```

### 2. ネイティブ拡張のビルド（開発環境のみ）

**影響**: ソースから開発する場合

**必要な操作:**
```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

**注意**: PyPIからインストールする場合は不要です。

### 3. Pythonバージョン要件

- **v1.8.8**: Python 3.7+
- **v2.0.7**: Python 3.9+

## 新機能

### 1. Safe Pickle検証

信頼できないデータの安全なデシリアライズ:

```python
db = DictSQLite(
    'db.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp', 'mylib']
)
```

### 2. テーブルモード

#### Prefixモード（デフォルト、高速）

```python
db = DictSQLite(':memory:', table_mode='prefix')
users = db.table('users')
settings = db.table('settings')
```

#### Separateモード（完全分離）

```python
db = DictSQLite(':memory:', table_mode='separate')
# 各テーブルが個別のSQLiteテーブルとして作成される
```

### 3. 非同期Awaitable API

真のasyncio統合:

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

### 4. 接続プールサイズの調整

並行アクセスの最適化:

```python
db = DictSQLite('db.db', pool_size=50)  # 高並行環境向け
```

### 5. ホットキャパシティの調整

メモリキャッシュサイズの制御:

```python
db = DictSQLite('db.db', hot_capacity=10_000_000)  # 1000万エントリ
```

## 移行手順

### ステップ1: パッケージのインストール

```bash
pip install --upgrade dictsqlite
```

### ステップ2: インポートの確認

コードのインポート文を確認（通常は変更不要）:

```python
from dictsqlite import DictSQLite  # これは変更不要
```

### ステップ3: パラメータ名の更新

暗号化を使用している場合、パラメータ名を更新:

```python
# 移行前
db = DictSQLite('db.db', password='secret')

# 移行後
db = DictSQLite('db.db', encryption_password='secret')
```

### ステップ4: テストの実行

既存のテストスイートを実行して動作を確認:

```bash
python -m pytest tests/
```

### ステップ5: パフォーマンスの確認

統計情報を確認してパフォーマンスを測定:

```python
stats = db.stats()
print(stats)
```

## コード例

### 例1: 基本的な移行

**v1.8.8のコード:**
```python
from dictsqlite import DictSQLite

# 基本的な使用
db = DictSQLite('myapp.db')
db['user:1'] = {'name': 'Alice', 'age': 30}
user = db['user:1']
db.close()

# 暗号化
secure_db = DictSQLite('secure.db', password='secret123')
secure_db['token'] = 'abc123'
secure_db.close()
```

**v2.0.7への移行:**
```python
from dictsqlite import DictSQLite

# 基本的な使用（変更なし）
db = DictSQLite('myapp.db')
db['user:1'] = {'name': 'Alice', 'age': 30}
user = db['user:1']
db.close()

# 暗号化（パラメータ名を変更）
secure_db = DictSQLite('secure.db', encryption_password='secret123')
secure_db['token'] = 'abc123'
secure_db.close()
```

### 例2: 新機能の活用

```python
from dictsqlite import DictSQLite

# Safe Pickleを有効化
db = DictSQLite(
    'db.db',
    encryption_password='secret',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['myapp']
)

# テーブル機能
users = db.table('users')
users['alice'] = {'name': 'Alice', 'role': 'admin'}

settings = db.table('settings')
settings['theme'] = 'dark'

db.close()
```

### 例3: 非同期への移行

**v1.8.8（同期のみ）:**
```python
from dictsqlite import DictSQLite

db = DictSQLite('db.db')

for i in range(1000):
    db[f'key_{i}'] = f'value_{i}'

db.close()
```

**v2.0.7（非同期）:**
```python
from dictsqlite import AsyncDictSQLite
import asyncio

async def main():
    db = AsyncDictSQLite('db.db')
    
    # バッチ操作で高速化
    items = [(f'key_{i}', f'value_{i}') for i in range(1000)]
    await db.abatch_set(items)
    
    await db.aclose()

asyncio.run(main())
```

### 例4: パフォーマンス最適化

```python
from dictsqlite import DictSQLite

# v1.8.8のデフォルト設定
db_old = DictSQLite('db.db')

# v2.0.7の最適化設定
db_new = DictSQLite(
    'db.db',
    hot_capacity=10_000_000,  # 大きなキャッシュ
    persist_mode='lazy',       # 遅延書き込み
    pool_size=50,              # 大きな接続プール
    buffer_size=1000           # 大きなバッファ
)
```

## トラブルシューティング

### 問題1: RuntimeError: DictSQLite native extension not available

**原因**: ネイティブ拡張がビルドされていない（開発環境のみ）

**解決方法:**
```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

**注意**: PyPIからインストールした場合、この問題は発生しません。

### 問題2: KeyError or TypeError after migration

**原因**: 暗号化パラメータ名の変更

**解決方法:**
```python
# 誤り
db = DictSQLite('db.db', password='secret')

# 正しい
db = DictSQLite('db.db', encryption_password='secret')
```

### 問題3: Pickle関連のエラー

**原因**: v1.8.8とv2.0.7でpickleの扱いが異なる場合がある

**解決方法:**

Safe Pickleを有効化:
```python
db = DictSQLite(
    'db.db',
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=['your_module']
)
```

または、ストレージモードを変更:
```python
db = DictSQLite('db.db', storage_mode='jsonb')
```

### 問題4: 既存のデータベースが読めない

**原因**: 暗号化パスワードの不一致

**解決方法:**

v1.8.8で使用したパスワードを正確に指定:
```python
# v1.8.8で保存
# db = DictSQLite('db.db', password='old_password')

# v2.0.7で読み込み
db = DictSQLite('db.db', encryption_password='old_password')
```

### 問題5: パフォーマンスが期待より遅い

**診断:**
```python
stats = db.stats()
print(f"Hot tier size: {stats['hot_tier_size']}")
print(f"Persist mode: {stats['persist_mode']}")
```

**解決方法:**

パラメータを調整:
```python
db = DictSQLite(
    'db.db',
    hot_capacity=10_000_000,  # 増やす
    persist_mode='lazy',       # 変更
    pool_size=50               # 増やす
)
```

## データベースファイルの互換性

### v1.8.8のデータベースをv2.0.7で使用

**暗号化なし:**
```python
# v1.8.8で作成したデータベースをそのまま開ける
db = DictSQLite('old_v1.8.8.db')
```

**暗号化あり:**
```python
# パラメータ名を変更するだけ
# v1.8.8: password='secret'
# v2.0.7: encryption_password='secret'
db = DictSQLite('encrypted_v1.8.8.db', encryption_password='secret')
```

### v2.0.7のデータベースをv1.8.8で使用

基本的に互換性がありますが、v2.0.7の新機能（Safe Pickle、テーブルモードなど）を使用した場合は、v1.8.8では正しく動作しない可能性があります。

## チェックリスト

移行前に以下を確認してください:

- [ ] Python 3.9以上がインストールされている
- [ ] `pip install --upgrade dictsqlite` を実行した
- [ ] `password=` を `encryption_password=` に変更した
- [ ] テストスイートが通過する
- [ ] パフォーマンスが改善されているか確認した
- [ ] 新機能（Safe Pickle、テーブルモードなど）を検討した

## 推奨される移行戦略

### 戦略1: 段階的移行（推奨）

1. まず、テスト環境で移行
2. パラメータ名を更新
3. テストを実行して動作確認
4. 本番環境に展開

### 戦略2: 並行運用

1. v1.8.8とv2.0.7を並行運用
2. 新機能はv2.0.7で実装
3. 徐々にv2.0.7に移行
4. v1.8.8を廃止

## 参考資料

- [README_JP.md](README_JP.md) - v2.0.7のクイックスタート
- [EXAMPLES_JP.md](EXAMPLES_JP.md) - 実践的な使用例
- [README_EN.md](README_EN.md) - English documentation
- [EXAMPLES_EN.md](EXAMPLES_EN.md) - English examples

## サポート

移行に関する質問やサポートが必要な場合:

- **GitHub Issues**: [https://github.com/disnana/DictSQLite/issues](https://github.com/disnana/DictSQLite/issues)
- **Email**: support@disnana.com
- **Discord**: [https://discord.gg/KzeHDrgwAz](https://discord.gg/KzeHDrgwAz)

---

**最終更新**: 2025年12月7日  
**対象バージョン**: v1.8.8 → v2.0.7（内部バージョン v4）

