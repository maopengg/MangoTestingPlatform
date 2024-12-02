# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import os
import traceback

from PySide6.QtWidgets import QApplication
from mangokit import Mango

from src.pages.login.login_window import LoginLogic
from src.tools import InitPath
from src.tools.log_collector import log

os.environ["QT_FONT_DPI"] = "96"


# 4K
# os.environ["QT_SCALE_FACTOR"] = "2"


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

# pyinstaller .\执行器.spec
