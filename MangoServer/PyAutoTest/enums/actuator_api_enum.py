from enum import Enum


class ApiEnum(Enum):
    A_DEBUG_CASE = 'a_debug_case'
    A_BATCH_CASE = 'a_batch_case'
    A_GROUP_CASE = 'a_group_case'
    REFRESH_CACHE = 'refresh_cache'
    A_COMMON_PARAMETERS = 'a_common_parameters'


class UiEnum(Enum):
    U_DEBUG_CASE = 'u_debug_case'
    U_GROUP_CASE = 'u_group_case'


class ToolsEnum(Enum):
    T_MYSQL_CONFIG = "t_mysql_config"
