# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-12 18:20
# @Author : 毛鹏
# import json

from mangotools.contracts import SocketEnvelopeContract

from src.apps.auto_api.models import ApiInfo
# from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.schemas.recording import ApiRecordingSchema
from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.test_center.models import ProductModule


class Recording:
    # with open(r"D:\code\MangoTestingPlatform\MangoServer\tests\test.json", 'r', encoding='utf-8') as f:
    #     data = json.load(f)

    @classmethod
    def write(cls, data: ApiRecordingSchema):
        username = data.username
        # try:
        #     for i in cls.data:
        #         if (data.url in i.get('url') or i.get('url') in data.url) and MethodEnum.get_value(
        #                 data.method).lower() == i.get('method'):
        #             data.name = i.get('name')
        # except Exception as e:
        #     print(e)
        try:
            module = ProductModule.objects.filter(project_product_id=data.project_product).first()
            exists = False
            for api_info in ApiInfo.objects.filter(project_product_id=data.project_product).only('id'):
                try:
                    runtime = ApiInfoRuntimeService.resolve_runtime(api_info.id, allow_draft=True)
                except Exception:
                    continue
                if runtime.url == data.url and runtime.method == data.method:
                    exists = True
                    break
            if exists:
                msg = f'接口URL:<{data.url}>已经存在，所以不需要进行录制到数据库中！'
            else:
                msg = f'接口URL:<{data.url}>录制成功，刷新页面可查看'
                data.module = module.id
                data = data.model_dump()
                ApiInfoMutationService.create(data, source="recording")
        except ProductModule.DoesNotExist:
            msg = '该项目没有任务模块，请先新增模块再录制，录制的时候会默认给接口绑定一个模块'
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg=msg,
            user=username,
            is_notice=ClientTypeEnum.WEB,
        ))
