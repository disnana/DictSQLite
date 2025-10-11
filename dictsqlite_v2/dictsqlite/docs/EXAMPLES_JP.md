DictSQLite v4 — 使い方例（日本語）

インポート（2通りの等価な書き方）
--------------------------------
# 推奨される公開 API 名
from dictsqlite import DictSQLite

# 実装名を使った例（リポジトリ内の例に出てくることがある）
from dictsqlite import DictSQLiteV4 as DictSQLite

基本的な同期使用例
-----------------
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')
# 文字列を保存
db['user:alice'] = 'Alice Smith'
# Python オブジェクト（デフォルトでは自動的に pickle される）
db['config'] = {'theme': 'dark', 'version': 2}

print(db['user:alice'])            # -> 'Alice Smith'
print(db.get('notfound', 'n/a'))   # -> 'n/a'

# イテレート
for k in db.keys():
    print(k, db[k])

db.close()

暗号化の例
---------
from dictsqlite import DictSQLite

# encryption_password を指定して AES-256-GCM 暗号化を有効にする
db = DictSQLite('secure.db', encryption_password='my_password')

db['token'] = 'secret'
print(db.stats()['encryption_enabled'])  # True を期待

db.close()

# 再度開いて読み込み
db2 = DictSQLite('secure.db', encryption_password='my_password')
print(db2['token'])
db2.close()

一括挿入（bulk_insert）の例
-------------------------
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')
# データの準備
data = {f'record:{i}': f'value_{i}' for i in range(1000)}
# 高速一括挿入
db.bulk_insert(data)

print('Inserted', len(list(db.keys())))

# クリア
db.clear()

非同期の例
---------
import asyncio
from dictsqlite import AsyncDictSQLite

async def async_demo():
    db = AsyncDictSQLite(':memory:')
    await db.aset('k', {'a': 1})
    v = await db.aget('k')
    print('async get:', v)

asyncio.run(async_demo())

Safe Pickle の例
----------------
from dictsqlite import DictSQLite

# enable_safe_pickle を使うと unpickle の検証が入る
db = DictSQLite(':memory:', enable_safe_pickle=True, safe_pickle_allowed_modules=['myapp'])

# 書き込み時や Rust 側の検証で危険なオブジェクトは弾かれる

val = db.get('maybe_bytes')
if isinstance(val, (bytes, bytearray)):
    import pickle
    try:
        obj = pickle.loads(val)
    except Exception:
        # 生のバイト列として扱う
        pass

テーブルプロキシ
--------------
other = db.table('other_table')
# テーブルプロキシ上でも多くの同様の API を使える

統計とフラッシュ
---------------
print(db.stats())
db.flush()

db.close()

備考
---
- これらの例はネイティブ拡張がビルドされて利用可能であることを前提としています。RuntimeError でネイティブ拡張が無いと出る場合はビルド手順に従ってください。
- リポジトリ内の例では `DictSQLiteV4` が登場することがありますが、公開 API としては `DictSQLite` を使うのが推奨です（V4 サフィックスは任意です）。
