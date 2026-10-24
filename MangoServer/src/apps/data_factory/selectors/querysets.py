from src.apps.data_factory.models import (
    DataFactoryCaseConfig,
    DataFactoryDatasourceAlias,
    DataFactoryDatasourceBinding,
    DataFactoryEntity,
    DataFactoryEntityStatusLog,
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryField,
    DataFactoryTemplate,
    SqlExecutionRecord,
)


class DataFactoryQuerySelector:
    @staticmethod
    def database_bindings(database_id, *, user):
        from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService

        queryset = DataFactoryDatasourceBinding.objects.filter(database_id=database_id)
        if user is None:
            return queryset.none()
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            queryset = queryset.filter(datasource_alias__project_product_id__in=
                                       ProjectProductScopeService.project_product_ids_for_user(user))
        return queryset.values(
            'id', 'environment', 'database_name', 'schema_name', 'redis_db', 'db_c_status', 'db_rud_status',
            'datasource_alias_id',
            'datasource_alias__name', 'datasource_alias__project_product_id',
            'datasource_alias__project_product__name',
            'datasource_alias__project_product__project__name',
        )

    @staticmethod
    def data_factory_case_config():
        return DataFactoryCaseConfig.objects.all()

    @staticmethod
    def data_factory_datasource_alias():
        return DataFactoryDatasourceAlias.objects.all()

    @staticmethod
    def data_factory_datasource_binding():
        return DataFactoryDatasourceBinding.objects.all()

    @staticmethod
    def data_factory_entity():
        return DataFactoryEntity.objects.all()

    @staticmethod
    def data_factory_entity_status_log():
        return DataFactoryEntityStatusLog.objects.all()

    @staticmethod
    def data_factory_execution():
        return DataFactoryExecution.objects.all()

    @staticmethod
    def data_factory_execution_item():
        return DataFactoryExecutionItem.objects.all()

    @staticmethod
    def data_factory_field():
        return DataFactoryField.objects.all()

    @staticmethod
    def data_factory_template():
        return DataFactoryTemplate.objects.all()

    @staticmethod
    def sql_execution_record():
        return SqlExecutionRecord.objects.all()
