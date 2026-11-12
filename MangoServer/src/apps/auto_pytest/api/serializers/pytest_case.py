# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.auto_pytest.api.serializers.pytest_product import PytestProductSerializersC
from src.apps.auto_pytest.enums import (
    PytestAssetStatusEnum,
    PytestCasePublicationStatusEnum,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.selectors.case_publication import PytestCasePublicationSelector
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class PytestCaseSerializersC(serializers.ModelSerializer):
    publication_status = serializers.SerializerMethodField()
    is_product_owner = serializers.BooleanField(read_only=True, default=False)

    def get_publication_status(self, instance):
        return PytestCasePublicationSelector.status(instance)

    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_seen_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    missing_since = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = PytestProductSerializersC(read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    case_people = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if (
                instance.publication_status == PytestCasePublicationStatusEnum.PUBLISHED.value
                and instance.asset_status == PytestAssetStatusEnum.DRAFT.value
        ):
            data['asset_status'] = PytestAssetStatusEnum.PUBLISHED.value
        return data

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project_product',
            'project_product__project_product__project',
            'project_product__repository',
            'project_product__repository__credential',
            'case_people',
            'update_user',
        )
        return queryset
