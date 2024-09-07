import dict_sqlite

db = dict_sqlite.DictSQLite("sample.db")
# データの追加
db['name'] = 'Alice'
db['age'] = '30'
print("データ追加後:", db)

# データの取得
print("名前:", db['name'])
print("年齢:", db['age'])

# キーの確認
print("nameキーは存在するか:", 'name' in db)
print("addressキーは存在するか:", 'address' in db)

# データの削除
del db['age']
print("データ削除後:", db)

# 全てのキーを取得
print("全てのキー:", db.keys())

# トランザクションの使用例
db.begin_transaction()
db['transaction_key'] = 'transaction_value'
print("トランザクション中の状態:", db)
db.rollback_transaction()  # ロールバックして変更をキャンセル
print("ロールバック後:", db)

# トランザクションをコミットする例
db.begin_transaction()
db['another_key'] = 'another_value'
db.commit_transaction()  # コミットして変更を保存
print("コミット後:", db)

# データベースをクリア
db.clear()
print("データベースクリア後:", db)

# コンテキストマネージャの使用例
with dict_sqlite.DictSQLite('context_example.db') as ctx_db:
    ctx_db['context_key'] = 'context_value'
    print("コンテキスト内のデータ:", ctx_db)

# データベース接続を閉じる
db.close()
