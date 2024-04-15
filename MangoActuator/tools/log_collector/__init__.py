# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-05 12:40
# @Author : 毛鹏
from tools import Initialization
from tools.log_collector.log_control import LogHandler


class Log:
    log_path = Initialization.log_dir
    DEBUG = LogHandler(fr"{log_path}\debug-log.log", 'debug')
    INFO = LogHandler(fr"{log_path}\info-log.log", 'info')
    WARNING = LogHandler(fr"{log_path}\warning-log.log", 'warning')
    ERROR = LogHandler(fr"{log_path}\error-log.log", 'error')
    CRITICAL = LogHandler(fr"{log_path}\critical-log.log", 'critical')

    @classmethod
    def debug(cls, msg: str):
        cls.DEBUG.logger.debug(msg)

    @classmethod
    def info(cls, msg: str):
        cls.INFO.logger.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.WARNING.logger.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.CRITICAL.logger.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.ERROR.logger.error(msg)


log = Log
if __name__ == '__main__':
    log.debug('DEBUG')
    log.info("INFO")
    log.warning("WARNING")
    log.error("ERROR")
    log.critical("CRITICAL")
