# -*- coding: utf-8 -*-
from django.db import connection

from src.common.tools.log_collector import log


def _is_mysql_connection() -> bool:
    return connection.vendor == 'mysql'


def acquire_mysql_lock(name: str, timeout: int = 0) -> bool:
    if not _is_mysql_connection():
        log.system.warning(f'当前数据库不是MySQL，跳过MySQL分布式锁：{name}')
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT GET_LOCK(%s, %s)', [name, timeout])
            row = cursor.fetchone()
        return bool(row and row[0] == 1)
    except Exception as error:
        log.system.error(f'获取MySQL分布式锁失败：{name}，异常：{error}')
        return False


def release_mysql_lock(name: str) -> bool:
    if not _is_mysql_connection():
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT RELEASE_LOCK(%s)', [name])
            row = cursor.fetchone()
        return bool(row and row[0] == 1)
    except Exception as error:
        log.system.error(f'释放MySQL分布式锁失败：{name}，异常：{error}')
        return False
