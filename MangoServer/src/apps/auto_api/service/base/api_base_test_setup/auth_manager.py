# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API授权Token缓存与刷新

import time
import traceback
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from src.apps.auto_api.models import ApiAuthConfig
from src.common.enums.api_enum import ApiAuthRefreshModeEnum, ApiAuthRefreshStatusEnum, ApiAuthTypeEnum
from src.common.enums.tools_enum import StatusEnum
from src.common.exceptions import ApiError
from src.common.tools.log_collector import log


@dataclass
class ApiAuthContext:
    test_data: Any
    test_env: int
    project_product_id: int
    test_object: Any = None
    mysql_connect: Any = None


class ApiAuthManager:
    """API授权Token加载和刷新。"""

    LOCK_TIMEOUT_SECONDS = 30
    LOCK_WAIT_SECONDS = 5

    def __init__(self, test_setup=None):
        self.test_setup = test_setup

    @classmethod
    def load(cls, project_product_id: int, test_env: int, test_setup):
        configs = ApiAuthConfig.objects.filter(
            project_product_id=project_product_id,
            test_env=test_env,
            status=StatusEnum.SUCCESS.value,
        ).order_by('id')
        manager = cls(test_setup)
        for config in configs:
            manager.load_config(config)

    def load_config(self, config: ApiAuthConfig):
        if self._is_cache_available(config):
            self.inject_cache(config)
            return
        if config.refresh_mode == ApiAuthRefreshModeEnum.MANUAL.value:
            raise ApiError(300, f'API授权缓存不可用，请手动刷新：{config.name}')
        self.refresh(config.id, self.test_setup, force=False, raise_error=True)
        config.refresh_from_db()
        if self._is_cache_available(config, allow_refresh_window=True):
            self.inject_cache(config)
            return
        raise ApiError(300, f'API授权Token刷新失败：{config.last_refresh_error or config.name}')

    @classmethod
    def refresh(cls, config_id: int, test_setup=None, force: bool = False, raise_error: bool = False) -> dict:
        manager = cls(test_setup)
        config = ApiAuthConfig.objects.get(id=config_id)
        if not force and manager._is_cache_available(config):
            manager.inject_cache(config)
            return manager.preview(config_id)

        if not manager._acquire_lock(config_id):
            config = manager._wait_for_refresh(config_id)
            if manager._is_cache_available(config, allow_refresh_window=True):
                manager.inject_cache(config)
                return manager.preview(config_id)
            if raise_error:
                raise ApiError(300, f'API授权Token刷新等待超时：{config.name}')
            return manager.preview(config_id)

        try:
            config = ApiAuthConfig.objects.get(id=config_id)
            if not force and manager._is_cache_available(config):
                manager.inject_cache(config)
                return manager.preview(config_id)
            cache_data = manager._refresh_cache_data(config)
            now = timezone.now()
            config.cache_data = cache_data
            config.expires_at = now + timedelta(minutes=config.token_ttl)
            config.last_refresh_time = now
            config.last_refresh_status = ApiAuthRefreshStatusEnum.SUCCESS.value
            config.last_refresh_error = None
            config.refreshing = False
            config.refresh_lock_until = None
            config.save(update_fields=[
                'cache_data',
                'expires_at',
                'last_refresh_time',
                'last_refresh_status',
                'last_refresh_error',
                'refreshing',
                'refresh_lock_until',
                'update_time',
            ])
            manager.inject_cache(config)
            return manager.preview(config_id)
        except Exception as error:
            error_msg = getattr(error, 'msg', str(error))
            log.api.error(f'API授权Token刷新失败，config_id={config_id}，错误：{error_msg}')
            log.api.debug(traceback.format_exc())
            ApiAuthConfig.objects.filter(id=config_id).update(
                last_refresh_time=timezone.now(),
                last_refresh_status=ApiAuthRefreshStatusEnum.FAIL.value,
                last_refresh_error=error_msg,
                refreshing=False,
                refresh_lock_until=None,
            )
            if raise_error:
                if isinstance(error, ApiError):
                    raise error
                raise ApiError(300, f'API授权Token刷新失败：{error_msg}')
            return manager.preview(config_id)
        finally:
            ApiAuthConfig.objects.filter(
                id=config_id,
                refreshing=True,
                refresh_lock_until__lte=timezone.now(),
            ).update(refreshing=False, refresh_lock_until=None)

    @classmethod
    def clear(cls, config_id: int):
        ApiAuthConfig.objects.filter(id=config_id).update(
            cache_data={},
            expires_at=None,
            last_refresh_error=None,
            refreshing=False,
            refresh_lock_until=None,
        )
        return cls.preview(config_id)

    @classmethod
    def preview(cls, config_id: int) -> dict:
        config = ApiAuthConfig.objects.get(id=config_id)
        now = timezone.now()
        expires_at = config.expires_at
        remaining_minutes = None
        if expires_at:
            remaining_minutes = max(0, int((expires_at - now).total_seconds() / 60))
        return {
            'id': config.id,
            'name': config.name,
            'cache_data': config.cache_data or {},
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else None,
            'remaining_minutes': remaining_minutes,
            'last_refresh_time': config.last_refresh_time.strftime('%Y-%m-%d %H:%M:%S')
            if config.last_refresh_time else None,
            'last_refresh_status': config.last_refresh_status,
            'last_refresh_error': config.last_refresh_error,
            'refreshing': config.refreshing,
        }

    def inject_cache(self, config: ApiAuthConfig):
        if not self.test_setup:
            return
        for key, value in (config.cache_data or {}).items():
            self.test_setup.test_data.set_cache(key, value)

    def _refresh_cache_data(self, config: ApiAuthConfig) -> dict:
        self._validate_config(config)
        if config.auth_type == ApiAuthTypeEnum.API.value:
            return self._refresh_by_api(config)
        if config.auth_type == ApiAuthTypeEnum.CUSTOM.value:
            return self._refresh_by_custom(config)
        raise ApiError(300, f'不支持的授权方式：{config.auth_type}')

    def _refresh_by_api(self, config: ApiAuthConfig) -> dict:
        test_setup = self._get_or_create_test_setup()
        test_setup.init_test_object(config.project_product_id, config.test_env)
        old_skip_auth_load = getattr(test_setup, 'skip_auth_load', False)
        test_setup.skip_auth_load = True
        try:
            test_setup.init_public(config.project_product_id, config.test_env)
            before_cache = dict(test_setup.test_data.get_all())
            response = test_setup.api_request(config.api_info_id, config.test_env)
            after_cache = test_setup.test_data.get_all()
        finally:
            test_setup.skip_auth_load = old_skip_auth_load
        declared_cache = self._collect_declared_api_cache_data(config, test_setup, after_cache, response)
        return self._collect_changed_cache_data(before_cache, after_cache, declared_cache)

    def _refresh_by_custom(self, config: ApiAuthConfig) -> dict:
        test_setup = self._get_or_create_test_setup()
        test_setup.init_test_object(config.project_product_id, config.test_env)
        old_skip_auth_load = getattr(test_setup, 'skip_auth_load', False)
        test_setup.skip_auth_load = True
        try:
            test_setup.init_public(config.project_product_id, config.test_env)
        finally:
            test_setup.skip_auth_load = old_skip_auth_load
        context = ApiAuthContext(
            test_data=test_setup.test_data,
            test_env=config.test_env,
            project_product_id=config.project_product_id,
            test_object=test_setup.test_object,
            mysql_connect=test_setup.mysql_connect,
        )
        namespace = {}
        exec(config.custom_code, namespace)
        auth_func = namespace.get('auth')
        if not callable(auth_func):
            raise ApiError(300, '自定义授权代码必须定义 auth(context) 函数')
        result = auth_func(context)
        if not isinstance(result, dict):
            raise ApiError(300, '自定义授权代码 auth(context) 必须返回 dict')
        return self._collect_cache_data(result)

    def _collect_cache_data(self, data: dict) -> dict:
        if not data:
            raise ApiError(300, '授权数据为空，请检查登录接口后置提取或自定义代码返回值')
        cache_data = {key: value for key, value in data.items() if value is not None}
        if not cache_data:
            raise ApiError(300, '授权数据为空，请检查登录接口后置提取或自定义代码返回值')
        return cache_data

    def _collect_changed_cache_data(self, before_cache: dict, after_cache: dict, declared_cache: dict) -> dict:
        cache_data = {
            key: value
            for key, value in after_cache.items()
            if value is not None and before_cache.get(key) != value
        }
        cache_data.update(declared_cache)
        return self._collect_cache_data(cache_data)

    def _collect_declared_api_cache_data(self, config: ApiAuthConfig, test_setup, after_cache: dict, response) -> dict:
        cache_data = {}
        api_info = config.api_info
        for item in (api_info.posterior_json_path or []) + (api_info.posterior_re or []):
            key = test_setup.test_data.replace(item.get('key'))
            if key and key.startswith('$.') and response and response.json is not None:
                key = test_setup.test_data.get_json_path_value(response.json, key)
            if key in after_cache and after_cache.get(key) is not None:
                cache_data[key] = after_cache.get(key)
        if api_info.posterior_file and api_info.posterior_file in after_cache:
            cache_data[api_info.posterior_file] = after_cache.get(api_info.posterior_file)
        return cache_data

    def _get_or_create_test_setup(self):
        if self.test_setup:
            return self.test_setup
        from src.apps.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
        self.test_setup = APIBaseTestSetup()
        return self.test_setup

    @staticmethod
    def _validate_config(config: ApiAuthConfig):
        if config.token_ttl <= 0:
            raise ApiError(300, 'Token有效期必须大于0')
        if config.refresh_margin < 0:
            raise ApiError(300, '提前刷新时间不能小于0')
        if config.refresh_margin >= config.token_ttl:
            raise ApiError(300, '提前刷新时间必须小于Token有效期')
        if config.auth_type == ApiAuthTypeEnum.API.value and not config.api_info_id:
            raise ApiError(300, '接口登录授权必须选择登录接口')
        if config.auth_type == ApiAuthTypeEnum.CUSTOM.value and not config.custom_code:
            raise ApiError(300, '自定义代码授权必须填写代码')

    def _is_cache_available(self, config: ApiAuthConfig, allow_refresh_window: bool = False) -> bool:
        if not config.cache_data or not config.expires_at:
            return False
        compare_time = timezone.now()
        if not allow_refresh_window:
            compare_time += timedelta(minutes=config.refresh_margin)
        return config.expires_at > compare_time

    @classmethod
    def _acquire_lock(cls, config_id: int) -> bool:
        now = timezone.now()
        lock_until = now + timedelta(seconds=cls.LOCK_TIMEOUT_SECONDS)
        with transaction.atomic():
            config = ApiAuthConfig.objects.select_for_update().get(id=config_id)
            if config.refreshing and config.refresh_lock_until and config.refresh_lock_until > now:
                return False
            config.refreshing = True
            config.refresh_lock_until = lock_until
            config.save(update_fields=['refreshing', 'refresh_lock_until', 'update_time'])
            return True

    @classmethod
    def _wait_for_refresh(cls, config_id: int) -> ApiAuthConfig:
        end_time = time.time() + cls.LOCK_WAIT_SECONDS
        config = ApiAuthConfig.objects.get(id=config_id)
        while time.time() < end_time:
            time.sleep(0.3)
            config.refresh_from_db()
            if not config.refreshing:
                return config
        return config

    @classmethod
    def refresh_by_time_task(cls, time_task_id: int):
        configs = ApiAuthConfig.objects.filter(
            status=StatusEnum.SUCCESS.value,
            time_task_id=time_task_id,
            refresh_mode__in=[ApiAuthRefreshModeEnum.TIMING.value, ApiAuthRefreshModeEnum.BOTH.value],
        )
        for config in configs:
            cls.refresh(config.id, force=False, raise_error=False)
