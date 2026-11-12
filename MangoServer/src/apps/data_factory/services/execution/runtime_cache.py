# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂运行时缓存初始化

from contextlib import contextmanager
from copy import deepcopy

from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.models import ApiPublic
from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.models import UiPublic
from src.apps.test_center.models import ProjectProduct
from src.common.logging import log
from src.common.testing import ObtainTestData
from src.common.utils.environment_scope import test_envs_query


class DataFactoryRuntimeCache:
    """为数据工厂预览、调试和执行初始化可用于 ${{}} 替换的缓存。"""

    @staticmethod
    @contextmanager
    def bind_context(test_data: ObtainTestData, context: dict | None):
        """本次请求值覆盖普通公共变量，结束后恢复，不写入持久配置或跨执行缓存。"""
        values = {}

        def collect(data, prefix=''):
            for key, value in data.items():
                if not isinstance(key, str) or key.startswith('__'):
                    continue
                name = f'{prefix}.{key}' if prefix else key
                values[name] = deepcopy(value)
                if isinstance(value, dict):
                    collect(value, name)

        collect(context or {})
        if not values:
            yield test_data
            return
        original = test_data.get_all()
        try:
            for key, value in values.items():
                test_data.set_cache(key, value)
            yield test_data
        finally:
            for key in values:
                test_data.delete_cache(key)
            # LRU 缓存可能在注入时淘汰旧键；恢复被覆盖和被淘汰的原值。
            for key, value in original.items():
                if key in values or not test_data.has_cache(key):
                    test_data.set_cache(key, value)

    @classmethod
    def build_test_data(cls, project_product_id: int, test_env, api_public_ids=None,
                        ui_public_ids=None) -> ObtainTestData:
        test_data = ObtainTestData()
        project_product_ids = cls.get_same_project_product_ids(project_product_id)
        cls.load_api_public(test_data, project_product_id, project_product_ids, test_env, api_public_ids)
        cls.load_ui_public(test_data, project_product_id, project_product_ids, test_env, ui_public_ids)
        return test_data

    @staticmethod
    def normalize_id_list(value) -> list[int]:
        result = []
        for item in value or []:
            try:
                item_id = int(item)
            except (TypeError, ValueError):
                continue
            if item_id not in result:
                result.append(item_id)
        return result

    @classmethod
    def get_same_project_product_ids(cls, project_product_id: int) -> list[int]:
        project_product = ProjectProduct.objects.filter(id=project_product_id).first()
        if not project_product:
            return [project_product_id]
        return list(
            ProjectProduct.objects.filter(project_id=project_product.project_id)
            .order_by('id')
            .values_list('id', flat=True)
        )

    @classmethod
    def load_api_public(
            cls,
            test_data: ObtainTestData,
            project_product_id: int,
            project_product_ids: list[int],
            test_env,
            selected_ids=None,
    ) -> None:
        selected_ids = cls.normalize_id_list(selected_ids)
        env_query = test_envs_query(test_env)
        queryset = ApiPublic.objects.filter(
            project_product_id__in=project_product_ids,
            type=ApiPublicTypeEnum.CUSTOM.value,
        ).filter(env_query).filter(status=StatusEnum.SUCCESS.value)
        selected_queryset = ApiPublic.objects.filter(
            id__in=selected_ids,
            project_product_id=project_product_id,
            type=ApiPublicTypeEnum.CUSTOM.value,
        ).filter(env_query)
        if selected_ids:
            queryset = queryset | selected_queryset
        current_product_items = queryset.filter(project_product_id=project_product_id).order_by('id')
        same_project_items = queryset.exclude(project_product_id=project_product_id).order_by('id')
        for item in list(current_product_items) + list(same_project_items):
            cls.set_public_cache(
                test_data,
                item.key,
                item.value,
                "ApiPublic",
                overwrite=item.project_product_id == project_product_id,
            )

    @classmethod
    def load_ui_public(
            cls,
            test_data: ObtainTestData,
            project_product_id: int,
            project_product_ids: list[int],
            test_env,
            selected_ids=None,
    ) -> None:
        selected_ids = cls.normalize_id_list(selected_ids)
        env_query = test_envs_query(test_env)
        queryset = UiPublic.objects.filter(
            project_product_id__in=project_product_ids,
            type=UiPublicTypeEnum.CUSTOM.value,
        ).filter(env_query).filter(status=StatusEnum.SUCCESS.value)
        selected_queryset = UiPublic.objects.filter(
            id__in=selected_ids,
            project_product_id=project_product_id,
            type=UiPublicTypeEnum.CUSTOM.value,
        ).filter(env_query)
        if selected_ids:
            queryset = queryset | selected_queryset
        current_product_items = queryset.filter(project_product_id=project_product_id).order_by('id')
        same_project_items = queryset.exclude(project_product_id=project_product_id).order_by('id')
        for item in list(current_product_items) + list(same_project_items):
            cls.set_public_cache(test_data, item.key, item.value, "UiPublic", overwrite=False)

    @staticmethod
    def set_public_cache(
            test_data: ObtainTestData,
            key: str,
            value: str,
            source: str,
            overwrite: bool,
    ) -> None:
        if not key:
            return
        if not overwrite and test_data.get_cache(key) is not None:
            log.system.warning(f'数据工厂公共变量缓存key重复，已忽略{source}.{key}')
            return
        test_data.set_cache(key, value)
