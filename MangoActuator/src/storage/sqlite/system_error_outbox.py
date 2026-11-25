"""Bounded local outbox; isolated by platform host and actuator account, never stores credentials."""
import json
import time

from src.storage.sqlite.runtime import RuntimeSQLite


class SystemErrorOutbox:
    MAX_ITEMS = 500
    RETENTION_SECONDS = 7 * 86400

    @staticmethod
    def connect():
        connection = RuntimeSQLite.connect()
        connection.execute('''CREATE TABLE IF NOT EXISTS system_error_outbox (
            fingerprint TEXT PRIMARY KEY, scope TEXT NOT NULL, payload TEXT NOT NULL,
            created_at REAL NOT NULL, next_retry REAL NOT NULL, retries INTEGER NOT NULL DEFAULT 0)''')
        return connection

    @classmethod
    def put(cls, fingerprint, scope, payload):
        connection = cls.connect()
        try:
            now = time.time()
            connection.execute('DELETE FROM system_error_outbox WHERE created_at < ?', (now - cls.RETENTION_SECONDS,))
            connection.execute('INSERT OR IGNORE INTO system_error_outbox (fingerprint, scope, payload, created_at, next_retry) VALUES (?, ?, ?, ?, ?)',
                               (fingerprint, scope, json.dumps(payload, ensure_ascii=False), now, now))
            connection.execute('DELETE FROM system_error_outbox WHERE fingerprint IN (SELECT fingerprint FROM system_error_outbox ORDER BY created_at DESC LIMIT -1 OFFSET ?)', (cls.MAX_ITEMS,))
            connection.commit()
        finally:
            connection.close()

    @classmethod
    def due(cls, scope, limit=10):
        connection = cls.connect()
        try:
            connection.execute('DELETE FROM system_error_outbox WHERE created_at < ?', (time.time() - cls.RETENTION_SECONDS,))
            connection.commit()
            rows = connection.execute('SELECT fingerprint, payload, retries FROM system_error_outbox WHERE scope = ? AND next_retry <= ? AND created_at >= ? ORDER BY created_at LIMIT ?',
                                      (scope, time.time(), time.time() - cls.RETENTION_SECONDS, limit)).fetchall()
            return [{**dict(row), 'payload': json.loads(row['payload'])} for row in rows]
        finally:
            connection.close()

    @classmethod
    def acknowledge(cls, fingerprint):
        connection = cls.connect()
        try:
            connection.execute('DELETE FROM system_error_outbox WHERE fingerprint = ?', (fingerprint,))
            connection.commit()
        finally:
            connection.close()

    @classmethod
    def failed(cls, fingerprint, retries):
        connection = cls.connect()
        try:
            delay = min(300, 5 * 2 ** min(retries, 6))
            connection.execute('UPDATE system_error_outbox SET retries = retries + 1, next_retry = ? WHERE fingerprint = ?',
                               (time.time() + delay, fingerprint))
            connection.commit()
        finally:
            connection.close()
