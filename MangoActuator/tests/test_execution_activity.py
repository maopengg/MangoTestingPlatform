from unittest.mock import patch

from src.enums.tools_enum import MessageEnum
from src.tools.execution_activity import ExecutionActivity


def test_execution_activity_tracks_running_and_recent_result():
    ExecutionActivity.reset()
    with patch('src.tools.execution_activity.send_global_msg') as sender:
        ExecutionActivity.start('ui-case:1', 'UI 用例', '创建订单', 'maopeng')
        ExecutionActivity.update('ui-case:1', '正在执行：提交审批', 2, 3)
        running = ExecutionActivity.snapshot()['active'][0]

        assert running['task_name'] == '创建订单'
        assert running['current_action'] == '正在执行：提交审批'
        assert running['progress_current'] == 2
        assert running['progress_total'] == 3

        ExecutionActivity.finish('ui-case:1', True)
        snapshot = ExecutionActivity.snapshot()
        assert snapshot['active'] == []
        assert snapshot['recent'][0]['status'] == 'success'
        assert sender.call_args.args[1] == MessageEnum.EXECUTION_STATE


def test_execution_activity_preserves_parallel_tasks():
    ExecutionActivity.reset()
    with patch('src.tools.execution_activity.send_global_msg'):
        ExecutionActivity.start('ui-case:1', 'UI 用例', '用例一')
        ExecutionActivity.start('pytest-case:2', 'Pytest 用例', '用例二')
        ExecutionActivity.finish('ui-case:1', False, '定位失败')

    snapshot = ExecutionActivity.snapshot()
    assert [item['task_id'] for item in snapshot['active']] == ['pytest-case:2']
    assert snapshot['recent'][0]['error_message'] == '定位失败'
