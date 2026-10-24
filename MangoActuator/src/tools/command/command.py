# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-12-05 18:25
# @Author : 毛鹏
import subprocess
import threading


class Signal:
    """Small callback signal used without coupling command execution to a UI framework."""

    def __init__(self, *_args, **_kwargs):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in tuple(self._callbacks):
            callback(*args, **kwargs)


def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr


class CommandThread(threading.Thread):

    def __init__(self, parent=None, command=None):
        super().__init__(daemon=True)
        self.parent = parent
        self.command = command
        self.output_signal = Signal(str)
        self.error_signal = Signal(str)

    def run(self):
        output, error = run_command(self.command)
        if output:
            self.output_signal.emit(output)
        if error:
            self.error_signal.emit(error)
