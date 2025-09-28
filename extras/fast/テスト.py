import dictsqlite_fast


def test_dict_sqlite_v2():
    # version=2 で DictSQLite クラスのインスタンスを作成
    db = dictsqlite_fast.FastDictSQLite("sample_v2.db", version=2, journal_mode="WAL")

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
    db["users"]["user3"] = [1, 2, 3]  # リストを使用
    db["users"]["user3"].append(4)  # リストに値を追加
    db["users"]["user3"].append(5)  # リストに値を追加
    for i in db["users"]["user3"]:
        print(i)
    print(db["users"]["user3"])
    db["users"]["user3"].remove(2)  # リストから値を削除
    print(db["users"]["user3"])
    del db["users"]["user3"][1]
    print(db["users"]["user3"])
    db["users"]["user3"].pop(1)
    print(db["users"]["user3"])
    print("ユーザーデータ追加後:", db)

    # products テーブルにデータを追加
    db["products"]["product1"] = {"name": "ノートパソコン", "price": 80000, "stock": 10}
    db["products"]["product2"] = {"name": "スマートフォン", "price": 60000, "stock": 20}
    db["products"]["product3"] = {"name": "タブレッと", "price": 50000, "stock": 15}
    db["products"]["product3"]["name"] = "タブレット"
    db["products"]["product3"]["price"] = 55000
    print("stock" in db["products"]["product3"])
    print("商品データ追加後:", db)
    db["products"]["product3"]["stock"] = {"buy": 10, "sell": 5}
    db["products"]["product3"]["stock"]["buy"] = 9
    db["products"]["product3"]["stock"]["sell"] = 6
    print("商品データ編集後:", db)

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

    db["products"]["product1"] = {"name": "ノートパソコン", "price": 80000, "stock": 10}
    db["products"]["product2"] = set([1, 2, 3])  # setを使用
    print(db["products"])

    # データベース全体のクリア
    db.clear_db()
    print("データベース全体クリア後:", db)

    # 最後にデータベース接続を閉じる
    db.close()

    # コンテキストマネージャの使用
    with dictsqlite_fast.FastDictSQLite("sample_v2.db", version=2) as context_db:
        context_db.create_table("context_table")
        context_db["context_table"]["key1"] = "value1"
        print("コンテキスト内のデータ:", context_db)


# テストを実行
test_dict_sqlite_v2()
