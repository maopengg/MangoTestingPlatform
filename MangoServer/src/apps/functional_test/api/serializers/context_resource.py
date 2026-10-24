# -*- coding: utf-8 -*-

from src.apps.functional_test.api.serializers.context_resource_mutation import FunctionalTestContextResourceSerializer


class FunctionalTestContextResourceSerializerC(FunctionalTestContextResourceSerializer):
    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("suite", "file", "create_user", "update_user")
