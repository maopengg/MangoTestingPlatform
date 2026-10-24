import json
from datetime import datetime, timedelta

from src.storage.sqlite.runtime import RuntimeSQLite


class ExecutorTaskResultOutbox:
    """执行器任务最终结果本地发件箱，服务端确认终态后才删除。"""

    RETRY_INTERVAL_SECONDS = 5
    MAX_RETRY_INTERVAL_SECONDS = 60

    @classmethod
    def upsert(cls, task_id: int, payload: dict, error: Exception | str | None = None) -> None:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = RuntimeSQLite.connect()
        try:
            conn.execute(
                """
                INSERT INTO executor_task_result_outbox
                    (task_id, payload, retry_count, next_retry_time, created_time, update_time, last_error)
                VALUES (?, ?, 0, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    payload = excluded.payload,
                    next_retry_time = excluded.next_retry_time,
                    update_time = excluded.update_time,
                    last_error = excluded.last_error
                """,
                (
                    int(task_id),
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    now,
                    now,
                    str(error)[:1000] if error else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def list_due(cls, limit: int = 20) -> list[dict]:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = RuntimeSQLite.connect()
        try:
            rows = conn.execute(
                """
                SELECT id, task_id, payload, retry_count
                FROM executor_task_result_outbox
                WHERE next_retry_time <= ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (now, max(1, int(limit))),
            ).fetchall()
            return [
                {
                    **dict(row),
                    'payload': json.loads(row['payload']),
                }
                for row in rows
            ]
        finally:
            conn.close()

    @classmethod
    def mark_failed(cls, row_id: int, retry_count: int, error: Exception | str) -> None:
        next_retry_count = int(retry_count) + 1
        delay = min(
            cls.MAX_RETRY_INTERVAL_SECONDS,
            cls.RETRY_INTERVAL_SECONDS * (2 ** min(next_retry_count - 1, 4)),
        )
        next_retry = (datetime.now() + timedelta(seconds=delay)).strftime('%Y-%m-%d %H:%M:%S')
        conn = RuntimeSQLite.connect()
        try:
            conn.execute(
                """
                UPDATE executor_task_result_outbox
                SET retry_count = ?, next_retry_time = ?, update_time = ?, last_error = ?
                WHERE id = ?
                """,
                (
                    next_retry_count,
                    next_retry,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    str(error)[:1000],
                    int(row_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def delete(cls, row_id: int) -> None:
        conn = RuntimeSQLite.connect()
        try:
            conn.execute('DELETE FROM executor_task_result_outbox WHERE id = ?', (int(row_id),))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def delete_by_task_id(cls, task_id: int) -> None:
        conn = RuntimeSQLite.connect()
        try:
            conn.execute('DELETE FROM executor_task_result_outbox WHERE task_id = ?', (int(task_id),))
            conn.commit()
        finally:
            conn.close()
