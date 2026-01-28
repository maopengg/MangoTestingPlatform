# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import os
import traceback

from PySide6.QtWidgets import QApplication
from mangotools.mangos import Mango

from src.pages.login.login_window import LoginLogic
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig

os.environ["QT_FONT_DPI"] = "96"


async def main():
    try:
        project_dir.cache_file()
        await asyncio.sleep(0)
        SetConfig.set_web_default(False)  # type: ignore
        app = QApplication([])
        login_window = LoginLogic(Mango.t())
        login_window.show()
        app.exec()
    except Exception as error:
        traceback.print_exc()
        log.error(f"顶级任务出现异常：{error}")


asyncio.run(main())
# 下面是需要打包成exe的人看的
r"""
pyinstaller `
--name "芒果执行器" `
--onefile `
--noconsole `
--icon "app_icon.ico" `
--add-data "src/settings/settings.json;src/settings" `
--add-data "src/settings/menus.json;src/settings" `
--add-data "src/settings/menus_2.json;src/settings" `
--add-data ".venv\Lib\site-packages\mangotools\mangos;mangos" `
--add-data ".venv\Lib\site-packages\uiautomator2\assets\u2.jar;uiautomator2/assets" `
--add-data ".venv\Lib\site-packages\uiautomator2\assets\app-uiautomator.apk;uiautomator2/assets" `
--add-data ".venv\Lib\site-packages\allure_pytest;allure_pytest" `
--collect-all allure_pytest `
--collect-all pytest `
--hidden-import allure_pytest `
--hidden-import allure_pytest.plugin `
--hidden-import _pytest `
--hidden-import pytest `
--hidden-import mango `
--hidden-import uiautomator2 `
--hidden-import dulwich `
--hidden-import dulwich.porcelain `
--hidden-import email.mime.text `
--hidden-import email.mime.base `
--hidden-import email.mime.multipart `
--hidden-import openai `
--clean `
--noconfirm `
main.py
"""
# --add-data="" 这个参数中的-> .venv 要改为你自己虚拟环境的地址，即可打包~
