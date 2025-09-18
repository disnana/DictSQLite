# DictSQLite

DictSQLite は、SQLite をバックエンドにした辞書風 API を提供する Python ライブラリです。DB 操作はバックグラウンドワーカーに直列化され、手軽にスレッドセーフに使えます。必要に応じて保存値の暗号化にも対応します。本ページでは、スキーマや保存形式、対応型、API、安全な使い方を解説します。

ステータス: このリポジトリ同梱の参照テストは 20/20 で成功しています。

- ストレージモデル: Pickle + Base64（レガシー JSON は読み取り互換）、必要に応じて値を RSA で暗号化
- スキーマモデル: 既定は最小の key/value スキーマ。任意の CREATE TABLE 列定義を指定可能
- 型モデル: key が主キー。value は pickle 可能な任意の Python オブジェクト。可変型は一部が自動同期
- 併行モデル: 単一ワーカースレッドで直列処理。必要なら簡易ファイルロック
- セキュリティモデル: 許可リスト方式の Safe Unpickler で逆シリアライズを保護


## テーブルスキーマの管理

既定では、テーブルが無ければ次の単純なキーバリューテーブルを作成します。

```sql
CREATE TABLE IF NOT EXISTS "main" (
  key   TEXT PRIMARY KEY,
  value TEXT
);
```

- テーブル名: コンストラクタ引数 table_name（既定 "main"）。識別子は二重引用符で安全にクオートされます。
- カスタムスキーマ: schema に列定義文字列を渡します（例: '(key INTEGER PRIMARY KEY, value TEXT)'）。
  - 検証: 一時テーブルの作成/削除で妥当性を検証し、ステートメント分割防止のためセミコロンは拒否します。無効な場合は ValueError。
  - 辞書風アクセスの前提: 列名 key と value を必ず含めてください。型（TEXT/INTEGER など）は任意です。
- 複数テーブル: version=2 では db["table_name"] でテーブルプロキシを取得できます。create_table("name", schema?) で存在確保。
- ジャーナルモード: 指定時は PRAGMA journal_mode を許可リスト（DELETE/TRUNCATE/PERSIST/MEMORY/WAL/OFF）で設定。不正値は拒否。


## 値の保存方法

db[key] = value の代入時、value は次の手順で保存されます。

1) Pickle で最高プロトコルにて直列化。
2) Base64 で ASCII 文字列にエンコード。
3) password を設定している場合、上記 Base64 文字列を RSA-OAEP で暗号化（鍵 PEM は AES でパスワード保護）。暗号化後のバイト列を保存（列は TEXT 宣言でも SQLite は BLOB として保持可）。
4) (key, value) を INSERT OR REPLACE。

読み出し（db[key]）時:

- password がある場合はまず RSA-OAEP で復号して Base64 文字列を得ます。
- 後方互換のため JSON デコードを先に試行。
- 失敗した場合は Base64 をデコードし、Safe Unpickler（後述）で unpickle。いずれも不可なら最終手段として平文文字列を返します。

注意点:

- 新規書き込みは Pickle + Base64 が既定。過去に JSON 保存された行は引き続き読み取れます。
- 暗号化は value 列のみ対象です。key や他列は平文のままです。


## キー・インデックス・データ型

- 主キー: 既定スキーマでは key が PRIMARY KEY です。主キー検索は高速です。
- 型: 既定では key は TEXT。カスタムスキーマで INTEGER 等も可。value は TEXT 宣言が既定ですが、暗号化時は BLOB として格納される場合があります（SQLite は型に寛容）。
- インデックス: 既定は主キー索引のみ。必要に応じて execute_custom で追加索引を作成してください。
- 制約: NOT NULL、UNIQUE、CHECK などをスキーマに追加可能。辞書風 API のため key/value 列名は保持してください。


## 併行性・トランザクション・ロック

- ワーカキュー: すべての DB 操作は単一のバックグラウンドワーカーに直列投入されます。結果を要する操作（__getitem__、in、keys、tables 等）は内部で待機します。書き込み系はキュー投入後すぐ戻ります。
- トランザクション: begin_transaction / commit_transaction / rollback_transaction は順序を保ってキュー処理されます。明示トランザクション外では自動コミット。
- ロック: conflict_resolver モードはファイルロック（portalocker）も使いますが実験的/非推奨です。通常は既定ワーカーで十分です。


## セキュリティ: 安全な逆シリアライズと暗号化

- 安全な pickle ローダ: 許可リスト方式の safe_loads で unpickle します。
  - 既定の許可モジュール接頭辞: ("dictsqlite",) — このパッケージ由来の型と、一部のグローバルのみ許可。
  - 既定許可グローバル: {"dictsqlite.modules.utils.ExpiringDict"}。
  - コンストラクタ引数 safe_pickle_policy, safe_pickle_allowed_module_prefixes, safe_pickle_allowed_builtins, safe_pickle_allowed_globals で上書き可。
  - ポリシーで unpickle できない場合は警告を出し、最終手段として生文字列を返します。
- 保存時の暗号化（任意）:
  - password と 公開鍵/秘密鍵の PEM パスを指定。key_create=True の場合は RSA 鍵ペアを生成し、両 PEM を AES でパスワード暗号化して保存します。
  - 書き込み時: Base64 文字列を公開鍵で RSA-OAEP 暗号化して保存。
  - 読み出し時: 秘密鍵で RSA-OAEP 復号後、上記の手順で復元します。

注: 暗号化対象は value フィールドのみです。key など他列は平文です。


## 自動同期するプロキシ型

読み出し時、変更を検知して自動保存するプロキシを返す場合があります。

- RecursiveDict: 値が辞書系の場合、深い階層での代入/削除も直ちに最上位の辞書へ書き戻します。例: db['user']['profile']['age'] = 31 は即時永続化。
  - 制限: 辞書の下にあるリスト/セットなどは通常の Python オブジェクトで返り、自動同期しません。
- DBSyncedList / DBSyncedSet: 値が「トップレベルの」list/set の場合、append や add/remove などの変更を自動保存します。
  - 制限: 辞書の中に入った list/set はラップされないため自動同期しません。親値の再代入で保存するか、トップレベルで保存してください。


## API リファレンス

コンストラクタ

```python
DictSQLite(
  db_name: str,
  table_name: str = 'main',
  schema: str | None = None,
  conflict_resolver: bool = False,
  journal_mode: str | None = None,
  lock_file: str | None = None,
  password: str | None = None,
  publickey_path: str = './public_keys.pem',
  privatekey_path: str = './private_keys.pem',
  version: int = 1,
  key_create: bool = False,
  # Safe pickle
  safe_pickle_policy: Optional[SafePolicy] = None,
  safe_pickle_allowed_module_prefixes: tuple[str, ...] = ("dictsqlite",),
  safe_pickle_allowed_builtins: set[str] | None = None,
  safe_pickle_allowed_globals: set[str] = {"dictsqlite.modules.utils.ExpiringDict"},
)
```

辞書 API（主要操作）

- db[key] = value: 挿入/更新（Pickle+Base64。必要なら RSA 暗号化）。
- value = db[key]: 取り出し（上記復号/復元を実施）。状況によりプロキシ型を返します。
- del db[key]: 削除。
- key in db: 存在確認。
- repr(db): 現在テーブルの辞書風表現を返します。

テーブルとスキーマ

- db.create_table(table_name: str | None = None, schema: str | None = None): テーブルの存在確保（スキーマを与えた場合は検証）。
- db.switch_table(new_table_name, schema=None): テーブル切替（必要なら作成）。
- db.tables(): すべてのテーブル名を列挙。
- db.clear_table(table_name: str | None = None): テーブル内の全行削除。
- db.clear_db(): すべてのテーブルを drop して既定を再作成。

トランザクション

- db.begin_transaction()
- db.commit_transaction()
- db.rollback_transaction()

クエリ補助

- db.keys(table_name: str | None = None): テーブルの全キーを列挙。
- db.execute_custom(query: str, params: tuple = ()): ワーカー経由で任意 SQL を実行。

ユーティリティ

- dictsqlite.randomstrings(n: int) -> str: 英字ランダム文字列。
- dictsqlite.expiring_dict(seconds: int) -> ExpiringDict: 時間で期限切れになる辞書。


## 使用例

基本（v1）

```python
from dictsqlite import DictSQLite

with DictSQLite('sample_jp.db', journal_mode='WAL') as db:
    db['name'] = 'Alice'
    db['age'] = 30

    # トップレベル list は自動同期
    db['items'] = ['本', 'ペン']
    db['items'].append('ノート')  # 即時保存

    # 辞書は任意の深さで自動同期
    db['profile'] = {'city': 'Tokyo', 'likes': {'music': True}}
    db['profile']['likes']['music'] = False  # 永続化

    print('Keys:', db.keys())
    print('Name:', db['name'])
```

複数テーブル（v2）

```python
from dictsqlite import DictSQLite

with DictSQLite('sample_v2_jp.db', version=2, journal_mode='WAL') as db:
    db.create_table('users')
    db.create_table('products')

    users = db['users']
    products = db['products']

    users['user1'] = {'name': '田中太郎', 'age': 30}
    products['prod1'] = {'name': 'ノートPC', 'price': 80000}

    # 辞書内の自動同期
    users['user1']['age'] = 31

    print('All tables:', db.tables())
    print('Users:', users)
```

カスタムスキーマ

```python
from dictsqlite import DictSQLite

schema = '(key INTEGER PRIMARY KEY, value TEXT, updated_at TEXT)'

with DictSQLite('custom_int_jp.db', schema=schema) as db:
    db[100] = {'product': 'Laptop'}
    db.execute_custom('CREATE INDEX IF NOT EXISTS ix_updated ON "main"(updated_at)')
    print(db[100])
```

保存時暗号化

```python
from dictsqlite import DictSQLite
from dictsqlite.modules import crypto

# 初回のみ: RSA キーペアを生成（PEM は AES でパスワード暗号化して保存）
crypto.key_create(password='secret',
                  pubkey_path='./public_keys.pem',
                  private_key_path='./private_keys.pem')

with DictSQLite('secure_jp.db',
                password='secret',
                publickey_path='./public_keys.pem',
                privatekey_path='./private_keys.pem') as db:
    db['token'] = {'scopes': ['read', 'write']}
    print(db['token'])
```

Safe Pickle ポリシーの調整

```python
from dictsqlite import DictSQLite
from dictsqlite.modules.safe_pickle import SafePolicy

policy = SafePolicy()

with DictSQLite('policy_jp.db',
                safe_pickle_policy=policy,
                safe_pickle_allowed_module_prefixes=('dictsqlite', 'myapp.models'),
                safe_pickle_allowed_globals={'dictsqlite.modules.utils.ExpiringDict', 'myapp.Type'}) as db:
    db['k'] = {'v': 1}
```


## 互換性と移行

- レガシー JSON: 旧データでは value に JSON 文字列が入っている場合があります。読み取りは JSON → 失敗時に Pickle の順で試行。新規保存は Pickle+Base64 です。
- 列型のアフィニティ: SQLite は柔軟で、value を TEXT 宣言していても暗号化時は BLOB として格納され得ます。読み取り側は両方に対応します。
- conflict_resolver: 実験的/非推奨。通常はワーカー + WAL で十分です。


## トラブルシューティング

- 辞書の中の list/set を変更したが保存されない: 自動同期するのは「トップレベル」の list/set のみ。親辞書を再代入して保存するか、トップレベルに保持してください。
- Safe Unpickler の警告が出る: オブジェクトのモジュール/グローバルが許可リスト外の可能性。safe_pickle_allowed_* を拡張するか、より単純な型を保存してください。
- スキーマ検証エラー: スキーマはセミコロンなしの単一列定義文字列で記述し、辞書風 API のため key/value 列を含めてください。
- 性能ヒント: journal_mode='WAL' を有効化し、巨大単一値は避け、必要な列にインデックスを追加してください。
