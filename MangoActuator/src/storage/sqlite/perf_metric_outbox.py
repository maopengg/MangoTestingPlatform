import json
from datetime import datetime, timedelta

from src.storage.sqlite.runtime import RuntimeSQLite


class PerfMetricOutbox:
    RETRY_LIMIT = 20

    @classmethod
    def connect(cls):
        connection = RuntimeSQLite.connect()
        connection.execute("""
            CREATE TABLE IF NOT EXISTS perf_metric_outbox_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_key TEXT NOT NULL,
                run_node_id INTEGER NOT NULL,
                sequence INTEGER NOT NULL,
                payload TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_time TEXT,
                last_error TEXT,
                create_time TEXT NOT NULL,
                UNIQUE(run_key, sequence)
            )
        """)
        connection.commit()
        return connection

    @classmethod
    def upsert(cls, run_key: str, run_node_id: int, sequence: int, payload: dict):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection = cls.connect()
        try:
            connection.execute("""
                INSERT INTO perf_metric_outbox_v2(run_key, run_node_id, sequence, payload, next_retry_time, create_time)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_key, sequence) DO UPDATE SET payload=excluded.payload
            """, (str(run_key), run_node_id, sequence, json.dumps(payload, ensure_ascii=False), now, now))
            connection.commit()
        finally:
            connection.close()

    @classmethod
    def list_due(cls, run_key: str, limit: int = 20) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection = cls.connect()
        try:
            rows = connection.execute("""
                SELECT id, run_key, run_node_id, sequence, payload, retry_count FROM perf_metric_outbox_v2
                WHERE run_key=? AND (next_retry_time IS NULL OR next_retry_time<=?)
                ORDER BY sequence LIMIT ?
            """, (str(run_key), now, limit)).fetchall()
            return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]
        finally:
            connection.close()

    @classmethod
    def delete(cls, row_id: int):
        connection = cls.connect()
        try:
            connection.execute("DELETE FROM perf_metric_outbox_v2 WHERE id=?", (row_id,))
            connection.commit()
        finally:
            connection.close()

    @classmethod
    def mark_failed(cls, row_id: int, retry_count: int, error: Exception):
        delay = min(60, 2 ** min(retry_count, 6))
        next_time = (datetime.now() + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
        connection = cls.connect()
        try:
            if retry_count + 1 >= cls.RETRY_LIMIT:
                connection.execute("DELETE FROM perf_metric_outbox_v2 WHERE id=?", (row_id,))
            else:
                connection.execute("UPDATE perf_metric_outbox_v2 SET retry_count=?, next_retry_time=?, last_error=? WHERE id=?",
                                   (retry_count + 1, next_time, str(error)[:1000], row_id))
            connection.commit()
        finally:
            connection.close()
