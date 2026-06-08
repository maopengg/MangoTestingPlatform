# -*- coding: utf-8 -*-
import json
from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from mangotools.enums import CacheValueTypeEnum

from src.apps.auto_system.models import CacheData
from src.common.exceptions import SystemEError, ERROR_MSG_0038


CONFIG_GROUP_TITLES = {
    "system": "后端服务设置",
    "email": "邮箱配置",
    "report": "测试报告配置",
    "api": "接口自动化配置",
    "ui": "界面自动化配置",
    "pytest": "单元自动化配置",
    "ai": "AI配置",
    "internal": "系统内部配置",
}


@dataclass(frozen=True)
class SystemConfigDefinition:
    key: str
    describe: str
    group: str
    value_type: int = CacheValueTypeEnum.STR.value
    default_value: Any = None
    required: bool = False
    is_secret: bool = False
    is_public: bool = True
    is_enabled: bool = True
    sort: int = 100
    placeholder: str | None = None

    def default_value_text(self):
        if self.default_value is None:
            return None
        if self.value_type in (CacheValueTypeEnum.DICT.value, CacheValueTypeEnum.JSON.value, CacheValueTypeEnum.LIST.value):
            return json.dumps(self.default_value, ensure_ascii=False)
        return str(self.default_value)


SYSTEM_CONFIG_REGISTRY = [
    SystemConfigDefinition(
        key="SYSTEM_DOMAIN_NAME",
        describe="测试报告地址",
        group="report",
        value_type=CacheValueTypeEnum.STR.value,
        sort=10,
        placeholder="请输入测试报告访问地址",
    ),
    SystemConfigDefinition(
        key="SYSTEM_SEND_USER",
        describe="邮箱发送人",
        group="email",
        value_type=CacheValueTypeEnum.STR.value,
        sort=10,
        placeholder="请输入邮箱发送人",
    ),
    SystemConfigDefinition(
        key="SYSTEM_EMAIL_HOST",
        describe="邮箱域名",
        group="email",
        value_type=CacheValueTypeEnum.STR.value,
        sort=20,
        placeholder="请输入邮箱域名",
    ),
    SystemConfigDefinition(
        key="SYSTEM_STAMP_KET",
        describe="邮箱的stamp_key",
        group="email",
        value_type=CacheValueTypeEnum.STR.value,
        is_secret=True,
        sort=30,
        placeholder="请输入邮箱授权密钥",
    ),
    SystemConfigDefinition(
        key="API_TIMEOUT",
        describe="API请求超时时间",
        group="api",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=15,
        required=True,
        sort=10,
        placeholder="请输入 API 请求超时时间",
    ),
    SystemConfigDefinition(
        key="PYTEST_GIT_URL",
        describe="git仓库地址",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        sort=10,
        placeholder="请输入 Pytest 仓库地址",
    ),
    SystemConfigDefinition(
        key="PYTEST_GIT_USERNAME",
        describe="git账号",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        sort=20,
        placeholder="请输入 Git 账号",
    ),
    SystemConfigDefinition(
        key="PYTEST_GIT_PASSWORD",
        describe="git密码",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        is_secret=True,
        sort=30,
        placeholder="请输入 Git 密码",
    ),
    SystemConfigDefinition(
        key="PYTEST_ACT",
        describe="中间对象（PO模式的pageobject）目录名称",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="abstract",
        is_public=False,
        sort=40,
    ),
    SystemConfigDefinition(
        key="PYTEST_TESTCASE",
        describe="测试用例目录名称",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="test_cases",
        is_public=False,
        sort=50,
    ),
    SystemConfigDefinition(
        key="PYTEST_TOOLS",
        describe="脚本目录名称",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="scripts",
        is_public=False,
        sort=60,
    ),
    SystemConfigDefinition(
        key="PYTEST_UPLOAD",
        describe="上传文件目录名称",
        group="pytest",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="upload",
        is_public=False,
        sort=70,
    ),
    SystemConfigDefinition(
        key="AI_UI_LOCATOR_ENABLED",
        describe="是否开启AI元素定位",
        group="ui",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=0,
        sort=10,
        placeholder="0=关闭，1=开启",
    ),
    SystemConfigDefinition(
        key="AI_PROVIDER_TYPE",
        describe="AI供应商类型",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="openai_compatible",
        sort=5,
        placeholder="openai_compatible/openai/azure_openai/anthropic/gemini",
    ),
    SystemConfigDefinition(
        key="AI_API_KEY",
        describe="AI的APIKey",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        is_secret=True,
        sort=10,
        placeholder="请输入 AI APIKey",
    ),
    SystemConfigDefinition(
        key="AI_BASE_URL",
        describe="AI接口地址(兼容OpenAI格式)",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="https://api.deepseek.com",
        sort=20,
        placeholder="请输入 AI 接口地址",
    ),
    SystemConfigDefinition(
        key="AI_MODEL",
        describe="AI模型名称",
        group="ai",
        value_type=CacheValueTypeEnum.STR.value,
        default_value="deepseek-chat",
        sort=30,
        placeholder="请输入 AI 模型名称",
    ),
    SystemConfigDefinition(
        key="AI_TIMEOUT",
        describe="AI请求超时时间(秒)",
        group="ai",
        value_type=CacheValueTypeEnum.INT.value,
        default_value=60,
        sort=40,
        placeholder="请输入 AI 请求超时时间",
    ),
]


DEPRECATED_SYSTEM_CONFIG_KEYS = {
    "AI_TEMPERATURE",
    "AI_TOP_P",
    "AI_MAX_TOKENS",
    "AI_STREAM",
    "AI_API_VERSION",
    "AI_ORGANIZATION",
    "AI_PROJECT",
    "AI_EXTRA_HEADERS",
    "AI_EXTRA_BODY",
}


SYSTEM_INTERNAL_CONFIG_REGISTRY = [
    SystemConfigDefinition(
        key="select_value",
        describe="执行器操作方法选项",
        group="internal",
        value_type=CacheValueTypeEnum.DICT.value,
        is_public=False,
        sort=10,
    ),
    SystemConfigDefinition(
        key="ass_select_value",
        describe="断言方法选项",
        group="internal",
        value_type=CacheValueTypeEnum.DICT.value,
        is_public=False,
        sort=20,
    ),
]


def get_config_definition_map():
    return {item.key: item for item in [*SYSTEM_CONFIG_REGISTRY, *SYSTEM_INTERNAL_CONFIG_REGISTRY]}


class SystemConfigService:
    @classmethod
    def sync_registered_configs(cls):
        CacheData.objects.filter(key__in=DEPRECATED_SYSTEM_CONFIG_KEYS, is_enabled=True).update(is_enabled=False)
        for item in [*SYSTEM_CONFIG_REGISTRY, *SYSTEM_INTERNAL_CONFIG_REGISTRY]:
            defaults = cls._definition_defaults(item)
            obj, created = CacheData.objects.get_or_create(key=item.key, defaults=defaults)
            if created:
                continue
            changed_fields = []
            for field, value in defaults.items():
                if field == "value":
                    continue
                if getattr(obj, field, None) != value:
                    setattr(obj, field, value)
                    changed_fields.append(field)
            if changed_fields:
                changed_fields.append("update_time")
                obj.save(update_fields=changed_fields)
        cls.normalize_ai_locator_enabled()

    @classmethod
    def normalize_ai_locator_enabled(cls):
        try:
            obj = CacheData.objects.get(key="AI_UI_LOCATOR_ENABLED")
        except CacheData.DoesNotExist:
            return
        if obj.value in (True, "true", "True", "1", 1):
            normalized_value = "1"
        else:
            normalized_value = "0"
        if obj.value != normalized_value:
            obj.value = normalized_value
            obj.save(update_fields=["value", "update_time"])

    @classmethod
    def _definition_defaults(cls, item: SystemConfigDefinition):
        return {
            "describe": item.describe,
            "value": item.default_value_text(),
            "value_type": item.value_type,
            "group": item.group,
            "sort": item.sort,
            "required": item.required,
            "is_enabled": item.is_enabled,
            "is_secret": item.is_secret,
            "is_public": item.is_public,
            "placeholder": item.placeholder,
        }

    @classmethod
    def get_cache_key(cls, key: str):
        return f"cache_data_{key}"

    @classmethod
    def invalidate(cls, key: str):
        cache.delete(cls.get_cache_key(key))

    @classmethod
    def get(cls, key: str, default=None):
        cache_key = cls.get_cache_key(key)
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value
        try:
            cache_data_obj = CacheData.objects.get(key=key)
        except CacheData.DoesNotExist:
            if default is not None:
                return default
            raise SystemEError(*ERROR_MSG_0038)
        value = cls.cast_value(cache_data_obj.value, cache_data_obj.value_type, default)
        if value is not None:
            cache.set(cache_key, value, 300)
        return value

    @classmethod
    def cast_value(cls, value, value_type, default=None):
        if value is None:
            return default
        if value_type == CacheValueTypeEnum.INT.value:
            return int(value)
        if value_type == CacheValueTypeEnum.FLOAT.value:
            return float(value)
        if value_type == CacheValueTypeEnum.BOOL.value:
            return value in (True, "true", "True", "1", 1)
        if value_type in (CacheValueTypeEnum.DICT.value, CacheValueTypeEnum.JSON.value, CacheValueTypeEnum.LIST.value):
            return json.loads(value)
        return value
