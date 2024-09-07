import random
import sqlite3
import threading
import queue
import secrets
import string
import portalocker
import json

__version__ = '1.3.9'


def randomstrings(n):
    return ''.join(secrets.choice(string.ascii_letters) for _ in range(n))


class DictSQLite:
    def __init__(self, db_name: str, table_name: str = 'main', schema: bool = None, conflict_resolver: bool = False, journal_mode: str = None, lock_file: str = None):
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
        if self.conflict_resolver:
            self.worker_thread = threading.Thread(target=self._process_queue_conflict_resolver)
            self.worker_thread.daemon = True
            self.worker_thread.start()
        else:
            self.worker_thread = threading.Thread(target=self._process_queue)
            self.worker_thread.daemon = True
            self.worker_thread.start()
        self.create_table(schema=schema)
        if journal_mode is not None:
            self.conn.execute(f'PRAGMA journal_mode={journal_mode};')

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
        while True:
            operation, args, kwargs, result_queue = self.operation_queue.get()
            with open(self.lock_file, "w") as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                self._process_queue()
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

    def create_table(self, table_name=None, schema=None):
        if table_name is not None:
            self.table_name = table_name
        if schema is None:
            schema = schema if schema else '(key TEXT PRIMARY KEY, value TEXT)'
        else:
            # スキーマの妥当性をチェック
            if not self._validate_schema(schema):
                raise ValueError(f"Invalid schema provided: {schema}")

        create_table_sql = f'CREATE TABLE IF NOT EXISTS {self.table_name} {schema}'
        self.operation_queue.put((self._execute, (create_table_sql,), {}, None))

    def _validate_schema(self, schema):
        """一時的なテーブルを作成してスキーマを検証します。"""
        try:
            def tables():
                result_queue = queue.Queue()
                self.operation_queue.put((self._fetchall, (f'''
                    SELECT name FROM sqlite_master WHERE type='table'
                ''',), {}, result_queue))
                result = result_queue.get()
                if isinstance(result, Exception):
                    raise result
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

    def execute_custom(self, query, params=()):
        result_queue = queue.Queue()
        self.operation_queue.put((self._execute, (query, params), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return result

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            key, table_name = key
            temp = self.table_name
            self.create_table(table_name)
            self.switch_table(temp)
        else:
            table_name = self.table_name
        # dictをJSON文字列に変換
        if isinstance(value, dict):
            value = json.dumps(value)
        self.operation_queue.put((self._execute, (f'''
            INSERT OR REPLACE INTO {table_name} (key, value)
            VALUES (?, ?)
        ''', (key, value)), {}, None))

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key, table_name = key
        else:
            table_name = self.table_name
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchone, (f'''
            SELECT value FROM {table_name} WHERE key = ?
        ''', (key,)), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        if result is None:
            raise KeyError(f"Key {key} not found.")
        try:
            return json.loads(result[0])
        except json.JSONDecodeError:
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

    def keys(self, table_name=None):
        if table_name is None:
            table_name = self.table_name
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchall, (f'''
            SELECT key FROM {table_name}
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
