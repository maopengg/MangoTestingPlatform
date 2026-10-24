# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.exceptions import AutoApiError, API_REQUEST_BODY_INVALID
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService
from src.common.logging import log


class TestApiInfo:

    def __init__(self, user_id, test_env: int):
        self.user_id = user_id
        self.test_env = test_env
        self.test_setup = APIBaseTestSetup()

    def api_info_run(
            self,
            api_info_id: int,
            *,
            revision_id: int | None = None,
            release_id: int | None = None,
            runtime_parameters: dict | None = None,
    ) -> dict:
        if runtime_parameters is not None:
            if not isinstance(runtime_parameters, dict) or any(not isinstance(key, str) or not key for key in runtime_parameters):
                raise AutoApiError(API_REQUEST_BODY_INVALID, value=('runtime_parameters', '运行时参数必须是非空字符串键组成的对象'))
            for key, value in runtime_parameters.items():
                self.test_setup.test_data.set_cache(key, value)
        api_info = ApiInfo.objects.get(id=api_info_id)
        try:
            response = self.test_setup.api_request(
                api_info.id,
                self.test_env,
                revision_id=revision_id,
                release_id=release_id,
                preserve_unresolved_cache_placeholders=True,
                **({'runtime_parameters': runtime_parameters} if runtime_parameters else {}),
            )
            return self.save_api_info(api_info, response)
        except Exception as error:
            log.api.debug(f'API执行报错：{error}')
            raise error
        finally:
            self.test_setup.close_grpc_channels()
            self.test_setup.close_mcp_sessions()
            self.test_setup.close_db_connections()

    def save_api_info(self, api_info: ApiInfo, response: ApiExecutionResponse):
        res = response.model_dump()
        res.update(ProtocolCallOutcomeService.evaluate(response, display_name=api_info.name).result_fields())
        res['name'] = api_info.name
        res['cache_all'] = self.test_setup.test_data.get_all()
        return res
