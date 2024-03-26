# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-05 12:40
# @Author : 毛鹏
from tools import InitializationPath
from tools.logging_tool.log_control import LogHandler


class Logger:
    DEBUG = LogHandler(fr"{InitializationPath.log_file}\debug-log.log", 'debug')
    INFO = LogHandler(fr"{InitializationPath.log_file}\info-log.log", 'info')
    WARNING = LogHandler(fr"{InitializationPath.log_file}\warning-log.log", 'warning')
    ERROR = LogHandler(fr"{InitializationPath.log_file}\error-log.log", 'error')
    CRITICAL = LogHandler(fr"{InitializationPath.log_file}\critical-log.log", 'critical')

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


logger = Logger
if __name__ == '__main__':
    logger.debug('DEBUG')
    logger.info("INFO")
    logger.warning("WARNING")
    logger.error("ERROR")
    logger.critical("CRITICAL")
