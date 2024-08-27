# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import traceback

from PySide6.QtWidgets import QApplication

from src.login_window import LoginLogic
from src.tools import InitPath
from src.tools.log_collector import log

try:
    InitPath()
    app = QApplication([])
    app.setStyleSheet("* { font-size: 10pt; }")
    window = LoginLogic()
    window.show()
    app.exec()
except Exception as error:
    traceback.print_exc()
    log.error(f"顶级任务出现异常：{error}")

# pyinstaller -F -c .\main.py --upx-dir="E:\DevTool\Python\python-venv\upx-4.0.2-win64"
# pyinstaller -F -w --name=执行器 --icon=resources/icons/app_icon.png --add-data "resources/icons/app_icon.png;resources/icons" .\main.py
# pyinstaller -F -w  src/widgets/push_button.py
# playwright install ffmpeg