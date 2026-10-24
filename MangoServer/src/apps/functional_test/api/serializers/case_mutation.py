from rest_framework import serializers

from src.apps.auto_api.schemas.case_schema import validate_scenario_tag_list
from src.apps.functional_test.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_DYNAMIC_ERROR,
    FUNCTIONAL_TEST_STEP_RESULT_INVALID,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    ManualTestCase,
)
from src.apps.functional_test.services.suite import ManualTestSuiteService


class ManualTestCaseSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestCase
        fields = "__all__"

    def validate_scenario_tags(self, value):
        return validate_scenario_tag_list(value)

    def validate(self, attrs):
        for field in ("category_level_1", "category_level_2", "category_level_3"):
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = attrs[field].strip()
        data = {
            field: getattr(self.instance, field, None)
            for field in [
                "case_no",
                "title",
                "category_level_1",
                "test_point",
                "test_steps",
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
        errors = {}
        for field, message in {"case_no": "用例编号不能为空", "title": "用例标题不能为空",
                               "test_point": "测试场景不能为空"}.items():
            if not str(data.get(field) or "").strip():
                errors[field] = message
        test_steps = data.get("test_steps") or []
        if not isinstance(test_steps, list) or any(
                not isinstance(step, dict) or not (
                        str(step.get("action") or "").strip() or str(step.get("expected") or "").strip())
                for step in test_steps
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_STEP_RESULT_INVALID)
        if not data.get("test_types"):
            errors["test_types"] = "测试类型不能为空"
        for field, message in {
            "priority": "优先级不能为空",
            "scenario_layer": "测试层级不能为空",
            "scenario_type": "验证类型不能为空",
        }.items():
            if data.get(field) in (None, ""):
                errors[field] = message
        if not data.get("scenario_tags"):
            errors["scenario_tags"] = "执行场景不能为空"
        for field, message in {"owner": "负责人不能为空", "project_product": "项目产品不能为空",
                               "module": "模块不能为空"}.items():
            if not (data.get(field) or getattr(data.get(field), "id", None)):
                errors[field] = message
        if errors:
            raise FunctionalTestError(FUNCTIONAL_TEST_DYNAMIC_ERROR, value=('；'.join(errors.values()),))
        project_product = data.get("project_product")
        module = data.get("module")
        project_product_id = getattr(project_product, "id", project_product)
        module_id = getattr(module, "id", module)
        if project_product_id and module_id:
            ManualTestSuiteService.validate_module_product(project_product_id, module_id)
        return attrs
