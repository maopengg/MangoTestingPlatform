from typing import Any

from src.apps.auto_api.exceptions import (
    AUTO_API_BASE_SQL_ENVIRONMENT_CONFIG_EXECUTION_INVALID,
    AUTO_API_BASE_SQL_ENVIRONMENT_EXECUTION_INVALID,
    AUTO_API_BASE_SQL_ENVIRONMENT_CONFIG_EXECUTION_INVALID_CODE_CONFIG_EXECUTION_INVALID,
    AUTO_API_BASE_SQL_ENVIRONMENT_EXECUTION_INVALID_CODE_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.test_center.enums.environment import EnvironmentEnum


def should_apply_env_item(item: dict[str, Any], test_env: int | str, *, config_name: str = '配置') -> bool:
    test_envs = item.get('test_envs')
    if test_envs is None or test_envs == []:
        return True
    if not isinstance(test_envs, list):
        raise AutoApiError(AUTO_API_BASE_SQL_ENVIRONMENT_CONFIG_EXECUTION_INVALID, value=(config_name,))
    if isinstance(test_env, bool) or test_env is None or test_env == '':
        raise AutoApiError(AUTO_API_BASE_SQL_ENVIRONMENT_EXECUTION_INVALID, value=(test_env,))
    try:
        normalized_test_env = int(test_env)
    except (TypeError, ValueError) as error:
        raise AutoApiError(AUTO_API_BASE_SQL_ENVIRONMENT_EXECUTION_INVALID_CODE_EXECUTION_INVALID,
                           value=(test_env,)) from error

    valid_envs = set(EnvironmentEnum.get_key_list())
    if any(
            isinstance(item, bool) or not isinstance(item, int) or item not in valid_envs
            for item in test_envs
    ):
        raise AutoApiError(AUTO_API_BASE_SQL_ENVIRONMENT_CONFIG_EXECUTION_INVALID_CODE_CONFIG_EXECUTION_INVALID,
                           value=(config_name, test_envs))
    return normalized_test_env in test_envs


def should_execute_sql(sql_item: dict[str, Any], test_env: int | str) -> bool:
    return should_apply_env_item(sql_item, test_env, config_name='SQL')
