# # -*- coding: utf-8 -*-
# # @Project: auto_test
# # @Description: 日志封装，可设置不同等级的日志颜色
# # @Time   : 2022-11-04 22:05
# # @Author : 毛鹏

import logging
from logging import handlers

import colorlog

from utlis.logs.nuw_logs import get_log


class LogHandler:
    """ 日志打印封装"""
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(
            self,
            filename: str,
            level: str,
            fmt: str = "%(levelname)-8s[%(asctime)s][%(filename)s:%(lineno)d] %(message)s"
    ):
        self.logger = logging.getLogger(filename)

        formatter = self.log_color()

        # 设置日志格式
        format_str = logging.Formatter(fmt)
        # 设置日志级别
        self.logger.setLevel(self.level_relations.get(level))
        # 往屏幕上输出
        screen_output = logging.StreamHandler()
        # 设置屏幕上显示的格式
        screen_output.setFormatter(formatter)
        # 往文件里写入#指定间隔时间自动生成文件的处理器
        time_rotating = handlers.TimedRotatingFileHandler(
            filename=filename,
            when="D",
            backupCount=3,
            encoding='utf-8'
        )
        # 设置文件里写入的格式
        time_rotating.setFormatter(format_str)
        # 把对象加到logger里
        self.logger.addHandler(screen_output)
        self.logger.addHandler(time_rotating)
        self.log_path = get_log() + r'\log.log'

    @classmethod
    def log_color(cls):
        """ 设置日志颜色 """
        log_colors_config = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }

        formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(filename)s-->line:%(lineno)d]] [%(levelname)s]: %(message)s',
            log_colors=log_colors_config
        )
        return formatter


DEBUG = LogHandler(get_log() + r"\debug-log.log", 'debug')
INFO = LogHandler(get_log() + r"\info-log.log", 'info')
WARNING = LogHandler(get_log() + r"\warning-log.log", 'warning')
ERROR = LogHandler(get_log() + r"\error-log.log", 'error')
CRITICAL = LogHandler(get_log() + r"\critical-log.log", 'critical')

if __name__ == '__main__':
    DEBUG.logger.debug('DEBUG')
    INFO.logger.info("INFO")
    WARNING.logger.warning("WARNING")
    ERROR.logger.error("ERROR")
    CRITICAL.logger.critical("CRITICAL")
