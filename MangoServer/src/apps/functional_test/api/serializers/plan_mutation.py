from rest_framework import serializers

from src.apps.functional_test.enums import (
    FunctionalTestPlanScopeTypeEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID,
    FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_TYPE_REQUIRED,
    FUNCTIONAL_TEST_PLAN_ITERATION_TYPE_REQUIRED,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalTestPlan,
)


class FunctionalTestPlanSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    started_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    finished_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalTestPlan
        fields = "__all__"
        read_only_fields = ("status", "started_at", "finished_at")

    def validate(self, attrs):
        project_product = attrs.get("project_product", getattr(self.instance, "project_product", None))
        requirement_version = attrs.get("requirement_version", getattr(self.instance, "requirement_version", None))
        iteration = attrs.get("iteration", getattr(self.instance, "iteration", None))
        scope_type = attrs.get("scope_type", getattr(self.instance, "scope_type", None))
        if scope_type == FunctionalTestPlanScopeTypeEnum.REQUIREMENT.value and not requirement_version:
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_TYPE_REQUIRED)
        if scope_type == FunctionalTestPlanScopeTypeEnum.SPRINT.value and not iteration:
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_ITERATION_TYPE_REQUIRED)
        if scope_type == FunctionalTestPlanScopeTypeEnum.REQUIREMENT.value:
            attrs["requirement"] = requirement_version.requirement
            attrs["iteration"] = None
        else:
            attrs["requirement"] = None
            attrs["requirement_version"] = None
        if scope_type != FunctionalTestPlanScopeTypeEnum.SPRINT.value:
            attrs["iteration"] = None
            iteration = None
        if requirement_version and project_product and requirement_version.project_product_id != project_product.id:
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID)
        if iteration and project_product and iteration.project_product_id != project_product.id:
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID)
        return attrs
