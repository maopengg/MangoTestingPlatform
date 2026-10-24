# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime

from src.storage.sqlite.runtime import RuntimeSQLite
from src.tools.log_collector import log


class ExecutionCaseQueueFull(Exception):
    pass


class ExecutionCaseQueue:
    TYPE_UI = 'ui'
    TYPE_PYTEST = 'pytest'
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    DEFAULT_QUEUE_SIZE = 10

    @classmethod
    def connect(cls):
        conn = RuntimeSQLite.connect()
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
        cls._ensure_columns(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_case_queue_type_status "
            "ON execution_case_queue(queue_type, status, id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_case_queue_dispatch "
            "ON execution_case_queue(queue_type, dispatch_id)"
        )
        conn.commit()
        return conn

    @classmethod
    def _ensure_columns(cls, conn):
        rows = conn.execute("PRAGMA table_info(execution_case_queue)").fetchall()
        columns = {row['name'] for row in rows}
        column_sql = {
            'dispatch_id': 'ALTER TABLE execution_case_queue ADD COLUMN dispatch_id TEXT',
            'source_message_id': 'ALTER TABLE execution_case_queue ADD COLUMN source_message_id TEXT',
            'case_id': 'ALTER TABLE execution_case_queue ADD COLUMN case_id TEXT',
            'case_name': 'ALTER TABLE execution_case_queue ADD COLUMN case_name TEXT',
            'send_user': 'ALTER TABLE execution_case_queue ADD COLUMN send_user TEXT',
        }
        for column, sql in column_sql.items():
            if column not in columns:
                conn.execute(sql)

    @classmethod
    def queue_limit(cls, queue_type: str) -> int:
        try:
            from src.tools.set_config import SetConfig
            if queue_type == cls.TYPE_UI:
                value = SetConfig.get_ui_queue_size()  # type: ignore
            elif queue_type == cls.TYPE_PYTEST:
                value = SetConfig.get_pytest_queue_size()  # type: ignore
            else:
                value = cls.DEFAULT_QUEUE_SIZE
            value = int(value or cls.DEFAULT_QUEUE_SIZE)
            return max(1, value)
        except Exception as error:
            log.warning(f'读取本地执行队列容量失败，使用默认值{cls.DEFAULT_QUEUE_SIZE}，详情：{error}')
            return cls.DEFAULT_QUEUE_SIZE

    @classmethod
    def recover_running(cls):
        now = cls.now()
        conn = cls.connect()
        try:
            cursor = conn.execute(
                """
                UPDATE execution_case_queue
                SET status = ?, started_time = NULL, update_time = ?
                WHERE status = ?
                """,
                (cls.STATUS_PENDING, now, cls.STATUS_RUNNING),
            )
            conn.commit()
            if cursor.rowcount:
                log.warning(f'执行器启动恢复本地执行队列，running -> pending，数量：{cursor.rowcount}')
            return cursor.rowcount
        finally:
            conn.close()

    @classmethod
    def count(cls, queue_type: str):
        conn = cls.connect()
        try:
            return int(
                conn.execute(
                    "SELECT COUNT(1) FROM execution_case_queue WHERE queue_type = ?",
                    (queue_type,),
                ).fetchone()[0]
            )
        finally:
            conn.close()

    @classmethod
    def pending_count(cls, queue_type: str):
        conn = cls.connect()
        try:
            return int(
                conn.execute(
                    "SELECT COUNT(1) FROM execution_case_queue WHERE queue_type = ? AND status = ?",
                    (queue_type, cls.STATUS_PENDING),
                ).fetchone()[0]
            )
        finally:
            conn.close()

    @classmethod
    def insert(cls,
               queue_type: str,
               payload: str,
               dispatch_id: str | None = None,
               source_message_id: str | None = None,
               case_id: str | int | None = None,
               case_name: str | None = None,
               send_user: str | None = None) -> int:
        limit = cls.queue_limit(queue_type)
        now = cls.now()
        dispatch_id = dispatch_id or cls._default_dispatch_id(queue_type, payload)
        case_info = cls._extract_case_info(payload)
        case_id = case_id if case_id is not None else case_info.get('case_id')
        case_name = case_name if case_name is not None else case_info.get('case_name')
        send_user = send_user if send_user is not None else case_info.get('send_user')
        conn = cls.connect()
        try:
            count = int(
                conn.execute(
                    "SELECT COUNT(1) FROM execution_case_queue WHERE queue_type = ?",
                    (queue_type,),
                ).fetchone()[0]
            )
            if count >= limit:
                raise ExecutionCaseQueueFull(f'{queue_type}本地执行队列已满，当前数量：{count}，最大数量：{limit}')
            cursor = conn.execute(
                """
                INSERT INTO execution_case_queue
                    (
                        queue_type, dispatch_id, source_message_id, case_id, case_name, send_user,
                        payload, status, created_time, started_time, update_time
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    queue_type, dispatch_id, source_message_id, str(case_id) if case_id is not None else None,
                    case_name, send_user, payload, cls.STATUS_PENDING, now, now
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def bulk_insert(cls, queue_type: str, tasks: list[dict], source_message_id: str | None = None):
        accepted = []
        rejected = []
        limit = cls.queue_limit(queue_type)
        now = cls.now()
        conn = cls.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = int(
                conn.execute(
                    "SELECT COUNT(1) FROM execution_case_queue WHERE queue_type = ?",
                    (queue_type,),
                ).fetchone()[0]
            )
            for task in tasks:
                if count >= limit:
                    rejected.append({**task, 'reason': f'{queue_type}本地执行队列已满，最大数量：{limit}'})
                    continue
                payload = task.get('payload')
                if not isinstance(payload, str):
                    payload = json.dumps(payload, ensure_ascii=False)
                dispatch_id = task.get('dispatch_id') or cls._default_dispatch_id(queue_type, payload)
                case_info = cls._extract_case_info(payload)
                try:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO execution_case_queue
                            (
                                queue_type, dispatch_id, source_message_id, case_id, case_name, send_user,
                                payload, status, created_time, started_time, update_time
                            )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                        """,
                        (
                            queue_type, dispatch_id, task.get('source_message_id') or source_message_id,
                            str(task.get('case_id') or case_info.get('case_id') or '') or None,
                            task.get('case_name') or case_info.get('case_name'),
                            task.get('send_user') or case_info.get('send_user'),
                            payload, cls.STATUS_PENDING, now, now
                        ),
                    )
                    if cursor.rowcount:
                        accepted.append({'dispatch_id': dispatch_id, 'queue_id': int(cursor.lastrowid)})
                        count += 1
                    else:
                        accepted.append({'dispatch_id': dispatch_id, 'duplicate': True})
                except Exception as error:
                    rejected.append({**task, 'dispatch_id': dispatch_id, 'reason': str(error)})
            conn.commit()
            return accepted, rejected
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def fetch_next(cls, queue_type: str) -> dict | None:
        now = cls.now()
        conn = cls.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT
                    id, queue_type, dispatch_id, source_message_id, case_id, case_name, send_user,
                    payload, status, created_time, started_time, update_time, last_error
                FROM execution_case_queue
                WHERE queue_type = ? AND status = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (queue_type, cls.STATUS_PENDING),
            ).fetchone()
            if not row:
                conn.commit()
                return None
            conn.execute(
                """
                UPDATE execution_case_queue
                SET status = ?, started_time = ?, update_time = ?, last_error = NULL
                WHERE id = ?
                """,
                (cls.STATUS_RUNNING, now, now, row['id']),
            )
            conn.commit()
            return dict(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def delete(cls, queue_id: int):
        conn = cls.connect()
        try:
            conn.execute("DELETE FROM execution_case_queue WHERE id = ?", (queue_id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def remove_pending_by_test_suite(cls, test_suite_id: int, queue_type: str) -> int:
        conn = cls.connect()
        try:
            rows = conn.execute(
                """
                SELECT id, payload
                FROM execution_case_queue
                WHERE status = ? AND queue_type = ?
                """,
                (cls.STATUS_PENDING, queue_type),
            ).fetchall()
            queue_ids = [
                int(row['id'])
                for row in rows
                if cls._extract_test_suite_id(row['payload']) == int(test_suite_id)
            ]
            if not queue_ids:
                return 0
            placeholders = ','.join('?' for _ in queue_ids)
            cursor = conn.execute(
                f"DELETE FROM execution_case_queue WHERE id IN ({placeholders})",
                queue_ids,
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    @classmethod
    def mark_error(cls, queue_id: int, error: Exception):
        conn = cls.connect()
        try:
            conn.execute(
                """
                UPDATE execution_case_queue
                SET update_time = ?, last_error = ?
                WHERE id = ?
                """,
                (cls.now(), str(error)[:1000], queue_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _extract_case_info(payload: str):
        try:
            data = json.loads(payload)
            return {
                'case_id': data.get('id'),
                'case_name': data.get('name'),
                'send_user': data.get('send_user'),
            }
        except Exception:
            return {}

    @staticmethod
    def _extract_test_suite_id(payload: str) -> int | None:
        try:
            data = json.loads(payload)
            value = data.get('test_suite_id') or data.get('test_suite')
            return int(value) if value is not None else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _default_dispatch_id(queue_type: str, payload: str):
        case_info = ExecutionCaseQueue._extract_case_info(payload)
        case_id = case_info.get('case_id')
        if case_id is not None:
            return f'{queue_type}:{case_id}:{uuid.uuid4().hex}'
        return f'{queue_type}:{uuid.uuid4().hex}'
