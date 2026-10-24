from rest_framework.fields import empty

from src.apps.test_center.exceptions import (
    SYSTEM_MODULE_MODULE_BINDING_INVALID,
    TestCenterError,
)


class ProductModuleBindingSerializerMixin:
    def run_validation(self, data=empty):
        attrs = super().run_validation(data)
        if not isinstance(attrs, dict) or "module" not in attrs:
            return attrs
        module = attrs.get("module")
        if module is None:
            return attrs
        instance = getattr(self, "instance", None)
        if instance is not None and getattr(instance, "module_id", None) == module.id:
            return attrs
        if module.level != 3:
            raise TestCenterError(SYSTEM_MODULE_MODULE_BINDING_INVALID)
        return attrs
