import sqlite3


class DictSQLite:
    def __init__(self, db_name, table_name='main'):
        self.db_name = db_name
        self.table_name = table_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.in_transaction = False
        self.create_table()

    def create_table(self):
        # 指定されたテーブルが存在しない場合に作成する
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def __setitem__(self, key, value):
        # キーと値を挿入または更新する
        try:
            self.cursor.execute(f'''
                INSERT OR REPLACE INTO {self.table_name} (key, value)
                VALUES (?, ?)
            ''', (key, value))
            if not self.in_transaction:
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            self.conn.rollback()

    def __getitem__(self, key):
        # 指定されたキーの値を取得する
        self.cursor.execute(f'''
            SELECT value FROM {self.table_name} WHERE key = ?
        ''', (key,))
        row = self.cursor.fetchone()
        if row is None:
            raise KeyError(f"Key {key} not found.")
        return row[0]

    def __delitem__(self, key):
        # 指定されたキーを削除する
        self.cursor.execute(f'''
            DELETE FROM {self.table_name} WHERE key = ?
        ''', (key,))
        if self.cursor.rowcount == 0:
            raise KeyError(f"Key {key} not found.")
        if not self.in_transaction:
            self.conn.commit()

    def __contains__(self, key):
        # 指定されたキーが存在するかどうかを確認する
        self.cursor.execute(f'''
            SELECT 1 FROM {self.table_name} WHERE key = ?
        ''', (key,))
        return self.cursor.fetchone() is not None

    def __repr__(self):
        # データベース内の全てのキーと値を辞書形式で表示する
        self.cursor.execute(f'''
            SELECT key, value FROM {self.table_name}
        ''')
        return str(dict(self.cursor.fetchall()))

    def clear(self):
        # データベース内の全てのキーと値を削除する
        self.cursor.execute(f'''
            DELETE FROM {self.table_name}
        ''')
        if not self.in_transaction:
            self.conn.commit()

    def keys(self):
        # データベース内の全てのキーを取得する
        self.cursor.execute(f'''
            SELECT key FROM {self.table_name}
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

    def switch_table(self, new_table_name):
        # 現在のテーブルを切り替える
        self.table_name = new_table_name
        self.create_table()

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
