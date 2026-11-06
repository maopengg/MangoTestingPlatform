from django.db import connections

from src.apps.system.models import CacheData


class ConfigurationSelector:
    @staticmethod
    def shared_locked_value(key, using):
        """调用方必须持有短事务；共享锁允许不同实例并发准入，配置保存使用排他锁。"""
        connection = connections[using]
        table = connection.ops.quote_name(CacheData._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT value, value_type FROM {table} WHERE `key` = %s LOCK IN SHARE MODE', [key])
            return cursor.fetchone()
