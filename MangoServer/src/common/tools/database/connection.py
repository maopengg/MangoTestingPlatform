import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from queue import Empty, Full, Queue
from typing import Any

import pymysql
from pydantic import BaseModel
from pymysql.cursors import DictCursor
from pymysql.err import InternalError, OperationalError, ProgrammingError

from src.apps.auto_system.models import Database, TestObject
from src.common.enums.tools_enum import DatabaseTypeEnum, StatusEnum
from src.common.exceptions import ToolsError
from src.settings import MYSQL_IP


class DatabaseConnectionConfig(BaseModel):
    host: str = ""
    port: int = 0
    user: str = ""
    password: str | None = None
    database: str | None = None


class SqlPermissionGuard:
    QUERY_PREFIXES = ("SELECT", "WITH", "SHOW", "DESC", "DESCRIBE", "PRAGMA", "EXPLAIN")

    @classmethod
    def is_query(cls, sql: str) -> bool:
        sql_upper = sql.strip().upper()
        return sql_upper.startswith(cls.QUERY_PREFIXES)

    @classmethod
    def check(cls, sql: str, allow_query: bool, allow_write: bool) -> None:
        if not sql or not sql.strip():
            return
        if cls.is_query(sql):
            if not allow_query:
                raise ToolsError(300, "当前测试环境未开启数据库查询权限")
            return
        if not allow_write:
            raise ToolsError(300, "当前测试环境未开启数据库增删改权限")


class DatabaseConnection(ABC):
    def __init__(self, allow_query: bool = True, allow_write: bool = False):
        self.allow_query = allow_query
        self.allow_write = allow_write

    def condition_execute(self, sql: str):
        if not sql or not sql.strip():
            return None
        SqlPermissionGuard.check(sql, self.allow_query, self.allow_write)
        return self.execute(sql)

    @abstractmethod
    def execute(self, sql: str):
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @staticmethod
    def convert_datetime_to_string(data):
        if isinstance(data, dict):
            return {key: DatabaseConnection.convert_datetime_to_string(value) for key, value in data.items()}
        if isinstance(data, list):
            return [DatabaseConnection.convert_datetime_to_string(item) for item in data]
        if isinstance(data, (datetime, date)):
            return data.strftime("%Y-%m-%d %H:%M:%S")
        return data


class MysqlConnectionPool:
    def __init__(
            self,
            config: DatabaseConnectionConfig,
            pool_size: int = 5,
            max_overflow: int = 0,
            timeout: float = 30.0,
            retry_attempts: int = 3,
            retry_delay: float = 0.5,
    ):
        self.config = config
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self._pool: Queue = Queue(maxsize=pool_size)
        self._overflow_connections = set()
        self._overflow_count = 0
        self._created_connections = 0
        self._lock = threading.RLock()
        self._overflow_lock = threading.Lock()

    def _create_connection(self):
        try:
            return pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                autocommit=True,
                cursorclass=DictCursor,
                charset="utf8mb4",
                connect_timeout=30,
            )
        except OperationalError as error:
            raise ToolsError(300, "数据库连接失败，请检查数据库配置") from error
        except InternalError as error:
            raise ToolsError(300, f"数据库 {self.config.database} 不存在或无法访问") from error

    def get_connection(self):
        with self._lock:
            try:
                connection = self._pool.get_nowait()
                if self._is_connection_valid(connection):
                    return connection
                connection.close()
                return self._create_connection()
            except Empty:
                if self._created_connections < self.pool_size:
                    connection = self._create_connection()
                    self._created_connections += 1
                    return connection
                return self._create_overflow_connection()

    def _create_overflow_connection(self):
        with self._overflow_lock:
            if self._overflow_count >= self.max_overflow:
                raise ToolsError(300, "数据库连接池已满，无法创建更多连接")
            connection = self._create_connection()
            self._overflow_connections.add(connection)
            self._overflow_count += 1
            return connection

    def put_connection(self, connection):
        if connection is None:
            return
        with self._lock:
            try:
                if connection in self._overflow_connections:
                    with self._overflow_lock:
                        self._overflow_connections.remove(connection)
                        self._overflow_count -= 1
                    connection.close()
                    return
                if self._is_connection_valid(connection):
                    try:
                        self._pool.put(connection, timeout=1.0)
                    except Full:
                        connection.close()
                else:
                    connection.close()
                    new_connection = self._create_connection()
                    try:
                        self._pool.put(new_connection, timeout=1.0)
                    except Full:
                        new_connection.close()
            except Exception:
                try:
                    connection.close()
                except Exception:
                    pass

    @staticmethod
    def _is_connection_valid(connection) -> bool:
        if not connection or not connection.open:
            return False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def close_all(self):
        with self._lock:
            while not self._pool.empty():
                try:
                    self._pool.get_nowait().close()
                except Exception:
                    pass
            with self._overflow_lock:
                for connection in self._overflow_connections.copy():
                    try:
                        connection.close()
                    except Exception:
                        pass
                self._overflow_connections.clear()
                self._overflow_count = 0
                self._created_connections = 0


class MysqlConnection(DatabaseConnection):
    def __init__(self, config: DatabaseConnectionConfig, allow_query: bool = True, allow_write: bool = False):
        super().__init__(allow_query, allow_write)
        self.pool = MysqlConnectionPool(config)
        self._local = threading.local()
        self._active_connections = set()
        self._active_lock = threading.Lock()

    def _get_connection(self):
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = self.pool.get_connection()
            with self._active_lock:
                self._active_connections.add(self._local.connection)
        return self._local.connection

    def execute(self, sql: str):
        connection = self._get_connection()
        for attempt in range(self.pool.retry_attempts):
            try:
                with connection.cursor() as cursor:
                    if SqlPermissionGuard.is_query(sql):
                        cursor.execute(sql)
                        return self.convert_datetime_to_string(cursor.fetchall())
                    cursor.execute(sql)
                    return cursor.rowcount
            except ProgrammingError as error:
                raise ToolsError(300, f"SQL执行失败：{sql}，错误：{error}") from error
            except InternalError as error:
                raise ToolsError(300, f"SQL执行失败：{error}") from error
            except OperationalError as error:
                if "Lost connection" in str(error) or "MySQL server has gone away" in str(error):
                    if attempt < self.pool.retry_attempts - 1:
                        self.close()
                        connection = self._get_connection()
                        time.sleep(self.pool.retry_delay)
                        continue
                raise ToolsError(300, f"SQL执行失败：{sql}，错误：{error}") from error
            except Exception as error:
                if attempt < self.pool.retry_attempts - 1:
                    time.sleep(self.pool.retry_delay)
                    continue
                raise ToolsError(300, f"SQL执行失败：{sql}，错误：{error}") from error

    def close(self) -> None:
        if hasattr(self._local, "connection") and self._local.connection:
            connection = self._local.connection
            with self._active_lock:
                self._active_connections.discard(connection)
            self.pool.put_connection(connection)
            self._local.connection = None

    def close_all(self) -> None:
        self.close()
        with self._active_lock:
            for connection in list(self._active_connections):
                try:
                    connection.close()
                except Exception:
                    pass
            self._active_connections.clear()
        self.pool.close_all()

    def __del__(self):
        try:
            self.close_all()
        except Exception:
            pass


class SQLiteConnection(DatabaseConnection):
    def __init__(self, database_path: str, allow_query: bool = True, allow_write: bool = False):
        super().__init__(allow_query, allow_write)
        self.database_path = database_path
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql: str):
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            if SqlPermissionGuard.is_query(sql):
                rows = cursor.fetchall()
                return self.convert_datetime_to_string([dict(row) for row in rows])
            self.connection.commit()
            return cursor.rowcount
        except sqlite3.Error as error:
            raise ToolsError(300, f"SQLite执行失败：{sql}，错误：{error}") from error

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def close_all(self) -> None:
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class DatabaseConnectionFactory:
    @classmethod
    def build_config(cls, database: Database) -> DatabaseConnectionConfig:
        host = MYSQL_IP if database.host == "db" else database.host
        return DatabaseConnectionConfig(
            host=host or "",
            port=database.port or 0,
            user=database.user or "",
            password=database.password,
            database=database.name,
        )

    @classmethod
    def create(cls, database: Database, test_object: TestObject) -> DatabaseConnection:
        allow_query = test_object.db_c_status == StatusEnum.SUCCESS.value
        allow_write = test_object.db_rud_status == StatusEnum.SUCCESS.value
        if database.db_type == DatabaseTypeEnum.MYSQL.value:
            return MysqlConnection(cls.build_config(database), allow_query=allow_query, allow_write=allow_write)
        if database.db_type == DatabaseTypeEnum.SQLITE.value:
            return SQLiteConnection(database.name, allow_query=allow_query, allow_write=allow_write)
        db_type_name = DatabaseTypeEnum.obj().get(database.db_type, database.db_type)
        raise ToolsError(300, f"暂不支持该数据库类型：{db_type_name}")
