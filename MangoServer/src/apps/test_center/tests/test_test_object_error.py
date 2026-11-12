from django.test import TestCase

from src.apps.test_center.enums.environment import (
    AutoTypeEnum,
    EnvironmentEnum,
)
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import Project, ProjectProduct
from src.apps.test_center.services.datasource.factory import func_test_object_value


class TestObjectErrorMessageTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='订单中心')
        self.product = ProjectProduct.objects.create(project=project, name='订单服务')

    def test_missing_test_object_error_contains_actionable_context(self):
        with self.assertRaises(TestCenterError) as context:
            func_test_object_value(
                EnvironmentEnum.TEST.value,
                self.product.id,
                AutoTypeEnum.API.value,
            )

        message = context.exception.msg
        self.assertIn(f'订单中心 / 订单服务（产品ID：{self.product.id}）', message)
        self.assertIn('所选环境【测试环境】', message)
        self.assertIn('自动化类型【API自动化】', message)
        self.assertIn('测试配置 > 测试对象', message)
        self.assertIn('UI/API通用', message)
