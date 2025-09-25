# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 13:04
# @Author : 毛鹏
from mangotools.mangos import GitRepoOperator
from src.enums.system_enum import CacheDataKeyEnum
from src.exceptions import PytestError, ERROR_MSG_0043
from src.tools import project_dir
from src.tools.log_collector import log


def git_obj() -> GitRepoOperator:
    from src.auto_test.auto_system.models import CacheData
    repo_url = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_URL.name).value
    username = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_USERNAME.name).value
    password = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_PASSWORD.name).value
    if repo_url is None or repo_url == "":
        raise PytestError(*ERROR_MSG_0043)
    repo = GitRepoOperator(repo_url, project_dir.root_path(), log.pytest, username, password)
    return repo
