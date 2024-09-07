import sqlite3


class DictSQLite:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.in_transaction = False  # トランザクションの状態を管理するフラグ
        self.create_table()

    def create_table(self):
        # キーと値を保存するテーブルが存在しない場合に作成する
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def __setitem__(self, key, value):
        # キーと値を挿入または更新する
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO kv_store (key, value)
                VALUES (?, ?)
            ''', (key, value))
            if not self.in_transaction:
                self.conn.commit()
        except sqlite3.Error as e:
            # エラー発生時にエラーメッセージを表示し、ロールバックする
            print(f"An error occurred: {e}")
            self.conn.rollback()

    def __getitem__(self, key):
        # 指定されたキーの値を取得する
        self.cursor.execute('''
            SELECT value FROM kv_store WHERE key = ?
        ''', (key,))
        row = self.cursor.fetchone()
        if row is None:
            raise KeyError(f"Key {key} not found.")
        return row[0]

    def __delitem__(self, key):
        # 指定されたキーを削除する
        self.cursor.execute('''
            DELETE FROM kv_store WHERE key = ?
        ''', (key,))
        if self.cursor.rowcount == 0:
            raise KeyError(f"Key {key} not found.")
        if not self.in_transaction:
            self.conn.commit()

    def __contains__(self, key):
        # 指定されたキーが存在するかどうかを確認する
        self.cursor.execute('''
            SELECT 1 FROM kv_store WHERE key = ?
        ''', (key,))
        return self.cursor.fetchone() is not None

    def __repr__(self):
        # データベース内の全てのキーと値を辞書形式で表示する
        self.cursor.execute('''
            SELECT key, value FROM kv_store
        ''')
        return str(dict(self.cursor.fetchall()))

    def clear(self):
        # データベース内の全てのキーと値を削除する
        self.cursor.execute('''
            DELETE FROM kv_store
        ''')
        if not self.in_transaction:
            self.conn.commit()

    def keys(self):
        # データベース内の全てのキーを取得する
        self.cursor.execute('''
            SELECT key FROM kv_store
        ''')
        return [row[0] for row in self.cursor.fetchall()]

    def begin_transaction(self):
        # トランザクションを開始する
        self.conn.execute('BEGIN TRANSACTION')
        self.in_transaction = True

    def commit_transaction(self):
        # トランザクションをコミットする
        if self.in_transaction:
            self.conn.execute('COMMIT')
            self.in_transaction = False

    def rollback_transaction(self):
        # トランザクションをロールバックする
        if self.in_transaction:
            self.conn.execute('ROLLBACK')
            self.in_transaction = False

    def has_key(self, key):
        # 指定されたキーが存在するかどうかを確認する
        return key in self

    def __enter__(self):
        # コンテキストマネージャとして使用するために自分自身を返す
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # コンテキストマネージャを終了する際にデータベース接続を閉じる
        self.close()

    def close(self):
        # データベース接続を閉じる
        self.conn.close()
