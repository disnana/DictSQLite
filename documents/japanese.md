# DictSQLite

`DictSQLite`は、SQLiteデータベースを辞書のように扱えるPythonクラスです。スレッドセーフで、トランザクション管理やデータベース操作をキューで処理します。

## クラス `DictSQLite`

### コンストラクタ

```python
DictSQLite(db_name: str, table_name: str = 'main', schema: bool = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None)
```

- **db_name**: データベースファイルの名前
- **table_name**: 使用するテーブルの名前 (デフォルト: 'main')
- **schema**: テーブルのスキーマ (デフォルト: `'(key TEXT PRIMARY KEY, value TEXT)'`)
- **conflict_resolver**: コンフリクト解決機能の有無
- **journal_mode**: SQLiteのジャーナルモード
- **lock_file**: ロックファイルの名前

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
- `switch_table(self, new_table_name, schema=None)`: テーブルを切り替えます。
- `clear_db(self)`: データベース全体をクリアします。
- `clear_table(self, table_name=None)`: 現在のテーブルまたは指定したテーブルのデータをクリアします。
- `tables(self)`: 全てのテーブル名を取得します。
- `close(self)`: データベース接続を閉じます。



## 使用方法

以下のコードスニペットは、`DictSQLite`クラスの基本的な使い方を示しています。

```python
import dict_sqlite

def test_dict_sqlite():
    # DictSQLite クラスのインスタンスを作成
    db = dict_sqlite.DictSQLite("sample.db", journal_mode="WAL")
    
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
    with dict_sqlite.DictSQLite("sample.db") as context_db:
        context_db['context_key'] = 'context_value'
        print("コンテキスト内のデータ:", context_db)

# テストを実行
test_dict_sqlite()
```
