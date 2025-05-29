import asyncio
import asyncpg
import json
import logging
import socket
import sys
from contextlib import asynccontextmanager

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class AsyncDictPostgreSQL:
    def __init__(self, host='127.0.0.1', port=5432, database='postgres',
                 user='postgres', password='', min_size=10, max_size=20):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def init_pool(self):
        """接続プールを初期化"""
        if self.pool is None:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.pool = await asyncpg.create_pool(
                        host=self.host,
                        port=self.port,
                        database=self.database,
                        user=self.user,
                        password=self.password,
                        min_size=self.min_size,
                        max_size=self.max_size,
                        command_timeout=30
                    )
                    self.logger.info(f"接続プールを初期化しました (min: {self.min_size}, max: {self.max_size})")
                    break
                except socket.gaierror as e:
                    self.logger.warning(f"プール作成試行 {attempt + 1} 失敗: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise

    @asynccontextmanager
    async def get_connection(self):
        """プールから接続を取得する非同期コンテキストマネージャ"""
        if self.pool is None:
            await self.init_pool()

        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)

    def _convert_to_asyncpg_params(self, data: dict) -> tuple:
        """辞書データをasyncpgパラメータ形式に変換"""
        values = []
        placeholders = []

        for i, (key, value) in enumerate(data.items(), 1):
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value, ensure_ascii=False))
            else:
                values.append(value)
            placeholders.append(f"${i}")

        return tuple(values), placeholders

    def _is_character_type(self, column_type: str) -> bool:
        """文字列型かどうかを判定"""
        character_types = ['text', 'varchar', 'char', 'character']
        return any(char_type in column_type.lower() for char_type in character_types)

    async def _get_table_columns(self, table_name: str, connection) -> dict:
        """テーブルのカラム情報を取得"""
        query = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = $1
                """
        rows = await connection.fetch(query, table_name)
        return {row['column_name']: row['data_type'] for row in rows}

    async def create_table_from_dict(self, table_name: str, data: dict):
        """辞書データからテーブルを自動作成"""
        columns = []

        for key, value in data.items():
            if isinstance(value, int):
                column_type = "INTEGER"
            elif isinstance(value, float):
                column_type = "REAL"
            elif isinstance(value, bool):
                column_type = "BOOLEAN"
            elif isinstance(value, (dict, list)):
                column_type = "JSONB"
            else:
                column_type = "TEXT"

            columns.append(f"{key} {column_type}")

        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"

        async with self.get_connection() as conn:
            await conn.execute(create_sql)
            self.logger.info(f"テーブル {table_name} を作成しました")

    async def insert_data(self, table_name: str, data: dict) -> bool:
        """辞書データを挿入"""
        try:
            await self.create_table_from_dict(table_name, data)

            columns = list(data.keys())
            values, placeholders = self._convert_to_asyncpg_params(data)

            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

            async with self.get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(insert_sql, *values)
                self.logger.info(f"データを {table_name} に挿入しました")
                return True

        except Exception as e:
            self.logger.error(f"データ挿入エラー: {e}")
            return False

    async def search_data(self, table_name: str, conditions: dict = None) -> list:
        """条件に基づいてデータを検索"""
        try:
            async with self.get_connection() as conn:
                if not conditions:
                    query = f"SELECT * FROM {table_name}"
                    rows = await conn.fetch(query)
                else:
                    columns_info = await self._get_table_columns(table_name, conn)

                    where_clauses = []
                    values = []
                    param_count = 1

                    for key, value in conditions.items():
                        column_type = columns_info.get(key, 'text')

                        if self._is_character_type(column_type):
                            where_clauses.append(f"{key} ILIKE ${param_count}")
                            values.append(f"%{value}%")
                        else:
                            where_clauses.append(f"{key} = ${param_count}")
                            values.append(value)
                        param_count += 1

                    query = f"SELECT * FROM {table_name} WHERE {' AND '.join(where_clauses)}"
                    rows = await conn.fetch(query, *values)

                result = [dict(row) for row in rows]
                self.logger.info(f"{table_name} から {len(result)} 件のデータを検索しました")
                return result

        except Exception as e:
            self.logger.error(f"データ検索エラー: {e}")
            return []

    async def update_data(self, table_name: str, data: dict, conditions: dict) -> bool:
        """条件に基づいてデータを更新"""
        try:
            set_clauses = []
            where_clauses = []
            values = []
            param_count = 1

            for key, value in data.items():
                set_clauses.append(f"{key} = ${param_count}")
                if isinstance(value, (dict, list)):
                    values.append(json.dumps(value, ensure_ascii=False))
                else:
                    values.append(value)
                param_count += 1

            for key, value in conditions.items():
                where_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

            update_sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"

            async with self.get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(update_sql, *values)
                self.logger.info(f"{table_name} のデータを更新しました")
                return True

        except Exception as e:
            self.logger.error(f"データ更新エラー: {e}")
            return False

    async def delete_data(self, table_name: str, conditions: dict) -> bool:
        """条件に基づいてデータを削除"""
        try:
            where_clauses = []
            values = []
            param_count = 1

            for key, value in conditions.items():
                where_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

            delete_sql = f"DELETE FROM {table_name} WHERE {' AND '.join(where_clauses)}"

            async with self.get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(delete_sql, *values)
                self.logger.info(f"{table_name} からデータを削除しました")
                return True

        except Exception as e:
            self.logger.error(f"データ削除エラー: {e}")
            return False

    async def drop_table(self, table_name: str) -> bool:
        """テーブルを削除"""
        try:
            drop_sql = f"DROP TABLE IF EXISTS {table_name}"

            async with self.get_connection() as conn:
                await conn.execute(drop_sql)
                self.logger.info(f"テーブル {table_name} を削除しました")
                return True

        except Exception as e:
            self.logger.error(f"テーブル削除エラー: {e}")
            return False

    async def bulk_insert(self, table_name: str, data_list: list) -> bool:
        """複数のデータを一括挿入（バッチ処理対応, copy_records_to_table を使用）"""
        try:
            if not data_list:
                self.logger.info("挿入するデータがありません。")
                return True

            # テーブルが存在しない場合は、最初のデータに基づいて作成
            # この呼び出しは data_list[0] が存在することを前提としているため、上の if not data_list: で早期リターンしています。
            await self.create_table_from_dict(table_name, data_list[0])

            batch_size = 1000  # メモリ効率とパフォーマンスのバランスを考慮して調整
            total_inserted = 0

            async with self.get_connection() as conn:
                # 全ての辞書が同じキーと順序を持つことを期待するため、
                # カラム名は最初のデータから一度だけ取得する（効率化）
                # もしデータごとにカラムが異なる可能性がある場合は、バッチごとにカラムリストを生成する必要がある
                if not data_list[0]:  # 念のため最初のデータが空の辞書でないかチェック
                    self.logger.error("最初のデータが空のため、カラム情報を取得できません。")
                    return False
                columns = list(data_list[0].keys())

                for i in range(0, len(data_list), batch_size):
                    batch_of_dicts = data_list[i:i + batch_size]

                    if not batch_of_dicts:  # ループの最後で空のバッチになる可能性への対処
                        continue

                    # copy_records_to_table 向けのデータ形式 (タプルのリスト) に変換
                    records_to_copy = []
                    for item_dict in batch_of_dicts:
                        row_values = []
                        for col_name in columns:  # 事前に取得したカラムリストの順序で値を取得
                            value = item_dict.get(col_name)  # カラムが存在しない場合は None になる
                            if isinstance(value, (dict, list)):
                                row_values.append(json.dumps(value, ensure_ascii=False))
                            else:
                                row_values.append(value)
                        records_to_copy.append(tuple(row_values))

                    # トランザクション内で COPY を実行
                    # copy_records_to_table はそれ自体が効率的な操作なので、
                    # 各バッチを個別のトランザクションとして扱うことで、
                    # エラー発生時の影響範囲を限定し、長大なトランザクションを避ける
                    try:
                        async with conn.transaction():
                            await conn.copy_records_to_table(
                                table_name,  # テーブル名 (SQLインジェクションに注意！)
                                records=records_to_copy,  # 挿入するレコードのタプルのリスト
                                columns=columns,  # カラム名のリスト (順序が重要)
                                timeout=60  # タイムアウト（秒単位、適宜調整）
                            )
                        total_inserted += len(batch_of_dicts)
                        self.logger.info(
                            f"バッチ処理: {total_inserted}/{len(data_list)} 件 ({len(batch_of_dicts)}件) 挿入完了")
                    except Exception as batch_e:
                        # バッチ処理中にエラーが発生した場合、そのバッチは挿入されない
                        self.logger.error(f"バッチ挿入エラー (範囲 {i} - {i + batch_size - 1}): {batch_e}")
                        # ここで False を返して処理を中断するか、エラーを記録して続行するかは要件による
                        # 例として、一度エラーが発生したら全体を失敗とする
                        raise batch_e  # より上位の try-except で捕捉させるか、ここで False を返す

            self.logger.info(
                f"{table_name} に {total_inserted} 件のデータを一括挿入しました (総試行数: {len(data_list)})")
            return True

        except Exception as e:
            self.logger.error(f"一括挿入処理全体でエラーが発生しました: {e}")
            return False

    async def table_exists(self, table_name: str) -> bool:
        """テーブルが存在するかチェック"""
        try:
            async with self.get_connection() as conn:
                query = """
                        SELECT EXISTS (SELECT 1
                                       FROM information_schema.tables
                                       WHERE table_name = $1)
                        """
                result = await conn.fetchval(query, table_name)
                return result
        except Exception as e:
            self.logger.error(f"テーブル存在チェックエラー: {e}")
            return False

    async def get_table_info(self, table_name: str) -> dict:
        """テーブル情報を取得"""
        try:
            async with self.get_connection() as conn:
                columns_query = """
                                SELECT column_name, data_type, is_nullable
                                FROM information_schema.columns
                                WHERE table_name = $1
                                ORDER BY ordinal_position
                                """
                columns = await conn.fetch(columns_query, table_name)

                count_query = f"SELECT COUNT(*) FROM {table_name}"
                record_count = await conn.fetchval(count_query)

                return {
                    'table_name': table_name,
                    'columns': [dict(col) for col in columns],
                    'record_count': record_count
                }

        except Exception as e:
            self.logger.error(f"テーブル情報取得エラー: {e}")
            return {}

    async def get_pool_status(self) -> dict:
        """接続プールの状態を取得"""
        if self.pool is None:
            return {'status': 'プールが初期化されていません'}

        return {
            'size': self.pool.get_size(),
            'min_size': self.pool.get_min_size(),
            'max_size': self.pool.get_max_size(),
            'idle_size': self.pool.get_idle_size()
        }

    async def close_pool(self):
        """接続プールを終了"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.logger.info("接続プールを終了しました")

    async def __aenter__(self):
        """非同期コンテキストマネージャのエントリポイント"""
        await self.init_pool()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャの終了処理"""
        await self.close_pool()
