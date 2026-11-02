# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
from django.apps import AppConfig


class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.system'
    # Django 的 app label 同时是历史迁移图和 django_migrations 的持久标识。
    # 代码包已统一为 system，但该标识不能随目录重构改名，否则已有环境无法加载迁移图。
    label = 'auto_system'

    def ready(self):
        from src.common.prompts import checks  # noqa: F401
        from src.common.database.model_metadata import apply_database_comments

        apply_database_comments()

    @staticmethod
    def save_cache():
        from src.apps.system.services.system_initialization import SystemInitializationService
        return SystemInitializationService.save_cache()

    @staticmethod
    def populate_time_tasks():
        from src.apps.system.services.system_initialization import SystemInitializationService
        return SystemInitializationService.populate_time_tasks()

    def shutdown(self):
        pass

    def init_ass(self):
        from src.apps.system.services.system_initialization import SystemInitializationService
        return SystemInitializationService.init_ass()
