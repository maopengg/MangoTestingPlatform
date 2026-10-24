from rest_framework import serializers

from src.apps.functional_test.enums import FunctionalTestContextKeyEnum
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_DATABASE_CASE_NOT_ALLOWED,
    FunctionalTestError,
)
from src.apps.functional_test.models import FunctionalTestContextResource


class FunctionalTestContextResourceSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalTestContextResource
        fields = "__all__"

    def validate_context_key(self, value):
        if value == FunctionalTestContextKeyEnum.PLATFORM_CASE.value:
            raise FunctionalTestError(FUNCTIONAL_TEST_DATABASE_CASE_NOT_ALLOWED)
        return value
