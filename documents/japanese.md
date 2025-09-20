# DictSQLite

DictSQLite は、SQLite をバックエンドにした辞書風 API を提供する Python ライブラリです。DB 操作はバックグラウンドワーカーに直列化され、手軽にスレッドセーフに使えます。必要に応じて保存値の暗号化にも対応します。本ページでは、スキーマや保存形式、対応型、API、安全な使い方を解説します。

ステータス: このリポジトリ同梱の参照テストは 20/20 で成功しています。

- ストレージモデル: storage_mode='pickle'（Pickle + Base64、レガシー JSON 互換読込）または storage_mode='json'（純粋 JSON）。必要に応じて値を RSA で暗号化。（v1.8.8 で storage_mode 選択を追加）
- スキーマモデル: 既定は最小の key/value スキーマ。任意の CREATE TABLE 列定義を指定可能
- 型モデル: key が主キー。value は pickle モードでは pickle 可能な任意オブジェクト / json モードでは JSON シリアライズ可能（+ set 対応）オブジェクト。一部可変型は自動同期
- 併行モデル: 単一ワーカースレッドで直列処理。必要なら簡易ファイルロック
- セキュリティモデル: pickle モードでは許可リスト Safe Unpickler。json モードでは pickle を使用せず攻撃面減少


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

storage_mode に応じて value の直列化方式が変わります。

### storage_mode='pickle'（既定）

1) Pickle で最高プロトコルにて直列化
2) Base64 で ASCII 文字列化
3) password 設定時は Base64 文字列を RSA-OAEP 暗号化（PEM は AES でパスワード保護）
4) (key, value) を INSERT OR REPLACE

読み出し時:
- 暗号化されていれば復号
- 後方互換のため JSON デコードを先に試行（非常に旧い JSON 保存行）
- 失敗したら Base64 -> Safe Unpickler で unpickle。ポリシー不許可なら警告後に生文字列返却

### storage_mode='json'

1) json.dumps で UTF-8 文字列化（set は {"__type__":"set","value":[...]} 形式。RecursiveDict / 同期ラッパは通常型へ展開）
2) password 設定時は UTF-8 文字列を暗号化、無ければそのまま保存
3) 読み出し: （必要なら復号）-> json.loads(custom hook) -> Python オブジェクト
4) JSON デコード失敗時は pickle 互換読みを試みる（混在 DB 読取を許容）

影響:
- json モード: JSON ネイティブ型 + set のみ（関数/カスタムクラス等は TypeError）。
- pickle モード: 任意 pickle 可能オブジェクト対応（Safe Unpickler 制約下）だが攻撃面広い。
- モード変更後も既存行はそのまま。読取側が JSON → pickle の順で試みるため混在可。


## ストレージモードの選択 (v1.8.8+)

| モード | 長所 | 短所 | 推奨用途 |
|--------|------|------|----------|
| pickle | 複雑 / 任意オブジェクト保存 | セキュリティ監査必要・Base64 overhead | 内部信頼データ / 複雑モデル |
| json   | 可読・pickle 不使用で安全性向上 | 型制限（set 以外の非標準型不可） | 設定・共有データ・軽量 KV |

切替指針:
- storage_mode 変更は新規書込みのみ影響。既存行は再保存しない限り旧形式。
- 読取順序: JSON 試行 → pickle 試行 → 生文字列。
- 既存 pickle データを JSON 化したい場合は再代入マイグレーションが可能。

マイグレーション例:
```python
from dictsqlite import DictSQLite

# 以前は pickle モードで運用
# ... 既存データあり
# JSON モードへ新規インスタンス
with DictSQLite('app.db', storage_mode='json') as db:
    for k in db.keys():
        v = db[k]  # 自動判別で取得
        db[k] = v  # JSON 形式で再保存
```

セキュリティ: 任意オブジェクト不要なら json モード推奨。


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

- RecursiveDict: 値が辞書系の場合、深い階層での代入/削除も直ちに最上位の辞書へ書き戻します。例: `db['user']['profile']['age'] = 31` は即時永続化。
  - 制限: 辞書の下にあるリスト/セットなどは通常の Python オブジェクトで返り、自動同期しません。
- DBSyncedList / DBSyncedSet: 値が「トップレベルの」list/set の場合、append や add/remove などの変更を自動保存します。
  - 制限: 辞書の中に入った list/set はラップされないため自動同期しません。親値の再代入で保存するか、トップレベルで保存してください。


## API リファレンス

コンストラクタ

```python
from dictsqlite import DictSQLite

db = DictSQLite(
  db_name='example_jp.db',
  table_name='main',
  schema=None,
  conflict_resolver=False,
  journal_mode=None,
  lock_file=None,
  password=None,
  publickey_path='./public_keys.pem',
  privatekey_path='./private_keys.pem',
  version=1,
  key_create=False,
  # Safe pickle
  safe_pickle_policy=None,
  safe_pickle_allowed_module_prefixes=('dictsqlite',),
  safe_pickle_allowed_builtins=None,
  safe_pickle_allowed_globals={'dictsqlite.modules.utils.ExpiringDict'},
  storage_mode='pickle',  # or 'json'
)
```

storage_mode:
- 'pickle': 既定。任意 pickle 可能オブジェクト。Safe Unpickler で制御。
- 'json'  : JSON シリアライズ可能型 + set。非対応型は TypeError。

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

JSON モード例

```python
from dictsqlite import DictSQLite

with DictSQLite('settings_jp.db', storage_mode='json') as db:
    db['feature_flags'] = {'new_ui': True, 'beta_users': ['u1', 'u2']}
    db['tags'] = {'alpha', 'beta'}  # set も保存可
    print(db['tags'])

    # 非 JSON 直列化オブジェクトは TypeError
    # db['bad'] = lambda x: x  # エラー例
```

混在読取例（旧 pickle 行 + 新 JSON 行）:
```python
from dictsqlite import DictSQLite

# 旧: pickle モードで作成
with DictSQLite('mixed_jp.db', storage_mode='pickle') as db:
    db['user'] = {'name': 'Alice'}

# 後に JSON モードへ切替
with DictSQLite('mixed_jp.db', storage_mode='json') as db:
    print(db['user'])          # pickle fallback で読める
    db['config'] = {'theme': 'dark'}  # JSON 形式で保存
```


## 互換性と移行

- レガシー JSON（初期バージョン）: まず JSON 試行→失敗時 pickle。
- storage_mode='json': 新規保存は純粋 JSON。読取時は JSON→pickle 順で混在処理可。
- 列型アフィニティ: pickle + 暗号化時は BLOB 化され得る。json モードは平文 UTF-8（暗号化時はバイト列）。
- conflict_resolver: 実験的/非推奨。通常はワーカー + WAL 推奨。

## トラブルシューティング

- 辞書の中の list/set を変更したが保存されない: 自動同期するのは「トップレベル」の list/set のみ。親辞書を再代入して保存するか、トップレベルに保持してください。
- Safe Unpickler の警告が出る: オブジェクトのモジュール/グローバルが許可リスト外の可能性。safe_pickle_allowed_* を拡張するか、より単純な型を保存してください。
- スキーマ検証エラー: スキーマはセミコロンなしの単一列定義文字列で記述し、辞書風 API のため key/value 列を含めてください。
- 性能ヒント: journal_mode='WAL' を有効化し、巨大単一値は避け、必要な列にインデックスを追加してください。
