# ガイド

DictSQLite は、SQLite をバックエンドにした高速な永続化辞書です。v2 は Rust/PyO3 実装で、同期 API と非同期 API の両方を提供します。

## すぐ見る

- [API を見る](./api): DictSQLite / AsyncDictSQLite / TableProxy の操作一覧
- [モードを選ぶ](./storage): pickle/jsonb/json/bytes と lazy/writethrough の使い分け
- [非同期で使う](./async): asyncio 向けの set/get/batch/flush
- [性能を見る](./performance): サイズ・件数・バッチ・保存形式ごとの測定

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

## よく使う構成

| 用途 | おすすめ |
|---|---|
| 一時キャッシュ | `persist_mode="memory"` |
| 高速な永続キャッシュ | `persist_mode="lazy", storage_mode="jsonb"` |
| 書き込み直後の耐久性優先 | `persist_mode="writethrough"` |
| バイナリ保存 | `storage_mode="bytes"` |
| テーブル分離 | `table_mode="separate"` |
