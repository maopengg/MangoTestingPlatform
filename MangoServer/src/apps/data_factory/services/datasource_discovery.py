import base64
import json
import ssl
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.core.cache import cache
from django.utils import timezone
from sqlalchemy import inspect, text

from src.apps.data_factory.models import Database
from src.apps.data_factory.schemas.datasource_alias import DataSourceAliasSuggestion
from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource import DataFactoryDatasource
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.data_factory.services.elasticsearch_http import open_elasticsearch_request
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
from src.apps.system.services.ai.client import AiService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.exceptions import (
    DATA_SOURCE_DISCOVERY_FAILED, DATA_SOURCE_DISCOVERY_NOT_FOUND,
    DATA_SOURCE_DISCOVERY_UNSUPPORTED,
    DATA_SOURCE_ALIAS_SUGGESTION_FAILED, TestCenterError,
)
from src.apps.test_center.services.data_source import DataSourceConnectionService
from src.common.exceptions import MangoServerError
from src.common.prompts import get_prompt


class DataSourceDiscoveryService:
    """全局连接只读发现及逻辑数据库别名建议，不写入连接配置。"""

    @staticmethod
    def get_database(source_id):
        database = Database.objects.filter(id=source_id).first()
        if database is None:
            raise TestCenterError(DATA_SOURCE_DISCOVERY_NOT_FOUND)
        return database

    @staticmethod
    def require_relational(database):
        if database.db_type not in {DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value}:
            raise TestCenterError(DATA_SOURCE_DISCOVERY_UNSUPPORTED)

    @classmethod
    def tables(cls, database, *, refresh=False, table_name=None):
        if database.db_type != DataSourceTypeEnum.ELASTICSEARCH.value:
            cls.require_relational(database)
        elif table_name:
            raise TestCenterError(DATA_SOURCE_DISCOVERY_UNSUPPORTED)
        version = database.cache_key
        key = f'data_source:metadata:{database.id}:{version}:{table_name or "tables"}'
        result = None if refresh else cache.get(key)
        if result is None:
            try:
                if database.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
                    items = cls.indices(database)
                elif table_name:
                    items = DataFactoryDiscover.get_table_schema(
                        database, table_name, timeout_seconds=DataSourceConnectionService.timeout_seconds(),
                    )
                else:
                    items = DataFactoryDiscover.get_tables(
                        database, timeout_seconds=DataSourceConnectionService.timeout_seconds(),
                    )
            except MangoServerError:
                raise
            except Exception as error:
                raise TestCenterError(DATA_SOURCE_DISCOVERY_FAILED) from error
            result = {'items': items, 'scanned_at': timezone.now().isoformat()}
            cache.set(key, result, 30 * 60)
        return result

    @classmethod
    @SqlExecutionAuditService.audited(DatasourceAuditStageEnum.DISCOVER_INDICES.value)
    def indices(cls, database):
        options = database.extra_config or {}
        scheme = options.get('scheme', 'http')
        prefix = str(options.get('path_prefix', '')).strip('/')
        url = f'{scheme}://{database.host}:{database.port}/'
        if prefix:
            url += prefix + '/'
        url += '_cat/indices?format=json&h=index,status,health'
        headers = {'Accept': 'application/json'}
        if database.user or database.password:
            credential = base64.b64encode(f'{database.user}:{database.password}'.encode()).decode('ascii')
            headers['Authorization'] = f'Basic {credential}'
        context = ssl._create_unverified_context() if scheme == 'https' and not options.get('verify_certs',
                                                                                            True) else None
        request = urllib_request.Request(url, headers=headers, method='GET')
        try:
            with open_elasticsearch_request(
                    request, timeout=DataSourceConnectionService.timeout_seconds(), target=database, context=context,
            ) as response:
                body = response.read(1_048_577)
            if len(body) > 1_048_576:
                raise TestCenterError(DATA_SOURCE_DISCOVERY_FAILED)
            items = json.loads(body)
        except urllib_error.HTTPError as error:
            DataSourceErrorService.raise_elasticsearch_http_error(database, error)
        except (urllib_error.URLError, TimeoutError, ValueError, OSError) as error:
            DataSourceErrorService.raise_elasticsearch_transport_error(database, error)
        return [{'name': item['index'], 'comment': f"{item.get('status', '')} / {item.get('health', '')}"}
                for item in items if item.get('index')]

    @classmethod
    def databases(cls, source_id, *, refresh=False):
        source = cls.get_database(source_id)
        cls.require_relational(source)
        target = DatasourceTargetService.maintenance(source)
        key = 'data_source:databases:' + target.cache_key
        names = None if refresh else cache.get(key)
        if names is None:
            names = cls.discover_database_names(target)
            cache.set(key, names, 30 * 60)
        return [{'name': name} for name in sorted(names)]

    @classmethod
    def discover_database_names(cls, target):
        engine = DataFactoryDatasource.create_engine(target,
                                                     timeout_seconds=DataSourceConnectionService.timeout_seconds())
        try:
            if target.db_type == DataSourceTypeEnum.MYSQL.value:
                return inspect(engine).get_schema_names()
            with engine.connect() as connection:
                return [row[0] for row in connection.execute(text(
                    "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate "
                    "AND has_database_privilege(datname, 'CONNECT') ORDER BY datname"
                ))]
        except Exception as error:
            from src.apps.data_factory.services.data_source_error import DataSourceErrorService
            DataSourceErrorService.raise_sql_error(target, error)
        finally:
            engine.dispose()

    @classmethod
    def schemas(cls, source_id, database_name):
        source = cls.get_database(source_id)
        if source.db_type != DataSourceTypeEnum.POSTGRESQL.value:
            raise TestCenterError(DATA_SOURCE_DISCOVERY_UNSUPPORTED)
        target = DatasourceTargetService.build(source, database_name=database_name or 'postgres')
        engine = DataFactoryDatasource.create_engine(target,
                                                     timeout_seconds=DataSourceConnectionService.timeout_seconds())
        try:
            with engine.connect() as connection:
                return [{'name': row[0]} for row in connection.execute(text(
                    "SELECT nspname FROM pg_namespace WHERE has_schema_privilege(oid, 'USAGE') "
                    "AND nspname NOT IN ('pg_catalog','information_schema') "
                    "AND nspname NOT LIKE 'pg_toast%' AND nspname NOT LIKE 'pg_temp_%' ORDER BY nspname"
                ))]
        except Exception as error:
            DataSourceErrorService.raise_sql_error(target, error)
        finally:
            engine.dispose()

    @classmethod
    def suggest_alias(cls, source_id, name=''):
        source = cls.get_database(source_id)
        context = {'database_name': name or source.display_name,
                   'database_type': DataSourceTypeEnum.obj()[source.db_type],
                   'existing_aliases': [], 'tables': [], 'metadata_available': False}
        if name and source.db_type in {DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value}:
            try:
                target = DatasourceTargetService.build(source, database_name=name,
                                                       schema_name='public' if source.db_type == DataSourceTypeEnum.POSTGRESQL.value else '')
                context['tables'] = cls.alias_metadata(target)
                context['metadata_available'] = True
            except Exception:
                pass
        prompt = get_prompt('data_source.alias')
        try:
            response = AiService.json_chat(messages=[
                {'role': 'system', 'content': prompt.system},
                {'role': 'user', 'content': prompt.render('user', context=json.dumps(context, ensure_ascii=False))},
            ], max_tokens=500, thinking={'type': 'disabled'})
            result = DataSourceAliasSuggestion.model_validate(
                json.loads(response['choices'][0]['message']['content'])).model_dump()
        except Exception as error:
            raise TestCenterError(DATA_SOURCE_ALIAS_SUGGESTION_FAILED) from error
        return {**result, 'metadata_available': context['metadata_available']}

    @staticmethod
    def alias_metadata(target):
        engine = DataFactoryDatasource.create_engine(target,
                                                     timeout_seconds=DataSourceConnectionService.timeout_seconds())
        try:
            if target.db_type == DataSourceTypeEnum.MYSQL.value:
                query = text("SELECT TABLE_NAME AS name, COALESCE(TABLE_COMMENT, '') AS comment "
                             "FROM information_schema.TABLES WHERE TABLE_SCHEMA = :database_name "
                             "AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME LIMIT 60")
                parameters = {'database_name': target.database_name}
            else:
                query = text("SELECT n.nspname AS schema, c.relname AS name, "
                             "COALESCE(obj_description(c.oid, 'pg_class'), '') AS comment "
                             "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                             "WHERE c.relkind IN ('r','p') AND has_schema_privilege(n.oid, 'USAGE') "
                             "AND has_table_privilege(c.oid, 'SELECT') AND n.nspname NOT IN ('pg_catalog','information_schema') "
                             "ORDER BY n.nspname, c.relname LIMIT 60")
                parameters = {}
            with engine.connect() as connection:
                return [dict(row) for row in connection.execute(query, parameters).mappings()]
        finally:
            engine.dispose()
