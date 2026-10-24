# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from src.storage.sqlite.runtime import RuntimeSQLite
from src.tools.log_collector import log


class WebSocketReliableQueue:
    retry_interval = 60
    retry_limit = 7
    expire_hours = 24
    batch_size = 50

    @classmethod
    def connect(cls):
        conn = RuntimeSQLite.connect()
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
        conn.commit()
        return conn

    @classmethod
    def cleanup_expired(cls):
        expire_time = (datetime.now() - timedelta(hours=cls.expire_hours)).strftime("%Y-%m-%d %H:%M:%S")
        conn = cls.connect()
        try:
            conn.execute("DELETE FROM websocket_reliable_queue WHERE created_time < ?", (expire_time,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def insert(cls, payload: str, message_type: str | None, send_user: str | None) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = cls.connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO websocket_reliable_queue
                    (message_type, send_user, payload, retry_count, next_retry_time, created_time, update_time)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                """,
                (message_type, send_user, payload, now, now, now),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def delete(cls, queue_id: int):
        conn = cls.connect()
        try:
            conn.execute("DELETE FROM websocket_reliable_queue WHERE id = ?", (queue_id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def mark_failed(cls, queue_id: int, retry_count: int, error: Exception):
        next_retry_count = retry_count + 1
        conn = cls.connect()
        try:
            if next_retry_count > cls.retry_limit:
                conn.execute("DELETE FROM websocket_reliable_queue WHERE id = ?", (queue_id,))
                log.warning(f"可靠消息超过最大重试次数，已删除，queue_id={queue_id}，失败详情：{error}")
            else:
                next_retry_time = (datetime.now() + timedelta(seconds=cls.retry_interval)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                conn.execute(
                    """
                    UPDATE websocket_reliable_queue
                    SET retry_count = ?, next_retry_time = ?, update_time = ?, last_error = ?
                    WHERE id = ?
                    """,
                    (
                        next_retry_count,
                        next_retry_time,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        str(error)[:1000],
                        queue_id,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def list_due(cls, limit: int | None = None) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = cls.connect()
        try:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, payload, retry_count, message_type
                    FROM websocket_reliable_queue
                    WHERE next_retry_time IS NULL OR next_retry_time <= ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (now, limit or cls.batch_size),
                ).fetchall()
            ]
        finally:
            conn.close()
