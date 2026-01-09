# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 监控基类，提供MySQL连接管理和日志输出功能
# @Time   : 2025-01-09
# @Author : 毛鹏
import json
import atexit
import pymysql
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class MonitorBase(ABC):
    """监控基类，提供MySQL连接管理和日志输出功能"""

    def __init__(self, mysql_config: Optional[Dict[str, Any]] = None, task_id: Optional[int] = None):
        """
        初始化监控基类

        Args:
            mysql_config: MySQL配置字典（可选），包含host, port, user, password, database等
                         如果不提供，则不初始化数据库连接
            task_id: 监控任务ID（可选），从命令行参数传入，用于记录日志到数据库
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
                autocommit=True  # 自动提交事务
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
        执行数据库查询

        Args:
            sql: SQL查询语句
            params: 查询参数

        Returns:
            查询结果字典或None
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
            # 尝试重新连接
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

        Args:
            sql: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表
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

    def log(self, message: str, level: str = "INFO"):
        """
        日志输出方法，自动添加时间戳，并尝试写入 MonitoringReport 表

        注意：
            - 为了保证此基类可以被抽离到独立库中，所有与 Django 相关的导入
              和写入逻辑都放在函数内部，并使用 try 包裹，失败时仅打印日志。
        
        Args:
            message: 日志消息
            level: 日志级别 (INFO, ERROR, WARNING, DEBUG)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_text = f"[{timestamp}] [{level}] {message}"
        # 永远保证控制台可见
        print(log_text)

        # 尝试写入 Django 的 MonitoringReport 表（失败时静默降级）
        try:
            # 这里的导入放在函数内部，避免在无 Django 环境下报错
            from src.auto_test.monitoring.models import MonitoringReport
            from src.enums.monitoring_enum import MonitoringLogStatusEnum

            # 如果没有 task_id，则不写入数据库（支持在项目外运行脚本）
            if not self.task_id:
                return

            # 将日志级别映射到 MonitoringLogStatusEnum
            level_upper = (level or "INFO").upper()
            level_map = {
                "INFO": MonitoringLogStatusEnum.INFO.value,
                "ERROR": MonitoringLogStatusEnum.ERROR.value,
                "WARNING": MonitoringLogStatusEnum.WARNING.value,
                "DEBUG": MonitoringLogStatusEnum.DEBUG.value,
            }
            status = level_map.get(level_upper, MonitoringLogStatusEnum.INFO.value)

            # 写入 MonitoringReport 表
            MonitoringReport.objects.create(
                task_id=self.task_id,
                status=status,
                msg=message,
                send_text=log_text,
            )
        except Exception:
            # 任何失败都不影响脚本运行；在非项目环境中打印提示，便于测试
            print(f"当前不在项目内，测试log方法成功！写入内容：{message}")

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
        写入一条“失败”状态的监控报告日志

        说明：
            - 默认按失败状态写入（ERROR）
            - 需要传入 send_text，msg 为可选说明
            - 为保证此基类可抽离到独立库中，所有 Django 相关导入和写入逻辑
              都放在函数内部并使用 try 包裹，失败时仅打印日志。

        Args:
            send_text: 详细信息（必填，将写入 MonitoringReport.send_text）
            msg: 简要消息（可选，将写入 MonitoringReport.msg）
        """
        # 简要消息（用于写入 MonitoringReport.msg）
        base_msg = msg if msg else "监控任务失败"

        # 尝试写入 Django 的 MonitoringReport 表（失败时静默降级）
        try:
            from src.auto_test.monitoring.models import MonitoringReport, MonitoringTask
            from src.auto_test.auto_system.service.notice import NoticeMain
            from src.enums.monitoring_enum import MonitoringLogStatusEnum
            from src.enums.tools_enum import StatusEnum

            # 如果没有 task_id，则不写入数据库（支持在项目外运行脚本）
            if not self.task_id:
                return
            
            task = MonitoringTask.objects.get(id=self.task_id)
            if task.notice_group_id is not None:
                NoticeMain.notice_monitoring(task.notice_group_id, send_text)
            MonitoringReport.objects.create(
                task_id=self.task_id,
                status=MonitoringLogStatusEnum.ERROR.value,  # 失败状态
                msg=base_msg,
                send_text=send_text,
                is_notice=StatusEnum.SUCCESS.value,
            )
        except Exception:
            # 任何失败都不影响脚本运行；在非项目环境中打印提示，便于测试
            print(f"当前不在项目内，测试send方法成功！发送内容：{send_text}")

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


# 使用示例：创建不需要MySQL的监控类
"""
class SimpleMonitor(MonitorBase):
    def __init__(self):
        # 不传入mysql_config，只使用日志和API功能
        super().__init__()

    def run(self):
        while True:
            self.log("简单的监控任务正在运行...")
            # 这里可以只使用API请求和日志功能，不使用数据库
            result = self.handle_api_request("https://api.example.com/status")
            if result:
                self.log(f"API响应: {result}")
            time.sleep(60)

# 使用方式
if __name__ == '__main__':
    monitor = SimpleMonitor()  # 不需要MySQL配置
    monitor.start_monitoring()
"""

# 邮件发送使用示例
"""
# 1. 使用默认配置发送邮件
monitor.send_email(
    content="监控报警：发现异常情况！",
    receivers=['admin@example.com', 'dev@example.com']
)

# 2. 自定义所有参数发送邮件
monitor.send_email(
    content="自定义邮件内容",
    receivers=['user@example.com'],
    sender_email='custom@example.com',
    sender_name='自定义发送者',
    subject='自定义主题',
    smtp_server='smtp.custom.com',
    smtp_port=587,
    smtp_password='custom_password'
)

# 3. 只自定义主题和接收者
monitor.send_email(
    content="报警内容",
    receivers=['alert@example.com'],
    subject='紧急报警'
)
"""
