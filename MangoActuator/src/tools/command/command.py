# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-12-05 18:25
# @Author : 毛鹏
import platform
import subprocess

if platform.system() != "Linux":
    from PySide6.QtCore import QThread
    from PySide6.QtCore import Signal
else:
    class QThread:
        pass


    class Signal:
        def __init__(self, *args, **kwargs):
            pass

        def emit(self, *args, **kwargs):
            pass


def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr


class CommandThread(QThread):
    output_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, parent=None, command=None):
        super().__init__(parent)
        self.command = command

    def run(self):
        output, error = run_command(self.command)
        if output:
            self.output_signal.emit(output)
        if error:
            self.error_signal.emit(error)
