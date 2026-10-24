from rest_framework import serializers

from src.apps.functional_test.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID,
    FUNCTIONAL_TEST_SUITE_REQUIRED,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    ManualTestSuite,
)


class ManualTestSuiteSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_sync_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestSuite
        fields = "__all__"

    def validate(self, attrs):
        if not (attrs.get("owner") or getattr(self.instance, "owner_id", None)):
            raise FunctionalTestError(FUNCTIONAL_TEST_SUITE_REQUIRED)
        if not (attrs.get("iteration_ref") or getattr(self.instance, "iteration_ref_id", None)):
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID)
        return attrs
