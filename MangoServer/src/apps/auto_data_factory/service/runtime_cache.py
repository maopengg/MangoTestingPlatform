# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂运行时缓存初始化

from src.apps.auto_api.models import ApiPublic
from src.apps.auto_system.models import ProjectProduct
from src.apps.auto_ui.models import UiPublic
from src.common.enums.api_enum import ApiPublicTypeEnum
from src.common.enums.tools_enum import StatusEnum
from src.common.enums.ui_enum import UiPublicTypeEnum
from src.common.tools.log_collector import log
from src.common.tools.obtain_test_data import ObtainTestData


class DataFactoryRuntimeCache:
    """为数据工厂预览、调试和执行初始化可用于 ${{}} 替换的缓存。"""

    @classmethod
    def build_test_data(cls, project_product_id: int, test_env) -> ObtainTestData:
        test_data = ObtainTestData()
        project_product_ids = cls.get_same_project_product_ids(project_product_id)
        cls.load_api_public(test_data, project_product_id, project_product_ids, test_env)
        cls.load_ui_public(test_data, project_product_id, project_product_ids, test_env)
        return test_data

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
            test_env
    ) -> None:
        queryset = ApiPublic.objects.filter(
                project_product_id__in=project_product_ids,
                type=ApiPublicTypeEnum.CUSTOM.value,
                status=StatusEnum.SUCCESS.value,
                test_env=test_env,
        )
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
    ) -> None:
        queryset = UiPublic.objects.filter(
                project_product_id__in=project_product_ids,
                type=UiPublicTypeEnum.CUSTOM.value,
                status=StatusEnum.SUCCESS.value,
                test_env=test_env,
        )
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
