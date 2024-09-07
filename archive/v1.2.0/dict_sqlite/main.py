import sqlite3
import threading
import queue

class DictSQLite:
    def __init__(self, db_name, table_name='main'):
        self.db_name = db_name
        self.table_name = table_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.in_transaction = False
        self.operation_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        self.lock = threading.Lock()
        self.create_table()

    def _process_queue(self):
        while True:
            operation, args, kwargs = self.operation_queue.get()
            try:
                with self.lock:
                    operation(*args, **kwargs)
            except Exception as e:
                print(f"An error occurred while processing the queue: {e}")
            self.operation_queue.task_done()

    def create_table(self):
        self.operation_queue.put((self._execute, (f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''',), {}))

    def _execute(self, query, params=()):
        self.cursor.execute(query, params)
        if not self.in_transaction:
            self.conn.commit()

    def __setitem__(self, key, value):
        self.operation_queue.put((self._execute, (f'''
            INSERT OR REPLACE INTO {self.table_name} (key, value)
            VALUES (?, ?)
        ''', (key, value)), {}))

    def __getitem__(self, key):
        with self.lock:
            self.cursor.execute(f'''
                SELECT value FROM {self.table_name} WHERE key = ?
            ''', (key,))
            row = self.cursor.fetchone()
            if row is None:
                raise KeyError(f"Key {key} not found.")
            return row[0]

    def __delitem__(self, key):
        self.operation_queue.put((self._execute, (f'''
            DELETE FROM {self.table_name} WHERE key = ?
        ''', (key,)), {}))

    def __contains__(self, key):
        with self.lock:
            self.cursor.execute(f'''
                SELECT 1 FROM {self.table_name} WHERE key = ?
            ''', (key,))
            return self.cursor.fetchone() is not None

    def __repr__(self):
        with self.lock:
            self.cursor.execute(f'''
                SELECT key, value FROM {self.table_name}
            ''')
            return str(dict(self.cursor.fetchall()))

    def keys(self):
        with self.lock:
            self.cursor.execute(f'''
                SELECT key FROM {self.table_name}
            ''')
            return [row[0] for row in self.cursor.fetchall()]

    def begin_transaction(self):
        with self.lock:
            self.conn.execute('BEGIN TRANSACTION')
            self.in_transaction = True

    def commit_transaction(self):
        with self.lock:
            if self.in_transaction:
                self.conn.execute('COMMIT')
                self.in_transaction = False

    def rollback_transaction(self):
        with self.lock:
            if self.in_transaction:
                self.conn.execute('ROLLBACK')
                self.in_transaction = False

    def switch_table(self, new_table_name):
        self.table_name = new_table_name
        self.create_table()
        self.operation_queue.join()  # キュー内のすべての操作が完了するのを待つ

    def has_key(self, key):
        return key in self

    def clear_db(self):
        # 新たにキューに追加する前に、すべての既存のタスクが完了するのを待ちます
        self.operation_queue.put((self._clear_db, (), {}))
        # _clear_db が完了するのを待ちます
        self.operation_queue.join()

    def _clear_db(self):
        print("Starting _clear_db")  # 追加: デバッグ出力
        # データベース内の全てのテーブルを削除する
        self.cursor.execute(f'''
            SELECT name FROM sqlite_master WHERE type='table'
        ''')
        tables = self.cursor.fetchall()
        print(f"Tables to drop: {tables}")  # 追加: デバッグ出力
        for table in tables:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table[0]}')
        if not self.in_transaction:
            self.conn.commit()
        self.table_name = "main"
        self.create_table()
        print("Finished _clear_db")  # 追加: デバッグ出力

    def tables(self):
        with self.lock:
            self.cursor.execute(f'''
                SELECT name FROM sqlite_master WHERE type='table'
            ''')
            return [row[0] for row in self.cursor.fetchall()]

    def clear_table(self, table_name=None):
        if table_name is None:
            table_name = self.table_name
        self.operation_queue.put((self._execute, (f'''
            DELETE FROM {table_name}
        ''',), {}))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.operation_queue.join()  # すべての操作が完了するのを待つ
        self.conn.close()
