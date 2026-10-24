# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import json
from urllib.parse import urlparse, parse_qs

from django.db.models import OuterRef, Subquery
from mangotools.enums import StatusEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_info import ApiInfoSerializersC, ApiInfoListSerializersC, \
    ApiInfoBoundCaseSerializers
from src.apps.auto_api.api.serializers.api_info_mutation import ApiInfoSerializers
from src.apps.auto_api.enums import ApiProtocolTypeEnum, MethodEnum
from src.apps.auto_api.exceptions import (
    AUTO_API_API_INFO_API_INFO_SCENARIO_ASSERTION_GENERATE_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiInfo,
    ApiInfoRelease,
)
from src.apps.auto_api.schemas.case_schema import (
    build_body_from_legacy,
    normalize_body_config_by_type,
    validate_body_config,
)
from src.apps.auto_api.schemas.config_fields import API_INFO_CONFIG_FIELDS
from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
from src.apps.auto_api.services.api_info.curl_import import parse_import_curl
from src.apps.auto_api.services.api_info.execution_parameters import ApiInfoExecutionParametersService
from src.apps.auto_api.api.serializers.api_info_execution import (
    ApiInfoExecutionTargetQuery, ApiInfoExecutionQuery, ApiInfoRuntimeParametersQuery,
)
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.test_case.test_api_info import TestApiInfo
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    API_BATCH_EXECUTION_VERSION_REQUIRED,
    API_EXECUTION_ITEMS_REQUIRED,
    API_EXECUTION_VERSION_BLOCKED,
    API_IMPORT_ONLY_CREATE_INVALID,
    API_IMPORT_ONLY_PROTOCOL_EDIT_INVALID,
    API_IMPORT_ONLY_PROTOCOL_SWITCH_INVALID,
    TEST_ENVIRONMENT_INVALID,
    TEST_ENVIRONMENT_REQUIRED,
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0071,
    RESPONSE_MSG_0072,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0083,
    RESPONSE_MSG_0137,
    RESPONSE_MSG_0138,
    RESPONSE_MSG_0140,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin, with_update_user
from src.common.utils.spreadsheet import read_excel_records


class ApiInfoCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiInfo
    queryset = ApiInfo.objects.all()
    serializer_class = ApiInfoSerializersC
    serializer = ApiInfoSerializers
    page_permission_key = 'api.info'
    not_matching_str = ModelCRUD.not_matching_str + [
        'project_product__api_client_type',
        'method',
        'protocol_type',
        'update_user',
    ]

    def get_serializer_class(self):
        if getattr(self.request, 'method', '').upper() == 'GET':
            return ApiInfoListSerializersC
        return super().get_serializer_class()

    @staticmethod
    def split_identity_and_config(data: dict) -> tuple[dict, dict]:
        identity_fields = {'id', 'project_product', 'module', 'name', 'update_user'}
        identity = {key: value for key, value in data.items() if key in identity_fields}
        config = {key: value for key, value in data.items() if key in API_INFO_CONFIG_FIELDS}
        if 'posterior_json_path' in data:
            config['posterior_json_path'] = data.get('posterior_json_path')
        if 'posterior_re' in data:
            config['posterior_re'] = data.get('posterior_re')
        if 'posterior_response' in data:
            config['posterior_json_path'] = data.get('posterior_response')
        if 'posterior_response_text' in data:
            config['posterior_re'] = data.get('posterior_response_text')
        if config.get('body_config') is not None:
            body_type = config.get('body_type') or data.get('body_type') or 'none'
            config['body_config'] = normalize_body_config_by_type(body_type, config.get('body_config'))
        if config.get('sse_config') is not None:
            config['sse_config'] = validate_body_config(config.get('sse_config'), 'SSE配置')
        return identity, config

    @classmethod
    def serializer_payload(cls, identity: dict, config: dict) -> dict:
        model_field_names = {field.name for field in cls.model._meta.concrete_fields}
        model_config = {key: value for key, value in config.items() if key in model_field_names}
        return {**identity, **model_config}

    @staticmethod
    def attach_runtime_config(instance: ApiInfo, config: dict):
        for key, value in config.items():
            setattr(instance, key, value)

    @classmethod
    def attach_merged_runtime_config(
            cls,
            instance: ApiInfo,
            current_runtime: ApiInfo,
            config: dict,
    ):
        cls.attach_runtime_config(
            instance,
            ApiInfoRuntimeService.current_payload(current_runtime),
        )
        cls.attach_runtime_config(instance, config)

    @classmethod
    def _create_with_version(cls, data: dict, *, operator_id: int | None = None, record_config: bool = True) -> dict:
        instance = ApiInfoMutationService.create_definition(
            data,
            operator_id=operator_id,
            record_config=record_config,
        )
        return dict(ApiInfoSerializersC(instance).data)

    @classmethod
    def _update_with_version(cls, _id: int, data: dict, *, operator_id: int | None = None,
                             record_config: bool = True) -> dict:
        instance = ApiInfoMutationService.update_definition(
            _id,
            data,
            operator_id=operator_id,
            record_config=record_config,
        )
        return dict(ApiInfoSerializersC(instance).data)

    @error_response('system')
    def post(self, request: Request):
        data = self.with_update_user(request, request.data)
        if data.get('protocol_type') in (ApiProtocolTypeEnum.MCP.value, ApiProtocolTypeEnum.GRPC.value):
            return ResponseData.fail(API_IMPORT_ONLY_CREATE_INVALID)
        if not self.has_data_scope_permission(request, data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        try:
            data_obj = self._create_with_version(data, operator_id=self.get_operator_id(request))
        except AutoApiError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0002, data_obj)

    @error_response('system')
    def put(self, request: Request):
        data = self.with_update_user(request, request.data)
        instance_id = request.data.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance) or not self.has_data_scope_permission(request,
                                                                                                                data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        target_protocol_type = data.get('protocol_type')
        if (
                instance.protocol_type in (ApiProtocolTypeEnum.MCP.value, ApiProtocolTypeEnum.GRPC.value)
                and target_protocol_type
                and instance.protocol_type != target_protocol_type
        ):
            return ResponseData.fail(API_IMPORT_ONLY_PROTOCOL_EDIT_INVALID)
        if (
                target_protocol_type in (ApiProtocolTypeEnum.MCP.value, ApiProtocolTypeEnum.GRPC.value)
                and instance.protocol_type != target_protocol_type
        ):
            return ResponseData.fail(API_IMPORT_ONLY_PROTOCOL_SWITCH_INVALID)
        try:
            data_obj = self._update_with_version(
                instance_id,
                data,
                operator_id=self.get_operator_id(request),
            )
        except AutoApiError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0082, data_obj)

    @classmethod
    def inside_post(cls, data: dict, *, record_config: bool = True) -> dict:
        return cls._create_with_version(data, record_config=record_config)

    @classmethod
    def inside_put(cls, _id: int, data: dict, *, record_config: bool = True) -> dict:
        return cls._update_with_version(_id, data, record_config=record_config)


class ApiInfoViews(ViewSet):
    model = ApiInfo
    serializer_class = ApiInfoSerializers
    action_permission_map = {
        'get_api_info_run': ('api.info:debug', 'api.info:execute'),
        'get_execution_parameters': ('api.info:debug', 'api.info:execute'),
        'api_info_batch_run': 'api.info:execute',
        'get_api_name': 'api.info',
        'get_bound_cases': 'api.info',
        'import_api': 'api.info:create',
        'post_upload_api': 'api.info:create',
        'put_auto_schema': 'api.info:status',
    }

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_execution_parameters(self, request: Request):
        query = ApiInfoExecutionTargetQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        target = query.validated_data
        api_info = ApiInfo.objects.filter(id=target['id']).first()
        if api_info is not None and not ApiInfoCRUD().has_instance_data_scope_permission(request, api_info):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(RESPONSE_MSG_0001, {
            'variables': ApiInfoExecutionParametersService.names(
                target['id'], revision_id=target.get('revision_id'), release_id=target.get('release_id'),
            ),
        })

    @action(methods=['get', 'post'], detail=False)
    @error_response('api')
    def get_api_info_run(self, request: Request):
        query = ApiInfoExecutionQuery(data=request.data if request.method == 'POST' else request.query_params)
        query.is_valid(raise_exception=True)
        target = query.validated_data
        api_info_id = target['id']
        test_env = target['test_env']
        revision_id = target.get('revision_id')
        release_id = target.get('release_id')
        api_info = ApiInfo.objects.filter(id=api_info_id).first()
        if api_info is not None and not ApiInfoCRUD().has_instance_data_scope_permission(request, api_info):
            return ResponseData.fail(RESPONSE_MSG_0210)
        api_info_list = request.query_params.getlist('id[]')

        if not api_info_id and api_info_list:
            return ResponseData.fail(API_BATCH_EXECUTION_VERSION_REQUIRED)
        else:
            api_info_res: dict = TestApiInfo(request.user['id'], test_env).api_info_run(
                api_info_id,
                revision_id=int(revision_id) if revision_id else None,
                release_id=int(release_id) if release_id else None,
                **({'runtime_parameters': target['runtime_parameters']} if target['runtime_parameters'] else {}),
            )
            execution_result = ExecutionResultService.save_result(
                source_type=ExecutionResultService.SOURCE_PAGE,
                target_type=ExecutionResultService.TARGET_API_INFO,
                target_id=int(api_info_id),
                revision_id=int(revision_id) if revision_id else None,
                release_id=int(release_id) if release_id else None,
                test_env=int(test_env) if test_env not in [None, ''] else None,
                result_data=api_info_res,
                trigger_user_id=request.user.get('id'),
            )
            api_info_res['execution_result_id'] = execution_result.id
            response_data = ExecutionResultService.serialize_run_response(execution_result)
            return ResponseData.success(RESPONSE_MSG_0072, response_data)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def api_info_batch_run(self, request: Request):
        runtime_query = ApiInfoRuntimeParametersQuery(data=request.data)
        runtime_query.is_valid(raise_exception=True)
        runtime_parameters = runtime_query.validated_data['runtime_parameters']
        test_env = request.data.get('test_env')
        api_items = request.data.get('api_items') or []
        if test_env in [None, '']:
            return ResponseData.fail(TEST_ENVIRONMENT_REQUIRED)
        try:
            test_env = int(test_env)
        except (TypeError, ValueError):
            return ResponseData.fail(TEST_ENVIRONMENT_INVALID)
        if not isinstance(api_items, list) or not api_items:
            return ResponseData.fail(API_EXECUTION_ITEMS_REQUIRED)

        release_map = {}
        blocked_items = []
        for index, item in enumerate(api_items, start=1):
            api_info_id = item.get('api_info_id') if isinstance(item, dict) else None
            release_id = item.get('api_info_release_id') if isinstance(item, dict) else None
            try:
                api_info_id = int(api_info_id)
                release_id = int(release_id)
            except (TypeError, ValueError):
                blocked_items.append({'index': index, 'reason': '接口ID或发布版本ID不合法'})
                continue
            release = ApiInfoRelease.objects.select_related('revision', 'api_info').filter(
                id=release_id,
                api_info_id=api_info_id,
                status=ApiInfoRelease.STATUS_PUBLISHED,
            ).first()
            if not release:
                blocked_items.append({
                    'index': index,
                    'api_info_id': api_info_id,
                    'api_info_release_id': release_id,
                    'reason': '接口发布版本不存在或未发布',
                })
                continue
            if not ApiInfoCRUD().has_instance_data_scope_permission(request, release.api_info):
                return ResponseData.fail(RESPONSE_MSG_0210)
            release_map[api_info_id] = release

        if blocked_items:
            return ResponseData.fail(API_EXECUTION_VERSION_BLOCKED, blocked_items)

        results = []
        success_count = 0
        fail_count = 0
        for api_info_id, release in release_map.items():
            try:
                api_info_res: dict = TestApiInfo(request.user['id'], test_env).api_info_run(
                    api_info_id,
                    revision_id=release.revision_id,
                    release_id=release.id,
                    **({'runtime_parameters': runtime_parameters} if runtime_parameters else {}),
                )
                execution_result = ExecutionResultService.save_result(
                    source_type=ExecutionResultService.SOURCE_PAGE,
                    target_type=ExecutionResultService.TARGET_API_INFO,
                    target_id=api_info_id,
                    revision_id=release.revision_id,
                    release_id=release.id,
                    test_env=test_env,
                    result_data=api_info_res,
                    trigger_user_id=request.user.get('id'),
                )
                if api_info_res.get('status') == StatusEnum.SUCCESS.value:
                    success_count += 1
                else:
                    fail_count += 1
                results.append(ExecutionResultService.serialize_run_response(execution_result))
            except Exception as error:
                fail_count += 1
                error_result = {
                    'api_info_id': api_info_id,
                    'release_id': release.id,
                    'revision_id': release.revision_id,
                    'error_msg': str(error),
                }
                execution_result = ExecutionResultService.save_result(
                    source_type=ExecutionResultService.SOURCE_PAGE,
                    target_type=ExecutionResultService.TARGET_API_INFO,
                    target_id=api_info_id,
                    revision_id=release.revision_id,
                    release_id=release.id,
                    test_env=test_env,
                    status=StatusEnum.FAIL.value,
                    error_message=str(error),
                    result_data=error_result,
                    trigger_user_id=request.user.get('id'),
                )
                results.append(ExecutionResultService.serialize_run_response(execution_result))

        return ResponseData.success(RESPONSE_MSG_0072, {
            'total': len(results),
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results,
        })

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_api_name(self, request: Request):
        """
        获取用户名称
        :param request:
        :return:
        """
        current_release = ApiInfoRelease.objects.filter(
            api_info_id=OuterRef('pk'),
            is_current=True,
            status=ApiInfoRelease.STATUS_PUBLISHED,
        ).order_by('-version_no')
        queryset = self.model.objects.filter(
            module=request.query_params.get('module_id'),
        ).annotate(
            published_release_id=Subquery(current_release.values('id')[:1]),
            published_revision_id=Subquery(current_release.values('revision_id')[:1]),
            published_version_label=Subquery(current_release.values('version_label')[:1]),
        ).order_by('-id')
        data = []
        for item in queryset:
            is_published = bool(item.published_release_id)
            publish_text = f"已发布 {item.published_version_label}" if item.published_version_label else '已发布'
            data.append({
                'key': item.id,
                'title': f"{item.name}（{publish_text if is_published else '未发布'}）",
                'name': item.name,
                'publication_status': 'published' if is_published else 'unpublished',
                'published_release_id': item.published_release_id,
                'published_revision_id': item.published_revision_id,
                'published_version_label': item.published_version_label,
                'disabled': not is_published,
            })
        return ResponseData.success(RESPONSE_MSG_0071, data)

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_bound_cases(self, request: Request):
        api_info_id = request.query_params.get('id') or request.query_params.get('api_info_id')
        api_info = self.model.objects.filter(id=api_info_id).first()
        if not api_info:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not ApiInfoCRUD().has_instance_data_scope_permission(request, api_info):
            return ResponseData.fail(RESPONSE_MSG_0210)

        queryset = ApiCase.objects.filter(apicasedetailed__api_info=api_info) \
            .select_related(
            'project_product',
            'module',
            'case_people',
            'update_user',
        ) \
            .distinct() \
            .order_by('id')
        data = ApiInfoBoundCaseSerializers(instance=queryset, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data, queryset.count())

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def import_api(self, request: Request):
        parsed = parse_import_curl(request.data.get('curl_command'))
        url_components = urlparse(parsed.url)
        path = url_components.path
        result = {
            'name': request.data.get('name'),
            'module': request.data.get('module'),
            'project_product': request.data.get('project_product'),
            'url': path,
            'method': MethodEnum.get_key(parsed.method),
            'headers': dict(parsed.header),
        }
        result = with_update_user(result, request)
        query_params = parse_qs(url_components.query)
        params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        if params:
            result['params'] = json.dumps(params, indent=4, ensure_ascii=False)
        body_type, body_config = build_body_from_legacy(
            data=parsed.data if parsed.json is None else None,
            json_body=parsed.json,
        )
        result['body_type'] = body_type
        result['body_config'] = body_config
        data = ApiInfoCRUD.inside_post(result)
        return ResponseData.success(RESPONSE_MSG_0140, data=data)

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def post_upload_api(self, request):
        uploaded_file = request.FILES['file']
        records = read_excel_records(uploaded_file)
        method_mapping = MethodEnum.reversal_obj()
        column_mapping = {
            '*产品名称': 'project_product',
            '*模块名称': 'module',
            '*接口名称': 'name',
            '*请求方法': 'method',
            '*url': 'url',
            '请求头': 'headers',
            '参数': 'params',
            '表单': 'legacy_data',
            'JSON': 'legacy_json',
            '文件': 'legacy_file',
        }
        for source_record in records:
            source_record['*请求方法'] = method_mapping.get(source_record['*请求方法'])
            record = {
                column_mapping.get(key, key): value
                for key, value in source_record.items()
            }
            try:
                record['project_product'] = ProjectProduct.objects.get(name=record['project_product']).id
                record['module'] = ProductModule.objects.get(name=record['module'],
                                                             project_product=record['project_product']).id
            except (
                    ProductModule.MultipleObjectsReturned, ProjectProduct.MultipleObjectsReturned,
                    ProductModule.DoesNotExist,
                    ProjectProduct.DoesNotExist):
                return ResponseData.fail(RESPONSE_MSG_0138)
            for i in ['headers', 'params', 'legacy_data', 'legacy_json', 'legacy_file']:
                if record.get(i) == '' or record.get(i) is None:
                    record[i] = None
                elif i == 'legacy_file':
                    try:
                        record[i] = json.loads(record[i])
                    except json.decoder.JSONDecodeError:
                        return ResponseData.fail(RESPONSE_MSG_0137)
            body_type, body_config = build_body_from_legacy(
                data=record.pop('legacy_data', None),
                json_body=record.pop('legacy_json', None),
                file_payload=record.pop('legacy_file', None),
            )
            record['body_type'] = body_type
            record['body_config'] = body_config
            record = with_update_user(record, request)
            ApiInfoCRUD.inside_post(record)
        return ResponseData.success(RESPONSE_MSG_0083)

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_auto_schema(self, request):
        raise AutoApiError(AUTO_API_API_INFO_API_INFO_SCENARIO_ASSERTION_GENERATE_INVALID)
