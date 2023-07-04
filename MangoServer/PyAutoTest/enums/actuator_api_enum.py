from enum import Enum


class ApiApiEnum(Enum):
    api_debug_case = 'api_debug_case'
    api_batch_case = 'api_batch_case'
    api_group_case = 'api_group_case'
    refresh_cache = 'refresh_cache'


class UiApiEnum(Enum):
    # 执行调试用例对象浏览器对象
    run_debug_case = 'ui_debug_case'
    # 执行并发对象浏览器对象
    run_group_case = 'ui_group_case'
