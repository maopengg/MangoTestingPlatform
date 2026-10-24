# -*- coding: utf-8 -*-
import os
import sqlite3

from src.tools import project_dir
from src.tools.log_collector import log


class RuntimeSQLite:
    _initialized = False

    @classmethod
    def db_path(cls):
        return project_dir.cache_file()

    @classmethod
    def connect(cls):
        conn = sqlite3.connect(cls.db_path())
        conn.row_factory = sqlite3.Row
        if not cls._initialized:
            cls.initialize(conn)
            cls._initialized = True
        return conn

    @classmethod
    def initialize(cls, conn):
        cls._create_tables(conn)
        cls._migrate_legacy_databases(conn)
        conn.commit()

    @classmethod
    def _create_tables(cls, conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_case_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_type TEXT NOT NULL,
                dispatch_id TEXT,
                source_message_id TEXT,
                case_id TEXT,
                case_name TEXT,
                send_user TEXT,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                created_time TEXT NOT NULL,
                started_time TEXT,
                update_time TEXT NOT NULL,
                last_error TEXT
            )
            """
        )
        cls._ensure_columns(conn, 'execution_case_queue', {
            'dispatch_id': 'ALTER TABLE execution_case_queue ADD COLUMN dispatch_id TEXT',
            'source_message_id': 'ALTER TABLE execution_case_queue ADD COLUMN source_message_id TEXT',
            'case_id': 'ALTER TABLE execution_case_queue ADD COLUMN case_id TEXT',
            'case_name': 'ALTER TABLE execution_case_queue ADD COLUMN case_name TEXT',
            'send_user': 'ALTER TABLE execution_case_queue ADD COLUMN send_user TEXT',
        })
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_case_queue_type_status "
            "ON execution_case_queue(queue_type, status, id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_case_queue_dispatch "
            "ON execution_case_queue(queue_type, dispatch_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS websocket_reliable_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_type TEXT,
                send_user TEXT,
                payload TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_time TEXT,
                created_time TEXT NOT NULL,
                update_time TEXT NOT NULL,
                last_error TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_websocket_reliable_queue_next_retry "
            "ON websocket_reliable_queue(next_retry_time, retry_count)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS executor_task_result_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_time TEXT NOT NULL,
                created_time TEXT NOT NULL,
                update_time TEXT NOT NULL,
                last_error TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_executor_task_result_due "
            "ON executor_task_result_outbox(next_retry_time, id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS step_heal_report_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_time TEXT NOT NULL,
                created_time TEXT NOT NULL,
                update_time TEXT NOT NULL,
                last_error TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_step_heal_report_due "
            "ON step_heal_report_outbox(next_retry_time, id)"
        )

    @staticmethod
    def _ensure_columns(conn, table_name: str, column_sql: dict[str, str]):
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = {row['name'] for row in rows}
        for column, sql in column_sql.items():
            if column not in columns:
                conn.execute(sql)

    @classmethod
    def _migrate_legacy_databases(cls, conn):
        legacy_paths = [
            os.path.join(project_dir.cache(), 'actuator_runtime.db'),
            os.path.join(project_dir.cache(), 'websocket_reliable_queue.db'),
        ]
        for legacy_path in legacy_paths:
            if not os.path.exists(legacy_path) or os.path.abspath(legacy_path) == os.path.abspath(cls.db_path()):
                continue
            try:
                cls._migrate_legacy_database(conn, legacy_path)
                os.remove(legacy_path)
                log.info(f'SQLite旧运行库已合并并删除：{legacy_path}')
            except Exception as error:
                log.warning(f'SQLite旧运行库合并失败，保留原文件：{legacy_path}，错误：{error}')

    @classmethod
    def _migrate_legacy_database(cls, target_conn, legacy_path: str):
        legacy_conn = sqlite3.connect(f"file:{legacy_path}?mode=ro", uri=True)
        legacy_conn.row_factory = sqlite3.Row
        try:
            tables = {
                row['name']
                for row in legacy_conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            if 'execution_case_queue' in tables:
                cls._copy_execution_case_queue(target_conn, legacy_conn)
            if 'websocket_reliable_queue' in tables:
                cls._copy_websocket_reliable_queue(target_conn, legacy_conn)
            target_conn.commit()
        finally:
            legacy_conn.close()

    @staticmethod
    def _table_columns(conn, table_name: str):
        return [row['name'] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]

    @classmethod
    def _copy_execution_case_queue(cls, target_conn, legacy_conn):
        columns = [
            column for column in cls._table_columns(target_conn, 'execution_case_queue')
            if column != 'id' and column in cls._table_columns(legacy_conn, 'execution_case_queue')
        ]
        if not columns:
            return
        rows = legacy_conn.execute(f"SELECT {', '.join(columns)} FROM execution_case_queue").fetchall()
        if not rows:
            return
        placeholders = ', '.join(['?'] * len(columns))
        target_conn.executemany(
            f"INSERT OR IGNORE INTO execution_case_queue ({', '.join(columns)}) VALUES ({placeholders})",
            [[row[column] for column in columns] for row in rows],
        )
        log.info(f'SQLite已合并旧执行队列表，数量：{len(rows)}')

    @classmethod
    def _copy_websocket_reliable_queue(cls, target_conn, legacy_conn):
        columns = [
            column for column in cls._table_columns(target_conn, 'websocket_reliable_queue')
            if column != 'id' and column in cls._table_columns(legacy_conn, 'websocket_reliable_queue')
        ]
        if not columns:
            return
        rows = legacy_conn.execute(f"SELECT {', '.join(columns)} FROM websocket_reliable_queue").fetchall()
        inserted_count = 0
        for row in rows:
            row_data = dict(row)
            exists = target_conn.execute(
                """
                SELECT 1 FROM websocket_reliable_queue
                WHERE payload = ? AND created_time = ?
                  AND IFNULL(message_type, '') = IFNULL(?, '')
                  AND IFNULL(send_user, '') = IFNULL(?, '')
                LIMIT 1
                """,
                (
                    row_data.get('payload'),
                    row_data.get('created_time'),
                    row_data.get('message_type'),
                    row_data.get('send_user'),
                ),
            ).fetchone()
            if exists:
                continue
            placeholders = ', '.join(['?'] * len(columns))
            target_conn.execute(
                f"INSERT INTO websocket_reliable_queue ({', '.join(columns)}) VALUES ({placeholders})",
                [row[column] for column in columns],
            )
            inserted_count += 1
        if rows:
            log.info(f'SQLite已合并旧可靠消息队列表，读取：{len(rows)}，新增：{inserted_count}')
