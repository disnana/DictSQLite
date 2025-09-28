# dictsqlite-fast

APSW を用いて `DictSQLite` の主要 API と互換性を保ちながら高速化・競合制御 (ファイルロック)・安全なシリアライズを提供する拡張パッケージです。

## 特長
- APSW による低オーバーヘッド / 細かな PRAGMA 制御
- `storage_mode`: `pickle` / `json`
- RSA 暗号化 (本家 `DictSQLite` の crypto モジュール再利用)
- safe pickle 復元 (許可モジュール / 組み込み / グローバル制御)
- `DBSyncedList` / `DBSyncedSet` / `RecursiveDict` によるトップレベル同期とネスト辞書操作
- `version=2` モード対応 (テーブル選択 / `(key, table)` 指定)
- `conflict_resolver=True` で `portalocker` による排他 (並列プロセス/スレッド書き込み軽減)
- 旧 API: `has_key`, `clear_table`, `clear_db`, `switch_table`, `execute_custom`, `expiring_dict` 互換

## インストール
```bash
pip install DictSQLite apsw
# または (将来の PyPI 公開後)
# pip install dictsqlite-fast
```

Windows で APSW をビルドせず使いたい場合は、事前に対応する Python / SQLite バージョンのホイールがあるか確認してください。

## 使い方
```python
from dictsqlite_fast import FastDictSQLite

db = FastDictSQLite('example.db', storage_mode='pickle')
db['a'] = {'nested': {'x': 1}, 'lst': [1, 2], 's': {1, 2}}
print(db['a']['nested']['x'])  # 1

lst = db['a']['lst']  # DBSyncedList (トップレベル list のみ同期対象)
lst.append(3)
print(db['a']['lst'])  # [1,2,3]

with FastDictSQLite('tmp.db', conflict_resolver=True) as txdb:
    txdb.begin()
    txdb['k'] = 123
    txdb.commit()
```

## JSON モード
```python
jdb = FastDictSQLite('json.db', storage_mode='json')
jdb['cfg'] = {'features': {'enable': True}, 'tags': {1,2,3}}
print(jdb['cfg']['features']['enable'])
```
`s.storage_mode == 'json'` の場合、`set` は `{"__type__":"set","value":[...]}` として保存されます。ネスト list / set は本家同様自動同期されません。

## 安全な pickle
```python
from dictsqlite.modules.safe_pickle import SafePolicy
policy = SafePolicy(disable_functions=True)
pdb = FastDictSQLite('secure.db', safe_pickle_policy=policy)
pdb['obj'] = {'a': 1}
```

## テーブル操作 (version=2)
```python
v2 = FastDictSQLite('multi.db', version=2)
v2.switch_table('user')
v2[('u1','user')] = {'name': 'Alice'}
v2.switch_table('cache')
v2[('c1','cache')] = 42
print(v2['user']['u1'])
```

## 差異 / 注意
- value カラム型は常に BLOB。TEXT 互換を期待する既存 DB とは直接互換でない可能性があります。
- 旧実装のバックグラウンドスレッド構造を簡素化 (単一ワーカーモデル) しています。
- トランザクションは `BEGIN IMMEDIATE` を非同期キューに投入して実行。
- 競合解決モードでは各操作単位でファイルロックを取得します。

## テスト実行
プロジェクトルートで:
```bash
pytest extras/fast/dictsqlite-fast/tests -q
```
APSW が未インストールの場合はスキップされます。

## ライセンス
MIT (本家 DictSQLite と同一)

## 今後の改善候補
- AsyncFastDictSQLite の API を本家テーブル操作互換に拡張
- 一括フェッチ最適化 (items の高速化)
- ベンチマークスクリプト追加

