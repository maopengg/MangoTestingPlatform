import json
from pathlib import Path
from unittest.mock import patch

from src.settings import settings
from src.tools.debug_case_file import save_ui_debug_payload


def test_debug_payload_is_not_saved_when_debug_is_disabled(tmp_path: Path):
    with (
        patch.object(settings, 'IS_DEBUG', False),
        patch('src.tools.debug_case_file.project_dir.root_path', return_value=str(tmp_path)),
    ):
        result = save_ui_debug_payload({'name': '示例用例'}, '用例')

    assert result is None
    assert not (tmp_path / 'tests' / 'test.json').exists()


def test_debug_payload_replaces_test_json_when_debug_is_enabled(tmp_path: Path):
    target = tmp_path / 'tests' / 'test.json'
    target.parent.mkdir(parents=True)
    target.write_text('{"name": "旧数据"}', encoding='utf-8')
    payload = {
        'id': 1,
        'name': '示例步骤',
        'test_object': 'https://example.com',
        'element_list': [],
    }

    with (
        patch.object(settings, 'IS_DEBUG', True),
        patch('src.tools.debug_case_file.project_dir.root_path', return_value=str(tmp_path)),
    ):
        result = save_ui_debug_payload(payload, '页面步骤')

    assert result == target
    assert json.loads(target.read_text(encoding='utf-8')) == payload
    assert list(target.parent.glob('.test.json.*.tmp')) == []
