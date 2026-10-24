import json
from datetime import datetime, timedelta

from src.storage.sqlite.runtime import RuntimeSQLite


class StepHealReportOutbox:
    """页面步骤自愈报告发件箱，服务端确认保存后才删除。"""

    @classmethod
    def upsert(cls, trace_id: str, payload: dict, error=None) -> int:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = RuntimeSQLite.connect()
        try:
            conn.execute(
                """
                INSERT INTO step_heal_report_outbox
                    (trace_id, payload, retry_count, next_retry_time, created_time, update_time, last_error)
                VALUES (?, ?, 0, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                    payload = excluded.payload,
                    next_retry_time = excluded.next_retry_time,
                    update_time = excluded.update_time,
                    last_error = excluded.last_error
                """,
                (trace_id, json.dumps(payload, ensure_ascii=False), now, now, now,
                 str(error)[:1000] if error else None),
            )
            row = conn.execute(
                'SELECT id FROM step_heal_report_outbox WHERE trace_id = ?', (trace_id,),
            ).fetchone()
            conn.commit()
            return int(row['id'])
        finally:
            conn.close()

    @classmethod
    def list_due(cls, limit=20):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = RuntimeSQLite.connect()
        try:
            rows = conn.execute(
                """
                SELECT id, trace_id, payload, retry_count
                FROM step_heal_report_outbox
                WHERE next_retry_time <= ?
                ORDER BY id ASC LIMIT ?
                """,
                (now, max(1, int(limit))),
            ).fetchall()
            return [{**dict(row), 'payload': json.loads(row['payload'])} for row in rows]
        finally:
            conn.close()

    @classmethod
    def mark_failed(cls, row_id, retry_count, error):
        retry_count = int(retry_count) + 1
        delay = min(300, 5 * (2 ** min(retry_count - 1, 6)))
        next_retry = (datetime.now() + timedelta(seconds=delay)).strftime('%Y-%m-%d %H:%M:%S')
        conn = RuntimeSQLite.connect()
        try:
            conn.execute(
                """
                UPDATE step_heal_report_outbox
                SET retry_count = ?, next_retry_time = ?, update_time = ?, last_error = ?
                WHERE id = ?
                """,
                (retry_count, next_retry, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 str(error)[:1000], int(row_id)),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def delete(cls, row_id):
        conn = RuntimeSQLite.connect()
        try:
            conn.execute('DELETE FROM step_heal_report_outbox WHERE id = ?', (int(row_id),))
            conn.commit()
        finally:
            conn.close()
