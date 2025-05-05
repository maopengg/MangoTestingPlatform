# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-05-04 20:34
# @Author : 毛鹏
from mangokit.data_processor import SqlCache
from mangokit.enums import CacheValueTypeEnum

from src.enums.tools_enum import CacheKeyEnum
from src.tools import project_dir


class SetConfig:

    @classmethod
    def _generate_methods(cls):
        for key in CacheKeyEnum:
            set_method_name = f"set_{key.value.lower()}"
            get_method_name = f"get_{key.value.lower()}"

            @staticmethod
            def set_method(value, k=key.value):
                value_type = CacheKeyEnum.obj().get(k, CacheValueTypeEnum.STR)
                SqlCache(project_dir.cache_file()).set_sql_cache(k, value, value_type)

            setattr(cls, set_method_name, set_method)

            @staticmethod
            def get_method(k=key.value):
                return SqlCache(project_dir.cache_file()).get_sql_cache(k)

            setattr(cls, get_method_name, get_method)
        if not cls.get_web_parallel():  # type: ignore
            cls.set_web_parallel(2)  # type: ignore
        if not cls.get_web_type():  # type: ignore
            cls.set_web_type(0)  # type: ignore


SetConfig._generate_methods()
