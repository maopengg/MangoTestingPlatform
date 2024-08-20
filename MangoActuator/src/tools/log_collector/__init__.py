# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-05 12:40
# @Author : 毛鹏
from src.tools import InitPath
from src.tools.log_collector.log_control import LogHandler


class Log:
    DEBUG = LogHandler(fr"{InitPath.log_dir}\debug-log.log", 'debug')
    INFO = LogHandler(fr"{InitPath.log_dir}\info-log.log", 'info')
    WARNING = LogHandler(fr"{InitPath.log_dir}\warning-log.log", 'warning')
    ERROR = LogHandler(fr"{InitPath.log_dir}\error-log.log", 'error')
    CRITICAL = LogHandler(fr"{InitPath.log_dir}\critical-log.log", 'critical')

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
