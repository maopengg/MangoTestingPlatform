from django.test import SimpleTestCase, override_settings

from src.apps.auto_api.schemas.execution import ApiAssertionResult


@override_settings(ASSERTION_RESULT_DISPLAY_MAX_LENGTH=50)
class AssertionResultSerializationTests(SimpleTestCase):
    def test_large_actual_and_message_are_truncated_only_when_serialized(self):
        actual = [{'id': index, 'name': '测试数据'} for index in range(20)]
        message = f'断言通过，实际={actual}'
        result = ApiAssertionResult(
            method='不是空值',
            actual=actual,
            ass_msg=message,
        )

        serialized = result.model_dump()

        self.assertEqual(result.actual, actual)
        self.assertEqual(result.ass_msg, message)
        self.assertIsInstance(serialized['actual'], str)
        self.assertLessEqual(len(serialized['actual']), 50)
        self.assertLessEqual(len(serialized['ass_msg']), 50)
        self.assertIn('已截断', serialized['actual'])
        self.assertIn('已截断', serialized['ass_msg'])

    def test_small_structured_actual_keeps_its_original_type(self):
        result = ApiAssertionResult(
            method='等于预期值',
            actual={'code': 200},
            ass_msg='断言通过',
        )

        serialized = result.model_dump()

        self.assertEqual(serialized['actual'], {'code': 200})
        self.assertEqual(serialized['ass_msg'], '断言通过')
