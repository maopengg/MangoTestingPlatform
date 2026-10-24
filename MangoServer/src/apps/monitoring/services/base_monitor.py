# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 监控基类，提供MySQL连接管理和日志输出功能
# @Time   : 2025-01-09
# @Author : 毛鹏
from datetime import datetime

from mangotools.monitoring import MonitorBase as Mb

from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.monitoring.enums import MonitoringLogStatusEnum
from src.apps.monitoring.models import MonitoringReport
from src.apps.monitoring.services.environment_context import MonitoringEnvironmentContextService
from src.apps.test_center.services.test_suite.send_notice import SendNotice
from src.common.decorators.retry import async_task_db_connection


class MonitorBase(Mb):
    """监控基类"""

    def __init__(self, mysql_config=None, task_id=None):
        super().__init__(mysql_config=mysql_config, task_id=task_id)
        self.test_env = None
        self.test_env_name = None
        self.test_config = None
        self.domain = None
        self.domains = {}
        self.database_configs = {}
        self.databases = self.database_configs
        self._project_product_id = None
        self._load_environment_context()

    def _load_environment_context(self):
        if not self.task_id:
            return
        from src.apps.monitoring.models import MonitoringTask

        task = MonitoringTask.objects.only(
            'id', 'project_product_id', 'test_env'
        ).filter(id=self.task_id).first()
        if task is None:
            return
        context = MonitoringEnvironmentContextService.build(task)
        if context is None:
            return
        self._project_product_id = task.project_product_id
        self.test_config = context
        self.test_env = context['test_env']
        self.test_env_name = context['test_env_name']
        self.domain = context['domain']
        self.domains = context['domains']
        self.database_configs = context['databases']
        self.databases = self.database_configs

    def get_database_config(self, alias: str | None = None) -> dict | None:
        """按逻辑数据库名称获取配置；只有一个数据库时可省略 alias。"""
        if alias:
            return self.database_configs.get(alias)
        if len(self.database_configs) == 1:
            return next(iter(self.database_configs.values()))
        return None

    def get_database_connection(self, alias: str | None = None):
        """获取带平台读写权限校验的数据库连接；调用完成后需要 close。"""
        config = self.get_database_config(alias)
        if config is None or self.test_env is None or self._project_product_id is None:
            return None

        from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver
        from src.apps.test_center.services.database_connection import DatabaseConnectionFactory

        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            config['alias_id'],
            self._project_product_id,
            self.test_env,
        )
        return DatabaseConnectionFactory.create(
            DatasourceTargetService.resolve(binding),
            allow_query=config['can_query'],
            allow_write=config['can_write'],
        )

    @async_task_db_connection
    def run(self):
        pass

    def log(self, message: str, level: str = "INFO"):
        """
        日志输出方法
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_text = f"[{timestamp}] [{level}] {message}"
        print(log_text)

        if not self.task_id or level == "INFO":
            return

        level_upper = (level or "INFO").upper()
        level_map = {
            "INFO": MonitoringLogStatusEnum.INFO.value,
            "ERROR": MonitoringLogStatusEnum.ERROR.value,
            "WARNING": MonitoringLogStatusEnum.WARNING.value,
            "DEBUG": MonitoringLogStatusEnum.DEBUG.value,
        }
        status = level_map.get(level_upper, MonitoringLogStatusEnum.INFO.value)
        from django.db import connection
        try:
            connection.close()
            MonitoringReport.objects.create(
                task_id=self.task_id,
                status=status,
                msg=message,
                send_text=log_text,
            )
        except Exception as e:
            self.log(f"监控任务日志失败: {e}")
        finally:
            connection.close()

    def send(self, send_text: str, msg: str = None):
        """
        发送通知
        """
        base_msg = msg if msg else "监控任务失败"
        self.log(f'准备发送消息：{self.task_id}，{base_msg}，{send_text}')

        if not self.task_id:
            return

        SendNotice.send_monitoring(self.task_id, send_text, base_msg)
