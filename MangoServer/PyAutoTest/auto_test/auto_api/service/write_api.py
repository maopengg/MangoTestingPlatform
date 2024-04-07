# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-12 18:20
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.models.socket_model.api_model import ApiInfoModel

log = logging.getLogger('api')


class WriteAPI:
    def __init__(self):
        self.api_info_list: list = [str(method) + url for url, method in
                                    ApiInfo.objects.all().values_list('url', 'method')]

    def write(self, data: ApiInfoModel):
        data = data.dict()
        data['json'] = data['json_data']
        del data['json_data']
        check = str(data['method']) + data['url']
        if check not in self.api_info_list:
            serializers = ApiInfoSerializers(data=data)
            if serializers.is_valid():
                serializers.save()
                self.api_info_list.append(check)
            else:
                log.error(str(serializers.errors))
        else:
            log.info(f'url:{data["url"]}是重复的数据，跳过该接口信息的保存！')
