from types import SimpleNamespace
import html
import json
import re
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.reporting.offline_report.api_details import ApiDetailsRenderer
from src.apps.test_center.services.reporting.offline_report.renderer import ReportHtmlService
from src.apps.test_center.services.reporting.offline_report.snapshot import ReportSnapshotService
from src.apps.test_center.tests.test_report_delivery import sample_snapshot


def api_example():
    return {
        'id': 11, 'parameter_id': 12, 'name': '查询审批状态', 'status': TaskEnum.FAIL.value,
        'test_time': '2026-10-28 10:00:39', 'error_message': '响应字段与预期不一致',
        'request': {'method': 'POST', 'url': 'https://example.com/api/status',
                    'headers': {'Authorization': 'Bearer secret-credential'}, 'request_body': {'configured': True}},
        'response': {'code': 200, 'time': 0.23, 'headers': {'Content-Type': 'application/json', 'Set-Cookie': 'private-cookie'},
                     'request_headers': {'Authorization': 'Bearer actual-credential'},
                     'request_body': {'business_id': 'example-item', 'password': 'private-password'},
                     'request_params': {'page': 0}, 'json': {'status': 'processing', 'enabled': False}},
        'ass': [{'group_name': '状态检查', 'group_logic': 'and', 'source_type': 'jsonpath', 'actual_source': '$.status',
                 'actual': 'processing', 'method': '等于预期值', 'expect': 'completed',
                 'status': TaskEnum.FAIL.value, 'ass_msg': '断言失败：实际为处理中'}],
        'cache_data': {'context': '示例缓存', 'token': 'private-token'},
        'data_factory_cache_data': {'entity': '示例实体'},
    }


class OfflineApiDetailsTests(SimpleTestCase):
    def test_report_keeps_drawer_sections_in_case_template_not_list_rows(self):
        snapshot = sample_snapshot()
        snapshot['suites'][0]['cases'][0]['payload'] = [api_example()]
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        for text in ('查询审批状态', 'POST', 'https://example.com/api/status', '状态码', '响应时间', '响应类型',
                     '断言结果', '响应结果', '请求信息', '请求头', '参数', '请求体', '断言数据', '缓存数据', '数据工厂',
                     '实际值', '预期值', 'processing', 'completed', 'business_id', 'example-item'):
            self.assertIn(text, content)
        self.assertIn('<template id="case-1-1"', content)
        self.assertIn('data-case-open href="#case-1-1"', content)
        self.assertNotIn('<tr class="mango-api-detail-row"', content)
        self.assertNotIn('响应结果', content.split('<tbody>')[1].split('</tbody>')[0])
        self.assertNotIn('请求、响应与执行信息（已脱敏，可能截断）', content)
        self.assertNotIn('configured', content)
        for secret in ('secret-credential', 'actual-credential', 'private-cookie', 'private-password', 'private-token'):
            self.assertNotIn(secret, content)
        self.assertIn('[已脱敏]', content)

    def test_all_steps_remain_without_internal_execution_metadata(self):
        failure = api_example()
        recovery = {**api_example(), 'name': '恢复步骤', 'status': TaskEnum.SUCCESS.value, 'is_recovery': True, 'retry_index': 2}
        content = ApiDetailsRenderer.render([failure, recovery])
        self.assertEqual(content.count('<article class="mango-api-call"'), 2)
        self.assertIn('恢复步骤', content)
        for label in ('执行信息', '接口定义 ID', '重试序号', '主流程结果', 'retry_index', 'is_recovery'):
            self.assertNotIn(label, content)
        self.assertEqual(recovery['retry_index'], 2)

    def test_unsafe_text_is_escaped_and_null_zero_false_are_readable(self):
        step = api_example()
        step['name'] = '<script>alert(1)</script>'
        step['response']['json'] = {'empty': None, 'zero': 0, 'enabled': False, 'html': '<img src=x onerror=alert(1)>'}
        content = ApiDetailsRenderer.render(step)
        self.assertNotIn('<script>', content)
        self.assertNotIn('<img src=x', content)
        self.assertIn('&lt;script&gt;', content)
        for text in ('null', '&quot;zero&quot;: 0', 'false'):
            self.assertIn(text, content)

    def test_streaming_and_empty_json_responses_have_structured_sections(self):
        step = api_example()
        step['response'].update(json={}, sse_events=[{'event': 'message', 'data': '示例事件'}],
                                ws_messages=[{'direction': 'receive', 'data': '示例消息'}], ws_close_code=1000)
        content = ApiDetailsRenderer.render(step)
        for text in ('响应 JSON', '<code>{}</code>', 'SSE 事件', 'WebSocket 消息', '示例消息', '示例事件', '1000'):
            self.assertIn(text, content)

    def test_request_response_use_readable_json_without_field_tables_or_double_encoding(self):
        step = api_example()
        step['response']['json'] = {'items': [{'中文': True, 'value': None}], 'count': 0}
        step['response']['request_body'] = {'enabled': False, 'ids': [1, 2]}
        step['response']['request_headers'] = {'Content-Type': 'application/json'}
        content = ApiDetailsRenderer.render(step)
        blocks = [html.unescape(text) for text in re.findall(r'<pre class="mango-api-json"[^>]*><code>(.*?)</code></pre>', content, re.S)]
        parsed = [json.loads(text) for text in blocks]
        self.assertIn(step['response']['json'], parsed)
        self.assertIn(step['response']['request_body'], parsed)
        self.assertTrue(any('\n  "items"' in text for text in blocks))
        self.assertNotIn('<dt>enabled</dt>', content)
        self.assertIn('<dt>Content-Type</dt>', content)
        self.assertEqual(ApiDetailsRenderer.json_value('{"enabled":false}'),
                         '<pre class="mango-api-json" tabindex="0"><code>{&quot;enabled&quot;:false}</code></pre>')

    def test_empty_and_null_json_values_are_not_replaced_by_missing_content(self):
        for response in ({}, [], None, False, 0):
            step = api_example()
            step['response']['json'] = response
            step['response']['request_body'] = {}
            content = ApiDetailsRenderer.render(step)
            self.assertIn(f'<code>{json.dumps(response)}</code>', content)
            self.assertIn('<summary>请求体</summary>', content)
            self.assertIn('<code>{}</code>', content)

    def test_missing_result_is_explicit_instead_of_invented_request_data(self):
        self.assertIn('未保留', ApiDetailsRenderer.render(None))
        content = ApiDetailsRenderer.render([{'name': '历史摘要', 'status': TaskEnum.FAIL.value}])
        self.assertIn('原始执行明细未保留', content)
        self.assertNotIn('未记录响应数据', content)
        self.assertNotIn('未记录请求参数', content)
        self.assertNotIn('role="tab"', content)

    def test_internal_leftover_fields_are_not_exposed_as_other_information(self):
        step = api_example()
        step['request'].update(protocol_type='http', body_type='none', posterior_file=None,
                               mcp_server_id=None, grpc_config=None, trace_parent_step_id=581324)
        step['response']['internal_extra'] = 'internal-response-marker'
        content = ApiDetailsRenderer.render(step)
        for text in ('其他请求信息', '其他响应信息', 'protocol_type', 'body_type', 'posterior_file',
                     'mcp_server_id', 'grpc_config', 'trace_parent_step_id', '581324', 'internal-response-marker'):
            self.assertNotIn(text, content)
        for text in ('请求头', '参数', '请求体', '响应 JSON', '断言数据', '缓存数据'):
            self.assertIn(text, content)
        self.assertEqual(step['request']['trace_parent_step_id'], 581324)

    def test_metrics_round_duration_and_tabs_have_unique_controls(self):
        content = ApiDetailsRenderer.render([api_example(), api_example()], prefix='case-1-2')
        self.assertIn('0.230 秒', content)
        self.assertIn('id="case-1-2-step-1-panel-response"', content)
        self.assertIn('id="case-1-2-step-2-panel-response"', content)
        self.assertIn('aria-controls="case-1-2-step-1-panel-request"', content)
        self.assertIn('data-step-target="case-1-2-step-2"', content)
        self.assertEqual(ApiDetailsRenderer.duration(0.12473464012145996), '0.125 秒')
        self.assertEqual(ApiDetailsRenderer.duration(0), '0.000 秒')
        self.assertEqual(ApiDetailsRenderer.duration(float('nan')), '—')

    def test_snapshot_prefers_original_result_over_list_summary(self):
        row = SimpleNamespace(type=TestCaseTypeEnum.API.value)
        payload = SimpleNamespace(id=1)
        original = [api_example()]
        with patch('src.apps.test_center.services.reporting.offline_report.snapshot.ExecutionResultService.load_result_data', return_value=original) as load, \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteExecutionResultService.normalize_detail_result_data', return_value=original) as normalize, \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteExecutionResultService.get_result_data') as summary:
            self.assertEqual(ReportSnapshotService.case_result_data(row, payload), original)
        load.assert_called_once_with(payload)
        normalize.assert_called_once_with(row, original)
        summary.assert_not_called()

    def test_cleaned_original_result_falls_back_to_saved_summary(self):
        row = SimpleNamespace(type=TestCaseTypeEnum.API.value)
        with patch('src.apps.test_center.services.reporting.offline_report.snapshot.ExecutionResultService.load_result_data', return_value=None), \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteExecutionResultService.get_result_data', return_value=[{'name': '历史摘要'}]) as summary:
            self.assertEqual(ReportSnapshotService.case_result_data(row, SimpleNamespace()), [{'name': '历史摘要'}])
        summary.assert_called_once_with(row)
