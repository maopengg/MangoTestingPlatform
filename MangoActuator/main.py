# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import os
import traceback

from PySide6.QtWidgets import QApplication

from src.login_window import LoginLogic
from src.tools import InitPath
from src.tools.log_collector import log
try:
    InitPath()
    app = QApplication([])
    window = LoginLogic()
    app.exec()
except Exception as error:
    traceback.print_exc()
    log.error(f"顶级任务出现异常：{error}")

# pyinstaller -F -c .\main.py --upx-dir="E:\DevTool\Python\python-venv\upx-4.0.2-win64"
# pyinstaller -F -w --name=执行器 --icon=resources/icons/app_icon.png --add-data "resources/icons/app_icon.png;resources/icons" .\main.py
# pyinstaller -F -w  .\main.py
# playwright install ffmpeg
# pyside6-rcc resources.qrc -o resources/icons/app_rc.py
# pyinstaller -F -w --onefile --add-data "src/settings/settings.json;src/settings" --add-data "src/settings/menus.json;src/settings" --add-data "src/settings/mango.json;src/settings" --name=执行器 --icon=resources/icons/app_icon.png main.py

