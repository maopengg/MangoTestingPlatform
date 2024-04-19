# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-12 18:20
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD
from PyAutoTest.models.socket_model.api_model import ApiInfoModel

log = logging.getLogger('api')


class WriteAPI:

    @classmethod
    def write(cls, data: ApiInfoModel):
        data = data.dict()
        data['json'] = data['json_data']
        del data['json_data']
        try:
            api_info_obj = ApiInfo.objects.get(url=data['url'], method=data['method'])
        except ApiInfo.DoesNotExist:
            ApiInfoCRUD.inside_post(data)
