# 非同期 API

```python
from dictsqlite import AsyncDictSQLite

db = AsyncDictSQLite("async.db", persist_mode="lazy")
await db.set("k", "v")
value = await db.get("k")
await db.flush()
await db.close()
```

## バッチ操作

```python
await db.batch_set({"a": 1, "b": 2})
values = await db.batch_get(["a", "b", "missing"])
```

v2.1.3 では batch get のキャッシュミスを一括読み込みに寄せ、SQLite への細かい往復を減らしています。

## 終了処理

`lazy` モードでは `flush()` または `close()` を呼んでください。flush 失敗時は保留データを戻して再試行できるようにしています。
