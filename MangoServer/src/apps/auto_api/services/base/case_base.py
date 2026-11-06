from mangotools.enums import StatusEnum
# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-25 20:57
# @Author : 毛鹏
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.exceptions import (
    API_CASE_POSTERIOR_CLEANUP_FAILED,
    API_CASE_POSTERIOR_SQL_CONFIG_INVALID,
    API_CASE_POSTERIOR_SQL_PROJECT_PRODUCT_SQL_DATABASE_CASE_EXECUTION_FAILED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase, ApiHeaders
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.base.case_data_factory import CaseDataFactory
from src.apps.auto_api.services.base.data_source_operation import (
    cache_data_source_result,
    execute_data_source_operation,
)
from src.apps.auto_api.services.base.sql_environment import should_apply_env_item, should_execute_sql
from src.apps.test_center.exceptions import (
    TEST_CASE_POST_SQL_EMPTY,
    TEST_CASE_PRE_KEY_VALUE_EMPTY,
    TEST_SUITE_KEY_EMPTY,
    TEST_CASE_PRE_SQL_REQUIRED,
)
from src.common.exceptions import (
    MangoServerError,
)
from src.common.logging import log


class CaseBase:
    """ 测试用例前后置 """

    def __init__(
            self,
            test_setup: APIBaseTestSetup,
            api_case: ApiCase,
            test_env: int,
            user_id: int | None = None,
            data_factory_configs=None,
    ):
        self.test_setup = test_setup
        self.api_case = api_case
        self.test_env = test_env
        self.case_headers = {}
        self.case_data_factory = CaseDataFactory(
            test_setup,
            api_case,
            user_id=user_id,
            configs=data_factory_configs,
        )

    def case_front_main(self):
        if self.api_case.front_custom:
            self.__front_custom(self.api_case.front_custom)
        self.test_setup.ensure_execution_context()
        self.case_data_factory.run_front()
        if self.api_case.front_sql:
            self.__front_sql(self.api_case.front_sql)
        self.init_headers()

    def init_headers(self):
        self.case_headers = {}
        self.__front_headers()

    def case_posterior_main(self, ):
        errors = []
        try:
            try:
                if self.api_case.posterior_sql:
                    self.__posterior_sql(self.api_case.posterior_sql)
            except Exception as error:
                errors.append(error)
        finally:
            try:
                self.case_data_factory.cleanup()
            except Exception as error:
                errors.append(error)
        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise AutoApiError(API_CASE_POSTERIOR_CLEANUP_FAILED,
                               value=('；'.join(getattr(error, 'msg', str(error)) for error in errors),)) from errors[0]

    def case_parametrize(self, parametrize: dict):
        if parametrize:
            for i in parametrize.get('parametrize') or []:
                if not should_apply_env_item(i, self.test_env, config_name='用例参数化变量'):
                    log.api.info(
                        f'用例参数化变量跳过注入，key：{i.get("key")}，'
                        f'当前环境：{self.test_env}，配置环境：{i.get("test_envs")}'
                    )
                    continue
                key = i.get('key', None)
                value = i.get('value', None)
                if not key:
                    raise AutoApiError(TEST_SUITE_KEY_EMPTY)
                if value is not None:
                    value = self.test_setup.test_data.replace(value)
                log.api.debug(f'用例参数化->key:{i.get("key")}，value：{value}')
                self.test_setup.test_data.set_cache(key, value)

    def __front_custom(self, front_custom):
        for custom in front_custom:
            if not should_apply_env_item(custom, self.test_env, config_name='用例自定义变量'):
                log.api.info(
                    f'用例自定义变量跳过注入，key：{custom.get("key")}，'
                    f'当前环境：{self.test_env}，配置环境：{custom.get("test_envs")}'
                )
                continue
            key = custom.get('key', None)
            value = custom.get('value', None)
            if not key or not value:
                raise AutoApiError(TEST_CASE_PRE_KEY_VALUE_EMPTY)
            log.api.debug(f'前置自定义->key:{key}，value:{value}')
            self.test_setup.test_data.set_cache(key, value)

    def __front_sql(self, front_sql):
        for index, i in enumerate(front_sql, start=1):
            if not should_execute_sql(i, self.test_env):
                log.api.info(
                    f'用例前置SQL跳过执行，当前环境：{self.test_env}，配置环境：{i.get("test_envs")}'
                )
                continue
            key = self.test_setup.test_data.replace(i.get('key'))
            operation_config = self.test_setup.test_data.replace(i.get('value'))
            if not operation_config:
                raise AutoApiError(TEST_CASE_PRE_SQL_REQUIRED)
            result = execute_data_source_operation(
                self.test_setup,
                self.test_env,
                i,
                project_product_id=self.api_case.project_product_id,
                source_context={
                    'source_type': 'api_case',
                    'source_stage': 'case_front',
                    'source_id': self.api_case.id,
                    'case_id': self.api_case.id,
                    'operation_index': index,
                },
            )
            log.api.debug(f'用例前置数据库操作->key:{key}，执行结果：{result}')
            if key:
                cache_data_source_result(self.test_setup, key, result)

    def __front_headers(self):
        if hasattr(self.api_case, '_revision_front_headers'):
            self.case_headers = dict(self.api_case._revision_front_headers)
            log.api.debug(f'前置自定义->用例headers:{self.case_headers}')
            return
        if self.api_case.front_headers:
            queryset = ApiHeaders.objects.filter(id__in=self.api_case.front_headers)
        else:
            queryset = ApiHeaders.objects.filter(
                project_product_id=self.api_case.project_product_id,
                status=StatusEnum.SUCCESS.value,
            )
        for i in queryset:
            self.case_headers[i.key] = i.value
        log.api.debug(f'前置自定义->用例headers:{self.case_headers}')

    def __posterior_sql(self, posterior_sql):
        errors = []
        for index, sql_item in enumerate(posterior_sql, start=1):
            raw_key = datasource_alias = '-'
            try:
                if not isinstance(sql_item, dict):
                    raise AutoApiError(API_CASE_POSTERIOR_SQL_CONFIG_INVALID, value=(index,))
                raw_key = sql_item.get('key') or '-'
                datasource_alias = sql_item.get('datasource_alias') or '-'
                if not should_execute_sql(sql_item, self.test_env):
                    continue
                key = self.test_setup.test_data.replace(
                    self.test_setup.test_data.replace(sql_item.get('key'))
                )
                operation_config = self.test_setup.test_data.replace(
                    self.test_setup.test_data.replace(sql_item.get('value'))
                )
                if not operation_config:
                    raise AutoApiError(TEST_CASE_POST_SQL_EMPTY)
                result = execute_data_source_operation(
                    self.test_setup,
                    self.test_env,
                    sql_item,
                    project_product_id=self.api_case.project_product_id,
                    source_context={
                        'source_type': 'api_case',
                        'source_stage': 'case_posterior',
                        'source_id': self.api_case.id,
                        'case_id': self.api_case.id,
                        'operation_index': index,
                    },
                )
                if key:
                    cache_data_source_result(self.test_setup, key, result)
            except Exception as error:
                # 每一项只尝试一次；后续依赖值缺失仍失败，不放宽条件或重放未知写入。
                errors.append(AutoApiError(
                    API_CASE_POSTERIOR_SQL_PROJECT_PRODUCT_SQL_DATABASE_CASE_EXECUTION_FAILED,
                    value=(index, raw_key, datasource_alias, self.test_env,
                           self.api_case.project_product_id, getattr(error, 'msg', str(error))),
                ))
        if errors:
            raise AutoApiError(API_CASE_POSTERIOR_CLEANUP_FAILED,
                               value=('；'.join(error.msg for error in errors),)) from errors[0]
