# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-05-04 20:34
# @Author : 毛鹏
from mangotools.data_processor import SqlCache
from mangotools.enums import CacheValueTypeEnum

from src.enums.tools_enum import CacheKeyEnum
from src.tools import project_dir


class SetConfig:
    _runtime_password = None

    @classmethod
    def delete_cache(cls, key: str):
        SqlCache(project_dir.cache_file()).delete_sql_cache(key)

    @classmethod
    def get_login_password(cls):
        if cls._runtime_password is not None:
            return cls._runtime_password
        return cls.get_password()  # type: ignore

    @classmethod
    def get_remembered_login(cls) -> tuple[str, str, bool]:
        username = cls.get_remember_username() or cls.get_username() or ''  # type: ignore
        password = cls.get_remember_password() or ''  # type: ignore
        return str(username), str(password), bool(password)

    @classmethod
    def save_login_credentials(cls, username: str, password: str, remember: bool):
        cls.set_username(username)  # type: ignore
        cls.set_remember_username(username)  # type: ignore
        cls._runtime_password = password
        if remember:
            cls.set_password(password)  # type: ignore
            cls.set_remember_password(password)  # type: ignore
            return
        cls.delete_cache(CacheKeyEnum.PASSWORD.value)
        cls.delete_cache(CacheKeyEnum.REMEMBER_PASSWORD.value)

    @classmethod
    def set_open_status(cls, value) -> bool:
        from src.settings import settings

        is_open = bool(value)
        cls.set_is_open(is_open)  # type: ignore
        settings.IS_OPEN = is_open
        return is_open

    @classmethod
    def restore_runtime_settings(cls):
        from src.settings import settings

        cached_is_open = cls.get_is_open()  # type: ignore
        settings.IS_OPEN = True if cached_is_open is None else bool(cached_is_open)

    @classmethod
    def ensure_web_headers_default(cls, default: bool) -> bool:
        cached_value = cls.get_web_headers()  # type: ignore
        if cached_value is None:
            cached_value = bool(default)
            cls.set_web_headers(cached_value)  # type: ignore
        return bool(cached_value)

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
            cls.set_web_parallel(5)  # type: ignore
        if not cls.get_ui_queue_size():  # type: ignore
            cls.set_ui_queue_size(10)  # type: ignore
        if not cls.get_pytest_parallel():  # type: ignore
            cls.set_pytest_parallel(5)  # type: ignore
        if not cls.get_pytest_queue_size():  # type: ignore
            cls.set_pytest_queue_size(10)  # type: ignore
        if not cls.get_web_type():  # type: ignore
            cls.set_web_type(0)  # type: ignore
        if not cls.get_web_static_cache_path():  # type: ignore
            cls.set_web_static_cache_path(project_dir.web_static_cache())  # type: ignore
        if cls.get_web_static_cache_enabled() is None:  # type: ignore
            cls.set_web_static_cache_enabled(True)  # type: ignore
        if cls.get_is_open() is None:  # type: ignore
            cls.set_is_open(True)  # type: ignore
        if not cls.get_ios_appium_url():  # type: ignore
            cls.set_ios_appium_url('http://127.0.0.1:4723')  # type: ignore
        if not cls.get_ios_device_name():  # type: ignore
            cls.set_ios_device_name('iPhone Simulator')  # type: ignore


SetConfig._generate_methods()
