# -*- coding: utf-8 -*-
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.services.api_case.global_variable import ApiCaseGlobalVariableService
from src.apps.auto_api.services.base.api_base_test_setup.public_base import PublicBase
from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.services.case_global_variable import UiCaseGlobalVariableService
from src.apps.data_factory.services.runtime_cache import DataFactoryRuntimeCache
from src.apps.gray_config.exceptions import (
    GRAY_VARIABLE_GRAY_UNSUPPORTED,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayFeature
from src.common.testing import ObtainTestData


class GrayTargetValueResolver:
    API = "api"
    UI = "ui"

    @classmethod
    def resolve(
            cls,
            feature: GrayFeature,
            target_value: str | None,
            variable_source: str | None = None,
            test_env: int | str | None = None,
    ) -> str:
        if target_value is None:
            return ""
        value = str(target_value)
        if value == "":
            return ""
        if not variable_source:
            return value
        if variable_source == cls.API:
            return cls.resolve_api(feature, value, test_env)
        if variable_source == cls.UI:
            return cls.resolve_ui(feature, value, test_env)
        raise GrayConfigError(GRAY_VARIABLE_GRAY_UNSUPPORTED, value=(variable_source,))

    @classmethod
    def resolve_api(cls, feature: GrayFeature, value: str, test_env: int | str | None) -> str:
        setup = PublicBase()
        setup.skip_auth_load = True
        try:
            cls.load_api_custom_public(setup.test_data, feature, test_env)
            try:
                return str(setup.test_data.replace(value))
            except MangoToolsError:
                pass
            if test_env in (None, ""):
                return value
            setup.init_test_object(feature.project_product_id, test_env)
            setup.init_public(feature.project_product_id, test_env)
            return str(setup.test_data.replace(value))
        except MangoToolsError as error:
            raise
        finally:
            setup.close_db_connections()

    @classmethod
    def resolve_ui(cls, feature: GrayFeature, value: str, test_env: int | str | None) -> str:
        test_data = ObtainTestData()
        cls.load_ui_custom_public(test_data, feature, test_env)
        try:
            return str(test_data.replace(value))
        except MangoToolsError:
            pass
        if test_env in (None, ""):
            return value
        project_product_ids = DataFactoryRuntimeCache.get_same_project_product_ids(feature.project_product_id)
        DataFactoryRuntimeCache.load_ui_public(
            test_data,
            feature.project_product_id,
            project_product_ids,
            test_env,
        )
        try:
            return str(test_data.replace(value))
        except MangoToolsError as error:
            raise

    @staticmethod
    def load_api_custom_public(test_data: ObtainTestData, feature: GrayFeature, test_env: int | str | None):
        for item in ApiCaseGlobalVariableService.list_public(feature.project_product_id, test_env):
            if item.type == ApiPublicTypeEnum.CUSTOM.value:
                test_data.set_cache(item.key, item.value)

    @staticmethod
    def load_ui_custom_public(test_data: ObtainTestData, feature: GrayFeature, test_env: int | str | None):
        for item in UiCaseGlobalVariableService.list_public(feature.project_product_id, test_env):
            if item.type == UiPublicTypeEnum.CUSTOM.value:
                test_data.set_cache(item.key, item.value)
