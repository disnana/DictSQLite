# DictSQLite v4.2 - クイックリファレンス（JSONB & テーブル）

## 🚀 クイックスタート

### インストール

```bash
cd dictsqlite_v4.2
maturin develop --release
```

## 📦 ストレージモード

### 使い分けガイド

| 用途 | 推奨モード | 理由 |
|------|-----------|------|
| 本番環境 | `jsonb` | 最速・最小サイズ |
| デバッグ | `json` | 可読性（SQLiteブラウザで確認可） |
| 複雑なオブジェクト | `pickle` | 任意のPythonオブジェクト対応 |
| バイナリデータ | `bytes` | 変換なし |

### コード例

```python
from dictsqlite_v4 import DictSQLiteV4

# JSONB（推奨）
db = DictSQLiteV4("data.db", storage_mode="jsonb")
db["user"] = {"name": "Alice", "age": 30}

# JSON（デバッグ用）
db = DictSQLiteV4("data.db", storage_mode="json")

# Pickle（デフォルト）
db = DictSQLiteV4("data.db")  # storage_mode="pickle"

# Bytes
db = DictSQLiteV4("data.db", storage_mode="bytes")
db["data"] = b"\x00\x01\x02"
```

## 🗂️ テーブル操作

### 方法1: テーブルプロキシ

```python
db = DictSQLiteV4("app.db", storage_mode="jsonb")

# テーブル取得
users = db.table("users")
products = db.table("products")

# 操作
users["user1"] = {"name": "Alice"}
products["prod1"] = {"price": 100}

# 読み取り
print(users["user1"])
print(products["prod1"])
```

### 方法2: デフォルトテーブル

```python
users_db = DictSQLiteV4(
    "app.db",
    table_name="users",
    storage_mode="jsonb"
)

users_db["user1"] = {"name": "Alice"}
print(users_db["user1"])
```

## 📋 TableProxy API

```python
table = db.table("my_table")

# 基本操作
table["key"] = value          # 設定
value = table["key"]          # 取得
del table["key"]              # 削除
"key" in table               # 存在確認

# イテレーション
table.keys()                 # キー一覧
table.values()               # 値一覧
table.items()                # (key, value)のリスト

# その他
table.get("key", default)    # デフォルト値付き取得
table.clear()                # 全削除
len(table)                   # アイテム数
```

## 🔄 非同期版

```python
from dictsqlite_v4 import AsyncDictSQLite

async_db = AsyncDictSQLite(
    "async.db",
    storage_mode="jsonb"
)

# テーブル
users = async_db.table("users")
users["user1"] = {"name": "Alice"}
```

## 🎯 パフォーマンス設定

### 最高速度

```python
db = DictSQLiteV4(
    "fast.db",
    storage_mode="jsonb",       # 最速
    persist_mode="memory",      # メモリのみ
    buffer_size=500             # 大きいバッファ
)
```

### バランス型

```python
db = DictSQLiteV4(
    "balanced.db",
    storage_mode="jsonb",
    persist_mode="lazy",        # 定期フラッシュ
    buffer_size=100             # デフォルト
)
```

### 安全性重視

```python
db = DictSQLiteV4(
    "safe.db",
    storage_mode="jsonb",
    persist_mode="writethrough", # 即座に永続化
    buffer_size=50               # 小さいバッファ
)
```

## ⚡ よくあるパターン

### マルチテーブルアプリ

```python
db = DictSQLiteV4("app.db", storage_mode="jsonb")

users = db.table("users")
posts = db.table("posts")
comments = db.table("comments")

users["u1"] = {"name": "Alice"}
posts["p1"] = {"title": "Hello", "author": "u1"}
comments["c1"] = {"post": "p1", "text": "Nice!"}
```

### 設定管理

```python
config_db = DictSQLiteV4(
    "config.db",
    table_name="app_config",
    storage_mode="json"  # 可読性重視
)

config_db["theme"] = "dark"
config_db["language"] = "ja"
```

### キャッシュ

```python
cache = DictSQLiteV4(
    "cache.db",
    storage_mode="jsonb",
    persist_mode="memory",  # メモリのみ
    hot_capacity=10_000     # 大きいキャッシュ
)

cache["api_response"] = {"data": [...]}
```

## 🔍 デバッグ

### テーブル内容確認

```python
# すべてのテーブル
print(db.tables())

# テーブル内のキー
users = db.table("users")
print(users.keys())

# すべてのアイテム
for key in users.keys():
    print(f"{key}: {users[key]}")
```

### JSON形式で保存して確認

```python
db = DictSQLiteV4("debug.db", storage_mode="json")
db["test"] = {"data": "value"}

# SQLiteブラウザで直接確認可能
```

## ⚠️ 注意点

### JSONBの制約

```python
# ✅ OK
db["data"] = {"list": [1, 2, 3], "dict": {"a": 1}}

# ❌ NG（JSON非互換）
db["data"] = {"set": {1, 2, 3}}  # setは不可
db["data"] = MyClass()           # カスタムクラス不可

# → Pickleモードを使用
db_pickle = DictSQLiteV4("data.db", storage_mode="pickle")
db_pickle["data"] = {"set": {1, 2, 3}}  # OK
```

### テーブル名の制約

```python
# ✅ 推奨
db.table("users")
db.table("user_profiles")

# ❌ 避ける（コロンはプレフィックス区切り文字）
db.table("user:profiles")  # 動作するが推奨しない
```

## 📚 さらに詳しく

- [README_V4.2_JP.md](./README_V4.2_JP.md) - 完全なドキュメント
- [JSONB_TABLE_IMPLEMENTATION_SUMMARY_JP.md](./JSONB_TABLE_IMPLEMENTATION_SUMMARY_JP.md) - 実装詳細
- [examples/jsonb_table_usage_example.py](./examples/jsonb_table_usage_example.py) - サンプルコード

---

**バージョン**: v4.2.0
