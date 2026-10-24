# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务

from .runner_parts.execution import DataFactoryRunnerExecutionMixin
from .runner_parts.persistence import DataFactoryRunnerPersistenceMixin
from .runner_parts.preview import DataFactoryRunnerPreviewMixin
from .runner_parts.scene import DataFactoryRunnerSceneMixin


class DataFactoryRunner(DataFactoryRunnerPreviewMixin, DataFactoryRunnerSceneMixin, DataFactoryRunnerExecutionMixin,
                        DataFactoryRunnerPersistenceMixin):
    pass
