"""ES 精确索引/文档操作。资源所有权由调用方验证，本模块不提供任意写入或批量删除。"""
import base64
import json
import re
import ssl
from urllib import error as urllib_error, parse, request

from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
from src.apps.data_factory.exceptions import (
    DataFactoryError, DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID,
)
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.protocols.elasticsearch_http import open_elasticsearch_request
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService


class ElasticsearchDatasourceService:
    @staticmethod
    def resource_error(definition, *, reason):
        error = DataFactoryError(definition)
        error.msg += '。' + reason
        return error

    @classmethod
    def resolve_index(cls, target, name):
        """只解析一个精确索引/别名，冻结物理索引和UUID；拒绝多目标、过滤及路由别名。"""
        def read():
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,254}', name):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('必须指定精确索引或别名，不允许通配、多索引或路径',))
            options = target.extra_config or {}
            scheme = options.get('scheme', 'http')
            prefix = str(options.get('path_prefix', '') or '').strip('/')
            url = f'{scheme}://{target.host}:{target.port}' + (f'/{prefix}' if prefix else '')
            url += '/' + parse.quote(name, safe='') + '?filter_path=*.settings.index.uuid,*.aliases'
            headers = {'Accept': 'application/json'}
            if target.user or target.password:
                headers['Authorization'] = 'Basic ' + base64.b64encode(f'{target.user}:{target.password}'.encode()).decode()
            tls = ssl._create_unverified_context() if scheme == 'https' and not options.get('verify_certs', True) else None
            try:
                with open_elasticsearch_request(request.Request(url, headers=headers), timeout=5,
                                                target=target, context=tls) as response:
                    body = response.read(1_048_577)
                if len(body) > 1_048_576:
                    raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('索引元数据响应过大',))
                result = json.loads(body)
            except urllib_error.HTTPError as error:
                DataSourceErrorService.raise_elasticsearch_http_error(target, error)
            except (urllib_error.URLError, OSError, ValueError) as error:
                DataSourceErrorService.raise_elasticsearch_transport_error(target, error, timeout=5)
            if not isinstance(result, dict) or len(result) != 1:
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('索引或别名必须唯一指向一个物理索引',))
            physical, metadata = next(iter(result.items()))
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,254}', physical) or not isinstance(metadata, dict):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('物理索引元数据格式不合法',))
            aliases = metadata.get('aliases', {})
            settings = metadata.get('settings')
            index_settings = settings.get('index') if isinstance(settings, dict) else None
            index_uuid = index_settings.get('uuid') if isinstance(index_settings, dict) else None
            if (not isinstance(index_uuid, str) or not 1 <= len(index_uuid) <= 128
                    or not isinstance(aliases, dict) or (physical != name and name not in aliases)
                    or (physical != name and (not isinstance(aliases[name], dict)
                        or any(key in aliases[name] for key in ('filter', 'routing', 'index_routing', 'search_routing'))))):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                                       value=('无法确认索引UUID，或别名带有过滤/路由约束，禁止猜测清理目标',))
            return physical, index_uuid
        return SqlExecutionAuditService.call(target, {'operation': 'resolve_cleanup_index', 'index': name}, read,
                                              stage=SqlExecutionAuditService.current_source().get('source_stage') or DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value)

    @classmethod
    def document(cls, target, index, document_id, *, delete=False, timeout=5, expected=None, tenant_path=None,
                 realtime=True):
        operation = 'delete_document' if delete else 'get_document'
        return SqlExecutionAuditService.call(
            target, {'operation': operation, 'index': index, 'document_id': document_id,
                     'realtime': realtime if not delete else None,
                     'if_seq_no': (expected or {}).get('_seq_no') if delete else None,
                     'if_primary_term': (expected or {}).get('_primary_term') if delete else None},
            lambda: cls.request_document(target, index, document_id, delete=delete, timeout=timeout,
                                         expected=expected, tenant_path=tenant_path, realtime=realtime),
            stage=SqlExecutionAuditService.current_source().get('source_stage') or DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value,
            result_summary=lambda result: {
                'result': result, 'row_count': int(not delete and result is not None),
                'affected_rows': int(delete and isinstance(result, dict) and result.get('result') == 'deleted'),
            },
        )

    @staticmethod
    def request_document(target, index, document_id, *, delete, timeout, expected=None, tenant_path=None,
                         realtime=True):
        if (not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,254}', index)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', document_id)):
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('必须指定精确索引及文档ID',))
        options = target.extra_config or {}
        scheme = options.get('scheme', 'http')
        prefix = str(options.get('path_prefix', '') or '').strip('/')
        url = f'{scheme}://{target.host}:{target.port}' + (f'/{prefix}' if prefix else '')
        url += '/' + parse.quote(index, safe='') + '/_doc/' + parse.quote(document_id, safe='')
        if delete:
            sequence = (expected or {}).get('_seq_no')
            term = (expected or {}).get('_primary_term')
            if type(sequence) is not int or sequence < 0 or type(term) is not int or term < 1:
                raise ElasticsearchDatasourceService.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID,
                    reason='ES文档缺少有效的_seq_no或_primary_term版本，无法安全执行条件删除。请检查文档回查结果')
            # 删除响应不等待刷新；sample 同时核对实时和非实时视图，完整观察窗口仍必须完成。
            url += f'?refresh=false&if_seq_no={sequence}&if_primary_term={term}'
        else:
            # 回查仅获取租户字段和文档版本，不读取无关业务正文或凭据。
            url += '?_source_includes=' + parse.quote(tenant_path, safe='') if tenant_path else '?_source=false'
            if not realtime:
                url += '&realtime=false'
        headers = {'Accept': 'application/json'}
        if target.user or target.password:
            credentials = base64.b64encode(f'{target.user}:{target.password}'.encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'
        tls = ssl._create_unverified_context() if scheme == 'https' and not options.get('verify_certs', True) else None
        try:
            with open_elasticsearch_request(request.Request(url, headers=headers, method='DELETE' if delete else 'GET'),
                                            timeout=timeout, target=target, context=tls) as response:
                body = response.read(1_048_577)
            if len(body) > 1_048_576:
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=(f'ES清理响应超过1048576字节，已读取至少 {len(body)} 字节；请管理员检查清理回查返回字段',))
            result = json.loads(body)
            if not isinstance(result, dict) or result.get('_id') != document_id or result.get('_index') != index:
                raise ElasticsearchDatasourceService.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID,
                    reason='ES响应结构、文档ID或索引与本次精确请求不一致。请检查ES响应和执行快照')
            return None if not delete and result.get('found') is False else result
        except urllib_error.HTTPError as error:
            if error.code == 404:
                try:
                    missing = json.loads(error.read(1_048_577))
                except (ValueError, OSError):
                    missing = {}
                if (isinstance(missing, dict) and missing.get('_id') == document_id and missing.get('_index') == index
                        and (missing.get('found') is False or missing.get('result') == 'not_found')):
                    return None
            DataSourceErrorService.raise_elasticsearch_http_error(target, error)
        except (urllib_error.URLError, OSError, ValueError) as error:
            DataSourceErrorService.raise_elasticsearch_transport_error(target, error, timeout=timeout)
