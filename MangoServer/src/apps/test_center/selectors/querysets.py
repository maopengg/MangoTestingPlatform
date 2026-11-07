from django.db.models import Case, IntegerField, Value, When

from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import (
    FileData,
    NoticeGroup,
    ProductModule,
    ProjectProduct,
    TestObject,
    TestSuite,
    TestSuiteDetails,
)


class TestCenterQuerySelector:
    @staticmethod
    def notice_group():
        return NoticeGroup.objects.all()

    @staticmethod
    def with_project_product_display(queryset, relation='project_product'):
        prefix = f'{relation}__' if relation else ''
        return queryset.select_related(
            f'{prefix}project',
            f'{prefix}project__update_user',
            f'{prefix}update_user',
        ).prefetch_related(f'{prefix}owners')

    @staticmethod
    def execution_environment_priority():
        environments = list(reversed(EnvironmentEnum.default_obj()))
        return Case(
            *(When(test_env=value, then=Value(rank)) for rank, value in enumerate(environments)),
            default=Value(len(environments)),
            output_field=IntegerField(),
        )

    @staticmethod
    def file_data():
        return FileData.objects.all()

    @staticmethod
    def product_module():
        return ProductModule.objects.all()

    @staticmethod
    def project_product():
        return ProjectProduct.objects.all()

    @staticmethod
    def has_project_product_owner(project_product_id: int) -> bool:
        return ProjectProduct.objects.filter(
            id=project_product_id,
            owners__isnull=False,
        ).exists()

    @staticmethod
    def is_project_product_owner(project_product_id: int, user_id: int | None) -> bool:
        if user_id is None:
            return False
        return ProjectProduct.objects.filter(
            id=project_product_id,
            owners__id=user_id,
        ).exists()

    @staticmethod
    def owned_project_product_ids(user_id: int | None) -> set[int]:
        if user_id is None:
            return set()
        return set(
            ProjectProduct.objects.filter(owners__id=user_id).values_list('id', flat=True)
        )

    @staticmethod
    def project_product_ids_with_owners(project_product_ids) -> set[int]:
        return set(
            ProjectProduct.objects.filter(
                id__in=project_product_ids,
                owners__isnull=False,
            ).values_list('id', flat=True)
        )

    @staticmethod
    def test_object():
        return TestObject.objects.all()

    @staticmethod
    def test_suite():
        return TestSuite.objects.filter(report_retained=True)

    @staticmethod
    def test_suite_details():
        return TestSuiteDetails.objects.all()
