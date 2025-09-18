# DictSQLite

`DictSQLite`は、SQLiteデータベースを辞書のように扱えるPythonライブラリです。スレッドセーフで、トランザクション管理やデータベース操作をバックグラウンドのキューで処理するように設計されています。

## 仕組み

DictSQLiteは、SQLiteデータベースの上に辞書風のインターフェースを提供します。内部でデータがどのように扱われるかを理解することで、より効果的にライブラリを使用できます。

### データ格納とシリアライズ

Pythonオブジェクトをキーの値として代入すると、DictSQLiteはオブジェクトを直接保存するわけではありません。代わりに、以下の手順を実行します。

1.  **シリアライズ**: Pythonオブジェクト（例: `dict`, `list`, `set`, カスタムオブジェクト）は、Pythonの`pickle`モジュールを使用してバイナリ形式にシリアライズされます。
2.  **エンコード**: 生成されたバイナリデータは、`Base64`を使用してテキスト文字列にエンコードされます。
3.  **保存**: このBase64文字列が、デフォルトで`TEXT`型として定義されているSQLiteテーブルの`value`カラムに保存されます。

このプロセスにより、ほぼすべてのPythonオブジェクトをデータベースに保存できます。データを取得する際には逆のプロセスが実行されます。テキストがBase64からデコードされ、`pickle`でデシリアライズされて元のPythonオブジェクトが再構築されます。

### テーブルスキーマ

デフォルトでは、DictSQLiteの各テーブルは単純なキーバリュースキーマで作成されます。

```sql
CREATE TABLE table_name (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

-   `key`: プライマリキーとして機能する一意の`TEXT`文字列。
-   `value`: Base64でエンコードされた、pickle化されたPythonオブジェクトを格納する`TEXT`カラム。

`DictSQLite`インスタンスの作成時や新しいテーブルの作成時に、カスタムスキーマを指定することも可能です。ただし、辞書形式のアクセス（`db['key'] = value`）を使用するには、スキーマに**必ず** `key` と `value` カラムが含まれている必要があります。

### キー、インデックス、データ型

-   **プライマリキー**: `key`カラムがプライマリキーとして機能し、高速な検索を保証します。
-   **インデックス**: デフォルトスキーマでは、インデックスはプライマリキーにしかありません。カスタムインデックスが必要な場合は、カスタムスキーマの一部として定義する必要があります。
-   **データ型**: `key`は通常文字列ですが、カスタムスキーマを使用すれば`INTEGER`などの他の型も使用できます。`value`には、pickle化可能な任意のPythonオブジェクトを指定できます。ライブラリは、変更時に自動的にデータベースに書き戻す特殊なプロキシオブジェクト`DBSyncedList`および`DBSyncedSet`も提供します。

## クラス `DictSQLite`

### コンストラクタ

```python
DictSQLite(db_name: str, table_name: str = 'main', schema: str = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None, password: str = None, publickey_path: str = "./public_keys.pem", privatekey_path: str = "./private_keys.pem", version: int = 1, key_create: bool = False)
```

- **db_name**: データベースファイルの名前。
- **table_name**: 使用するテーブルの名前 (デフォルト: 'main')。
- **schema**: テーブルのスキーマ。デフォルトは `'(key TEXT PRIMARY KEY, value TEXT)'` です。テーブルにカスタムSQLスキーマを文字列で指定できます。ライブラリはテーブルを作成する前にスキーマを検証します。
- **conflict_resolver**: 非推奨。この機能は将来のバージョンで削除される可能性があります。
- **journal_mode**: SQLiteのジャーナルモード (例: "WAL")。
- **lock_file**: 競合解決のためのロックファイルの名前。
- **password**: データを暗号化するためのパスワード。
- **publickey_path**: 暗号化用の公開鍵へのパス。
- **privatekey_path**: 暗号化用の秘密鍵へのパス。
- **version**: データベースのバージョン (1または2)。バージョン2では、複数のテーブルをより簡単に管理できます。
- **key_create**: `True`の場合、新しい暗号化キーが生成されます。

### メソッド

- `__setitem__(self, key, value)`: データを追加または更新します。
- `__getitem__(self, key)`: データを取得します。
- `__delitem__(self, key)`: データを削除します。
- `__contains__(self, key)`: キーが存在するか確認します。
- `__repr__(self)`: データベースの内容を辞書形式で表示します。
- `keys(self)`: 全てのキーを取得します。
- `begin_transaction(self)`: トランザクションを開始します。
- `commit_transaction(self)`: トランザクションをコミットします。
- `rollback_transaction(self)`: トランザクションをロールバックします。
- `switch_table(self, new_table_name, schema=None)`: アクティブなテーブルを切り替えます。
- `create_table(self, table_name, schema=None)`: 新しいテーブルを作成します。
- `clear_db(self)`: すべてのテーブルを削除してデータベース全体をクリアします。
- `clear_table(self, table_name=None)`: テーブルからすべてのデータをクリアします。
- `tables(self)`: すべてのテーブル名のリストを取得します。
- `close(self)`: データベース接続を閉じます。
- `execute_custom(self, query, params=())`: カスタムSQLクエリを実行します。

## 使用方法

### マルチテーブルでの使用 (v2 - 推奨)

```python
import dictsqlite

with dictsqlite.DictSQLite("sample_v2_jp.db", version=2, journal_mode="WAL") as db:
    db.clear_db()
    
    # テーブルを作成
    db.create_table("users")
    db.create_table("products")
    
    # 'users' テーブルにデータを追加
    users = db["users"]
    users["user1"] = {"name": "田中太郎", "age": 30}
    users["user2"] = {"name": "佐藤花子", "age": 25}
    
    # 'products' テーブルにデータを追加
    products = db["products"]
    products["prod1"] = {"name": "ノートパソコン", "price": 80000}
    
    print("データベースの全内容:", db)
    print("Usersテーブル:", db["users"])
    
    # データを削除
    del db["users"]["user2"]
    print("削除後のUsersテーブル:", db["users"])
```

### カスタムスキーマの使用

カスタムスキーマを定義することができます。ただし、標準の辞書形式のアクセス（`db['key'] = value`）を使用するには、スキーマに`key`と`value`カラムが含まれている必要があります。この例では、キーのデータ型を`INTEGER`に変更します。

```python
import dictsqlite

# スキーマは、列定義を含む単一の文字列でなければなりません。
custom_schema = '(key INTEGER PRIMARY KEY, value TEXT)'

with dictsqlite.DictSQLite("custom_int_jp.db", schema=custom_schema) as db:
    db.clear_db()
    
    # これでキーとして整数を使用できます
    db[100] = {"product": "ノートパソコン", "stock": 20}
    db[200] = {"product": "マウス", "stock": 150}

    print("整数キーを持つデータベースの内容:", db)
    print("キー100の値:", db[100])

    # キーは整数として取得されます
    print("テーブルのキー:", db.keys())
```

### 基本的な使用 (v1)

```python
import dictsqlite

# DictSQLiteのインスタンスを作成
with dictsqlite.DictSQLite("sample_jp.db", journal_mode="WAL") as db:
    # データを追加
    db['name'] = 'Alice'
    db['age'] = 30
    db['items'] = ['本', 'ペン']
    print("データ追加後:", db)

    # データを取得
    print("名前:", db['name'])
    
    # 可変オブジェクトの変更
    # 変更は自動的には保存されません
    items = db['items']
    items.append('ノート')
    
    # 変更を保存するには、再代入する必要があります
    db['items'] = items
    print("items変更後:", db)

    # キーの存在確認
    print("'age'は存在するか:", 'age' in db)

    # データを削除
    del db['age']
    print("'age'削除後:", db)
```