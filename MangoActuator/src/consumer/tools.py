# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from src.models.system_model import CmdTestModel
from src.tools.command.command import run_command
from src.tools.decorator.convert_args import convert_args
from src.tools.decorator.error_handle import async_error_handle
from src.tools.log_collector import log


class Tools:

    @classmethod
    @async_error_handle()
    @convert_args(CmdTestModel)
    async def t_mango_pytest(cls, data: CmdTestModel):
        for cmd in data.cmd:
            output, error = run_command(cmd)
            if output:
                print(output)
            if error:
                print(error)

    @classmethod
    @async_error_handle()
    @convert_args(dict)
    async def t_set_open_status(cls, data):
        log.debug(f'设置open状态：{data.get("is_open")}')
        from src.settings import settings
        settings.IS_OPEN = data.get('is_open')
