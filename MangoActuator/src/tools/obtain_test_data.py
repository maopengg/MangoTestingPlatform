# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
import json
import os
import uuid

from mangotools.data_processor import DataProcessor, ObtainRandomData

from src.exceptions import ToolsError, ERROR_MSG_0026
from src.network import HTTP
from src.tools import project_dir


class ObtainTestData(DataProcessor):

    @classmethod
    def random_demo(cls, demo1, demo2) -> str:
        """示例方法"""
        # 1.必须写在这个类下面，如果需要给UI自动化使用，则执行器也需要写
        # 2.必须要写 """示例方法""" 这种注释
        # 3.函数名称必须是唯一，跟我已使用的不可重复
        # 4.函数必须要返回一个值，返回值就是你需要的随机数据
        # 5.函数如果要接受传值，则直接接收参数，传入进来的参数默认是字符串类型
        print(demo1, demo2)
        return str(uuid.uuid4())

    @classmethod
    def get_file(cls, file_name) -> str:
        """传入文件名称，返回文件"""
        HTTP.not_auth.download_file(file_name)
        file_path = os.path.join(project_dir.upload(), file_name)
        if os.path.exists(file_path):
            return file_path
        else:
            raise ToolsError(*ERROR_MSG_0026)


if __name__ == '__main__':
    print(json.dumps(ObtainRandomData.get_methods(), ensure_ascii=False))
