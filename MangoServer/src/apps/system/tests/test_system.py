# Create your tests here.
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from mangotools.enums import TaskEnum
from minio.error import S3Error
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from src.apps.system.api.views.cache_data import CacheDataCRUD, CacheDataViews, SECRET_VALUE_MASK
from src.apps.system.exceptions import SystemError
from src.apps.system.models import CacheData
from src.apps.system.services.assertion_catalog import AssertionCatalogService
from src.apps.system.services.socket_link.consumer import UIConsumer
from src.apps.system.services.system_config import (
    DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY,
    EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY,
    EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY,
    EXECUTOR_TIMEOUT_DEFAULT_MINUTES,
    EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY,
    EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY,
    SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT,
    SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
    TEST_SUITE_STUCK_RESET_MINUTES_DEFAULT,
    TEST_SUITE_STUCK_RESET_MINUTES_KEY,
    TEST_SUITE_TIMEOUT_RETRY_COUNT_DEFAULT,
    TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY,
    SYSTEM_CONFIG_REGISTRY,
    SystemConfigService,
)
from src.apps.task_center.api.serializers.tasks import TasksSerializers
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.api.serializers.file_data_mutation import FileDataSerializers
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import (
    Project,
    ProjectProduct,
    TestSuite,
    ExecutionResult,
    TestSuiteDetails,
)
from src.apps.test_center.services.execution_artifact import ExecutionArtifactService
from src.apps.test_center.services.save_minio import SaveMinio
from src.apps.test_center.services.test_suite.retry import TestSuiteRetryService
from src.apps.user.models import User


class YourTestClass(TestCase):

    def test_your_function(self):
        with open(r'D:\GitCode\uitest\MangoServer\test.json') as f:
            data = json.load(f)
            UIConsumer().u_case_batch_result(data)


class FileDataSerializerTests(SimpleTestCase):

    def test_test_file_allows_empty_upload(self):
        field = FileDataSerializers().fields['test_file']
        empty_docx = SimpleUploadedFile(
            'empty.docx',
            b'',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

        try:
            field.run_validation(empty_docx)
        except ValidationError as error:
            self.fail(f'空文件应该允许上传，当前校验失败：{error.detail}')


class ExecutionArtifactServiceTests(SimpleTestCase):

    @override_settings(MINIO_STORAGE_MEDIA_BUCKET_NAME='regression-report')
    def test_normalize_path_removes_bucket_prefix(self):
        path = ExecutionArtifactService.normalize_path(
            'regression-report/auto_test_report/test/screenshot/failure.jpg'
        )

        self.assertEqual(path, 'auto_test_report/test/screenshot/failure.jpg')

    @override_settings(MINIO_STORAGE_MEDIA_BUCKET_NAME='regression-report', UI_EXECUTION_ARTIFACT_ROOT_DIR='uitest')
    def test_normalize_path_accepts_ui_artifact_directory(self):
        path = ExecutionArtifactService.normalize_path(
            'regression-report/mango-testing-platform/master/uitest/screenshot/failure.jpg'
        )

        self.assertEqual(path, 'mango-testing-platform/master/uitest/screenshot/failure.jpg')

    @override_settings(MINIO_STORAGE_MEDIA_BUCKET_NAME='regression-report', UI_EXECUTION_ARTIFACT_ROOT_DIR='uitest')
    def test_normalize_path_keeps_legacy_ui_artifact_compatible(self):
        path = ExecutionArtifactService.normalize_path(
            'regression-report/auto_test_report/test/uitest/videos/failure.mp4'
        )

        self.assertEqual(path, 'auto_test_report/test/uitest/videos/failure.mp4')

    @patch('src.apps.test_center.services.execution_artifact.build_public_file_url')
    def test_public_url_uses_storage_backend(self, build_url):
        build_url.return_value = 'https://signed.example/failure.jpg'

        result = ExecutionArtifactService.public_url(
            'auto_test_report/test/screenshot/failure.jpg'
        )

        self.assertEqual(result, 'https://signed.example/failure.jpg')
        build_url.assert_called_once_with('auto_test_report/test/screenshot/failure.jpg')

    @patch('src.apps.test_center.services.execution_artifact.build_public_file_url')
    def test_public_url_strips_local_media_prefix(self, build_url):
        build_url.return_value = '/mango-file/uitest/screenshot/failure.jpg'

        result = ExecutionArtifactService.public_url('mango-file/uitest/screenshot/failure.jpg')

        self.assertEqual(result, '/mango-file/uitest/screenshot/failure.jpg')
        build_url.assert_called_once_with('uitest/screenshot/failure.jpg')

    def test_rejects_non_artifact_path(self):
        with self.assertRaises(TestCenterError):
            ExecutionArtifactService.normalize_path('auto_test_report/test/other/file.txt')


class ObjectStorageFailureReasonTests(SimpleTestCase):

    @staticmethod
    def s3_error(code: str) -> S3Error:
        return S3Error(code, 'provider detail', '/', 'request-id', 'host-id', None)

    @override_settings(FILE_STORAGE_BACKEND='tos')
    def test_access_denied_identifies_credentials_and_bucket_permission(self):
        reason = SaveMinio.failure_reason(self.s3_error('AccessDenied'))

        self.assertEqual(reason, 'TOS鉴权失败，请检查访问凭证及存储桶写入权限')

    @override_settings(FILE_STORAGE_BACKEND='tos')
    def test_missing_bucket_is_explicit(self):
        reason = SaveMinio.failure_reason(self.s3_error('NoSuchBucket'))

        self.assertEqual(reason, 'TOS存储桶不存在或访问路径错误')

    @override_settings(FILE_STORAGE_BACKEND='tos')
    def test_permission_error_identifies_tos(self):
        self.assertEqual(
            SaveMinio.failure_reason(PermissionError('denied')),
            'TOS文件写入权限不足',
        )

    @override_settings(FILE_STORAGE_BACKEND='minio')
    def test_timeout_error_is_safe_and_actionable(self):
        reason = SaveMinio.failure_reason(TimeoutError('connection timed out'))

        self.assertEqual(reason, '连接MinIO超时，请检查对象存储网络及服务状态')

    @override_settings(
        MINIO_STORAGE_ENDPOINT='storage.example',
        MINIO_STORAGE_ACCESS_KEY='access-key',
        MINIO_STORAGE_SECRET_KEY='secret-key',
        MINIO_STORAGE_USE_HTTPS=True,
        MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE=False,
        MINIO_STORAGE_MEDIA_BUCKET_NAME='regression-report',
    )
    @patch('src.apps.test_center.services.save_minio.Minio')
    def test_artifact_upload_does_not_change_bucket_lifecycle(self, minio_class):
        uploaded_file = SimpleUploadedFile('failure.jpg', b'image-content')

        result = SaveMinio('uitest/screenshot').main(uploaded_file)

        client = minio_class.return_value
        client.set_bucket_lifecycle.assert_not_called()
        client.fput_object.assert_called_once()
        self.assertEqual(
            result,
            'regression-report/mango-testing-platform/master/uitest/screenshot/failure.jpg',
        )


class UiLocatorSemanticStrengthConfigTests(SimpleTestCase):
    def test_registry_uses_lowest_semantic_strength_by_default(self):
        definition = next(
            item for item in SYSTEM_CONFIG_REGISTRY
            if item.key == 'AI_UI_LOCATOR_SEMANTIC_STRENGTH'
        )
        self.assertEqual(definition.default_value, 0)

    def test_invalid_semantic_strength_falls_back_to_default(self):
        self.assertEqual(
            SystemConfigService.normalize_ai_locator_semantic_strength_value('37'),
            0,
        )
        self.assertEqual(
            SystemConfigService.normalize_ai_locator_semantic_strength_value(None),
            0,
        )
        self.assertEqual(
            SystemConfigService.normalize_ai_locator_semantic_strength_value('80'),
            80,
        )


class ApiTimeoutConfigTests(SimpleTestCase):
    def test_registry_defaults_api_request_timeout_to_120_seconds(self):
        definition = next(
            item for item in SYSTEM_CONFIG_REGISTRY
            if item.key == 'API_TIMEOUT'
        )

        self.assertEqual(definition.default_value, 120)


class ExecutionTimeoutConfigTests(SimpleTestCase):
    def test_registry_initializes_execution_timeout_defaults(self):
        definitions = {item.key: item for item in SYSTEM_CONFIG_REGISTRY}

        for key, default in EXECUTOR_TIMEOUT_DEFAULT_MINUTES.items():
            self.assertEqual(definitions[key].group, 'execution')
            self.assertEqual(definitions[key].default_value, default)
        self.assertEqual(
            definitions[TEST_SUITE_STUCK_RESET_MINUTES_KEY].default_value,
            TEST_SUITE_STUCK_RESET_MINUTES_DEFAULT,
        )
        self.assertEqual(
            definitions[TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY].default_value,
            TEST_SUITE_TIMEOUT_RETRY_COUNT_DEFAULT,
        )

    @patch.object(SystemConfigService, 'get_runtime_int')
    def test_executor_timeout_uses_configured_minutes(self, get_runtime_int):
        get_runtime_int.return_value = 45

        timeout_seconds = SystemConfigService.get_executor_execution_timeout_seconds(
            'pytest_execution',
            default_seconds=3600,
        )

        self.assertEqual(timeout_seconds, 45 * 60)
        get_runtime_int.assert_called_once_with(
            EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY,
            default=60,
            min_value=1,
            max_value=1440,
        )

    def test_report_reset_must_be_later_than_case_execution_time(self):
        values = {
            EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY: 60,
            EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY: 60,
            EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY: 60,
            EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY: 30,
            TEST_SUITE_STUCK_RESET_MINUTES_KEY: 60,
            TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY: 3,
        }

        error = SystemConfigService.validate_execution_config_values(values)

        self.assertIn('必须大于', error)


class PytestRepositoryConfigTests(SimpleTestCase):
    def test_global_git_fields_are_not_registered(self):
        removed_keys = {
            'PYTEST_GIT_URL',
            'PYTEST_GIT_PROVIDER',
            'PYTEST_GIT_API_BASE_URL',
            'PYTEST_GIT_ACCESS_TOKEN',
            'PYTEST_GIT_OPERATION_MODE',
        }

        self.assertTrue(removed_keys.isdisjoint({item.key for item in SYSTEM_CONFIG_REGISTRY}))


class DataFactoryValidationEnvironmentConfigTests(SimpleTestCase):
    def test_registry_defaults_to_all_environments(self):
        definition = next(
            item for item in SYSTEM_CONFIG_REGISTRY
            if item.key == DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY
        )

        self.assertEqual(definition.group, 'data_factory')
        self.assertIsNone(definition.default_value)

    def test_environment_list_keeps_only_supported_unique_values(self):
        self.assertEqual(
            SystemConfigService.normalize_environment_list('[3, 0, "3", 9, "invalid"]'),
            [0, 3],
        )

    def test_empty_or_invalid_environment_list_means_all(self):
        self.assertEqual(SystemConfigService.normalize_environment_list(None), [])
        self.assertEqual(SystemConfigService.normalize_environment_list('invalid-json'), [])

    def test_environment_list_request_value_is_serialized_to_json(self):
        definition = next(
            item for item in SYSTEM_CONFIG_REGISTRY
            if item.key == DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY
        )
        config = SimpleNamespace(value_type=definition.value_type)

        value = CacheDataCRUD._CacheDataCRUD__normalize_config_value(config, [0])

        self.assertEqual(value, '[0]')


class DataFactoryValidationEnvironmentPersistenceTests(SimpleTestCase):
    def test_empty_environment_selection_is_stored_as_null(self):
        config = SimpleNamespace(value='[]', save=Mock())

        with patch.object(CacheData.objects, 'get', return_value=config):
            SystemConfigService.normalize_data_factory_validation_environments()

        self.assertIsNone(config.value)
        config.save.assert_called_once_with(update_fields=['value', 'update_time'])


class SqlExecutionConfigTests(SimpleTestCase):
    def test_slow_sql_threshold_defaults_to_twenty_seconds(self):
        definition = next(
            item for item in SYSTEM_CONFIG_REGISTRY
            if item.key == SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY
        )

        self.assertEqual(definition.group, 'data_factory')
        self.assertEqual(
            definition.default_value,
            SQL_SLOW_QUERY_THRESHOLD_SECONDS_DEFAULT,
        )

    def test_slow_sql_threshold_range_is_validated(self):
        self.assertIsNone(
            SystemConfigService.validate_sql_execution_config(
                SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
                20,
            )
        )
        self.assertIsNotNone(
            SystemConfigService.validate_sql_execution_config(
                SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
                0,
            )
        )

    def test_editable_config_uses_registered_validator_chain(self):
        self.assertIsNone(
            SystemConfigService.validate_editable_config(
                SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
                20,
            )
        )
        self.assertIsNotNone(
            SystemConfigService.validate_editable_config(
                SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY,
                0,
            )
        )


class AssertionCatalogServiceTests(SimpleTestCase):
    @patch('src.apps.system.services.assertion_catalog.assertion_func_info', [])
    @patch('src.apps.system.services.assertion_catalog.CacheDataValue.get_cache_value')
    def test_catalog_separates_ui_scopes(self, get_cache_value):
        get_cache_value.return_value = [
            {'value': 'web', 'label': 'Web操作', 'children': []},
            {
                'value': 'ass_web',
                'label': 'ass_web',
                'children': [
                    {
                        'value': '页面文本',
                        'label': '页面文本',
                        'children': [
                            {'value': 'w_contains', 'label': '包含文本'},
                        ],
                    }
                ],
            },
            {
                'value': 'ass_android',
                'label': 'ass_android',
                'children': [
                    {
                        'value': '元素断言',
                        'label': '元素断言',
                        'children': [{'value': 'a_exists', 'label': '元素存在'}],
                    }
                ],
            },
        ]

        result = AssertionCatalogService.catalog()

        self.assertEqual([item['value'] for item in result], ['ass_web', 'ass_android'])
        self.assertEqual(result[0]['label'], 'Web UI断言')
        self.assertEqual(result[0]['scope'], 'web')
        self.assertFalse(result[0]['testable'])
        self.assertEqual(result[1]['label'], 'Android UI断言')
        self.assertEqual(result[1]['scope'], 'android')

    @patch('src.apps.system.services.assertion_catalog.assertion_func_info', [])
    @patch('src.apps.system.services.assertion_catalog.CacheDataValue.get_cache_value')
    def test_catalog_marks_mysql_as_runtime_only(self, get_cache_value):
        get_cache_value.return_value = [
            {
                'value': 'sql断言',
                'label': '数据库断言',
                'children': [
                    {
                        'value': 'mysql',
                        'label': 'MySQL',
                        'children': [{'value': 'mysql_row_count', 'label': '行数等于'}],
                    }
                ],
            }
        ]

        result = AssertionCatalogService.catalog()
        method = result[0]['children'][0]['children'][0]

        self.assertEqual(result[0]['scope'], 'mysql')
        self.assertFalse(method['testable'])
        self.assertIn('用例运行时', method['test_disabled_reason'])

    @patch('src.apps.system.services.assertion_catalog.assertion_func_info', [])
    @patch('src.apps.system.services.assertion_catalog.CacheDataValue.get_cache_value')
    def test_catalog_marks_file_examples_as_placeholders(self, get_cache_value):
        get_cache_value.return_value = [
            {
                'value': '文件断言',
                'label': '文件断言',
                'children': [
                    {
                        'value': 'Excel断言',
                        'label': 'Excel断言',
                        'children': [
                            {
                                'value': 'assert_excel_row_data',
                                'label': '断言某一行数据',
                                'parameter': [
                                    {
                                        'f': 'expect',
                                        'v': {'行数据': 'json格式的行数据'},
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        method = AssertionCatalogService.catalog()[0]['children'][0]['children'][0]

        self.assertTrue(method['parameter'][0]['example_as_placeholder'])
        self.assertEqual(method['parameter'][0]['object_fields'][0]['n'], '行数据')
        self.assertEqual(method['parameter'][0]['object_fields'][0]['value_type'], 'json')

    def test_object_parameter_contains_named_field_metadata(self):
        parameter = AssertionCatalogService._normalize_parameter(
            {'f': 'expect', 'v': '{"min":10,"max":20}'},
            file_assertion=False,
        )

        self.assertTrue(parameter['example_as_placeholder'])
        self.assertEqual(parameter['object_fields'], [
            {'f': 'min', 'n': '最小值', 'p': '10', 'value_type': 'number'},
            {'f': 'max', 'n': '最大值', 'p': '20', 'value_type': 'number'},
        ])

    def test_object_parameter_prefers_mangotools_field_metadata(self):
        object_fields = [
            {
                'f': 'value',
                'n': '目标值',
                'p': '请输入目标值',
                'value_type': 'number',
                'input_type': 'number',
            },
            {
                'f': 'tolerance',
                'n': '允许误差',
                'p': '请输入允许误差',
                'value_type': 'number',
                'input_type': 'number',
            },
        ]

        parameter = AssertionCatalogService._normalize_parameter(
            {
                'f': 'expect',
                'v': {'value': 10, 'tolerance': 0.01},
                'object_fields': object_fields,
            },
            file_assertion=False,
        )

        self.assertEqual(object_fields, parameter['object_fields'])


class CacheDataSecretValueTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CacheDataViews.as_view({'get': 'get_key_value'})
        CacheData.objects.create(
            describe='AI API Key',
            key='AI_API_KEY',
            value='secret-value',
            is_secret=True,
        )
        CacheData.objects.create(
            describe='普通配置',
            key='PUBLIC_SETTING',
            value='public-value',
            is_secret=False,
        )

    def test_single_secret_value_is_masked(self):
        response = self.view(self.factory.get('/api/system/cache/data/key/value', {'key': 'AI_API_KEY'}))

        self.assertEqual(response.data['data'], SECRET_VALUE_MASK)

    def test_batch_secret_value_is_masked_and_public_value_is_returned(self):
        request = self.factory.get(
            '/api/system/cache/data/key/value',
            [('keys[]', 'AI_API_KEY'), ('keys[]', 'PUBLIC_SETTING')],
        )
        response = self.view(request)

        self.assertEqual(response.data['data']['AI_API_KEY'], SECRET_VALUE_MASK)
        self.assertEqual(response.data['data']['PUBLIC_SETTING'], 'public-value')

    def test_actuator_identity_can_read_secret_value(self):
        request = self.factory.get(
            '/api/system/cache/data/key/value',
            {'key': 'AI_API_KEY'},
            HTTP_SOURCE_TYPE='2',
        )
        force_authenticate(request, user={'client_type': 2})

        response = self.view(request)

        self.assertEqual(response.data['data'], 'secret-value')

    def test_actuator_header_without_actuator_identity_is_masked(self):
        request = self.factory.get(
            '/api/system/cache/data/key/value',
            {'key': 'AI_API_KEY'},
            HTTP_SOURCE_TYPE='2',
        )
        force_authenticate(request, user={'client_type': 1})

        response = self.view(request)

        self.assertEqual(response.data['data'], SECRET_VALUE_MASK)

    def test_empty_secret_value_returns_none(self):
        CacheData.objects.filter(key='AI_API_KEY').update(value='')

        response = self.view(self.factory.get('/api/system/cache/data/key/value', {'key': 'AI_API_KEY'}))

        self.assertIsNone(response.data['data'])


class ApiConcurrencyServiceTests(SimpleTestCase):
    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=6)
    def test_resolve_report_limit_uses_platform_when_empty(self, _mock_limit):
        self.assertEqual(ApiConcurrencyService.resolve_report_limit(None), 6)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=6)
    def test_explicit_limit_cannot_exceed_platform(self, _mock_limit):
        with self.assertRaises(SystemError):
            ApiConcurrencyService.resolve_report_limit(7)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=6)
    def test_task_trigger_clamps_saved_config_but_rejects_manual_override(self, _mock_limit):
        self.assertEqual(ApiConcurrencyService.resolve_task_trigger_limit(9), 6)
        with self.assertRaises(SystemError):
            ApiConcurrencyService.resolve_task_trigger_limit(
                2,
                override=9,
                override_provided=True,
            )

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=6)
    def test_boolean_is_not_a_valid_concurrency(self, _mock_limit):
        with self.assertRaises(SystemError):
            ApiConcurrencyService.resolve_report_limit(True)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=6)
    def test_task_serializer_uses_same_platform_limit(self, _mock_limit):
        serializer = TasksSerializers(
            data={'api_concurrency_limit': 7},
            partial=True,
        )
        with self.assertRaises(SystemError):
            serializer.is_valid()


class TestSuiteRetryServiceTests(TestCase):
    def setUp(self):
        release_patcher = patch(
            'src.apps.task_center.services.selection.api_case_binding.ApiCaseRevisionService.resolve_current_published',
            side_effect=lambda case_id: SimpleNamespace(
                case_revision_id=case_id * 10,
                case_release_id=case_id * 100,
                checksum=f'checksum-{case_id}',
            ),
        )
        release_patcher.start()
        self.addCleanup(release_patcher.stop)
        project = Project.objects.create(name='报告重试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.user = User.objects.create(
            name='报告重试用户',
            username='report_retry_user',
            password='pwd',
            is_super_admin=True,
        )
        self.token = jwt.encode({'id': self.user.id}, settings.SECRET_KEY, algorithm='HS256')
        self.suite = TestSuite.objects.create(
            id=30001,
            project_product=self.product,
            test_env=0,
            user=self.user,
            status=TaskEnum.FAIL.value,
            is_notice=0,
        )
        self.details = [
            TestSuiteDetails.objects.create(
                test_suite=self.suite,
                type=TestCaseTypeEnum.API.value,
                project_product=self.product,
                test_env=0,
                case_id=case_id,
                case_name=f'重试用例{case_id}',
                status=TaskEnum.FAIL.value,
                retry=2,
                success=1,
                warning=1,
                fail=1,
            )
            for case_id in (1, 2)
        ]
        for detail in self.details:
            ExecutionResult.objects.create(
                source_type='report',
                target_type='api_case',
                target_id=detail.case_id,
                test_suite=self.suite,
                test_suite_detail=detail,
                test_env=detail.test_env,
                status=detail.status,
                result_data={'status': 'old'},
                result_size=17,
            )

    def test_retry_all_switches_suite_and_all_details_environment(self):
        selected_env, _ = TestSuiteRetryService.retry_all(self.suite.id, 3)

        self.suite.refresh_from_db()
        self.assertEqual(selected_env, 3)
        self.assertEqual(self.suite.test_env, 3)
        self.assertEqual(self.suite.status, TaskEnum.STAY_BEGIN.value)
        for detail in TestSuiteDetails.objects.filter(test_suite=self.suite):
            self.assertEqual(detail.test_env, 3)
            self.assertEqual(detail.status, TaskEnum.STAY_BEGIN.value)
            self.assertEqual(detail.retry, 0)
            self.assertEqual((detail.success, detail.warning, detail.fail), (0, 0, 0))
            self.assertEqual(detail.api_case_revision_id, detail.case_id * 10)
            self.assertEqual(detail.api_case_release_id, detail.case_id * 100)
            self.assertEqual(detail.config_checksum, f'checksum-{detail.case_id}')
        self.assertEqual(ExecutionResult.objects.count(), 2)
        self.assertFalse(ExecutionResult.objects.filter(is_latest=True).exists())

    def test_retry_switches_legacy_unpublished_snapshot_to_current_editing(self):
        detail = SimpleNamespace(
            type=TestCaseTypeEnum.API.value,
            case_id=1,
            api_case_revision_id=101,
            api_case_release_id=None,
            config_checksum='snapshot-checksum',
            test_suite=SimpleNamespace(tasks_id=None),
        )

        with patch.object(
                ApiCaseTaskBindingService,
                'resolve_execution_selection',
        ) as resolve_selection:
            TestSuiteRetryService.refresh_current_api_release(detail)

        resolve_selection.assert_not_called()
        self.assertIsNone(detail.api_case_revision_id)
        self.assertIsNone(detail.api_case_release_id)
        self.assertIsNone(detail.config_checksum)

    def test_retry_all_without_environment_keeps_original_environment(self):
        selected_env, _ = TestSuiteRetryService.retry_all(self.suite.id)

        self.assertEqual(selected_env, 0)
        self.assertFalse(
            TestSuiteDetails.objects.filter(test_suite=self.suite).exclude(test_env=0).exists()
        )

    def test_retry_all_without_concurrency_override_keeps_original_concurrency(self):
        self.suite.api_concurrency_limit = 2
        self.suite.save(update_fields=['api_concurrency_limit'])

        _, selected_limit = TestSuiteRetryService.retry_all(
            self.suite.id,
            api_concurrency_limit='',
            concurrency_override_provided=False,
        )

        self.suite.refresh_from_db()
        self.assertEqual(selected_limit, 2)
        self.assertEqual(self.suite.api_concurrency_limit, 2)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_retry_all_switches_report_concurrency(self, _mock_limit):
        self.suite.api_concurrency_limit = 2
        self.suite.save(update_fields=['api_concurrency_limit'])

        _, selected_limit = TestSuiteRetryService.retry_all(
            self.suite.id,
            3,
            4,
            concurrency_override_provided=True,
        )

        self.suite.refresh_from_db()
        self.assertEqual(selected_limit, 4)
        self.assertEqual(self.suite.api_concurrency_limit, 4)

    def test_retry_all_rejects_invalid_environment_without_partial_update(self):
        with self.assertRaises(SystemError):
            TestSuiteRetryService.retry_all(self.suite.id, 99)

        self.suite.refresh_from_db()
        self.assertEqual(self.suite.test_env, 0)
        self.assertEqual(self.suite.status, TaskEnum.FAIL.value)
        self.assertEqual(
            TestSuiteDetails.objects.filter(
                test_suite=self.suite,
                status=TaskEnum.FAIL.value,
                test_env=0,
            ).count(),
            2,
        )
        self.assertEqual(ExecutionResult.objects.count(), 2)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_retry_endpoint_applies_selected_execution_config(self, _mock_limit):
        self.suite.api_concurrency_limit = 2
        self.suite.save(update_fields=['api_concurrency_limit'])
        response = self.client.get(
            '/api/system/test/suite/details/all/retry',
            {
                'test_suite_id': self.suite.id,
                'test_env': 4,
                'api_concurrency_limit': 4,
            },
            HTTP_AUTHORIZATION=self.token,
        )

        body = response.json()
        self.assertEqual(body['code'], 200)
        self.assertEqual(body['data']['test_env'], 4)
        self.assertEqual(body['data']['api_concurrency_limit'], 4)
        self.suite.refresh_from_db()
        self.assertEqual(self.suite.test_env, 4)
        self.assertEqual(self.suite.api_concurrency_limit, 4)
        self.assertFalse(
            TestSuiteDetails.objects.filter(test_suite=self.suite).exclude(test_env=4).exists()
        )
