# -*- coding: utf-8 -*-
from django.db.models import Count, Prefetch
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.views.api_case import ApiCaseSerializersC
from src.apps.system.views.product_module import ProductModuleSerializers
from src.apps.system.views.project_product import ProjectProductSerializersC
from src.apps.auto_ui.views.ui_case import UiCaseSerializersC
from src.apps.user.views.user import UserSerializers
from src.apps.functional_test.models import (
    FunctionalTestContextResource,
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.service.automation import ManualAutomationService
from src.apps.functional_test.service.suite import ManualTestSuiteService
from src.common.enums.manual_test_enum import FunctionalTestContextUrlTypeEnum, ManualTestRelationTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *

class ManualTestSuiteSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_sync_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestSuite
        fields = "__all__"

    def validate(self, attrs):
        if not (attrs.get("owner") or getattr(self.instance, "owner_id", None)):
            raise serializers.ValidationError({"owner": "测试负责人不能为空"})
        return attrs


class ManualTestSuiteSerializerC(ManualTestSuiteSerializer):
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    owner = UserSerializers(read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("project_product", "project_product__project", "module", "owner")


class ManualTestAutomationBindingSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    api_case = ApiCaseSerializersC(read_only=True)
    ui_case = UiCaseSerializersC(read_only=True)

    class Meta:
        model = ManualTestAutomationBinding
        fields = "__all__"


class ManualTestAutomationBindingLiteSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestAutomationBinding
        fields = "__all__"


class ManualTestCaseSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestCase
        fields = "__all__"

    def validate(self, attrs):
        data = {
            field: getattr(self.instance, field, None)
            for field in [
                "case_no",
                "title",
                "test_point",
                "test_types",
                "priority",
                "scenario_layer",
                "scenario_type",
                "scenario_tags",
                "owner",
                "project_product",
                "module",
            ]
        } if self.instance else {}
        data.update(attrs)
        required_text_fields = {
            "case_no": "用例编号不能为空",
            "title": "用例标题不能为空",
            "test_point": "测试点不能为空",
        }
        errors = {}
        for field, message in required_text_fields.items():
            if not str(data.get(field) or "").strip():
                errors[field] = message
        if not data.get("test_types"):
            errors["test_types"] = "测试类型不能为空"
        if data.get("priority") in (None, ""):
            errors["priority"] = "优先级不能为空"
        if data.get("scenario_layer") in (None, ""):
            errors["scenario_layer"] = "场景层级不能为空"
        if data.get("scenario_type") in (None, ""):
            errors["scenario_type"] = "场景类型不能为空"
        if not data.get("scenario_tags"):
            errors["scenario_tags"] = "场景标签不能为空"
        if not (data.get("owner") or getattr(data.get("owner"), "id", None)):
            errors["owner"] = "负责人不能为空"
        if not (data.get("project_product") or getattr(data.get("project_product"), "id", None)):
            errors["project_product"] = "项目产品不能为空"
        if not (data.get("module") or getattr(data.get("module"), "id", None)):
            errors["module"] = "模块不能为空"
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ManualTestCaseBindingMixin:
    @staticmethod
    def setup_eager_loading(queryset):
        bindings = ManualTestAutomationBinding.objects.all()
        return queryset.prefetch_related(Prefetch("manualtestautomationbinding_set", queryset=bindings, to_attr="prefetched_bindings"))

    def get_bindings(self, obj):
        bindings = getattr(obj, "prefetched_bindings", None)
        if bindings is None:
            bindings = ManualTestAutomationBinding.objects.filter(manual_case=obj)
        return ManualTestAutomationBindingLiteSerializer(instance=bindings, many=True).data


class ManualTestCaseListSerializer(ManualTestCaseBindingMixin, ManualTestCaseSerializer):
    bindings = serializers.SerializerMethodField()
    suite_id = serializers.IntegerField(read_only=True)
    suite_requirement_name = serializers.CharField(source="suite.requirement_name", read_only=True)
    suite_iteration = serializers.CharField(source="suite.iteration", read_only=True)
    project_product_id = serializers.IntegerField(read_only=True)
    project_product_name = serializers.CharField(source="project_product.name", read_only=True)
    module_id = serializers.IntegerField(read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    owner_name = serializers.CharField(source="owner.name", read_only=True)

    class Meta:
        model = ManualTestCase
        exclude = ("suite",)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            "suite",
            "suite__project_product",
            "suite__project_product__project",
            "suite__module",
            "project_product",
            "project_product__project",
            "module",
            "owner",
        )
        return ManualTestCaseBindingMixin.setup_eager_loading(queryset)


class ManualTestCaseSerializerC(ManualTestCaseBindingMixin, ManualTestCaseSerializer):
    bindings = serializers.SerializerMethodField()
    suite = ManualTestSuiteSerializerC(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    owner = UserSerializers(read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            "suite",
            "suite__project_product",
            "suite__project_product__project",
            "suite__module",
            "suite__owner",
            "project_product",
            "project_product__project",
            "module",
            "owner",
        )
        return ManualTestCaseBindingMixin.setup_eager_loading(queryset)


class FunctionalTestContextResourceSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalTestContextResource
        fields = "__all__"


class FunctionalTestContextResourceSerializerC(FunctionalTestContextResourceSerializer):
    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("suite", "file", "create_user", "update_user")


class ManualTestSuiteCRUD(ModelCRUD):
    model = ManualTestSuite
    queryset = ManualTestSuite.objects.all()
    serializer_class = ManualTestSuiteSerializerC
    serializer = ManualTestSuiteSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["owner", "sync_status"]

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            ManualTestSuiteService.refresh_stats(serializer.data["id"])
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)


class ManualTestCaseCRUD(ModelCRUD):
    model = ManualTestCase
    queryset = ManualTestCase.objects.all()
    serializer_class = ManualTestCaseListSerializer
    serializer = ManualTestCaseSerializer
    not_matching_str = ModelCRUD.not_matching_str + [
        "suite",
        "module",
        "project_product",
        "test_type",
        "scenario_tag",
        "owner",
        "priority",
        "scenario_layer",
        "scenario_type",
        "change_status",
        "automation_impact_status",
    ]

    @error_response("system")
    def get(self, request: Request):
        query_dict = {}
        for key, values in dict(request.query_params.lists()).items():
            value = values[0]
            if key in ("page", "pageSize", "test_type", "scenario_tag"):
                continue
            if key and isinstance(value, str) and key not in self.not_matching_str and "id" not in key:
                query_dict[f"{key}__contains"] = value
            else:
                query_dict[key] = value
        if self.has_invalid_integer_filter(query_dict):
            queryset = self.model.objects.none()
        else:
            queryset = self.model.objects.filter(**query_dict)
        test_type = request.query_params.get("test_type")
        if test_type not in (None, ""):
            try:
                queryset = queryset.filter(test_types__contains=[int(test_type)])
            except ValueError:
                queryset = self.model.objects.none()
        scenario_tag = request.query_params.get("scenario_tag")
        if scenario_tag not in (None, ""):
            try:
                queryset = queryset.filter(scenario_tags__contains=[int(scenario_tag)])
            except ValueError:
                queryset = self.model.objects.none()
        if request.query_params.get("pageSize") and request.query_params.get("page"):
            data_list, count = self.paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                queryset,
                self.get_serializer_class(),
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        return ResponseData.success(RESPONSE_MSG_0001, serializer(instance=queryset, many=True).data, queryset.count())

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        if data.get("suite"):
            suite = ManualTestSuite.objects.filter(id=data.get("suite")).first()
            if suite:
                if not data.get("owner"):
                    data["owner"] = suite.owner_id
                data["project_product"] = data.get("project_product") or suite.project_product_id
                data["module"] = data.get("module") or suite.module_id
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            ManualTestSuiteService.refresh_stats(serializer.data["suite"])
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        suite_id = request.data.get("suite")
        response = super().put(request)
        if suite_id:
            ManualTestSuiteService.refresh_stats(suite_id)
        return response

    @error_response("system")
    def delete(self, request: Request):
        ids = self._extract_delete_ids(request)
        if not ids:
            return ResponseData.fail(RESPONSE_MSG_0029)
        queryset = ManualTestCase.objects.filter(id__in=ids)
        suite_ids = set(queryset.values_list("suite_id", flat=True))
        count = queryset.count()
        if not count:
            return ResponseData.fail(RESPONSE_MSG_0029)
        queryset.delete()
        for suite_id in suite_ids:
            ManualTestSuiteService.refresh_stats(suite_id)
        return ResponseData.success(RESPONSE_MSG_0005, {"count": count})

    @staticmethod
    def _extract_delete_ids(request: Request) -> list[int]:
        raw_ids = (
            request.data.get("ids")
            or request.data.get("id")
            or request.query_params.getlist("ids[]")
            or request.query_params.getlist("ids")
            or request.query_params.getlist("id[]")
            or request.query_params.get("id")
        )
        if raw_ids in (None, ""):
            return []
        if not isinstance(raw_ids, (list, tuple)):
            raw_ids = [raw_ids]
        ids = []
        for item in raw_ids:
            if isinstance(item, (list, tuple)):
                values = item
            else:
                values = str(item).split(",")
            for value in values:
                value = str(value).strip()
                if value.isdigit():
                    ids.append(int(value))
        return list(dict.fromkeys(ids))


class ManualTestCaseViews(ViewSet):
    @action(methods=["get"], detail=False)
    @error_response("system")
    def case_modules(self, request: Request):
        queryset = ManualTestCase.objects.filter(module__isnull=False)
        project_product_id = request.query_params.get("project_product_id")
        products_queryset = queryset
        if project_product_id:
            queryset = queryset.filter(project_product_id=project_product_id)
        products = (
            products_queryset.values("project_product_id", "project_product__name")
            .annotate(case_count=Count("id"))
            .order_by("project_product__name")
        )
        modules = (
            queryset.values(
                "module_id",
                "module__name",
                "module__superior_module_1",
                "module__superior_module_2",
            )
            .annotate(case_count=Count("id"))
            .order_by("module__superior_module_1", "module__superior_module_2", "module__name")
        )
        data = [
            {
                "key": item["module_id"],
                "title": item["module__name"],
                "superior_module_1": item["module__superior_module_1"],
                "superior_module_2": item["module__superior_module_2"],
                "case_count": item["case_count"],
            }
            for item in modules
        ]
        return ResponseData.success(
            RESPONSE_MSG_0001,
            {
                "products": [
                    {
                        "key": item["project_product_id"],
                        "title": item["project_product__name"],
                        "case_count": item["case_count"],
                    }
                    for item in products
                ],
                "modules": data,
            },
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def case_detail(self, request: Request):
        case = ManualTestCase.objects.get(id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, ManualTestCaseSerializerC(instance=case).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def rewrite_preview(self, request: Request):
        case = ManualTestCase.objects.get(id=request.data.get("case_id"))
        instruction = request.data.get("user_instruction") or ""
        data = ManualTestCaseSerializerC(instance=case).data
        data["rewrite_instruction"] = instruction
        data["preview"] = {**data, "remark": instruction or data.get("remark")}
        return ResponseData.success(RESPONSE_MSG_0168, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def rewrite_confirm(self, request: Request):
        case = ManualTestCase.objects.get(id=request.data.get("case_id"))
        fields = request.data.get("fields") or {}
        for key in ("title", "precondition", "test_point", "test_data", "remark", "priority", "scenario_layer", "scenario_type", "scenario_tags"):
            if key in fields:
                setattr(case, key, fields.get(key))
        case.save()
        return ResponseData.success(RESPONSE_MSG_0082, ManualTestCaseSerializerC(instance=case).data)


class FunctionalTestContextResourceCRUD(ModelCRUD):
    model = FunctionalTestContextResource
    queryset = FunctionalTestContextResource.objects.all()
    serializer_class = FunctionalTestContextResourceSerializerC
    serializer = FunctionalTestContextResourceSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["suite", "context_key", "content_type", "url_type", "parse_status", "enabled"]

    @staticmethod
    def validate_url_type(data):
        if data.get("url_type") == FunctionalTestContextUrlTypeEnum.FEISHU.value:
            return ResponseData.fail(RESPONSE_MSG_0183)
        return None

    @error_response("system")
    def post(self, request: Request):
        error = self.validate_url_type(request.data)
        if error:
            return error
        data = dict(request.data)
        data["create_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        error = self.validate_url_type(request.data)
        if error:
            return error
        data = dict(request.data)
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        serializer = self.serializer(self.model.objects.get(id=request.data.get("id")), data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)


class ManualTestAutomationViews(ViewSet):
    @action(methods=["post"], detail=False)
    @error_response("system")
    def bind(self, request: Request):
        case = ManualTestCase.objects.get(id=request.data.get("case_id"))
        automation_type = request.data.get("automation_type")
        binding = ManualAutomationService.bind(
            case,
            automation_type,
            int(request.data.get("automation_case_id")),
            request.data.get("relation_type") or ManualTestRelationTypeEnum.BOUND.value,
            request.user.get("id") if isinstance(request.user, dict) else None,
        )
        return ResponseData.success(RESPONSE_MSG_0175, ManualTestAutomationBindingSerializer(instance=binding).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def binding(self, request: Request):
        queryset = ManualTestAutomationBinding.objects.all()
        case_id = request.query_params.get("case_id")
        if case_id:
            queryset = queryset.filter(manual_case_id=case_id)
        return ResponseData.success(RESPONSE_MSG_0001, ManualTestAutomationBindingSerializer(instance=queryset, many=True).data, queryset.count())
