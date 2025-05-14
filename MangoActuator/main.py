# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import os
import traceback

from PySide6.QtWidgets import QApplication
from mangokit.mangos import Mango

from src.pages.login.login_window import LoginLogic
from src.tools import project_dir
from src.tools.log_collector import log

os.environ["QT_FONT_DPI"] = "96"


# 4K
# os.environ["QT_SCALE_FACTOR"] = "2"

async def main():
    try:
        project_dir.cache_file()
        await asyncio.sleep(0)
        app = QApplication([])
        login_window = LoginLogic(Mango.t())
        login_window.show()
        app.exec()
    except Exception as error:
        traceback.print_exc()
        log.error(f"顶级任务出现异常：{error}")


asyncio.run(main())
# 下面是需要打包成exe的人看的
"""
pyinstaller `
--name "执行器" `
--onefile `
--noconsole `
--icon "app_icon.ico" `
--add-data "src/settings/settings.json;src/settings" `
--add-data "src/settings/menus.json;src/settings" `
--add-data "src/settings/menus_2.json;src/settings" `
--add-data "E:\DevTool\python-venv\MangoActuator\Lib\site-packages\mangokit\mangos\pyarmor_runtime_windows;mangos/pyarmor_runtime_windows" `
--add-data "E:\DevTool\python-venv\MangoActuator\Lib\site-packages\mangokit\mangos\pyarmor_runtime_linux;mangos/pyarmor_runtime_linux" `
--hidden-import "mango" `
--hidden-import "pyarmor_runtime" `
--hidden-import "pyarmor_runtime_000000" `
--clean `
--noconfirm `
--hidden-import "email.mime.text" `
--hidden-import "email.mime.base" `
--hidden-import "email.mime.multipart" `
main.py
"""
# --add-data="{{把上面的这一行，改为你自己的虚拟环境中的目录，虚拟环境或者是你安装包的包的目录}}\mangokit\mangos\pyarmor_runtime_windows\pyarmor_runtime_000000;pyarmor_runtime_000000"
# --add-data="{{把上面的这一行，改为你自己的虚拟环境中的目录，虚拟环境或者是你安装包的包的目录}}\mangokit\mangos\pyarmor_runtime_linux\pyarmor_runtime_000000;pyarmor_runtime_000000"
