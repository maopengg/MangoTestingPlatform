# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import asyncio
import json

from auto_api.api_tools.async_http_client import AsyncHttpClient


class ApiCaseRun(AsyncHttpClient):

    async def http_(self, data):
        data = await self.get(data.get('case_url') + data.get('case_data').get('url'), )
        print(data)


if __name__ == '__main__':
    with open(r'E:\GitCode\MangoTestingPlatform\MangoActuator\tests\api.json', 'r') as f:
        data = json.load(f)
    asyncio.run(ApiCaseRun().http_(data.get('group_case')[0]))
