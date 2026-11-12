# -*- coding: utf-8 -*-
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.case import (
    ManualTestCaseListSerializer,
    ManualTestCaseSerializer,
    ManualTestCaseSerializerC,
    ManualTestCaseVersionSerializer,
)
from src.apps.functional_test.models import (
    ManualTestCase,
    ManualTestCaseVersion,
)
from src.apps.functional_test.selectors.access_scope import (
    filter_manual_case_by_data_scope,
    has_manual_case_project_product_scope,
)
from src.apps.functional_test.services.cases.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.cases.mutation import FunctionalTestMutationService
from src.apps.functional_test.services.suites.suite import ManualTestSuiteService
from src.apps.test_center.models import ProductModule
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0168,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0283,
    RESPONSE_MSG_0284,
    RESPONSE_MSG_0285,
    RESPONSE_MSG_0286,
    RESPONSE_MSG_0322,
    RESPONSE_MSG_0323,
)


class ManualTestCaseCRUD(ModelCRUD):
    model = ManualTestCase
    queryset = ManualTestCase.objects.all()
    serializer_class = ManualTestCaseListSerializer
    serializer = ManualTestCaseSerializer
    page_permission_key = 'functional.case'
    not_matching_str = ModelCRUD.not_matching_str + [
        "suite",
        "module",
        "project_product",
        "test_type",
        "scenario_tag",
        "owner",
        "priority",
        "precondition",
        "test_point",
        "expected_result",
        "acceptance_source",
        "test_data",
        "scenario_layer",
        "scenario_type",
        "automation_status",
        "remark",
        "scenario_layer",
        "scenario_type",
        "change_status",
        "automation_impact_status",
        "status",
        "category_level_1",
        "category_level_2",
        "category_level_3",
    ]
    sortable_fields = frozenset({
        "case_no",
        "title",
        "category_level_1",
        "category_level_2",
        "category_level_3",
        "priority",
        "status",
        "owner_id",
        "project_product_id",
        "module_id",
        "version_no",
        "update_time",
        "create_time",
    })

    @error_response("system")
    def get(self, request: Request):
        """获取功能测试用例列表或指定记录"""
        query_dict = {}
        include_descendants = str(request.query_params.get("include_descendants") or "").lower() == "true"
        for key, values in dict(request.query_params.lists()).items():
            value = values[0]
            if key in (
                    "page",
                    "pageSize",
                    "test_type",
                    "scenario_tag",
                    "include_descendants",
                    "sort_field",
                    "sort_order",
            ):
                continue
            if key == "module" and include_descendants:
                try:
                    query_dict["module_id__in"] = ManualTestSuiteService.module_scope_ids(int(value))
                except (TypeError, ValueError):
                    query_dict["module_id__in"] = []
                continue
            if key and isinstance(value, str) and key not in self.not_matching_str and "id" not in key:
                query_dict[f"{key}__contains"] = value
            else:
                query_dict[key] = value
        queryset = self.model.objects.none() if self.has_invalid_integer_filter(
            query_dict) else self.model.objects.filter(**query_dict)
        queryset = self.filter_queryset_by_data_scope(request, queryset)
        test_type = request.query_params.get("test_type")
        if test_type not in (None, ""):
            try:
                queryset = queryset.filter(test_types__contains=[int(test_type)])
            except ValueError:
                queryset = self.model.objects.none()
        scenario_tag = request.query_params.get("scenario_tag")
        if scenario_tag not in (None, ""):
            queryset = queryset.filter(scenario_tags__contains=[str(scenario_tag)])
        sort_field = request.query_params.get("sort_field")
        if sort_field in self.sortable_fields:
            sort_prefix = "-" if request.query_params.get("sort_order") == "desc" else ""
            queryset = queryset.order_by(f"{sort_prefix}{sort_field}", "id")
        if request.query_params.get("pageSize") and request.query_params.get("page"):
            data_list, count = self.paging_list(request.query_params.get("pageSize"), request.query_params.get("page"),
                                                queryset, self.get_serializer_class())
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        return ResponseData.success(RESPONSE_MSG_0001, serializer(instance=queryset, many=True).data, queryset.count())

    @error_response("system")
    def post(self, request: Request):
        """新增功能测试用例"""
        result = FunctionalTestMutationService.create_case(
            dict(request.data),
            self.get_request_user_id(request),
            data_validator=lambda data: self.has_data_scope_permission(request, data),
        )
        if result.forbidden:
            return ResponseData.fail(RESPONSE_MSG_0210)
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0003, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def put(self, request: Request):
        """修改功能测试用例"""
        instance = self.model.objects.filter(id=request.data.get("id")).first()
        if not instance:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = FunctionalTestMutationService.update_case(
            instance.id,
            dict(request.data),
            self.get_request_user_id(request),
        )
        if result.data and result.data.get("conflicts"):
            return ResponseData.fail(RESPONSE_MSG_0286, result.data)
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0004, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0082,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def delete(self, request: Request):
        """删除功能测试用例"""
        ids = self._extract_delete_ids(request)
        if not ids:
            return ResponseData.fail(RESPONSE_MSG_0029)
        queryset = self.filter_queryset_by_data_scope(request, ManualTestCase.objects.filter(id__in=ids))
        if queryset.count() != len(ids):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if not queryset.exists():
            return ResponseData.fail(RESPONSE_MSG_0029)
        result = FunctionalTestMutationService.delete_cases(ids)
        return ResponseData.success(RESPONSE_MSG_0005, {"count": result["deleted_count"]})

    @staticmethod
    def _extract_delete_ids(request: Request) -> list[int]:
        raw_ids = request.data.get("ids") or request.data.get("id") or request.query_params.getlist(
            "ids[]") or request.query_params.getlist("ids") or request.query_params.getlist(
            "id[]") or request.query_params.get("id")
        if raw_ids in (None, ""):
            return []
        if not isinstance(raw_ids, (list, tuple)):
            raw_ids = [raw_ids]
        ids = []
        for item in raw_ids:
            values = item if isinstance(item, (list, tuple)) else str(item).split(",")
            for value in values:
                value = str(value).strip()
                if value.isdigit():
                    ids.append(int(value))
        return list(dict.fromkeys(ids))


class ManualTestCaseExportViews(ManualTestCaseCRUD):
    http_method_names = ['get', 'head', 'options']


class ManualTestCaseViews(ViewSet):
    model = ManualTestCase
    serializer_class = ManualTestCaseSerializerC

    @action(methods=["post"], detail=False)
    @error_response("system")
    def batch_create(self, request: Request):
        """批量创建功能测试用例"""
        result = FunctionalTestMutationService.bulk_create_cases(
            request.data.get("items"),
            ModelCRUD.get_operator_id(request),
            data_validator=lambda data: has_manual_case_project_product_scope(
                request,
                data.get("project_product") or data.get("project_product_id"),
            ),
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0323, result.errors)
        case_ids = [item.id for item in result.instance]
        queryset = self.serializer_class.setup_eager_loading(
            ManualTestCase.objects.filter(id__in=case_ids)
        )
        case_map = {item.id: item for item in queryset}
        ordered = [case_map[item_id] for item_id in case_ids if item_id in case_map]
        return ResponseData.success(
            RESPONSE_MSG_0322,
            self.serializer_class(instance=ordered, many=True).data,
        )

    @action(methods=["put"], detail=False)
    @error_response("system")
    def batch_update(self, request: Request):
        """批量更新功能测试用例"""
        updates = request.data.get("updates")
        normalized, errors = FunctionalTestMutationService.normalize_bulk_case_updates(updates)
        if errors:
            return ResponseData.fail(RESPONSE_MSG_0285, errors)
        ids = [item["id"] for item in normalized]
        scoped = filter_manual_case_by_data_scope(
            request,
            ManualTestCase.objects.filter(id__in=ids),
        )
        if scoped.count() != len(ids):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = FunctionalTestMutationService.bulk_update_cases(
            normalized,
            ModelCRUD.get_operator_id(request),
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0004, result.errors)
        if result.data and result.data.get("conflicts"):
            return ResponseData.success(RESPONSE_MSG_0284, result.data)
        return ResponseData.success(RESPONSE_MSG_0283, result.data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def module_counts(self, request: Request):
        """统计功能测试用例的模块分布"""
        project_product_id = int(request.query_params.get("project_product"))
        queryset = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all())
        data = ManualTestSuiteService.module_counts(queryset, project_product_id)
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def case_modules(self, request: Request):
        """获取功能测试用例模块分布"""
        queryset = filter_manual_case_by_data_scope(request, ManualTestCase.objects.filter(module__isnull=False))
        project_product_id = request.query_params.get("project_product_id")
        products_queryset = queryset
        if project_product_id:
            if not has_manual_case_project_product_scope(request, project_product_id):
                return ResponseData.success(RESPONSE_MSG_0001, {"products": [], "modules": []})
            queryset = queryset.filter(project_product_id=project_product_id)
            case_counts = {item["module_id"]: item["case_count"] for item in
                           queryset.values("module_id").annotate(case_count=Count("id"))}
            modules = ProductModule.objects.filter(project_product_id=project_product_id).select_related(
                "parent", "parent__parent"
            ).order_by("level", "sort", "id")
            data = [
                {
                    "key": item.id,
                    "title": item.name,
                    "level": item.level,
                    "parent_id": item.parent_id,
                    "path": ManualTestSuiteService.module_path(item),
                    "case_count": case_counts.get(item.id, 0),
                }
                for item in modules
            ]
        else:
            counts = {
                item["module_id"]: item["case_count"]
                for item in queryset.values("module_id").annotate(case_count=Count("id"))
            }
            modules = ProductModule.objects.filter(id__in=counts).select_related(
                "parent", "parent__parent"
            ).order_by("project_product_id", "level", "sort", "id")
            data = [
                {
                    "key": item.id,
                    "title": item.name,
                    "level": item.level,
                    "parent_id": item.parent_id,
                    "path": ManualTestSuiteService.module_path(item),
                    "case_count": counts.get(item.id, 0),
                }
                for item in modules
            ]
        products = products_queryset.values("project_product_id", "project_product__name").annotate(
            case_count=Count("id")).order_by("project_product__name")
        return ResponseData.success(
            RESPONSE_MSG_0001,
            {
                "products": [{"key": item["project_product_id"], "title": item["project_product__name"],
                              "case_count": item["case_count"]} for item in products],
                "modules": data,
            },
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def case_detail(self, request: Request):
        """获取功能测试用例详情"""
        case = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all()).get(
            id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, ManualTestCaseSerializerC(instance=case).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def category_options(self, request: Request):
        """获取功能测试用例分类选项"""
        queryset = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all())
        project_product_id = request.query_params.get("project_product")
        module_id = request.query_params.get("module")
        if project_product_id:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        fields = ("category_level_1", "category_level_2", "category_level_3")
        category_level_1 = str(request.query_params.get("category_level_1") or "").strip()
        category_level_2 = str(request.query_params.get("category_level_2") or "").strip()
        keyword = str(request.query_params.get("keyword") or "").strip()
        data = {}
        for field in fields:
            field_queryset = queryset
            if field in ("category_level_2", "category_level_3") and category_level_1:
                field_queryset = field_queryset.filter(category_level_1=category_level_1)
            if field == "category_level_3" and category_level_2:
                field_queryset = field_queryset.filter(category_level_2=category_level_2)
            if keyword:
                field_queryset = field_queryset.filter(**{f"{field}__icontains": keyword})
            data[field] = list(
                field_queryset.exclude(**{f"{field}__isnull": True})
                .exclude(**{field: ""})
                .values_list(field, flat=True)
                .distinct()
                .order_by(field)[:200]
            )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def versions(self, request: Request):
        """获取功能测试用例版本记录"""
        case = filter_manual_case_by_data_scope(
            request,
            ManualTestCase.objects.all(),
        ).get(id=request.query_params.get("id"))
        queryset = ManualTestCaseVersion.objects.filter(case=case).select_related(
            "changed_by"
        )[:ManualTestCaseVersionService.HISTORY_LIMIT]
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ManualTestCaseVersionSerializer(queryset, many=True).data,
            len(queryset),
        )

    @action(methods=["post"], detail=False)
    @error_response("system")
    def rewrite_preview(self, request: Request):
        """预览功能测试用例改写结果"""
        case = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all()).get(
            id=request.data.get("case_id"))
        instruction = request.data.get("user_instruction") or ""
        data = ManualTestCaseSerializerC(instance=case).data
        data["rewrite_instruction"] = instruction
        data["preview"] = {**data, "remark": instruction or data.get("remark")}
        return ResponseData.success(RESPONSE_MSG_0168, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def rewrite_confirm(self, request: Request):
        """确认保存功能测试用例改写结果"""
        case = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all()).get(
            id=request.data.get("case_id"))
        fields = request.data.get("fields") or {}
        payload = {}
        for key in (
                "title", "category_level_1", "category_level_2", "category_level_3",
                "test_types", "story_refs", "precondition", "test_point", "test_steps",
                "expected_result", "acceptance_source", "test_data", "remark", "priority",
                "scenario_layer", "scenario_type", "scenario_tags", "automation_status",
        ):
            if key in fields:
                payload[key] = fields.get(key)
        result = FunctionalTestMutationService.update_case(
            case.id,
            payload,
            ModelCRUD.get_operator_id(request),
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0004, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0082,
            ManualTestCaseSerializerC(instance=result.instance).data,
        )
