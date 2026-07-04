# ガイド

DictSQLite は、SQLite をバックエンドにした高速な永続化辞書です。v2 は Rust/PyO3 実装で、同期 API と非同期 API の両方を提供します。

## インストール

```bash
pip install dictsqlite
```

## 最小例

```python
from dictsqlite import DictSQLite

db = DictSQLite("cache.db")
db["user:1"] = {"name": "Alice", "score": 42}

print(db["user:1"])
db.close()
```

## 非同期 API

```python
import asyncio
from dictsqlite import AsyncDictSQLite

async def main():
    db = AsyncDictSQLite("cache.db")
    await db.set("job:1", {"status": "queued"})
    print(await db.get("job:1"))
    await db.close()

asyncio.run(main())
```

## 保存形式と永続化モード

- `storage_mode`: `pickle`, `jsonb`, `json`, `bytes`
- `persist_mode`: `memory`, `lazy`, `writethrough`
- `table_mode`: `prefix`, `separate`

Safe Pickle や暗号化が必要な場合は、信頼境界に合わせて設定してください。大量の書き込みでは `lazy`、確実な即時保存では `writethrough` が向いています。
