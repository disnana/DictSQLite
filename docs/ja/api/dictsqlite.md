---
outline: [2, 3]
---

# API リファレンス

## `DictSQLite`

```python
from dictsqlite import DictSQLite

db = DictSQLite(
    "data.db",
    storage_mode="pickle",
    persist_mode="lazy",
    table_mode="prefix",
    safe_pickle=True,
)
```

| 操作 | 説明 |
|---|---|
| `db[key] = value` / `db.set(key, value)` | 値を保存します。 |
| `db[key]` / `db.get(key, default=None)` | 値を取得します。 |
| `del db[key]` / `db.delete(key)` | キーを削除します。 |
| `db.batch_set(dict)` | 複数キーをまとめて保存します。 |
| `db.batch_get(keys)` | 複数キーをまとめて取得します。 |
| `db.clear()` | 全データを削除します。 |
| `db.flush()` | lazy buffer をストレージへ反映します。 |
| `db.close()` | flush してリソースを閉じます。 |

## `AsyncDictSQLite`

```python
from dictsqlite import AsyncDictSQLite

db = AsyncDictSQLite("data.db")
await db.set("key", "value")
value = await db.get("key")
await db.close()
```

非同期版は `asyncio` ワークロード向けです。バッチ取得ではストレージの一括読み込みを利用し、キャッシュミス時の SQLite 往復を抑えます。

## `TableProxy`

```python
users = db.table("users")
users["alice"] = {"role": "admin"}
```

テーブルは名前空間を分けるための API です。`prefix` モードではキー接頭辞、`separate` モードでは SQLite の別テーブルを使います。

## 主なオプション

| オプション | 値 |
|---|---|
| `storage_mode` | `pickle`, `jsonb`, `json`, `bytes` |
| `persist_mode` | `memory`, `lazy`, `writethrough` |
| `table_mode` | `prefix`, `separate` |
| `safe_pickle` | `True` / `False` |
| `encryption_password` | `str` / `None` |
| `compression` | 設定により有効化 |
