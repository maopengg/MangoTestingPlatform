# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-08-21 11:04
# @Author : 毛鹏
import os

from src.tools.set_config import SetConfig


def set_failed_retry_time():
    os.environ['FAILED_RETRY_TIME'] = str(SetConfig.get_failed_retry_time())


set_failed_retry_time()
