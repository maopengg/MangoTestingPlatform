# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂子路由

from django.urls import path

from src.apps.auto_data_factory.views.discover import DataFactoryDiscoverViews
from src.apps.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasCRUD
from src.apps.auto_data_factory.views.datasource_binding import DataFactoryDatasourceBindingCRUD
from src.apps.auto_data_factory.views.entity import (
    DataFactoryEntityCRUD,
    DataFactoryEntityViews,
)
from src.apps.auto_data_factory.views.field import DataFactoryFieldCRUD, DataFactoryFieldViews
from src.apps.auto_data_factory.views.execution import (
    DataFactoryExecutionCRUD,
    DataFactoryExecutionViews,
)
from src.apps.auto_data_factory.views.execution_item import DataFactoryExecutionItemCRUD
from src.apps.auto_data_factory.views.template import DataFactoryTemplateCRUD, DataFactoryTemplateViews
from src.apps.auto_data_factory.views.case_config import (
    DataFactoryCaseConfigCRUD,
    DataFactoryCaseConfigViews,
)

urlpatterns = [
    path("datasource-alias", DataFactoryDatasourceAliasCRUD.as_view()),
    path("datasource-binding", DataFactoryDatasourceBindingCRUD.as_view()),
    path("entity", DataFactoryEntityCRUD.as_view()),
    path("entity/batch-generate", DataFactoryEntityViews.as_view({'post': 'batch_generate'})),
    path("entity/copy", DataFactoryEntityViews.as_view({'post': 'copy'})),
    path("entity/status", DataFactoryEntityViews.as_view({'put': 'status'})),
    path("field", DataFactoryFieldCRUD.as_view()),
    path("field/batch-save", DataFactoryFieldViews.as_view({'post': 'batch_save'})),
    path("field/preview-values", DataFactoryFieldViews.as_view({'post': 'preview_values'})),
    path("template", DataFactoryTemplateCRUD.as_view()),
    path("template/copy", DataFactoryTemplateViews.as_view({'post': 'copy'})),
    path("template/status", DataFactoryTemplateViews.as_view({'put': 'status'})),
    path("template/sync-fields", DataFactoryTemplateViews.as_view({'post': 'sync_fields'})),
    path("template/preview", DataFactoryTemplateViews.as_view({'post': 'preview'})),
    path("template/debug-run", DataFactoryTemplateViews.as_view({'post': 'debug_run'})),
    path("template/debug-cleanup", DataFactoryTemplateViews.as_view({'post': 'debug_cleanup'})),
    path("case-config", DataFactoryCaseConfigCRUD.as_view()),
    path("case-config/sort", DataFactoryCaseConfigViews.as_view({'put': 'put_case_sort'})),
    path("case-config/preview", DataFactoryCaseConfigViews.as_view({'post': 'preview'})),
    path("execution", DataFactoryExecutionCRUD.as_view()),
    path("execution/item", DataFactoryExecutionItemCRUD.as_view()),
    path("execution/detail", DataFactoryExecutionViews.as_view({'get': 'detail_view'})),
    path("execution/context", DataFactoryExecutionViews.as_view({'get': 'context'})),
    path("execution/cleanup", DataFactoryExecutionViews.as_view({'post': 'cleanup'})),
    path("discover/test-connection", DataFactoryDiscoverViews.as_view({'post': 'test_connection'})),
    path("discover/tables", DataFactoryDiscoverViews.as_view({'post': 'tables'})),
    path("discover/table", DataFactoryDiscoverViews.as_view({'post': 'table'})),
]
