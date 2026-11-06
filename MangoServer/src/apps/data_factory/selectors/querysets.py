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
    def executions_for_case_attempt(detail_id, attempt):
        from django.db.models.fields.json import KeyTransform
        from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
        # 键以双下划线开头，不能拼进 Django lookup 路径，否则会被拆成空键。
        return DataFactoryExecution.objects.alias(
            report_owner=KeyTransform(CLEANUP_REPORT_CONTEXT_KEY, 'context')).filter(
            report_owner__parent_case_detail_id=detail_id, report_owner__parent_attempt=attempt)

    @staticmethod
    def performance_targets():
        from src.apps.data_factory.models import Database
        return Database.objects.only('id', 'db_type', 'host', 'port').all()

    @staticmethod
    def cleanup_backlog(database_ids, limit, *, resource_connection_ids=()):
        from django.db.models import Q, Exists, OuterRef
        from src.apps.data_factory.enums import (
            DataFactoryCleanupStatusEnum, DataFactoryCleanupStrategyEnum, DataFactoryExecutionStatusEnum,
        )
        from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
        # 只统计已可清理的自动清理明细；运行中夹具尚未交还，不能挡住它所属 Case 的后续造数。
        targets = Q(database_id__in=database_ids)
        if resource_connection_ids:
            # CleanupResourceState 最多 5 个 ES 快照；按执行时连接ID跨产品归组，不按主表库猜ES。
            for index in range(5):
                targets |= Q(**{f'cleanup_resources__snapshots__{index}__connection_id__in': resource_connection_ids})
        query = DataFactoryExecutionItem.objects.filter(targets,
            cleanup_strategy=DataFactoryCleanupStrategyEnum.EXECUTION_END.value,
        ).exclude(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value).alias(
            has_cleanup_task=Exists(TaskCenterQuerySelector.cleanup_for_execution(OuterRef('execution_id'))),
        ).filter(
            Q(has_cleanup_task=True)
            | Q(execution__status=DataFactoryExecutionStatusEnum.FAIL.value)
            | Q(cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value)
            | Q(execution__cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value)
        )
        # 水位判断只需读取上限条主键，不扫描/返回明细数据或执行上下文。
        return len(list(query.order_by().values_list('id', flat=True)[:limit]))

    @staticmethod
    def execution_targets(products, environments):
        return DataFactoryDatasourceBinding.objects.filter(
            datasource_alias__project_product_id__in=products, environment__in=environments,
        ).select_related('database', 'datasource_alias').only(
            'id', 'environment', 'datasource_alias_id', 'datasource_alias__project_product_id',
            'database_id', 'database__id', 'database__db_type', 'database__host', 'database__port', 'database__user',
        )

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
