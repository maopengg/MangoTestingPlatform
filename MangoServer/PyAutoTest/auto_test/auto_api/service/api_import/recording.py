# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-12 18:20
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD
from PyAutoTest.enums.tools_enum import ClientTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.models.socket_model.api_model import ApiInfoModel

log = logging.getLogger('api')


class Recording:

    @classmethod
    def write(cls, data: ApiInfoModel):
        from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
        username = data.username
        try:
            api_info_obj = ApiInfo.objects.get(url=data.url,
                                               method=data.method,
                                               project_product_id=data.project_product)
        except ApiInfo.DoesNotExist:
            msg = f'接口URL:<{data.url}>录制成功，刷新页面可查看'
            data = data.model_dump()
            data['json'] = data['json_data']
            del data['json_data']
            ApiInfoCRUD.inside_post(data)
        except ApiInfo.MultipleObjectsReturned:
            msg = f'接口URL:<{data.url}>已经存在，所以不需要进行录制到数据库中！'
        else:
            msg = f'项目：<{api_info_obj.project_product.project.name}>-产品：<{api_info_obj.project_product.name}>接口URL:<{data.url}>已经存在，所以不需要进行录制到数据库中！'
            log.info(msg)
        ChatConsumer.active_send(SocketDataModel(
            code=200,
            msg=msg,
            user=username,
            is_notice=ClientTypeEnum.WEB.value,
        ))
