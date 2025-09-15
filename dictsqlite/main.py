"""DictSQLite: SQLiteを辞書のように扱うためのメインモジュール。"""

import base64
import collections.abc
import json
import pickle
import queue
import random
import secrets
import sqlite3
import string
import threading
import logging

import portalocker

from dictsqlite.modules import crypto, utils

__version__ = '1.8.1'  # バージョンアップ

# ロガーの設定
logger = logging.getLogger(__name__)


def randomstrings(n):
    """英字からなる長さnのランダム文字列を返す。"""
    return ''.join(secrets.choice(string.ascii_letters) for _ in range(n))


def expiring_dict(expiration_time: int):
    """指定秒数の有効期限を持つ辞書を生成する。"""
    return utils.ExpiringDict(expiration_time)


# vvvvvvvvvvvvvvvv 新規追加: DBSyncedSet vvvvvvvvvvvvvvvv
# 動作未確認
class DBSyncedSet(set):
    """DBと自動同期するSetクラス"""

    def __init__(self, key, proxy, initial=None):
        super().__init__(initial if initial is not None else set())
        self._key = key
        self._proxy = proxy

    def sync(self):
        """現在のset内容をDBに保存"""
        self._proxy[self._key] = set(self)

    def add(self, element):
        super().add(element)
        self.sync()

    def remove(self, element):
        super().remove(element)
        self.sync()

    def discard(self, element):
        super().discard(element)
        self.sync()

    def pop(self):
        val = super().pop()
        self.sync()
        return val

    def clear(self):
        super().clear()
        self.sync()

    def update(self, *others):
        super().update(*others)
        self.sync()

    def intersection_update(self, *others):
        super().intersection_update(*others)
        self.sync()

    def difference_update(self, *others):
        super().difference_update(*others)
        self.sync()

    def symmetric_difference_update(self, other):
        super().symmetric_difference_update(other)
        self.sync()

    def __ior__(self, other):
        result = super().__ior__(other)
        self.sync()
        return result

    def __iand__(self, other):
        result = super().__iand__(other)
        self.sync()
        return result

    def __isub__(self, other):
        result = super().__isub__(other)
        self.sync()
        return result

    def __ixor__(self, other):
        result = super().__ixor__(other)
        self.sync()
        return result


# ^^^^^^^^^^^^^^^^ 新規追加: DBSyncedSet ^^^^^^^^^^^^^^^^


class DBSyncedList(list):
    """DBと自動同期するListクラス"""

    def __init__(self, key, proxy, initial=None):
        super().__init__(initial if initial is not None else [])
        self._key = key
        self._proxy = proxy

    def sync(self):
        """現在のlist内容をDBに保存"""
        self._proxy[self._key] = list(self)

    def append(self, val):
        super().append(val)
        self.sync()

    def extend(self, vals):
        super().extend(vals)
        self.sync()

    def remove(self, val):
        super().remove(val)
        self.sync()

    def pop(self, idx=-1):
        val = super().pop(idx)
        self.sync()
        return val

    def clear(self):
        super().clear()
        self.sync()

    def insert(self, idx, val):
        super().insert(idx, val)
        self.sync()

    def reverse(self):
        super().reverse()
        self.sync()

    def sort(self, key=None, reverse=False):
        super().sort(key=key, reverse=reverse)
        self.sync()

    def __setitem__(self, idx, val):
        super().__setitem__(idx, val)
        self.sync()

    def __delitem__(self, idx):
        super().__delitem__(idx)
        self.sync()

    def __iadd__(self, other):
        result = super().__iadd__(other)
        self.sync()
        return result

    def __imul__(self, other):
        result = super().__imul__(other)
        self.sync()
        return result


class DictSQLite:  # pylint: disable=too-many-instance-attributes
    """SQLiteを辞書風APIで扱うためのラッパークラス。"""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        db_name: str,
        table_name: str = 'main',
        schema: bool = None,
        conflict_resolver: bool = False,
        journal_mode: str = None,
        lock_file: str = None,
        password: str = None,
        publickey_path: str = "./public_keys.pem",
        privatekey_path: str = "./private_keys.pem",
        version: int = 1,
        key_create: bool = False,
    ):  # pylint: disable=too-many-arguments
        self.version = version
        self.db_name = db_name
        self.password = password
        self.publickey_path = publickey_path
        self.privatekey_path = privatekey_path
        self.table_name = table_name
        if self.password is not None and key_create:
            crypto.key_create(password, publickey_path, privatekey_path)
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

    # vvvvvvvvvvvvvvvv RecursiveDictは前回の修正のまま vvvvvvvvvvvvvvvv
    class RecursiveDict(collections.abc.MutableMapping):  # pylint: disable=protected-access
        """ネストした辞書をDBと同期しつつ操作するためのプロキシ。"""

        def __init__(self, proxy, base_key, path=()):
            self._proxy = proxy
            self._base_key = base_key
            self._path = path

        def to_dict(self):
            """現在の値を通常のdictとして返す。"""
            return self._get_db_value()

        def _get_db_value(self):
            base_val = self._proxy.get_raw_value(self._base_key)
            val = base_val
            for p in self._path:
                val = val[p]
            return val

        def _update_db(self, new_top_level_value):
            self._proxy[self._base_key] = new_top_level_value

        def __getitem__(self, key):
            current_dict = self._get_db_value()
            value = current_dict[key]
            # 値をプロキシでラップして返す
            return self._proxy.db._wrap_in_proxy(  # pylint: disable=protected-access
                self._base_key, self._proxy, value, path=self._path + (key,)
            )

        def __setitem__(self, key, value):
            if hasattr(value, 'to_dict'):
                value = value.to_dict()
            elif isinstance(value, (DBSyncedList, DBSyncedSet)):
                value = type(value).__bases__[0](value)

            top_level_dict = self._proxy.get_raw_value(self._base_key)
            target_dict_ref = top_level_dict
            for p in self._path:
                target_dict_ref = target_dict_ref[p]
            target_dict_ref[key] = value
            self._update_db(top_level_dict)

        def __delitem__(self, key):
            top_level_dict = self._proxy.get_raw_value(self._base_key)
            target_dict_ref = top_level_dict
            for p in self._path:
                target_dict_ref = target_dict_ref[p]
            del target_dict_ref[key]
            self._update_db(top_level_dict)

        def __iter__(self):
            return iter(self._get_db_value())

        def __len__(self):
            return len(self._get_db_value())

        def __repr__(self):
            return repr(self._get_db_value())

        def keys(self):
            return self._get_db_value().keys()

        def items(self):
            # items()の返り値の値もプロキシでラップする必要がある
            current_dict = self._get_db_value()
            result = []
            for key, value in current_dict.items():
                wrapped_value = self._proxy.db._wrap_in_proxy(  # pylint: disable=protected-access
                    self._base_key, self._proxy, value, path=self._path + (key,)
                )
                result.append((key, wrapped_value))
            return result

        def values(self):
            # values()の返り値もプロキシでラップする必要がある
            current_dict = self._get_db_value()
            result = []
            for key, value in current_dict.items():
                wrapped_value = self._proxy.db._wrap_in_proxy(  # pylint: disable=protected-access
                    self._base_key, self._proxy, value, path=self._path + (key,)
                )
                result.append(wrapped_value)
            return result

    # ^^^^^^^^^^^^^^^^ RecursiveDict ^^^^^^^^^^^^^^^^

    class TableProxy:  # pylint: disable=protected-access
        """特定テーブルのキー/値へ非同期キュー経由でアクセスするプロキシ。"""

        def __init__(self, db, table_name):
            self.db = db
            self.table_name = table_name

        def get_raw_value(self, key):
            """DBから生の値を取得し、必要に応じて復号/デコードして返す。"""
            result_queue = queue.Queue()
            self.db.operation_queue.put((
                self.db._fetchone,  # pylint: disable=protected-access
                (f"SELECT value FROM {self.table_name} WHERE key = ?", (key,)),
                {}, result_queue
            ))
            result = result_queue.get()
            if isinstance(result, Exception):
                raise result
            if result is None:
                raise KeyError(f"Key {key} not found in table {self.table_name}.")

            value_str = result[0]
            if self.db.password is not None:
                value_str = self.db._decrypt(value_str)  # pylint: disable=protected-access

            # データ形式を自動判定
            try:
                # まずJSONとして試行（既存データ）
                return json.loads(
                    value_str,
                    object_hook=self.db._extended_json_decoder_hook,  # pylint: disable=protected-access
                )
            except (json.JSONDecodeError, TypeError):
                try:
                    # JSONが失敗したらpickleとして試行（新しいデータ）
                    if isinstance(value_str, str):
                        # base64またはlatin1でエンコードされたpickleデータ
                        value_bytes = base64.b64decode(value_str)
                        # または: value_bytes = value_str.encode('latin1')
                    else:
                        value_bytes = value_str
                    return pickle.loads(value_bytes)
                except (pickle.UnpicklingError, ValueError, TypeError):
                    # pickleデコードも失敗した場合は文字列として返す
                    return value_str

        def __getitem__(self, key):
            raw_value = self.get_raw_value(key)
            # 生の値をプロキシオブジェクトでラップして返す
            return self.db._wrap_in_proxy(key, self, raw_value)  # pylint: disable=protected-access

        def __setitem__(self, key, value):
            # pickleでバイナリ化
            value_bytes = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

            # bytesを文字列にエンコード（TEXT列用）
            value_str = base64.b64encode(value_bytes).decode('ascii')
            # または: value_str = value_bytes.decode('latin1')  # latin1は全バイト値対応

            if self.db.password is not None:
                value_str = self.db._encrypt(value_str)  # pylint: disable=protected-access

            self.db.operation_queue.put((
                self.db._execute,  # pylint: disable=protected-access
                (
                    f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)",
                    (key, value_str),
                ),
                {},
                None,
            ))

        def __delitem__(self, key):
            self.db.operation_queue.put((
                self.db._execute,  # pylint: disable=protected-access
                (f"DELETE FROM {self.table_name} WHERE key = ?", (key,)),
                {}, None
            ))

        def __contains__(self, key):
            result_queue = queue.Queue()
            self.db.operation_queue.put((
                self.db._fetchone,  # pylint: disable=protected-access
                (f"SELECT 1 FROM {self.table_name} WHERE key = ?", (key,)),
                {}, result_queue
            ))
            result = result_queue.get()
            if isinstance(result, Exception):
                raise result
            return result is not None

        def __repr__(self):
            return f"{dict(self)}"

        def __iter__(self):
            for row in self.get_all_rows():
                key = row[0]
                try:
                    # __getitem__ を経由して正しいプロキシオブジェクトを取得
                    yield key, self[key]
                except (KeyError, json.JSONDecodeError):
                    # デコードできない値はそのまま返す
                    yield key, row[1]

        def get_all_rows(self):
            """テーブル内の全行を (key, value) のタプルで返す。"""
            result_queue = queue.Queue()
            self.db.operation_queue.put((
                self.db._fetchall,  # pylint: disable=protected-access
                (f"SELECT key, value FROM {self.table_name}",),
                {}, result_queue
            ))
            result = result_queue.get()
            if isinstance(result, Exception):
                raise result
            return result

    # vvvvvvvvvvvvvvvv 変更点: 暗号化/復号の責務を分離 vvvvvvvvvvvvvvvv
    def _encrypt(self, data_str: str) -> bytes:
        """文字列をRSAで暗号化してbytesを返す。"""
        # 文字列をバイトにエンコードしてから暗号化
        return crypto.encrypt_rsa(
            crypto.load_public_key(self.publickey_path, self.password),
            data_str.encode("utf-8"),
        )

    def _decrypt(self, data: bytes) -> str:
        """RSAで復号して文字列に戻す。"""
        # バイトを復号して文字列にデコード
        return crypto.decrypt_rsa(
            crypto.load_private_key(self.privatekey_path, self.password),
            data,
        ).decode("utf-8")

    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    # vvvvvvvvvvvvvvvv 新規追加: カスタムJSONフックとプロキシラッパー vvvvvvvvvvvvvvvv
    def _extended_json_encoder_hook(self, obj):
        """json.dumpsのdefaultフック。setやカスタムオブジェクトを処理。"""
        if isinstance(obj, set):
            return {"__type__": "set", "value": sorted(list(obj))}  # 順序を保証して保存
        if isinstance(obj, (DBSyncedList, DBSyncedSet)):
            # プロキシオブジェクトをその基本の型に変換してから再処理
            return self._extended_json_encoder_hook(type(obj).__bases__[0](obj))
        if hasattr(obj, 'to_dict'):  # RecursiveDictなど
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _extended_json_decoder_hook(self, dct):
        """json.loadsのobject_hook。カスタム型を復元。"""
        if "__type__" in dct:
            if dct["__type__"] == "set":
                return set(dct["value"])
        return dct

    def _wrap_in_proxy(self, key, proxy, value, path=()):
        """生の値を適切なプロキシオブジェクトでラップする。"""
        # vvvvvvvvvvvvvvvv 変更点 vvvvvvvvvvvvvvvv
        if isinstance(value, collections.abc.Mapping):
            # isinstance(value, dict) から変更
            return DictSQLite.RecursiveDict(proxy, key, path)
        if isinstance(value, list):
            # ネストされたリストは同期されない点に注意
            if path:
                return value
            return DBSyncedList(key, proxy, value)
        if isinstance(value, set):
            # ネストされたセットは同期されない点に注意
            if path:
                return value
            return DBSyncedSet(key, proxy, value)
        return value

    # ^^^^^^^^^^^^^^^^ 新規追加: カスタムJSONフックとプロキシラッパー ^^^^^^^^^^^^^^^^

    def _process_queue(self):
        """操作キューを順次処理するワーカー。"""
        # ... (変更なし)
        while True:
            operation, args, kwargs, result_queue = self.operation_queue.get()
            try:
                result = operation(*args, **kwargs)
                if result_queue is not None:
                    result_queue.put(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("An error occurred while processing the queue: %s", e, exc_info=True)
                if result_queue is not None:
                    result_queue.put(e)
            finally:
                self.operation_queue.task_done()

    def _process_queue_conflict_resolver(self):
        """排他ロックを使って操作キューを処理するワーカー。"""
        while True:
            operation, args, kwargs, result_queue = self.operation_queue.get()
            try:
                with open(self.lock_file, "w", encoding="utf-8") as f:
                    portalocker.lock(f, portalocker.LOCK_EX)
                    self._process_queue()
                    try:
                        result = operation(*args, **kwargs)
                    finally:
                        try:
                            portalocker.unlock(f)
                        except (OSError, ValueError):  # ロック解放での例外は無視
                            pass
                if result_queue is not None:
                    result_queue.put(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("An error occurred while processing the queue: %s", e, exc_info=True)
                if result_queue is not None:
                    result_queue.put(e)
            finally:
                self.operation_queue.task_done()

    def create_table(self, table_name=None, schema=None):
        """テーブルを作成（存在しない場合）。任意でスキーマを指定可能。"""
        if table_name is not None:
            self.table_name = table_name
        if schema is None:
            schema = schema if schema else '(key TEXT PRIMARY KEY, value TEXT)'
        else:
            if not self._validate_schema(schema):
                raise ValueError(f"Invalid schema provided: {schema}")

        create_table_sql = f'CREATE TABLE IF NOT EXISTS {self.table_name} {schema}'
        self.operation_queue.put((self._execute, (create_table_sql,), {}, None))

    def _validate_schema(self, schema):
        """与えられたスキーマが有効か一時テーブルで検証。"""
        try:
            def tables():
                result_queue = queue.Queue()
                self.operation_queue.put((self._fetchall, ("""
                    SELECT name FROM sqlite_master WHERE type='table'
                """,), {}, result_queue))
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
        except sqlite3.Error as e:
            logger.error("Schema validation failed: %s", e)
            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Unexpected error during schema validation: %s", e, exc_info=True)
            return False

    def _execute(self, query, params=()):
        """カーソルでクエリを実行し、トランザクション外なら即コミット。"""
        # ... (変更なし)
        self.cursor.execute(query, params)
        if not self.in_transaction:
            self.conn.commit()

    def execute_custom(self, query, params=()):
        """任意のクエリを安全に実行（内部キュー経由）。"""
        # ... (変更なし)
        result_queue = queue.Queue()
        self.operation_queue.put((self._execute, (query, params), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return result

    # vvvvvvvvvvvvvvvv 変更点: 新しいJSON処理を利用 vvvvvvvvvvvvvvvv
    def __setitem__(self, key, value):
        """キーに値を設定。versionに応じてテーブル切替に対応。"""
        if self.version == 2:
            if not isinstance(key, tuple):
                raise ValueError("version=2では (key, table_name) の形式で指定してください")
            key, table_name = key
        else:
            table_name = self.table_name

        # TableProxyの__setitem__に処理を委譲
        proxy = self.TableProxy(self, table_name)
        proxy[key] = value

    def __getitem__(self, key):
        """キーの値取得。version=2ではテーブル選択も可能。"""
        if self.version == 2:
            if key not in self.tables():
                raise KeyError(f"Table {key} not found.")
            return self.TableProxy(self, key)
        # TableProxyの__getitem__に処理を委譲
        proxy = self.TableProxy(self, self.table_name)
        return proxy[key]

    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    def _fetchone(self, query, params=()):
        """1行を取得して返す内部ヘルパー。"""
        # ... (変更なし)
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def __delitem__(self, key):
        self.operation_queue.put((self._execute, (f'''\
            DELETE FROM {self.table_name} WHERE key = ?
        ''', (key,)), {}, None))

    def __contains__(self, key):
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchone, (f'''\
            SELECT 1 FROM {self.table_name} WHERE key = ?
        ''', (key,)), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return result is not None

    def __repr__(self):
        if self.version == 2:
            result = {}
            for table in self.tables():
                result[table] = self[table]
            return str(result)
        # TableProxy経由で取得することで正しい表現を返す
        return repr(dict(self.TableProxy(self, self.table_name)))

    def _fetchall(self, query, params=()):
        """全行を取得して返す内部ヘルパー。"""
        # ... (変更なし)
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    # ... (以降のメソッドは変更なし)
    def keys(self, table_name=None):
        """指定テーブル（未指定なら現行）の全キー一覧を返す。"""
        if table_name is None:
            table_name = self.table_name
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchall, (f'''\
            SELECT key FROM {table_name}
        ''',), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return [row[0] for row in result]

    def begin_transaction(self):
        """トランザクションを開始。"""
        self.operation_queue.put((self._begin_transaction, (), {}, None))

    def _begin_transaction(self):
        """BEGINを実行しフラグを設定。"""
        self.conn.execute('BEGIN TRANSACTION')
        self.in_transaction = True

    def commit_transaction(self):
        """トランザクションをコミット。"""
        self.operation_queue.put((self._commit_transaction, (), {}, None))

    def _commit_transaction(self):
        """COMMITを実行しフラグをクリア。"""
        try:
            if self.in_transaction:
                self.conn.execute('COMMIT')
        finally:
            self.in_transaction = False

    def rollback_transaction(self):
        """トランザクションをロールバック。"""
        self.operation_queue.put((self._rollback_transaction, (), {}, None))

    def _rollback_transaction(self):
        """ROLLBACKを実行しフラグをクリア。"""
        try:
            if self.in_transaction:
                self.conn.execute('ROLLBACK')
        finally:
            self.in_transaction = False

    def switch_table(self, new_table_name, schema=None):
        """操作対象のテーブルを切り替える。"""
        self.operation_queue.put((self._switch_table, (new_table_name, schema,), {}, None))
        self.operation_queue.join()

    def _switch_table(self, new_table_name, schema):
        """内部的にテーブル名を切替えて必要なら作成。"""
        self.table_name = new_table_name
        self.create_table(schema)

    def has_key(self, key):
        """キーの存在を返す。"""
        return key in self

    def clear_db(self):
        """全テーブルを削除し、mainを再作成。"""
        self.operation_queue.put((self._clear_db, (), {}, None))
        self.operation_queue.join()

    def _clear_db(self):
        """DB内の全テーブルをDROPして初期化。"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='table'
        """)
        tables = self.cursor.fetchall()
        for table in tables:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table[0]}')
        if not self.in_transaction:
            self.conn.commit()
        self.table_name = "main"
        self.create_table()

    def tables(self):
        """DB内の全テーブル名を返す。"""
        result_queue = queue.Queue()
        self.operation_queue.put((self._fetchall, ("""
            SELECT name FROM sqlite_master WHERE type='table'
        """,), {}, result_queue))
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        return [row[0] for row in result]

    def clear_table(self, table_name=None):
        """指定テーブル（未指定なら現行）の全データを削除。"""
        if table_name is None:
            table_name = self.table_name
        self.operation_queue.put((self._execute, (f'''\
            DELETE FROM {table_name}
        ''',), {}, None))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """バックグラウンド処理の完了を待ってDB接続を閉じる。"""
        self.operation_queue.join()
        self.conn.close()
