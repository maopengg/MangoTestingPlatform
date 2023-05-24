# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-24 23:20
# @Author : 毛鹏
import json

from utils.test_data_cache.memory_cache import MemoryCache


class JsonDataProcessing(MemoryCache):

    @classmethod
    async def json_str(cls, json_data: dict):
        data = json.dumps(json_data)
        return data

    @classmethod
    async def json_dict(cls, json_data: str):
        data = json.loads(json_data)
        return data

    @classmethod
    async def get_json_path_data(cls):
        pass
