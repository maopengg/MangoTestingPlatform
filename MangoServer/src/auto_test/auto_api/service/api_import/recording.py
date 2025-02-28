# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-12 18:20
# @Author : 毛鹏

from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.views.api_info import ApiInfoCRUD
from src.auto_test.auto_system.models import ProductModule
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import TaskEnum
from src.models.api_model import RecordingApiModel
from src.models.socket_model import SocketDataModel


class Recording:

    @classmethod
    def write(cls, data: RecordingApiModel):
        from src.auto_test.auto_system.consumers import ChatConsumer
        username = data.username
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
            is_notice=ClientTypeEnum.WEB.value,
        ))
