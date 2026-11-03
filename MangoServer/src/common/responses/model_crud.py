# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 封装了分页查询，单条查询和增删改查
# @Time   : 2023-02-08 8:30
# @Author : 毛鹏
import traceback
from threading import Thread

from django.conf import settings
from django.core.exceptions import FieldError, FieldDoesNotExist
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models.query import QuerySet
from django.utils.module_loading import import_string
from minio.error import S3Error
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request

from src.common.decorators.error_response import error_response
from src.common.decorators.system_error import report_validation_failure
from src.common.exceptions import CommonError, SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED
from src.common.logging import log
from src.common.responses import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0026,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
    ResponseData,
)
from src.common.utils.environment_scope import test_envs_filter_query


def get_request_project_id(request: Request):
    return request.headers.get('X-Project-Id')


def get_request_project_product_id(request: Request):
    return request.headers.get('X-Project-Product-Id')


class ModelCRUD(GenericAPIView):
    model = None
    project_model = None
    serializer = None
    page_permission_key = None
    default_page_size = None
    max_page_size = None
    eager_loading_after_paging = False
    not_matching_str = [
        'pageSize', 'page',
        'type', 'status',
        'module', 'project_product', 'case_people', 'test_object', 'project', 'user', 'update_user'
    ]
    pytest_model = ['PytestAct', 'PytestCase', 'PytestTools', 'PytestTestFile']

    def model_has_field(self, field_name: str) -> bool:
        try:
            self.model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return False
        return True

    @staticmethod
    def _relation_id(value):
        if isinstance(value, (list, tuple)):
            return value[-1] if value else None
        if isinstance(value, dict):
            return value.get('id') or value.get('key') or value.get('value')
        return value

    def validate_business_module(self, data: dict, instance=None):
        validator = import_string(settings.MODEL_CRUD_MODULE_VALIDATOR)
        validator(self.model, data, instance)

    @staticmethod
    def get_request_user_id(request: Request):
        user = getattr(request, 'user', None)
        if isinstance(user, dict):
            return user.get('id')
        return getattr(user, 'id', None)

    def with_update_user(self, request: Request, data: dict) -> dict:
        if not self.model_has_field('update_user'):
            return data
        user_id = self.get_request_user_id(request)
        if not user_id:
            return data
        try:
            new_data = data.copy()
        except AttributeError:
            new_data = dict(data)
        new_data['update_user'] = user_id
        return new_data

    @staticmethod
    def get_operator_id(request: Request | dict | None) -> int | None:
        if request is None or isinstance(request, dict):
            return None
        user = getattr(request, 'user', None)
        if isinstance(user, dict):
            return user.get('id')
        user_obj = getattr(user, 'user_obj', None)
        if user_obj is not None:
            return getattr(user_obj, 'id', None)
        return getattr(user, 'id', None)

    @staticmethod
    def capture_config_snapshot(instance):
        adapter = import_string(settings.MODEL_CRUD_CONFIG_AUDIT_ADAPTER)
        return adapter.capture(instance)

    @classmethod
    def record_config_change(
            cls,
            instance,
            action: str,
            before_snapshot: dict | None = None,
            after_snapshot: dict | None = None,
            request: Request | dict | None = None,
            source: str = 'page',
            summary: str | None = None,
    ):
        adapter = import_string(settings.MODEL_CRUD_CONFIG_AUDIT_ADAPTER)
        return adapter.record_change(
            instance,
            action=action,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            operator_id=cls.get_operator_id(request),
            source=source,
            summary=summary,
        )

    @classmethod
    def record_config_delete(
            cls,
            instance,
            before_snapshot: dict | None,
            request: Request | dict | None = None,
            source: str = 'page',
    ):
        adapter = import_string(settings.MODEL_CRUD_CONFIG_AUDIT_ADAPTER)
        return adapter.record_delete(
            instance,
            before_snapshot,
            operator_id=cls.get_operator_id(request),
            source=source,
        )

    def is_valid_query_param(self, key: str) -> bool:
        if key in ['pageSize', 'page']:
            return True
        field_name = key.split('__')[0]
        try:
            self.model._meta.get_field(field_name)
        except FieldDoesNotExist:
            log.system.warning(f'忽略无效查询字段：model={self.model.__name__}, field={key}')
            return False
        return True

    @staticmethod
    def pop_paging_params(query_dict: dict) -> bool:
        page_size = query_dict.pop('pageSize', None)
        page = query_dict.pop('page', None)
        return bool(page_size and page)

    @staticmethod
    def parse_in_filter_values(values) -> list[str]:
        return [item.strip() for value in values for item in str(value).split(',') if item.strip()]

    def has_explicit_lookup_or_transform(self, key: str) -> bool:
        parts = key.split('__')
        model = self.model
        for index, part in enumerate(parts):
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist:
                return index > 0
            if field.is_relation and field.related_model is not None:
                model = field.related_model
                continue
            return index < len(parts) - 1
        return False

    def supports_contains_search(self, key: str) -> bool:
        """仅对最终指向文本字段的查询参数启用模糊匹配。"""
        parts = key.split('__')
        model = self.model
        for index, part in enumerate(parts):
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist:
                return False
            is_last = index == len(parts) - 1
            if field.is_relation:
                if is_last or field.related_model is None:
                    return False
                model = field.related_model
                continue
            if not is_last:
                return False
            return isinstance(field, (models.CharField, models.TextField))
        return False

    def has_invalid_integer_filter(self, query_dict: dict) -> bool:
        for key, value in query_dict.items():
            if not isinstance(value, str):
                continue
            key_parts = key.split('__')
            field_name = key_parts[0]
            try:
                field = self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            if isinstance(field, models.ForeignKey) and len(key_parts) > 1:
                related_lookup = key_parts[1]
                if related_lookup not in ("id", "pk", "exact", "in", "isnull") and not related_lookup.endswith("_id"):
                    continue
            target_field = field.target_field if isinstance(field, models.ForeignKey) else field
            if not isinstance(target_field, models.IntegerField):
                continue
            try:
                int(value)
            except ValueError:
                return True
        return False

    def has_request_data_scope_permission(self, request: Request) -> bool:
        policy = import_string(settings.MODEL_CRUD_DATA_SCOPE_POLICY)
        return policy.has_request_permission(self.model, request, set(self.pytest_model))

    def filter_queryset_by_data_scope(self, request: Request, queryset: QuerySet) -> QuerySet:
        policy = import_string(settings.MODEL_CRUD_DATA_SCOPE_POLICY)
        return policy.filter_queryset(self.model, request, queryset, set(self.pytest_model))

    def has_data_scope_permission(self, request: Request, data: dict) -> bool:
        policy = import_string(settings.MODEL_CRUD_DATA_SCOPE_POLICY)
        return policy.has_data_permission(self.model, request, data, set(self.pytest_model))

    def has_instance_data_scope_permission(self, request: Request, instance) -> bool:
        policy = import_string(settings.MODEL_CRUD_DATA_SCOPE_POLICY)
        return policy.has_instance_permission(self.model, request, instance, set(self.pytest_model))

    @error_response('system')
    def get(self, request: Request):
        def query() -> dict:
            query_dict = {}
            for k, v in dict(request.query_params.lists()).items():
                if not self.is_valid_query_param(k):
                    continue
                if k == 'test_envs':
                    query_dict[k] = v
                    continue
                if k.endswith('__in'):
                    query_dict[k] = self.parse_in_filter_values(v)
                    continue
                if k.endswith('__isnull'):
                    query_dict[k] = str(v[0]).lower() == 'true'
                    continue
                if (
                        k and
                        isinstance(v[0], str) and
                        k not in self.not_matching_str and
                        'id' not in k and
                        not self.has_explicit_lookup_or_transform(k) and
                        self.supports_contains_search(k)
                ):
                    query_dict[f'{k}__contains'] = v[0]
                else:
                    query_dict[k] = v[0]
            project_id = get_request_project_id(request)
            project_product_id = get_request_project_product_id(request)
            policy = import_string(settings.MODEL_CRUD_DATA_SCOPE_POLICY)
            policy.apply_project_context(
                self.model,
                query_dict,
                project_id,
                project_product_id,
                set(self.pytest_model),
            )
            return query_dict

        query_dict = query()
        paging = self.pop_paging_params(query_dict)
        test_envs_filter = None
        try:
            self.model._meta.get_field('test_envs')
            if 'test_envs' in query_dict:
                test_envs_filter = test_envs_filter_query(query_dict.pop('test_envs'))
            elif 'test_env' in query_dict:
                test_envs_filter = test_envs_filter_query(query_dict.pop('test_env'))
            elif query_dict.pop('test_env__isnull', False) is True:
                test_envs_filter = models.Q(test_envs=[]) | models.Q(test_envs__isnull=True)
        except FieldDoesNotExist:
            pass
        try:
            if self.has_invalid_integer_filter(query_dict):
                books = self.model.objects.none()
            else:
                try:
                    self.model._meta.get_field('case_sort')
                    books = self.model.objects.filter(**query_dict).order_by('case_sort')
                except FieldDoesNotExist:
                    books = self.model.objects.filter(**query_dict)
            if test_envs_filter is not None:
                books = books.filter(test_envs_filter)
            books = self.filter_queryset_by_data_scope(request, books)
            if paging or self.default_page_size is not None:
                data_list, count = self.paging_list(
                    request.query_params.get("pageSize") or self.default_page_size,
                    request.query_params.get("page") or 1,
                    books,
                    self.get_serializer_class()
                )
                return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
            serializer = self.get_serializer_class()
            try:
                books = serializer.setup_eager_loading(books)
            except FieldError:
                pass
            return ResponseData.success(
                RESPONSE_MSG_0001,
                serializer(instance=books, many=True).data,
                books.count()
            )
        except S3Error as error:
            log.system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
            return ResponseData.fail(RESPONSE_MSG_0026)

    @error_response('system')
    def post(self, request: Request):
        data = self.with_update_user(request, request.data)
        if not self.has_data_scope_permission(request, data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        self.validate_business_module(data)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                self.record_config_change(serializer.instance, action='create', request=request)
            self.asynchronous_callback(data.get('parent_id'))
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        report_validation_failure(serializer.errors, request=request)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response('system')
    def put(self, request: Request):
        if isinstance(request, dict):
            data = request
            instance_id = request.get('id')
        else:
            data = self.with_update_user(request, request.data)
            instance_id = request.data.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance):
            return ResponseData.fail(RESPONSE_MSG_0210)
        self.validate_business_module(data, instance)
        serializer = self.serializer(
            instance=instance,
            data=data,
            partial=True
        )
        if not self.has_data_scope_permission(request, data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if serializer.is_valid():
            before_snapshot = self.capture_config_snapshot(instance).snapshot
            with transaction.atomic():
                serializer.save()
                self.record_config_change(
                    serializer.instance,
                    action='update',
                    before_snapshot=before_snapshot,
                    request=request,
                )
            parent_id = data.get('parent_id')
            self.asynchronous_callback(parent_id)
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        report_validation_failure(serializer.errors, request=request)
        return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)

    @error_response('system')
    def delete(self, request: Request):
        _id = request.query_params.get('id')
        id_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]
        try:
            if not _id and id_list:
                for i in id_list:
                    instance = self.model.objects.get(pk=i)
                    if not self.has_instance_data_scope_permission(request, instance):
                        return ResponseData.fail(RESPONSE_MSG_0210)
                    before_snapshot = self.capture_config_snapshot(instance).snapshot
                    instance.delete()
                    self.record_config_delete(instance, before_snapshot, request=request)
            else:
                instance = self.model.objects.get(id=_id)
                if not self.has_instance_data_scope_permission(request, instance):
                    return ResponseData.fail(RESPONSE_MSG_0210)
                before_snapshot = self.capture_config_snapshot(instance).snapshot
                instance.delete()
                self.record_config_delete(instance, before_snapshot, request=request)
                self.asynchronous_callback(request.query_params.get('parent_id'))
        except CommonError as error:
            return ResponseData.fail((error.code, error.msg))
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0029)
        else:
            return ResponseData.success(RESPONSE_MSG_0005)

    @classmethod
    def inside_post(cls, data: dict, *, record_config: bool = True) -> dict:
        serializer = cls.serializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                if record_config:
                    cls.record_config_change(serializer.instance, action='create', source='internal')
            return dict(serializer.data)
        log.system.warning('内部保存参数校验失败')
        raise CommonError(SAVE_VALIDATION_FAILED, value=(serializer.errors,))

    @classmethod
    def inside_put(cls, _id: int, data: dict, *, record_config: bool = True) -> dict:
        instance = cls.model.objects.get(pk=_id)
        before_snapshot = cls.capture_config_snapshot(instance).snapshot
        serializer = cls.serializer(instance=instance, data=data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                if record_config:
                    cls.record_config_change(
                        serializer.instance,
                        action='update',
                        before_snapshot=before_snapshot,
                        source='internal',
                    )
            return dict(serializer.data)
        log.system.warning('内部修改参数校验失败')
        raise CommonError(UPDATE_VALIDATION_FAILED, value=(serializer.errors,))

    @classmethod
    def inside_delete(cls, _id: int) -> None:
        instance = cls.model.objects.get(id=_id)
        before_snapshot = cls.capture_config_snapshot(instance).snapshot
        instance.delete()
        cls.record_config_delete(instance, before_snapshot, source='internal')

    def asynchronous_callback(self, parent_id: int = None):
        if hasattr(self, 'callback'):
            th = Thread(target=self.callback, args=(parent_id,))
            th.start()

    @classmethod
    def paging_list(
            cls,
            size: int,
            current: int,
            books: QuerySet,
            serializer
    ) -> tuple[list, int]:

        size = max(1, int(size))
        current = max(1, int(current))
        if cls.max_page_size is not None:
            size = min(size, cls.max_page_size)

        if not cls.eager_loading_after_paging:
            try:
                books = serializer.setup_eager_loading(books)
            except (AttributeError, FieldError):
                pass
        paginator = Paginator(books, size)
        if current > paginator.num_pages and paginator.num_pages > 0:
            current = paginator.num_pages
        page_obj = paginator.page(current)

        queryset = page_obj.object_list
        if cls.eager_loading_after_paging:
            try:
                queryset = serializer.setup_eager_loading(queryset)
            except (AttributeError, FieldError):
                pass

        data = serializer(
            instance=queryset,
            many=True
        ).data

        return data, paginator.count
