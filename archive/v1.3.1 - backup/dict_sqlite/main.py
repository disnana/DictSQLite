import json
import random
import sqlite3
import sys
import threading
import queue
import secrets
import string
import portalocker
import socket


def randomstrings(n):
    return ''.join(secrets.choice(string.ascii_letters) for _ in range(n))


class DictSQLite:
    def __init__(self, db_name: str, table_name: str = 'main', schema: bool = None, conflict_resolver: bool = True,
                 journal_mode: str = None, lock_file: str = None, socket_ip: str = "localhost",
                 socket_port: int = 5000):
        self.db_name = db_name
        self.table_name = table_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.in_transaction = False
        if lock_file is None:
            self.lock_file = f"{db_name}.lock"
        else:
            self.lock_file = lock_file
        self.operation_queue = queue.Queue()
        self.conflict_resolver = conflict_resolver
        self.lock = False

        def queue_process_create():
            self.worker_thread = threading.Thread(target=self._process_queue)
            self.worker_thread.daemon = True
            self.worker_thread.start()

        if self.conflict_resolver:
            host = (socket_ip, socket_port)
            if self._check_lock():
                self.lock = True
                self._db_lock()
                queue_process_create()
                self.server_start(host)
            else:
                self.host = host
                self.worker_thread = threading.Thread(target=self._process_queue_conflict_resolver)
                self.worker_thread.daemon = True
                self.worker_thread.start()

        else:
            queue_process_create()
        self.create_table(schema=schema)
        if not journal_mode is None:
            self.conn.execute(f'PRAGMA journal_mode={journal_mode};')

    def execute_function(self, func_name, *args, **kwargs):
        functions = {
            'tables': self.tables,
            '_execute': self._execute
        }
        func = functions.get(func_name)
        if func:
            return func(*args, **kwargs)
        else:
            return 'Function not found'

    def handle_client(self, connection):
        data = connection.recv(1024)
        if data:
            request = json.loads(data.decode())
            func_name = request['func']
            args = request.get('args', [])  # argsがない場合は空リスト
            kwargs = request.get('kwargs', {})  # kwargsがない場合は空辞書
            result = self.execute_function(func_name, *args, **kwargs)
            connection.sendall(str(result).encode())

    def server_start(self, host):
        # ソケットを作成
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # SO_REUSEADDRオプションを設定
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # サーバーのアドレスとポートを指定
        self.server_socket.bind(host)

        def check():
            try:
                while True:
                    # クライアントからの接続を待機
                    self.server_socket.listen(1)

                    # クライアントからの接続を受け入れる
                    connection, client_address = self.server_socket.accept()
                    self.handle_client(connection)
            finally:
                self.server_socket.close()

        # 接続を処理するスレッドを開始
        self.socket_server = threading.Thread(target=check)
        self.socket_server.daemon = True
        self.socket_server.start()

    def _check_lock(self):
        """ロックファイルのロック状態を確認します。"""
        try:
            with open(self.lock_file, 'w') as file:
                try:
                    portalocker.lock(file, portalocker.LOCK_EX | portalocker.LOCK_NB)
                    portalocker.unlock(file)
                    # print("ロックを取得できました (ロックされていません)")
                    return True
                except portalocker.LockException:
                    # print("ロックは既に取得されています")
                    return False
        except Exception as e:
            print(f"エラー: {e}")

    def _db_lock(self):
        """ファイルロックを取得します。"""
        self.lock_file_handle = open(self.lock_file, 'w')
        portalocker.lock(self.lock_file_handle, portalocker.LOCK_EX)

    def _db_unlock(self):
        """ファイルロックを解放します。"""
        portalocker.unlock(self.lock_file_handle)
        self.lock_file_handle.close()

    def _process_queue(self):
        while True:
            operation, args, kwargs, result_queue = self.operation_queue.get()
            try:
                result = operation(*args, **kwargs)
                if result_queue is not None:
                    result_queue.put(result)
            except Exception as e:
                print(f"An error occurred while processing the queue: {e}")
                if result_queue is not None:
                    result_queue.put(e)
            finally:
                self.operation_queue.task_done()

    def _process_queue_conflict_resolver(self):
        # ソケットを作成
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # サーバーのアドレスとポートに接続
        self.client_socket.connect(self.host)
        try:
            while True:
                operation, args, kwargs, result_queue = self.operation_queue.get()
                try:
                    request = {
                        'func': operation.__name__,
                        'args': args,
                        'kwargs': kwargs
                    }
                    self.client_socket.sendall(json.dumps(request).encode())
                    response = self.client_socket.recv(1024)
                    print(response)
                    if result_queue is not None:
                        result_queue.put(response.decode())
                except Exception as e:
                    print(f"An error occurred while processing the queue: {e}")
                    if result_queue is not None:
                        result_queue.put(e)
                finally:
                    self.operation_queue.task_done()
        finally:
            self.client_socket.close()
            print("exit")

    def create_table(self, table_name=None, schema=None):
        if not table_name is None:
            self.table_name = table_name
        schema = schema if schema else '(key TEXT PRIMARY KEY, value TEXT)'
        create_table_sql = f'CREATE TABLE IF NOT EXISTS {self.table_name} {schema}'

        # スキーマの妥当性をチェック
        if not self._validate_schema(schema):
            raise ValueError(f"Invalid schema provided: {schema}")

        self.operation_queue.put((self._execute, (create_table_sql,), {}, None))

    def _validate_schema(self, schema):
        """一時的なテーブルを作成してスキーマを検証します。"""
        try:
            def tables():
                self.cursor.execute('''
                        SELECT name FROM sqlite_master WHERE type='table'
                    ''')
                result = self.cursor.fetchall()
                return [row[0] for row in result]

            temp = randomstrings(random.randint(1, 30))
            while temp in tables():
                temp = randomstrings(random.randint(1, 30))
            self.cursor.execute(f'CREATE TABLE {temp} {schema}')
            self.cursor.execute(f'DROP TABLE {temp}')
            return True
        except Exception as e:
            print(f"Schema validation failed: {e}")
            return False

    def _execute(self, query, params=()):
        self.cursor.execute(query, params)
        if not self.in_transaction:
            self.conn.commit()

    def __setitem__(self, key, value):
        self.operation_queue.put((self._execute, (f'''
            INSERT OR REPLACE INTO {self.table_name} (key, value)
            VALUES (?, ?)
        ''', (key, value)), {}, None))

    def __getitem__(self, key):
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchone, (f'''
            SELECT value FROM {self.table_name} WHERE key = ?
        ''', (key,)), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        if result is None:
            raise KeyError(f"Key {key} not found.")
        return result[0]

    def _fetchone(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def __delitem__(self, key):
        self.operation_queue.put((self._execute, (f'''
            DELETE FROM {self.table_name} WHERE key = ?
        ''', (key,)), {}, None))

    def __contains__(self, key):
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchone, (f'''
            SELECT 1 FROM {self.table_name} WHERE key = ?
        ''', (key,)), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return result is not None

    def __repr__(self):
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchall, (f'''
            SELECT key, value FROM {self.table_name}
        ''',), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return str(dict(result))

    def _fetchall(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def keys(self):
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchall, (f'''
            SELECT key FROM {self.table_name}
        ''',), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return [row[0] for row in result]

    def begin_transaction(self):
        self.operation_queue.put((self._begin_transaction, (), {}, None))

    def _begin_transaction(self):
        self.conn.execute('BEGIN TRANSACTION')
        self.in_transaction = True

    def commit_transaction(self):
        self.operation_queue.put((self._commit_transaction, (), {}, None))

    def _commit_transaction(self):
        try:
            if self.in_transaction:
                self.conn.execute('COMMIT')
        finally:
            self.in_transaction = False

    def rollback_transaction(self):
        self.operation_queue.put((self._rollback_transaction, (), {}, None))

    def _rollback_transaction(self):
        try:
            if self.in_transaction:
                self.conn.execute('ROLLBACK')
        finally:
            self.in_transaction = False

    def switch_table(self, new_table_name, schema=None):
        self.operation_queue.put((self._switch_table, (new_table_name, schema,), {}, None))
        # Add a sync point to wait until table is switched and created
        self.operation_queue.join()

    def _switch_table(self, new_table_name, schema):
        self.table_name = new_table_name
        # Ensure table is created after switching
        self.create_table(schema)

    def has_key(self, key):
        return key in self

    def clear_db(self):
        self.operation_queue.put((self._clear_db, (), {}, None))
        self.operation_queue.join()

    def _clear_db(self):
        self.cursor.execute(f'''
            SELECT name FROM sqlite_master WHERE type='table'
        ''')
        tables = self.cursor.fetchall()
        for table in tables:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table[0]}')
        if not self.in_transaction:
            self.conn.commit()
        self.table_name = "main"
        self.create_table()

    def tables(self):
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchall, (f'''
            SELECT name FROM sqlite_master WHERE type='table'
        ''',), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return [row[0] for row in result]

    def clear_table(self, table_name=None):
        if table_name is None:
            table_name = self.table_name
        self.operation_queue.put((self._execute, (f'''
            DELETE FROM {table_name}
        ''',), {}, None))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.operation_queue.join()
        self.conn.close()
        if self.lock:
            self._db_unlock()
