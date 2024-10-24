# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import traceback

from PySide6.QtWidgets import QApplication
from mangokit import Mango

from src.login_window import LoginLogic
from src.tools import InitPath
from src.tools.log_collector import log


async def main():
    try:
        InitPath()
        await asyncio.sleep(0)
        app = QApplication([])
        login_window = LoginLogic(Mango.t())
        login_window.show()
        app.exec()
    except Exception as error:
        traceback.print_exc()
        log.error(f"顶级任务出现异常：{error}")


asyncio.run(main())

# pyinstaller -F -w --onefile --add-data "src/settings/settings.json;src/settings" --add-data "src/settings/menus.json;src/settings"  --name=执行器 --icon=resources/icons/app_icon.png main.py
