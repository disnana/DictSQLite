DictSQLite v4 — クイックスタート（日本語）

概要
----
DictSQLite は、ネイティブな高性能ストレージをバックエンドに持つ、辞書ライクな Python API を提供します。同期・非同期の両方のバリアントがあり、パフォーマンス向上、暗号化、安全性の機能が追加されています。v1.8.8 と互換性を保つよう設計されています。

インポート / クラス名
--------------------
ドキュメント内では推奨するインポート名を `DictSQLite` としています。リポジトリや一部の例で `DictSQLiteV4` と書かれている箇所がありますが、この "V4" サフィックスは任意です。インストール環境で `DictSQLite` がエクスポートされているか確認し、どちらか利用してください。
```py
from dictsqlite import DictSQLite
```
同期（基本）使用例
------------------
```py
from dictsqlite import DictSQLite

db = DictSQLite(':memory:')
db['user:alice'] = 'Alice Smith'        # 文字列をそのまま保存
db['config'] = {'theme': 'dark'}       # デフォルトではオブジェクトは pickle される

print(db['user:alice'])                 # -> 'Alice Smith'
print(db.get('missing', 'default'))     # -> 'default'

db.close()
```
コンテキストマネージャ
---------------------
```py
with DictSQLite('app.db') as db:
    db['a'] = 1
    print(db['a'])
```
非同期（awaitable）
------------------
非同期用ラッパー `AsyncDictSQLite` は awaitable なメソッドを提供します。
```py
from dictsqlite import AsyncDictSQLite

async def main():
    db = AsyncDictSQLite(':memory:')
    await db.aset('k', 'value')
    v = await db.aget('k')
```
非同期クラスは互換目的の同期ラッパー（`get`, `set`, `batch_get`, `batch_set`）も持っていますが、asyncio を使うなら awaitable API を推奨します。

主なコンストラクタオプション
---------------------------
- db_path (str): ファイルパスまたは ':memory:'
- hot_capacity (int): メモリ上のホットキャッシュの最大サイズ（デフォルト 1_000_000）
- enable_async (bool): バックグラウンドの非同期フラッシュを有効にするか
- persist_mode (str): 'memory', 'lazy', 'writethrough'（耐久性に関する設定）
- storage_mode (str): 'pickle'（デフォルト）または 'jsonb'（値の格納方式）
- table_name (str): 使用するテーブル名（デフォルト 'main'）
- encryption_password (str|None): AES-256-GCM 暗号化を有効にするパスワード
- enable_safe_pickle (bool): SAFE Pickle 検証を有効にする
- safe_pickle_allowed_modules (list): Safe Pickle で許可するモジュール接頭辞リスト
- buffer_size (int): 非同期バッチのバッファサイズ
- encoding (str): bytes->str デコードに使うエンコーディング（'utf-8'）

シリアライズ動作
----------------
- デフォルトの storage_mode は 'pickle' で、ほとんどの Python オブジェクトが自動的に pickle / unpickle されます。
- 文字列は可能な限り str のまま返されます。
- 'jsonb' などを使う、あるいはバイト列を直接保存した場合はバイナリが返ることがあります。その場合は pickle.loads や decode を手動で行ってください。

Safe Pickle
-----------
`enable_safe_pickle=True` にすると、unpickle 時の安全性検証が有効になります。`safe_pickle_allowed_modules` を設定すると、許可するオブジェクトのモジュールを制限できます。

一括操作（Bulk）
----------------
- `bulk_insert(items)` は多数のアイテムを一度に挿入できる便利なメソッドです（dict または (key, value) の反復可能を受け取ります）。
- 大量挿入は `bulk_insert` または非同期のバッチ API を使うと高速になります。

その他便利なメソッド
-------------------
- `keys()`, `values()`, `items()` — データベースの走査
- `table(name)` — テーブル/名前空間を切り替えて操作
- `stats()` — パフォーマンスと設定の統計情報（例: encryption_enabled, hot_tier_size）
- `flush()` — ホットティアをストレージへフラッシュ
- `clear()` — 全エントリを削除

移行の要点（簡易）
-----------------
- v1.x では暗号化パラメータが `password=` だった場合があり、v4 では `encryption_password=` に変更されています。
- デフォルトの pickle モードは v1.8.8 と互換性を保つことを目指しています。既存データは多くの場合そのまま動作します。

トラブルシューティング: ネイティブ拡張が見つからない
--------------------------------------------
ネイティブ拡張が見つからない場合、RuntimeError が発生します。開発環境ではビルドを行ってください。

    cd dictsqlite_v2/dictsqlite
    # プロジェクトのビルド手順（maturin など）に従ってください

ライセンスとサポート
-------------------
MIT ライセンスです。サポートはリポジトリの Issue やパッケージメタデータの連絡先を参照してください。

詳細
---
`examples/` と `tests/` 配下に実践的な例とベンチマークがあります。移行ガイド（MIGRATION_FROM_1.8.8_JP.md）も参照してください。
