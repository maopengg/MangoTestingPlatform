# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from src.models.tools_model import CmdModel
from src.tools.command.command import run_command
from src.tools.decorator.convert_args import convert_args
from src.tools.decorator.error_handle import async_error_handle


class Tools:
    @async_error_handle()
    @convert_args(list[CmdModel])
    async def t_cmd(self, data: list[CmdModel]):
        for cmd in data:
            output, error = run_command(cmd)
            if output:
                print(output)
            if error:
                print(error)
