# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-05 12:40
# @Author : 毛鹏
from mangokit.log_collector import set_log

from src.settings.settings import IS_DEBUG
from src.tools import project_dir

log = set_log(project_dir.logs(), IS_DEBUG)
