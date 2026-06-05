# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-12 18:20
# @Author : 毛鹏
# import json

from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.views.api_info import ApiInfoCRUD
from src.apps.auto_system.models import ProductModule
from src.common.enums.system_enum import ClientTypeEnum
from src.common.enums.tools_enum import TaskEnum
# from src.common.enums.api_enum import MethodEnum
from src.common.models.api_model import RecordingApiModel
from src.common.models.socket_model import SocketDataModel


class Recording:
    # with open(r"D:\code\MangoTestingPlatform\MangoServer\tests\test.json", 'r', encoding='utf-8') as f:
    #     data = json.load(f)

    @classmethod
    def write(cls, data: RecordingApiModel):
        from src.apps.auto_system.consumers import ChatConsumer
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
            if ApiInfo.objects.filter(url=data.url,
                                      method=data.method,
                                      project_product_id=data.project_product).exists():
                msg = f'接口URL:<{data.url}>已经存在，所以不需要进行录制到数据库中！'
            else:
                msg = f'接口URL:<{data.url}>录制成功，刷新页面可查看'
                data.module = module.id
                data.status = TaskEnum.STAY_BEGIN.value
                data = data.model_dump()
                ApiInfoCRUD.inside_post(data)
        except ProductModule.DoesNotExist:
            msg = '该项目没有任务模块，请先新增模块再录制，录制的时候会默认给接口绑定一个模块'
        ChatConsumer.active_send(SocketDataModel(
            code=200,
            msg=msg,
            user=username,
            is_notice=ClientTypeEnum.WEB,
        ))
