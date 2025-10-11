移行ガイド: DictSQLite v1.8.8 → 現在のラッパー（内部ラベル 'v4' 相当）（日本語）

目的
----
このドキュメントは DictSQLite v1.8.8 で書かれたコードやデータを、このリポジトリにある現在の Python ラッパーに移行する際の手順と注意点をまとめたものです。ラッパーのデフォルトはできる限り v1.8.8 と互換性（デフォルト storage_mode='pickle'）を保つようになっています。

重要な変更点（要約）
------------------
- Python ラッパーの公開クラスは `DictSQLite` です。リポジトリ内や例では `DictSQLiteV4` と表記されることがありますが、これは実装名でありサフィックス "V4" は任意です。推奨するインポートは次の通りです。

    # 推奨（ドキュメントで使う例）
    from dictsqlite import DictSQLite

    # もし既存コードや例が DictSQLiteV4 を使っている場合（任意のエイリアスの例）

    ```
    from dictsqlite import DictSQLiteV4 as DictSQLite
    ```

- 暗号化用のコンストラクタ引数名が変更されました:
    - v1.8.8: `password='mypw'`
    - 現在のラッパー:    `encryption_password='mypw'`

- デフォルトのシリアライズ方式は `storage_mode='pickle'` で、多くの Python オブジェクトを明示的な pickle.dumps/loads なしに扱えます。

- 非同期 API は awaitable メソッド（`aget`, `aset`, `abatch_get`, `abatch_set`）を持つ `AsyncDictSQLite` に変更されました。互換性のために同期ラッパー（`get`, `set`, `batch_get`, `batch_set`）も残されています。

- Safe Pickle 機能が追加され、`enable_safe_pickle=True` とし `safe_pickle_allowed_modules` で許可モジュールを制限できます。

- 一括挿入やバッファリングが改善されました。大量データは `bulk_insert` または非同期バッチ API を使ってください。

詳細な移行手順
----------------
1) インポート名の確認
   - 多くの場合、`from dictsqlite import DictSQLite` のままで変更は不要です。
   - 例やスクリプトに `DictSQLiteV4` が出てきたら、次のどちらでも動作します。

       # そのまま（推奨）
       from dictsqlite import DictSQLite

       # または例に合わせるためにエイリアス
       from dictsqlite import DictSQLiteV4 as DictSQLite

   - ドキュメントでは "V4 は任意" である旨を強調しています。

2) 暗号化パラメータ
   - v1.8.8 の `password=` を使っていた場合は `encryption_password=` に名前を変更してください。

       # v1.8.8
       db = DictSQLite('secrets.db', password='my_password')

       # 現在のラッパー
       db = DictSQLite('secrets.db', encryption_password='my_password')

   - 同じパスワードを使用すれば、既存の暗号化データベースを開けるはずです。
   - 開いたあと `db.stats()['encryption_enabled']` が True か確認してください。

3) シリアライズ動作（storage_mode）
   - デフォルトの `storage_mode='pickle'` は v1.8.8 と互換性を意図しています。
   - もし以前に手動で pickle.dumps() して保存していた場合、v4 のラッパーがバイトを返すことがあるため、`pickle.loads()` を使って復元してください。
   - JSONB や別フォーマットを使っていた場合は `storage_mode='jsonb'` を明示してください。

4) Safe Pickle の導入
   - 信頼できないデータソースを扱うなら `enable_safe_pickle=True` を検討してください。
   - 必要に応じて `safe_pickle_allowed_modules=['myapp', 'mylib']` のように許可するモジュール接頭辞を指定します。
   - 注意: Safe Pickle を有効化すると、従来許容されていた型が拒否される可能性があります。

5) 大量挿入とパフォーマンス
   - for ループでの逐次書き込みはそのまま動作しますが、`bulk_insert()` または非同期の `abatch_set` を使うと高速化できます。

       data = {f'record:{i}': f'data_{i}' for i in range(10000)}
       db.bulk_insert(data)

6) 非同期の移行
   - 新しい awaitable API の使用を推奨します。

       from dictsqlite import AsyncDictSQLite
       async def main():
           db = AsyncDictSQLite(':memory:')
           await db.aset('k', {'x': 1})
           v = await db.aget('k')

   - 既存の同期コードで互換性が必要なら、`AsyncDictSQLite` の同期ラッパー `get`/`set` が使えますが、asyncio コードでは `aget`/`aset` を使ってください。

7) テーブル/名前空間
   - 複数テーブルを使っていた場合は `db.table('other')` を使ってアクセスしてください。

8) 動作確認チェックリスト
   - 文字列が正しく文字列として返るか: `db['key'] = 'value'` -> `db['key']`
   - 複雑オブジェクトのラウンドトリップ: `db['obj'] = {'a':1}` -> `db['obj'] == {'a':1}`
   - 暗号化: `db = DictSQLite(path, encryption_password='pw')` -> `db.stats()['encryption_enabled'] is True`
   - bulk_insert が期待通り高速か

互換性問題と注意点
-------------------
- 直接 sqlite テーブルに対して SQL を投げていた場合や、オンディスクフォーマットに依存している場合は注意してください。v4 は値を pickle や jsonb などで内部格納するため、スキーマやバイナリレイアウトが変わる可能性があります。
- `password` -> `encryption_password` はパラメータ名の変更だけなので、同じパスワードを使えば既存の暗号DBを開けるはずです。
- Safe Pickle を有効にすると従来動いていた unpickle が失敗するケースがあります。必要に応じて `safe_pickle_allowed_modules` を調整してください。

開発環境でのネイティブ拡張のビルド
----------------------------------
ネイティブ拡張が見つからない場合、RuntimeError が出ます。開発機でビルドしてください。一般的な手順:

    cd dictsqlite_v2/dictsqlite
    # maturin などプロジェクトのビルド手順に従ってください
    maturin develop --release

テストと例の実行
----------------
- 例: `dictsqlite_v2/dictsqlite/examples/v4.2_migration_example.py` に移行サンプルがあります。実行して振る舞いを確認できます。
- テスト: python wrapper ディレクトリで pytest を実行して環境の妥当性を確認してください。

    cd dictsqlite_v2/dictsqlite/python
    pytest -q

ロールバックと対処
----------------
- 期待しない振る舞いがあれば、開くときに明示的に `storage_mode` を指定してフォーマットを合わせるか、一時 DB にデータを移し替えてから再インポートしてください。

デプロイ前チェックリスト
----------------------
- [ ] ステージングでユニット／統合テストを通す
- [ ] 暗号化キーの確認
- [ ] bulk 書き込み／読み込みのパフォーマンス確認
- [ ] CI にネイティブ拡張のビルド手順を含める

付録: よくある置換（旧 -> 新）
---------------------------
- コンストラクタ
    v1.8.8: `DictSQLite(path, password='pw')`
    v4.x:    `DictSQLite(path, encryption_password='pw')`

- 非同期 API
    v1.x: 独自のヘルパ
    v4.x: `AsyncDictSQLite` の `aget`/`aset` を使用
