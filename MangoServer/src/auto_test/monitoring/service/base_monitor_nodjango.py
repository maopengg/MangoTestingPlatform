# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 监控基类（纯净版，无任何 Django 依赖），可直接拷贝到第三方库使用
# @Time   : 2025-01-09
# @Author : 毛鹏

import atexit
import pymysql
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class MonitorBase(ABC):
    """
    监控基类（纯净版），仅包含：
        - MySQL 连接管理
        - 基础日志输出（print）

    不依赖 Django / settings / ORM 等任何框架代码，
    方便直接复制到第三方库（如 mangotools）中复用。
    """

    def __init__(self, mysql_config: Optional[Dict[str, Any]] = None, task_id: Optional[int] = None):
        """
        初始化监控基类

        Args:
            mysql_config: MySQL配置字典（可选），包含host, port, user, password, database等
                         如果不提供，则不初始化数据库连接
            task_id: 监控任务ID（可选），这里只是一个普通属性，方便你在脚本中自行使用
        """
        self.mysql_config = mysql_config
        self._db_connection = None
        self.task_id = task_id

        # 如果没有显式传入 task_id，尝试从命令行参数读取
        if self.task_id is None:
            import sys
            if len(sys.argv) > 1:
                try:
                    self.task_id = int(sys.argv[1])
                except (ValueError, IndexError):
                    pass

        if mysql_config:
            self._setup_mysql_connection()

    # ===== MySQL 相关 =====
    def _setup_mysql_connection(self):
        """设置MySQL连接"""
        if self._db_connection is None or (hasattr(self._db_connection, 'open') and not self._db_connection.open):
            self._db_connection = pymysql.connect(
                host=self.mysql_config['host'],
                port=self.mysql_config['port'],
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                database=self.mysql_config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,  # 自动提交事务
            )
            self.log("数据库连接已创建")

        # 注册退出时关闭数据库连接
        atexit.register(self._close_db_connection)

    def _close_db_connection(self):
        """关闭数据库连接"""
        if self._db_connection and self._db_connection.open:
            self._db_connection.close()
            self.log("数据库连接已关闭")

    def ensure_connection(self):
        """确保数据库连接有效"""
        if not self.mysql_config:
            raise RuntimeError("MySQL配置未提供，无法确保数据库连接")
        if not self._db_connection or not self._db_connection.open:
            self.log("数据库连接已断开，重新连接...")
            self._setup_mysql_connection()

    def get_db_connection(self):
        """获取数据库连接"""
        if not self.mysql_config:
            raise RuntimeError("MySQL配置未提供，无法获取数据库连接")
        self.ensure_connection()
        return self._db_connection

    def execute_query(self, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        执行数据库查询，返回单条记录
        """
        if not self.mysql_config:
            self.log_warning("MySQL配置未提供，跳过数据库查询")
            return None

        try:
            self.ensure_connection()
            with self._db_connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                result = cursor.fetchone()
                return result
        except pymysql.Error as e:
            self.log_error(f"数据库查询错误: {e}")
            # 尝试重新连接一次
            try:
                self._setup_mysql_connection()
                with self._db_connection.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    result = cursor.fetchone()
                    return result
            except Exception as retry_error:
                self.log_error(f"重试查询也失败: {retry_error}")
                return None
        except Exception as e:
            self.log_error(f"执行查询时发生其他错误: {e}")
            return None

    def execute_query_many(self, sql: str, params: tuple = None) -> list:
        """
        执行查询返回多条记录
        """
        if not self.mysql_config:
            self.log_warning("MySQL配置未提供，跳过数据库批量查询")
            return []

        try:
            self.ensure_connection()
            with self._db_connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                results = cursor.fetchall()
                return results or []
        except pymysql.Error as e:
            self.log_error(f"数据库批量查询错误: {e}")
            return []
        except Exception as e:
            self.log_error(f"执行批量查询时发生其他错误: {e}")
            return []

    # ===== 日志相关（纯 print，不依赖任何框架） =====
    def log(self, message: str, level: str = "INFO"):
        """
        基础日志输出方法，自动添加时间戳

        这里不做任何数据库/框架写入，仅 print，方便在任意环境使用。
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_text = f"[{timestamp}] [{level}] {message}"
        print(log_text)

    def log_error(self, message: str):
        """错误日志"""
        self.log(message, "ERROR")

    def log_warning(self, message: str):
        """警告日志"""
        self.log(message, "WARNING")

    def log_debug(self, message: str):
        """调试日志"""
        self.log(message, "DEBUG")

    def send(self, send_text: str, msg: str = None):
        """
        通知方法（纯文本版）

        在纯净版中，不做任何数据库 / 邮件 / 企业微信 等发送逻辑，
        仅统一以一条 ERROR 级别日志的形式打印出来，方便你在第三方库中自己扩展。
        """
        base_msg = msg if msg else "监控任务通知"
        self.log_error(f"{base_msg} | send_text={send_text}")

    # ===== 业务入口 =====
    @abstractmethod
    def run(self):
        """运行监控的主要逻辑，由子类实现"""
        pass

    def start_monitoring(self):
        """启动监控服务"""
        self.log("开始启动监控服务...")
        try:
            self.run()
        except KeyboardInterrupt:
            self.log_warning("收到中断信号，正在退出...")
        except Exception as e:
            self.log_error(f"监控服务异常退出: {e}")
        finally:
            # 只有在有MySQL配置时才尝试关闭连接
            if self.mysql_config:
                self._close_db_connection()
            self.log("监控服务已停止")


