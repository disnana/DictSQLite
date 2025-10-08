# DictSQLite v4.2 使用ガイド (日本語)

## 目次

1. [概要](#概要)
2. [インストール](#インストール)
3. [基本的な使い方](#基本的な使い方)
4. [セキュリティ機能](#セキュリティ機能)
5. [パフォーマンスモード](#パフォーマンスモード)
6. [高度な使い方](#高度な使い方)
7. [API リファレンス](#apiリファレンス)
8. [ベストプラクティス](#ベストプラクティス)
9. [トラブルシューティング](#トラブルシューティング)

---

## 概要

DictSQLite v4.2は、Pythonの辞書のように使える超高速SQLiteデータベースラッパーです。

### 主な特徴

- **🚀 超高速**: 100M+ ops/sec のロックフリー並行アクセス
- **🔒 セキュリティ**: AES-256-GCM暗号化とSafe Pickle検証
- **💾 柔軟な永続化**: メモリ、遅延、即時の3つの永続化モード
- **🔄 互換性**: DictSQLite v1/v2/v3との完全な後方互換性
- **⚡ Rust実装**: PyO3によるネイティブパフォーマンス

### v4.2での新機能

- **自動unpickle**: Safe Pickle有効時も自動的にデータを復元
- **改善されたセキュリティ**: デフォルトで危険な関数をブロック
- **バッファリング最適化**: WriteThoughモードでのバッチ処理

---

## インストール

### PyPIからインストール

```bash
pip install dictsqlite-v4
```

### ソースからビルド

```bash
# Rustツールチェーンが必要
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# プロジェクトをクローン
git clone https://github.com/yourusername/dictsqlite.git
cd dictsqlite/others/beta-versions/dictsqlite_v4.2

# ビルド＆インストール
maturin build --release
pip install target/wheels/dictsqlite_v4-*.whl
```

### 要件

- Python 3.9以上
- 64-bit OS (Windows, macOS, Linux)

---

## 基本的な使い方

### クイックスタート

```python
from dictsqlite_v4 import DictSQLiteV4

# データベースを作成
db = DictSQLiteV4("mydata.db")

# 辞書のように使う
db["user:1"] = b"Alice"
db["user:2"] = b"Bob"

# データを読み込む
print(db["user:1"])  # b"Alice"

# キーが存在するか確認
if "user:1" in db:
    print("User 1 exists!")

# 全キーを取得
for key in db.keys():
    print(key, db[key])

# データベースを閉じる
db.close()
```

### コンテキストマネージャー

```python
with DictSQLiteV4("mydata.db") as db:
    db["key"] = b"value"
    # 自動的にクローズされる
```

### メモリモード

```python
# 永続化なし、最速
db = DictSQLiteV4(":memory:")
```

---

## セキュリティ機能

### AES-256-GCM暗号化

機密データを暗号化して保存します。

```python
# 暗号化を有効化
db = DictSQLiteV4(
    "encrypted.db",
    encryption_password="your_secure_password_here"
)

# データは自動的に暗号化/復号化される
db["api_key"] = b"sk-1234567890abcdef"
db["password"] = b"super_secret"

# 読み込み時に自動復号化
api_key = db["api_key"]  # 自動的に復号化される
```

**重要な注意事項:**

- パスワードを忘れるとデータを復元できません
- 本番環境では環境変数からパスワードを読み込んでください
- パスワードは十分に複雑なものを使用してください

```python
import os

# 推奨: 環境変数から読み込む
password = os.getenv("DB_PASSWORD")
if not password:
    raise ValueError("DB_PASSWORD environment variable not set")

db = DictSQLiteV4("secure.db", encryption_password=password)
```

### Safe Pickle（安全なpickle）

信頼できないデータからシステムを保護します。

```python
import pickle

# Safe Pickleを有効化
db = DictSQLiteV4(
    "safe.db",
    enable_safe_pickle=True
)

# 安全なデータ型（dict, list, int, str など）は許可される
user_data = {
    "id": 1,
    "name": "Alice",
    "hobbies": ["reading", "coding"]
}
db["user:1"] = pickle.dumps(user_data)

# 自動的に安全にunpickleされる
restored = db["user:1"]  # 辞書が返される
print(restored["name"])  # "Alice"

# 危険な関数（__import__, os.system など）はブロックされる
try:
    dangerous = pickle.dumps(__import__)
    db["danger"] = dangerous  # 例外が発生！
except Exception as e:
    print(f"ブロックされました: {e}")
```

#### カスタムモジュールの許可

自作のクラスを使用したい場合:

```python
# 特定のモジュールプレフィックスを許可
db = DictSQLiteV4(
    "custom.db",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp", "mylib"]
)

# これで myapp.* と mylib.* 配下のクラスが使用可能
from myapp.models import User

user = User(name="Alice", age=30)
db["user:1"] = pickle.dumps(user)
restored_user = db["user:1"]  # Userオブジェクトが返される
```

### 暗号化 + Safe Pickle（最高セキュリティ）

両方を組み合わせて最高レベルのセキュリティを実現:

```python
db = DictSQLiteV4(
    "ultra_secure.db",
    encryption_password="ultra_secure_password",
    enable_safe_pickle=True
)

# データは暗号化され、かつpickle検証も行われる
sensitive_data = {
    "user_id": 1,
    "credit_card": "1234-5678-9012-3456",
    "balance": 100000
}
db["user:1"] = pickle.dumps(sensitive_data)

# 読み込み時: 復号化 → unpickle検証 → データ取得
user = db["user:1"]
```

---

## パフォーマンスモード

### 1. メモリモード（最速）

```python
db = DictSQLiteV4(
    ":memory:",
    persist_mode="memory"
)

# 永続化なし、全てメモリ上
# 最速だがプロセス終了時にデータ消失
```

**用途:**
- 一時的なキャッシュ
- セッションデータ
- テスト環境

### 2. 遅延永続化モード（高速 + 永続化）

```python
db = DictSQLiteV4(
    "data.db",
    persist_mode="lazy"
)

# 書き込みはメモリに保持
# 手動または自動でディスクに保存
db["key1"] = b"value1"
db["key2"] = b"value2"

# 明示的にディスクに保存
db.flush()

# コンテキストマネージャー使用時は自動保存
with DictSQLiteV4("data.db", persist_mode="lazy") as db:
    db["key"] = b"value"
    # 終了時に自動的にflush()される
```

**用途:**
- バッチ処理
- ログ収集
- 高速書き込みが必要な場合

### 3. 即時永続化モード（最も安全）

```python
db = DictSQLiteV4(
    "critical.db",
    persist_mode="writethrough"
)

# 全ての書き込みが即座にディスクに保存される
db["important"] = b"critical data"
# ↑ 即座にディスクに書き込まれる
```

**用途:**
- ミッションクリティカルなデータ
- トランザクション処理
- データ損失が許されない場合

### バッファサイズの調整

WriteThroughモードでバッファリングを活用:

```python
db = DictSQLiteV4(
    "buffered.db",
    persist_mode="writethrough",
    buffer_size=500  # 500件溜まったら一括保存
)

# バッファが溜まるまでメモリに保持
for i in range(1000):
    db[f"key_{i}"] = f"value_{i}".encode()
    # 500件ごとに自動的にディスクへ書き込み
```

---

## 高度な使い方

### ホットティアキャパシティの調整

```python
# ホットティア（メモリキャッシュ）のサイズを設定
db = DictSQLiteV4(
    "large.db",
    hot_capacity=10_000_000  # 1000万エントリまでメモリに保持
)
```

**推奨値:**
- 小規模: 100,000
- 中規模: 1,000,000（デフォルト）
- 大規模: 10,000,000以上

### テーブル名の指定

```python
# 異なるテーブルを使用
db_users = DictSQLiteV4("app.db", table_name="users")
db_products = DictSQLiteV4("app.db", table_name="products")

db_users["user:1"] = b"Alice"
db_products["product:1"] = b"Laptop"

# 同じDBファイルで別々のテーブルを使用
```

### JSONB ストレージモード

JSONデータを効率的に保存:

```python
db = DictSQLiteV4(
    "json.db",
    storage_mode="jsonb"  # MessagePack形式
)

# Pythonオブジェクトを直接保存
data = {
    "id": 1,
    "name": "Alice",
    "tags": ["admin", "active"]
}
db["user:1"] = data  # 自動的にシリアライズ

# 自動的にデシリアライズ
user = db["user:1"]  # 辞書が返される
```

### 統計情報の取得

```python
stats = db.stats()
print(stats)

# 出力例:
# {
#     'hot_tier_size': 1000,
#     'hot_tier_capacity': 1000000,
#     'num_shards': 32,
#     'encryption_enabled': True,
#     'safe_pickle_enabled': True,
#     'persist_mode': 'WriteThrough'
# }
```

### 辞書操作

```python
# 長さ
print(len(db))

# キーの存在確認
if "user:1" in db:
    print("Exists")

# デフォルト値付き取得
value = db.get("maybe_missing", default=b"default value")

# 更新
db.update({
    "key1": b"value1",
    "key2": b"value2"
})

# setdefault
value = db.setdefault("key", b"default")

# イテレーション
for key in db.keys():
    print(key)

for value in db.values():
    print(value)

for key, value in db.items():
    print(key, value)

# 削除
del db["key"]

# クリア
db.clear()
```

---

## APIリファレンス

### DictSQLiteV4クラス

#### コンストラクタ

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

**パラメータ:**

- `db_path`: データベースファイルのパス（`:memory:`でメモリモード）
- `hot_capacity`: ホットティア（メモリキャッシュ）の最大エントリ数
- `enable_async`: 非同期バックグラウンド処理を有効化（将来の拡張用）
- `persist_mode`: 永続化モード
  - `"memory"`: 永続化なし
  - `"lazy"`: 遅延永続化
  - `"writethrough"`: 即時永続化（デフォルト）
- `storage_mode`: ストレージ形式
  - `"pickle"`: Pythonピックル（デフォルト）
  - `"jsonb"`: MessagePack（JSON互換）
  - `"json"`: JSON文字列
  - `"bytes"`: 生バイト列
- `table_name`: 使用するテーブル名（デフォルト: "main"）
- `encryption_password`: 暗号化パスワード（Noneで暗号化なし）
- `enable_safe_pickle`: Safe Pickle検証を有効化
- `safe_pickle_allowed_modules`: 許可するモジュールプレフィックスのリスト
- `buffer_size`: WriteThoughモードのバッファサイズ
- `encoding`: 文字列エンコーディング（デフォルト: 'utf-8'）

#### メソッド

##### `__setitem__(key, value)`
```python
db["key"] = value
```
値を設定します。

##### `__getitem__(key)`
```python
value = db["key"]
```
値を取得します。キーが存在しない場合は`KeyError`を発生させます。

##### `__delitem__(key)`
```python
del db["key"]
```
キーと値を削除します。

##### `__contains__(key)`
```python
if "key" in db:
    ...
```
キーの存在を確認します。

##### `__len__()`
```python
size = len(db)
```
保存されているエントリ数を返します。

##### `get(key, default=None)`
```python
value = db.get("key", default=b"default")
```
デフォルト値付きで値を取得します。

##### `keys()`
```python
for key in db.keys():
    print(key)
```
全キーのイテレータを返します。

##### `values()`
```python
for value in db.values():
    print(value)
```
全値のイテレータを返します。

##### `items()`
```python
for key, value in db.items():
    print(key, value)
```
全キーと値のペアのイテレータを返します。

##### `update(other)`
```python
db.update({"key1": b"value1", "key2": b"value2"})
```
辞書または別のDictSQLiteから値を更新します。

##### `setdefault(key, default)`
```python
value = db.setdefault("key", b"default")
```
キーが存在しない場合のみデフォルト値を設定します。

##### `clear()`
```python
db.clear()
```
全てのエントリを削除します。

##### `flush()`
```python
db.flush()
```
バッファされたデータをディスクに書き込みます（lazyモードで使用）。

##### `stats()`
```python
stats = db.stats()
```
統計情報を辞書で返します。

##### `close()`
```python
db.close()
```
データベースを閉じます（コンテキストマネージャー使用時は自動）。

---

## ベストプラクティス

### 1. セキュリティ

```python
# ✅ 良い例: 環境変数から読み込む
import os
password = os.getenv("DB_PASSWORD")
db = DictSQLiteV4("secure.db", encryption_password=password)

# ❌ 悪い例: ハードコード
db = DictSQLiteV4("secure.db", encryption_password="hardcoded_password")
```

### 2. リソース管理

```python
# ✅ 良い例: コンテキストマネージャー
with DictSQLiteV4("data.db") as db:
    db["key"] = b"value"
    # 自動的にクローズ

# ❌ 悪い例: 手動管理（忘れる可能性）
db = DictSQLiteV4("data.db")
db["key"] = b"value"
# close()を忘れやすい
```

### 3. パフォーマンス

```python
# ✅ 良い例: バッチ処理にはlazyモード
with DictSQLiteV4("batch.db", persist_mode="lazy") as db:
    for i in range(100000):
        db[f"key_{i}"] = f"value_{i}".encode()
    # 終了時に一括保存

# ❌ 悪い例: 大量書き込みにwritethrough
db = DictSQLiteV4("batch.db", persist_mode="writethrough")
for i in range(100000):
    db[f"key_{i}"] = f"value_{i}".encode()
    # 毎回ディスクI/O → 遅い
```

### 4. エラーハンドリング

```python
# ✅ 良い例: 適切な例外処理
try:
    value = db["key"]
except KeyError:
    value = b"default"

# または
value = db.get("key", b"default")
```

### 5. データ型

```python
# ✅ 良い例: バイト列を使用
db["key"] = b"value"

# または pickle を使用
import pickle
db["user"] = pickle.dumps({"name": "Alice", "age": 30})
user = db["user"]  # 自動的に辞書に戻る

# ⚠️ 注意: 文字列は自動的にバイト列に変換されますが
# 明示的にバイト列を使う方が明確
```

### 6. 信頼できないデータ

```python
# ✅ 良い例: Safe Pickleを使用
db = DictSQLiteV4(
    "untrusted.db",
    enable_safe_pickle=True
)

# 外部からのデータでも安全
user_input = get_user_pickle_data()
db["user_data"] = user_input  # 危険な関数はブロックされる

# ❌ 悪い例: Safe Pickleなしで外部データ
db = DictSQLiteV4("unsafe.db")
db["user_data"] = user_input  # 危険！
```

---

## トラブルシューティング

### Q: パスワードを忘れました

**A:** 残念ながら、暗号化パスワードを忘れるとデータを復元できません。パスワード管理ツールの使用を推奨します。

### Q: "forbidden global" エラーが発生します

**A:** Safe Pickleが危険な関数をブロックしています。必要であれば`safe_pickle_allowed_modules`で許可してください。

```python
# カスタムクラスを許可
db = DictSQLiteV4(
    "data.db",
    enable_safe_pickle=True,
    safe_pickle_allowed_modules=["myapp"]
)
```

### Q: パフォーマンスが遅い

**A:** 以下を確認してください:

1. **永続化モード**: 大量書き込みには`lazy`モードを使用
2. **ホットキャパシティ**: `hot_capacity`を増やす
3. **バッファサイズ**: `buffer_size`を調整
4. **暗号化**: 必要ない場合は無効化

```python
# 高速化設定
db = DictSQLiteV4(
    "fast.db",
    hot_capacity=10_000_000,
    persist_mode="lazy",
    buffer_size=1000,
    encryption_password=None  # 暗号化なし
)
```

### Q: メモリ使用量が多い

**A:** `hot_capacity`を減らしてください:

```python
db = DictSQLiteV4(
    "low_memory.db",
    hot_capacity=10_000  # デフォルトの1,000,000から削減
)
```

### Q: データが永続化されない

**A:** 以下を確認:

1. メモリモード（`:memory:`）を使用していないか
2. `lazy`モードで`flush()`を呼んでいるか
3. コンテキストマネージャーまたは`close()`を使用しているか

```python
# 確実に永続化
with DictSQLiteV4("data.db", persist_mode="lazy") as db:
    db["key"] = b"value"
    db.flush()  # 明示的にフラッシュ
# 終了時にも自動フラッシュ
```

### Q: 複数プロセスから同じDBにアクセスできますか？

**A:** はい、可能です。SQLiteは複数プロセスからの読み込みと、適切なロックを持つ書き込みをサポートしています。ただし、同時書き込みが多い場合は注意が必要です。

### Q: スレッドセーフですか？

**A:** はい。内部でロックフリーなDashMapを使用しており、マルチスレッド環境で安全に使用できます。

---

## パフォーマンスベンチマーク

### テスト環境
- CPU: Intel Core i7
- RAM: 16GB
- OS: Windows 11

### 結果

| 操作 | 速度 | モード |
|------|------|--------|
| 書き込み | 100M+ ops/sec | Memory |
| 読み込み | 150M+ ops/sec | Memory |
| 暗号化書き込み | 12K ops/sec | WriteThrough + Encryption |
| Safe Pickle | 10K ops/sec | WriteThrough + Safe Pickle |
| 両方 | 8K ops/sec | WriteThrough + Both |

---

## バージョン履歴

### v4.2.0 (2025-10-08)
- ✨ Safe Pickle有効時の自動unpickle
- 🔒 デフォルトでDEFAULT_DENYを適用
- ⚡ WriteThroughモードのバッファリング最適化
- 🐛 Pickle検証の修正

### v4.1.0
- 🔒 Safe Pickle機能の追加
- 🔐 AES-256-GCM暗号化の追加

### v4.0.0
- 🚀 Rustによる完全書き直し
- ⚡ 100M+ ops/secの性能
- 💾 3つの永続化モード

---

## ライセンス

MIT License

---

## サポート

問題が発生した場合:

1. [GitHub Issues](https://github.com/disnana/DictSQLite/issues)
2. ドキュメントを確認
3. サンプルコードを参照

---

## 関連リンク

- [GitHub リポジトリ](https://github.com/disnana/DictSQLite)
- [PyPI パッケージ](https://pypi.org/project/dictsqlite-v4/)
- [サンプルコード](examples/)

---

**Happy Coding! 🎉**
