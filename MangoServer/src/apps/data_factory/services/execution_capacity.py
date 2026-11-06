import logging

from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.test_center.enums.data_source import DataSourceTypeEnum

logger = logging.getLogger(__name__)


class DatasourceExecutionCapacityService:
    """工厂新增造数的清理积压背压；不接管业务请求并发。"""

    @staticmethod
    def targets_by_scope(scopes, policy):
        scopes = set(scopes)
        targets = {scope: {} for scope in scopes}
        if scopes:
            for binding in DataFactoryQuerySelector.execution_targets(
                    {product for product, _ in scopes}, {env for _, env in scopes}):
                key = (binding.datasource_alias.project_product_id, binding.environment)
                if key in targets:
                    group = Governor.target_policy(binding.database, policy)[2]
                    if group is not None:
                        targets[key][group] = binding.database
        return targets

    @classmethod
    def wait_for_fixture(cls, template, test_object_id):
        from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver
        test_object = DataFactoryDatasourceResolver.get_test_object(test_object_id)
        cls.wait_for_cleanup_backlog(template.project_product_id, test_object.environment)

    @classmethod
    def wait_for_cleanup_backlog(cls, product, environment):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        from django.db import DatabaseError
        from src.apps.data_factory.exceptions import DATASOURCE_GOVERNOR_UNAVAILABLE
        waited = False
        while True:
            try:
                policy = Governor.policy()
                targets = cls.targets_by_scope({(product, environment)}, policy)[(product, environment)]
                groups = {group: [] for group in targets}
                for target in DataFactoryQuerySelector.performance_targets():
                    group = Governor.target_policy(target, policy)[2]
                    if group in groups:
                        groups[group].append(target.id)
                congested = False
                for group, ids in groups.items():
                    if not ids:
                        continue
                    limit = Governor.target_policy(targets[group], policy)[1].cleanup_backlog_limit
                    kwargs = {'resource_connection_ids': ids} if targets[group].db_type == DataSourceTypeEnum.ELASTICSEARCH.value else {}
                    if DataFactoryQuerySelector.cleanup_backlog(ids, limit, **kwargs) >= limit:
                        congested = True
                        break
            except DatabaseError as error:
                raise Governor.infrastructure_error(DATASOURCE_GOVERNOR_UNAVAILABLE) from error
            if not congested:
                if waited:
                    logger.debug('event=fixture_cleanup_backlog_resumed product_id=%s environment=%s', product, environment)
                return
            if not waited:
                logger.debug('event=fixture_cleanup_backlog_wait product_id=%s environment=%s', product, environment)
                waited = True
            # 不持有业务连接/事务/SQL名额，scheduler 和同步清理均不走此入口。
            DatasourceWaitService.pause(1)
