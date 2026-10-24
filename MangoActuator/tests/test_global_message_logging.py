from unittest.mock import patch

from src.enums.gui_enum import TipsTypeEnum
from src.enums.tools_enum import MessageEnum
from src.tools.send_global_msg import global_msg_queue, send_global_msg


def _drain_queue():
    while not global_msg_queue.empty():
        global_msg_queue.get_nowait()


def test_realtime_message_defaults_to_debug_and_is_enqueued():
    _drain_queue()
    with patch('src.tools.send_global_msg.log.debug') as log_debug:
        send_global_msg('UI-开始执行步骤')

    log_debug.assert_called_once_with('UI-开始执行步骤')
    message = global_msg_queue.get_nowait()
    assert message.type == MessageEnum.REAL_TIME
    assert message.msg == 'UI-开始执行步骤'


def test_realtime_business_error_uses_warning_log():
    _drain_queue()
    with patch('src.tools.send_global_msg.log.warning') as log_warning:
        send_global_msg('元素执行失败', level=TipsTypeEnum.ERROR)

    log_warning.assert_called_once_with('元素执行失败')
    _drain_queue()


def test_realtime_info_must_be_explicit():
    _drain_queue()
    with patch('src.tools.send_global_msg.log.info') as log_info:
        send_global_msg('开始执行UI测试用例：示例', log_level='info')

    log_info.assert_called_once_with('开始执行UI测试用例：示例')
    _drain_queue()


def test_non_realtime_message_is_not_written_to_runtime_log():
    _drain_queue()
    with patch('src.tools.send_global_msg.log.info') as log_info:
        send_global_msg('连接正常', _type=MessageEnum.BOTTOM)

    log_info.assert_not_called()
    _drain_queue()
