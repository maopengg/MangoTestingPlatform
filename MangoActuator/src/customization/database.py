# -*- coding: utf-8 -*-
from mangotools.database import (
    DatabaseConnection,
    database_driver_info,
    get_database_driver_info,
    register_database_driver,
)


class ObtainDatabase:
    """自定义数据库驱动注册入口；执行器不创建业务数据库连接。"""

    @staticmethod
    def register(db_type: int | str, label: str, connection_class: type[DatabaseConnection], sort: int = -1):
        return register_database_driver(db_type, label, connection_class, sort)

    @staticmethod
    def get_driver_info() -> list[dict]:
        return get_database_driver_info()
