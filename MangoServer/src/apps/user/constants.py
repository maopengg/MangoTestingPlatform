
# 子资产沿所属父记录取得产品范围；可空的多类归属使用多个路径。
RELATED_PRODUCT_SCOPE_PATHS = {
    'auto_ui.pageelement': ('page__project_product_id',),
    'auto_ui.pagestepsdetailed': ('page_step__project_product_id',),
    'auto_ui.uicasestepsdetailed': ('case__project_product_id',),
    'auto_api.apicasedetailed': ('case__project_product_id',),
    'auto_api.apicasedetailedparameter': ('case_detailed__case__project_product_id',),
    'auto_api.grpcmethoddefinition': ('service__project_product_id',),
    'auto_data_factory.datafactorydatasourcebinding': ('datasource_alias__project_product_id',),
    'auto_data_factory.datafactoryfield': ('entity__project_product_id',),
    'auto_data_factory.datafactorycaseconfig': ('template__project_product_id',),
    'auto_data_factory.datafactoryexecutionitem': ('execution__project_product_id',),
    'task_center.tasksdetails': ('task__project_product_id',),
    'task_center.schedulefire': ('task__project_product_id', 'group_execution__project_product_id', 'test_suite__project_product_id'),
    'monitoring.monitoringreport': ('task__project_product_id',),
    'gray_config.grayyamlfilebinding': ('yaml_file__project_product_id',),
    'gray_config.automationcasegrayconfig': (
        'api_case__project_product_id', 'ui_case__project_product_id',
        'api_case_detailed__case__project_product_id',
        'api_case_detailed_parameter__case_detailed__case__project_product_id',
    ),
    'gray_config.grayexecutionlog': (
        'gray_feature__project_product_id', 'yaml_file__project_product_id',
        'yaml_file_binding__yaml_file__project_product_id',
    ),
}
