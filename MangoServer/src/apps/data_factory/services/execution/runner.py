# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务

from src.apps.data_factory.services.execution.parts.execution import DataFactoryRunnerExecutionMixin
from src.apps.data_factory.services.execution.parts.persistence import DataFactoryRunnerPersistenceMixin
from src.apps.data_factory.services.execution.parts.preview import DataFactoryRunnerPreviewMixin
from src.apps.data_factory.services.execution.parts.scene import DataFactoryRunnerSceneMixin


class DataFactoryRunner(DataFactoryRunnerPreviewMixin, DataFactoryRunnerSceneMixin, DataFactoryRunnerExecutionMixin,
                        DataFactoryRunnerPersistenceMixin):
    pass
