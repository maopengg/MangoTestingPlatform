# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-03 22:03
# @Author : 毛鹏

import traceback
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import time

from mangokit import Mango
from src.models.system_model import ConsumerCaseModel
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log


class FlowConsumer:
    queue = Queue()
    max_tasks = 2

    executor = ThreadPoolExecutor(max_workers=max_tasks)
    running = True
