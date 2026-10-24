# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏


class Perf:
    @staticmethod
    async def perf_execution(data):
        from src.services.perf import PerfRunner
        return await PerfRunner(data).run()
