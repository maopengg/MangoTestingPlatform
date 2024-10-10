# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-05-24 11:51
# @Author : 毛鹏
import asyncio

import psutil
import time

from src.settings import settings
from src.tools.desktop.signal_send import SignalSend
from src.tools.log_collector import log


def async_memory(func):
    async def wrapper(*args, **kwargs):
        current_mix = 0
        while True:
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > settings.MEMORY_THRESHOLD and not settings.IS_DEBUG:
                await asyncio.sleep(3)
                current_mix += 1
                SignalSend.notice_signal_c(
                    f'程序占用内存过多，请减少并发浏览器的数量，或者检查电脑是否有满足执行自动化任务的内存空间！')
                log.info(f'程序占用内存过多，请减少并发浏览器的数量，或者检查电脑是否有满足执行自动化任务的内存空间！')
            else:
                break
            if current_mix >= settings.LOOP_MIX:
                break
        return await func(*args, **kwargs)

    return wrapper


def sync_memory(func):
    def wrapper(*args, **kwargs):
        current_mix = 0
        while True:
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > settings.MEMORY_THRESHOLD:
                # log.info(f'当前的内存使用率不足以支持继续启动浏览器，请稍等内存减少后继续，当前次数：{current_mix}')
                time.sleep(3)
                current_mix += 1
                if current_mix == 10:
                    SignalSend.notice_signal_c(
                        f'程序占用内存过多，请减少并发浏览器的数量，或者检查电脑是否有满足执行自动化任务的内存空间！')
            else:
                break
            if current_mix > settings.LOOP_MIX:
                break
        return func(*args, **kwargs)

    return wrapper
