# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import traceback

from PySide6.QtWidgets import QApplication

from desktop.login_window import LoginWindow
from service.socket_client.api_reflection import InterfaceMethodReflection
from tools import InitPath
from tools.log_collector import log

try:
    InitPath()
    InterfaceMethodReflection()
    app = QApplication([])
    window = LoginWindow()
    window.show()
    app.exec()
except Exception as error:
    traceback.print_exc()
    log.error(f"顶级任务出现异常：{error}")

# pyinstaller -F -c .\执行器.py --upx-dir="E:\DevTool\Python\python-venv\upx-4.0.2-win64"
# pyinstaller -F -w .\执行器.py
