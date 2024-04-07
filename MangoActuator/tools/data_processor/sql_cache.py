# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-08-30 14:20
# @Author : 毛鹏
from enums.tools_enum import CacheValueTypeEnum
from tools.database.sql_statement import sql_statement_5, sql_statement_6, sql_statement_4
from tools.database.sqlite_connect import SQLiteConnect


class SqlCache:
    """ 文件缓存 """

    @classmethod
    def get_sql_cache(cls, key: str) -> str | list | dict | int | None:
        """
        获取缓存中指定键的值
        :param key: 缓存键
        :return:
        """
        res = SQLiteConnect().execute_sql(sql_statement_5, (key,))
        if res:
            res = res[0]
        else:
            return None
        if res.get('type') == CacheValueTypeEnum.STR.value:
            return res.get('value')
        elif res.get('type') == CacheValueTypeEnum.INT.value:
            return int(res.get('value'))

    @classmethod
    def set_sql_cache(cls, key: str, value: str | list | dict, value_type: CacheValueTypeEnum = 0) -> None:
        """
        设置缓存键的值
        :param key: 缓存键
        :param value: 缓存值
        :param value_type: 值类型
        :return:
        """
        res2 = SQLiteConnect().execute_sql(sql_statement_5, (key,))
        if res2:
            SQLiteConnect().execute_sql(sql_statement_6, (key,))
        SQLiteConnect().execute_sql(sql_statement_4, (key, value, value_type))

    @classmethod
    def delete_persistent_cache(cls, key: str) -> None:
        """
        删除缓存中指定键的值
        :param key: 缓存键
        :return:
        """
        cls.cache.delete(key)

    @classmethod
    def contains_persistent_cache(cls, key: str) -> bool:
        """
        检查缓存中是否包含指定键
        :param key: 缓存键
        :return: 如果缓存中包含指定键，返回True；否则返回False
        """
        return key in cls.cache

    @classmethod
    def clear_persistent_cache(cls) -> None:
        """
        清空缓存中的所有键值对
        :return:
        """
        cls.cache.clear()
