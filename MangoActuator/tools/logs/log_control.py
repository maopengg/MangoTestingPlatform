# # -*- coding: utf-8 -*-
# # @Project: MangoActuator
# # @Description: 日志封装，可设置不同等级的日志颜色
# # @Time   : 2022-11-04 22:05
# # @Author : 毛鹏

import logging
from logging import handlers

import colorlog

from tools import Initialization


class LogHandler:
    """ 日志打印封装"""
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self, file_name: str, level: str):

        self.logger = logging.getLogger(file_name)

        fmt = "%(levelname)-8s[%(asctime)s][%(filename)s:%(lineno)d] %(message)s"
        # 设置日志格式
        format_str = logging.Formatter(fmt)
        # 设置日志级别
        self.logger.setLevel(self.level_relations.get(level))
        # 往屏幕上输出
        screen_output = logging.StreamHandler()
        # 设置屏幕上显示的格式
        screen_output.setFormatter(self.log_format(level))
        # 往文件里写入#指定间隔时间自动生成文件的处理器
        time_rotating = handlers.TimedRotatingFileHandler(
            filename=file_name,
            when="D",
            backupCount=3,
            encoding='utf-8'
        )
        # 设置文件里写入的格式
        time_rotating.setFormatter(format_str)
        # 把对象加到logger里
        self.logger.addHandler(screen_output)
        self.logger.addHandler(time_rotating)

    @classmethod
    def log_format(cls, level):
        """ 设置日志格式 """
        if level == "debug" or level == "info":
            fmt = "%(log_color)s[%(asctime)s] [%(levelname)s]: %(message)s"  # 指定bug级别的日志格式
        else:
            fmt = "%(log_color)s[%(asctime)s] [%(filename)s-->line:%(lineno)d]] [%(levelname)s]: %(message)s"
        format_str = colorlog.ColoredFormatter(
            fmt,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        )
        return format_str


log_path = Initialization.get_log()
DEBUG = LogHandler(fr"{log_path}\debug-log.log", 'debug')
INFO = LogHandler(fr"{log_path}\info-log.log", 'info')
WARNING = LogHandler(fr"{log_path}\warning-log.log", 'warning')
ERROR = LogHandler(fr"{log_path}\error-log.log", 'error')
CRITICAL = LogHandler(fr"{log_path}\critical-log.log", 'critical')

if __name__ == '__main__':
    DEBUG.logger.debug('DEBUG')
    INFO.logger.info("INFO")
    WARNING.logger.warning("WARNING")
    ERROR.logger.error("ERROR")
    CRITICAL.logger.critical("CRITICAL")
