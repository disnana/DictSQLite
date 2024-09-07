import dict_sqlite


def test_dict_sqlite():
    # DictSQLite クラスのインスタンスを作成
    db = dict_sqlite.DictSQLite("sample.db")

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

    # コンテキストマネージャの使用
    with dict_sqlite.DictSQLite("sample.db") as context_db:
        context_db['context_key'] = 'context_value'
        print("コンテキスト内のデータ:", context_db)

    # 最後にデータベース接続を閉じる
    db.close()


# テストを実行
test_dict_sqlite()
