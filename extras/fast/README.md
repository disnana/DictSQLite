# dictsqlite-fast (統合高速拡張)

`DictSQLite` 本体にオプション拡張として同梱された APSW ベース高速 / 互換レイヤです。
`pip install DictSQLite[fast]` で `apsw` を含む高速モード依存を追加インストールし、
`dictsqlite_fast` パッケージ (同期 `FastDictSQLite` / 非同期 `AsyncFastDictSQLite`) を利用できます。

## 目的 / コンセプト
- 既存 `DictSQLite` (sqlite3 + TEXT/BLOB) の *主要ユーザ API を保持* しつつ I/O オーバーヘッド削減
- 競合 (並列プロセス/スレッド) 発生時の簡易ファイルロック (`portalocker`) による衝突低減
- 透過的シリアライズ: `storage_mode = 'pickle' | 'json'`
  - pickle: 高速 / 任意オブジェクト (安全復元ガード付き)
  - json  : 監査性 / 外部ツール互換 (set は `{"__type__":"set","value":[...]}`)
- RSA 公開鍵暗号 (本家 `dictsqlite.modules.crypto`) 再利用
- safe pickle 復元 (許可モジュール / builtins / グローバル名ホワイトリスト)
- トップレベル list/set 双方向同期 (`DBSyncedList` / `DBSyncedSet`)
- ネスト辞書は遅延同期付きプロキシ (`RecursiveDict`) で部分更新
- version=2: テーブル多重化 (`db[(key, table)] = value` / `db['table']` -> `TableProxy`)
- 非同期 API (`AsyncFastDictSQLite`): スレッドプール + 内部直列キューで await 対応

## インストール
```bash
pip install DictSQLite
pip install "DictSQLite[fast]"
```
Windows で APSW ホイールが無い組み合わせはビルドが走るため、Python / SQLite バージョンに適合する事前ビルドの有無を確認してください。

## 主要クラス速習
| クラス | 用途 | 備考 |
|--------|------|------|
| `FastDictSQLite` | 同期版高速辞書 DB | 旧 `DictSQLite` API 互換 (一部メソッド名 / 振る舞い) |
| `AsyncFastDictSQLite` | 非同期ラッパ | await ベース / dict アクセス構文は `get/set` メソッドで代替 |
| `DBSyncedList` / `DBSyncedSet` | トップレベルコレクション自動同期 | ネスト内 (再帰的 list/set) は非同期 (意図的) |
| `RecursiveDict` | ネスト dict プロキシ | 部分更新時のみトップレベル差し替え |

## 最小例 (同期)
```python
from dictsqlite_fast import FastDictSQLite

db = FastDictSQLite('example.db', storage_mode='pickle')
db['user'] = {'profile': {'name': 'Alice'}, 'tags': {1,2}}
print(db['user']['profile']['name'])  # 'Alice'

# top-level list/set は同期される
db['nums'] = [1,2]
nums = db['nums']
nums.append(3)
assert db['nums'] == [1,2,3]

db.close()
```

## 最小例 (非同期)
```python
import asyncio
from dictsqlite_fast import AsyncFastDictSQLite

async def main():
    db = AsyncFastDictSQLite('example_async.db', storage_mode='json')
    try:
        await db.set('cfg', {'x': 1})
        val = await db.get('cfg')
        print(val['x'])  # 1
        await db.transaction_bulk([(f'k{i}', i) for i in range(5)])
        assert await db.get('k4') == 4
    finally:
        await db.close()

asyncio.run(main())
```

## version=2 / マルチテーブル
```python
v2 = FastDictSQLite('multi.db', version=2)
# 明示的にテーブル作成
v2.create_table(table_name='user')
v2.create_table(table_name='cache')

v2[('u1','user')] = {'name': 'Alice'}
v2[('c1','cache')] = 42
print(v2['user']['u1'])  # {'name': 'Alice'}
```

## 競合解決 (ロック)
```python
from dictsqlite_fast import FastDictSQLite

# 全書き込みオペレーションをロック付きで順次処理
shared = FastDictSQLite('shared.db', conflict_resolver=True)
shared['a'] = 1
shared.flush()
```
`conflict_resolver=True` 時は各キュー処理単位で `portalocker` による排他ロックファイル (デフォルト `<db>.lock`) を取得してから SQL を実行します。超高並列 (> 数十スレッド) ケースでは OS ロック競合が律速になる可能性があります。

## JSON モード詳細
```python
jdb = FastDictSQLite('j.db', storage_mode='json')
jdb['cfg'] = {'features': {'enable': True}, 'tags': {1,2,3}}
assert jdb['cfg']['features']['enable'] is True
```
- set は `{"__type__":"set","value":[...]}` 形式で保存
- `DBSyncedList/Set` は list / set として JSON 化 (set -> ソート済 list)
- ネスト list/set は再取得時に同期されない (意図: 無駄な DB 書き込み抑制)

## 安全な pickle 復元
```python
from dictsqlite.modules.safe_pickle import SafePolicy
pdb = FastDictSQLite('secure.db', safe_pickle_policy=SafePolicy(disable_functions=True))
pdb['obj'] = {'a': 1}
# 復元時: 許可ポリシー外 (関数等) は base64 文字列フォールバック
```

## 暗号化 (RSA 公開鍵)
```python
from dictsqlite_fast import FastDictSQLite
from dictsqlite.modules import crypto

crypto.key_create(password='pw', pubkey_path='pub.pem', private_key_path='priv.pem')
edb = FastDictSQLite('enc.db', password='pw', publickey_path='pub.pem', privatekey_path='priv.pem')
edb['secret'] = {'token': 'xxx'}
assert edb['secret']['token'] == 'xxx'
```
内部ではシリアライズ (pickle/JSON) 後に RSA で暗号化したバイト列を BLOB 保存します。

## `AsyncFastDictSQLite` 設計
- 内部に 1 つの `FastDictSQLite` インスタンスを保持
- 各 API 呼び出しは `loop.run_in_executor()` で同期メソッドを実行 (GIL 競合が軽微なため十分高速)
- 低レイテンシ用途では将来的に APSW の asyncio インターフェイス活用へ移行可能
- dict 構文 (`db['k']`) は await を挟めないため *利用不可* -> `await db.get('k') / await db.set('k', v)` を使用

## 本家 API 互換表
| 元 `DictSQLite` メソッド | FastDictSQLite | AsyncFastDictSQLite | 備考 |
|--------------------------|----------------|---------------------|------|
| `__getitem__` / `__setitem__` | 対応 | 非同期版は `get/set` メソッド | version=2 で (key, table) 受付 |
| `has_key` | 対応 | `has_key` (内部 `contains`) | |
| `clear_table` | 対応 | `clear_table` | |
| `clear_db` | 対応 | `clear_db` | 全テーブル drop + `main` 再作成 |
| `switch_table` | 対応 | `switch_table` | |
| `execute_custom` | `execute` alias | `execute_custom` alias | |
| `begin/commit/rollback` | 対応 | 対応 | キュー投入 (`BEGIN IMMEDIATE`) |
| `expiring_dict` | 対応 | `expiring_dict` | utils.ExpiringDict を生成 |

## 相違点 / 注意
- 値カラムは常時 BLOB (pickle/暗号化/JSON バイト列)。旧 TEXT 想定 DB とは直接互換でない場合あり
- version=2 の `db['table']` は「テーブル辞書」プロキシ (直接キー列挙可能) を返し、`db['table']['key']` で値アクセス
- ネスト list/set 自動同期無し (トップレベルのみ同期) 方針は旧版互換
- 例外: 非同期版は `KeyError` -> `await get()` で `default` を返却 (デフォルト None)
- 競合解決はロックコストのため高頻度ライト/超並列環境ではベンチ確認推奨

## 内部アーキテクチャ概要
```
 FastDictSQLite
 ├─ Queue (operation_queue)
 │   └─ Worker Thread 1  (serialize -> (lock?) -> execute)
 ├─ Serialization
 │   ├─ pickle (safe_loads wrapper)
 │   └─ json   (set 型カスタム / DBSyncedList/Set flatten)
 ├─ Encryption (optional RSA, crypto module)
 ├─ Conflict Resolver (portalocker EX lock per op)
 ├─ Proxies
 │   ├─ TableProxy (テーブル単位 CRUD)
 │   ├─ RecursiveDict (ネスト dict 部分更新)
 │   ├─ DBSyncedList / DBSyncedSet (トップレベル同期)
 └─ Version=2: (key, table) multi-table addressing

 AsyncFastDictSQLite
 └─ run_in_executor -> FastDictSQLite (順序保証: 単一内部キュー)
```

## テスト
プロジェクトルートで (APSW がインストールされている場合):
```bash
pytest extras/fast/tests -q
```
非同期 API 用に同期テストを反映した `test_async_*.py` 群を追加しています。

## 今後の改善候補
- APSW の asyncio ネイティブ API への移行 (run_in_executor オーバーヘッド削減)
- items()/values() の一括フェッチ最適化
- prefix/範囲検索の追加 (適切なインデックス/バイナリ比較)
- BLOB 圧縮 (統計しきい値ベース)
- バッチ書き込み (複数 put の単一トランザクション化ヘルパ)

## ライセンス
MIT (本家 DictSQLite と同一)
