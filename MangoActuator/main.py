# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import traceback
from asyncio import AbstractEventLoop
from threading import Thread

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication

from src.login_window import LoginLogic
from src.tools import InitPath
from src.tools.log_collector import log


class AsyncioThread(Thread):
    def __init__(self, loop: AbstractEventLoop):
        super().__init__()
        self._loop = loop
        self.daemon = True

    def run(self) -> None:
        self._loop.run_forever()


async def main():
    try:
        InitPath()
        await asyncio.sleep(0)
        app = QApplication([])
        loop = asyncio.new_event_loop()
        thd = AsyncioThread(loop)
        thd.start()
        login_window = LoginLogic(loop)
        login_window.show()
        app.exec()
    except Exception as error:
        traceback.print_exc()
        log.error(f"顶级任务出现异常：{error}")


asyncio.run(main())


# try:
#     InitPath()
#     app = QApplication([])
#     window = LoginLogic()
#     app.exec()
# except Exception as error:
#     traceback.print_exc()
#     log.error(f"顶级任务出现异常：{error}")

# pyinstaller -F -w --onefile --add-data "src/settings/settings.json;src/settings" --add-data "src/settings/menus.json;src/settings"  --name=执行器 --icon=resources/icons/app_icon.png main.py
