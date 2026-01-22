# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-25 上午10:01
# @Author : 毛鹏
import logging

from src import settings


class System:
    log = logging.getLogger('system')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)


class Ui:
    log = logging.getLogger('ui')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)


class Api:
    log = logging.getLogger('api')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)


class User:
    log = logging.getLogger('user')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)


class Perf:
    log = logging.getLogger('perf')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)


class Pytest:
    log = logging.getLogger('pytest')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)



class Monitoring:
    log = logging.getLogger('monitoring')

    @classmethod
    def debug(cls, msg: str):
        if settings.IS_DEBUG_LOG:
            cls.log.critical(msg)

    @classmethod
    def info(cls, msg: str):
        cls.log.info(msg)

    @classmethod
    def warning(cls, msg: str):
        cls.log.warning(msg)

    @classmethod
    def critical(cls, msg: str):
        cls.log.critical(msg)

    @classmethod
    def error(cls, msg: str):
        cls.log.error(msg)

class Log:
    system = System
    ui = Ui
    api = Api
    user = User
    perf = Perf
    pytest = Pytest
    monitoring = Monitoring


log = Log
if __name__ == '__main__':
    log.system.debug('DEBUG')
    log.system.info('DEBUG')
    log.system.warning('DEBUG')
    log.system.critical('DEBUG')
    log.system.error('DEBUG')
    log.ui.debug('DEBUG')
    log.ui.info('DEBUG')
    log.ui.warning('DEBUG')
    log.ui.critical('DEBUG')
    log.ui.error('DEBUG')
