# DictSQLite

`DictSQLite`は、SQLiteデータベースを辞書のように扱えるPythonクラスです。スレッドセーフで、トランザクション管理やデータベース操作をキューで処理します。

## 自動競合解決について

自動競合解決は非推奨です。パフォーマンスが大幅に低下する可能性があります。私はその実装に多くの時間を費やし、心配しました。もしもっと良いアイデアがあれば、それを実装したいと考えています。

通常は、次のようなコードで変数のクラスを呼び出し、適切に使用したり開いたり閉じたりすれば、問題は発生しません。

```python
db = dictsqlite.DictSQLite("db_path")
```

しかし、異なるPythonコードから同時にデータベースにアクセスして書き込む場合は、自動競合解決が必要になる可能性があります。とはいえ、速度が非常に速いため、衝突の可能性は非常に低いと思われます。

本当に心配な場合は、パフォーマンスを犠牲にして自動競合解決を有効にすることをお勧めします。

## クラス `DictSQLite`

### コンストラクタ

```python
DictSQLite(db_name: str, table_name: str = 'main', schema: bool = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None, password: str = None, publickey_path: str = "./public_keys.pem", privatekey_path: str = "./private_keys.pem", version: int = 1, key_create: bool = False)
```

- **db_name**: データベースファイルの名前
- **table_name**: 使用するテーブルの名前 (デフォルト: 'main')
- **schema**: テーブルのスキーマ (デフォルト: `'(key TEXT PRIMARY KEY, value TEXT)'`)
- **conflict_resolver**: コンフリクト解決機能の有無
- **journal_mode**: SQLiteのジャーナルモード
- **lock_file**: ロックファイルの名前
- **password**: データベースのパスワード
- **publickey_path**: 公開鍵のパス
- **privatekey_path**: 秘密鍵のパス
- **version**: データベースのバージョン
- **key_create**: キーの作成フラグ

### メソッド

- `__setitem__(self, key, value)`: データを追加または更新します。
- `__getitem__(self, key)`: データを取得します。
- `__delitem__(self, key)`: データを削除します。
- `__contains__(self, key)`: キーが存在するか確認します。
- `__repr__(self)`: データベースの内容を辞書形式で表示します。
- `TableProxy(self, db, table_name)`: version2のためのテーブルプロキシクラス
- `keys(self)`: 全てのキーを取得します。
- `begin_transaction(self)`: トランザクションを開始します。
- `commit_transaction(self)`: トランザクションをコミットします。
- `rollback_transaction(self)`: トランザクションをロールバックします。
- `switch_table(self, new_table_name, schema=None)`: テーブルを切り替えます。
- `clear_db(self)`: データベース全体をクリアします。
- `clear_table(self, table_name=None)`: 現在のテーブルまたは指定したテーブルのデータをクリアします。
- `tables(self)`: 全てのテーブル名を取得します。
- `close(self)`: データベース接続を閉じます。

## 使用方法

以下のコードスニペットは、`DictSQLite`(Version 2)クラスの基本的な使い方を示しています。

```python
import dictsqlite

def test_dict_sqlite_v2():
    # version=2 で DictSQLite クラスのインスタンスを作成
    db = dictsqlite.DictSQLite("sample_v2.db", version=2, journal_mode="WAL")
    
    # データベースをクリア
    db.clear_db()
    print("初期状態:", db)
    
    # テーブルを作成
    db.create_table("users")
    db.create_table("products")
    print("テーブル作成後:", db)
    
    # users テーブルにデータを追加
    db["users"]["user1"] = {"name": "田中太郎", "age": 30, "email": "tanaka@example.com"}
    db["users"]["user2"] = {"name": "佐藤花子", "age": 25, "email": "sato@example.com"}
    print("ユーザーデータ追加後:", db)
    
    # products テーブルにデータを追加
    db["products"]["product1"] = {"name": "ノートパソコン", "price": 80000, "stock": 10}
    db["products"]["product2"] = {"name": "スマートフォン", "price": 60000, "stock": 20}
    print("商品データ追加後:", db)
    
    # 特定のテーブルの内容を表示
    print("ユーザーテーブルの内容:", db["users"])
    print("商品テーブルの内容:", db["products"])
    
    # 特定のデータを取得
    print("user1の情報:", db["users"]["user1"])
    print("product2の情報:", db["products"]["product2"])
    
    # キーの存在確認
    print("user1は存在するか:", "user1" in db["users"])
    print("user3は存在するか:", "user3" in db["users"])
    
    # データの削除
    del db["users"]["user2"]
    print("user2削除後のユーザーテーブル:", db["users"])
    
    # テーブル内の全キーを取得
    print("usersテーブルの全キー:", db.keys("users"))
    
    # トランザクションの使用
    db.begin_transaction()
    try:
        db["users"]["user3"] = {"name": "山田次郎", "age": 40, "email": "yamada@example.com"}
        db["products"]["product3"] = {"name": "タブレット", "price": 40000, "stock": 15}
        print("トランザクション中の状態:", db)
        db.commit_transaction()
        print("コミット後:", db)
    except Exception as e:
        db.rollback_transaction()
        print(f"エラーが発生しました: {e}")
    
    # ロールバックのデモ
    db.begin_transaction()
    db["users"]["user4"] = {"name": "鈴木一郎", "age": 35, "email": "suzuki@example.com"}
    print("ロールバック前:", db["users"])
    db.rollback_transaction()
    print("ロールバック後:", db["users"])
    
    # 新しいテーブルの作成と切り替え
    db.create_table("orders")
    db["orders"]["order1"] = {"user_id": "user1", "product_id": "product1", "quantity": 1}
    print("注文テーブル作成後:", db["orders"])
    
    # データベース内のテーブル一覧を取得
    print("テーブル一覧:", db.tables())
    
    # 特定のテーブルのクリア
    db.clear_table("products")
    print("productsテーブルクリア後:", db["products"])
    
    # データベース全体のクリア
    db.clear_db()
    print("データベース全体クリア後:", db)
    
    # 最後にデータベース接続を閉じる
    db.close()
    
    # コンテキストマネージャの使用
    with dictsqlite.DictSQLite("sample_v2.db", version=2) as context_db:
        context_db.create_table("context_table")
        context_db["context_table"]["key1"] = "value1"
        print("コンテキスト内のデータ:", context_db)

# テストを実行
test_dict_sqlite_v2()
```


以下のコードスニペットは、`DictSQLite`(Version 1)クラスの基本的な使い方を示しています。

```python
import dictsqlite

def test_dict_sqlite():
    # DictSQLite クラスのインスタンスを作成
    db = dictsqlite.DictSQLite("sample.db", journal_mode="WAL")
    
    # データ追加
    db['name'] = 'Alice'
    db['age'] = '30'
    print("データ追加後:", db)

    # データ取得
    print("名前:", db['name'])
    print("年齢:", db['age'])

    # キーの存在確認
    print("nameキーは存在するか:", 'name' in db)
    print("addressキーは存在するか:", 'address' in db)

    # データ削除
    del db['age']
    print("データ削除後:", db)

    # 全てのキーを取得
    print("全てのキー:", db.keys())

    # トランザクションの使用
    db.begin_transaction()
    db['transaction_key'] = 'transaction_value'
    print("トランザクション中の状態:", db)
    db.rollback_transaction()  # ロールバックして変更をキャンセル
    print("ロールバック後:", db)

    # トランザクションを再試行してコミット
    db.begin_transaction()
    db['transaction_key'] = 'transaction_value'
    print("トランザクション中の状態:", db)
    db.commit_transaction()  # コミットして変更を保存
    print("コミット後:", db)

    # テーブルの切り替え
    db.create_table('new_table')
    db.switch_table('new_table')
    db['another_key'] = 'another_value'
    print("新しいテーブルでのデータ:", db)
    print("テーブル一覧:", db.tables())

    # データベース全体のクリア
    db.clear_db()
    print("データベース全体のクリア後:", db)
    db.clear_table()
    print("現在選択されているテーブルのデータクリア後:", db)

    # 指定したテーブルのデータクリア
    db.switch_table('new_table')
    db['context_key'] = 'context_value'
    db.clear_table('new_table')
    print("指定したテーブルのデータクリア後:", db)

    # 最後にデータベース接続を閉じる
    db.close()
    # コンテキストマネージャの使用
    with dictsqlite.DictSQLite("sample.db") as context_db:
        context_db['context_key'] = 'context_value'
        print("コンテキスト内のデータ:", context_db)

# テストを実行
test_dict_sqlite()
```
