# -*- coding: utf-8 -*-
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mangoautomation.enums import ElementExpEnum, ElementOperationEnum
from mangoautomation.uidrives._async_element import AsyncElement
from mangoautomation.uidrives._sync_element import SyncElement
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from src.services.runtime_config import AiRuntimeConfig, get_ai_config, set_ai_config
from src.services.ui.element_snapshot import UiElementSnapshotReporter
from src.services.ui.element_locator_engine import UiElementLocatorEngine


class _Element:
    id = 15
    element_id = 15
    name = '创建一级订单类型-适用部门'
    category = '新建编辑弹窗-一级分类'
    elements = []


class _NameElement:
    id = 12
    element_id = 12
    name = '创建一级订单类型-订单类型名称'
    category = '新建编辑弹窗-一级分类'
    elements = []


class _OptionElement:
    id = 16
    element_id = 16
    name = '全部部门'
    category = '新建编辑弹窗-一级分类'
    elements = []


class _SubmitElement:
    id = 17
    element_id = 17
    name = '提交'
    category = '新建编辑弹窗-一级分类'
    elements = []


class _RuntimeElement:
    def __init__(self, loc, ele_quantity, visible=True):
        self.loc = loc
        self.ele_quantity = ele_quantity
        self.visible = visible


class _ElementResult:
    def __init__(self, elements):
        self.elements = elements
        self.ope_key = 'w_click'
        self.type = ElementOperationEnum.OPE
        self.status = 0
        self.error_message = 'element failed'
        self.locator_engine = {}


class _FakeLocatorEngine:
    def __init__(self):
        self.calls = []

    async def locate_async(self, **kwargs):
        self.calls.append(kwargs)
        return None

    def get_last_attempt(self, element_id):
        return {}


class _AsyncFirstLocator:
    first = None

    def __init__(self, click_error=None, enabled=True, editable=True):
        self.first = self
        self.click_error = click_error
        self.enabled = enabled
        self.editable = editable

    async def click(self, **kwargs):
        if self.click_error:
            raise self.click_error

    async def is_enabled(self):
        return self.enabled

    async def is_editable(self):
        return self.editable


class _SyncFirstLocator:
    first = None

    def __init__(self, click_error=None, enabled=True, editable=True):
        self.first = self
        self.click_error = click_error
        self.enabled = enabled
        self.editable = editable

    def click(self, **kwargs):
        if self.click_error:
            raise self.click_error

    def is_enabled(self):
        return self.enabled

    def is_editable(self):
        return self.editable


_HTML = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <span>订单类型名称</span>
      <input placeholder="请输入订单类型名称" />
    </div>
    <div class="form-item">
      <span>适用部门</span>
      <input type="hidden" value="hidden-dept" />
      <div class="fake-select" tabindex="0">请选择</div>
    </div>
    <div style="margin-top:20px"><span>适用部门</span></div>
    <table><thead><tr><th>适用部门</th></tr></thead></table>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_TABLE_BEFORE_MODAL = """<!doctype html>
<html>
<body>
  <table>
    <thead><tr><th>适用部门</th></tr></thead>
    <tbody>
      <tr><td><button>全部部门</button></td></tr>
    </tbody>
  </table>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="form-item">
      <span>适用部门</span>
      <input type="hidden" value="hidden-dept" />
      <div class="fake-select" tabindex="0">请选择</div>
    </div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_TABLE_HEADER_AND_FORM = """<!doctype html>
<html>
<body>
  <table class="ud__table">
    <thead class="ud__table-header"><tr><th><span>适用部门</span></th></tr></thead>
    <tbody>
      <tr><td><button>全部部门</button></td></tr>
    </tbody>
  </table>
  <section class="edit-panel">
    <div class="form-item">
      <span>适用部门</span>
      <input type="hidden" value="hidden-dept" />
      <div class="fake-select" tabindex="0">请选择</div>
    </div>
  </section>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_CONTRACT_TYPE_INPUTS = """<!doctype html>
<html>
<body>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="form-item">
      <span>订单类型名称</span>
      <input placeholder="请输入订单类型名称" />
    </div>
    <div class="form-item">
      <span>订单类型说明</span>
      <input placeholder="请输入订单类型说明" />
    </div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; align-items: center; }
    input { border: 1px solid #ccc; padding: 4px 12px; }
  </style>
</body>
</html>"""


_HTML_PORTAL_OPTION = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <span>适用部门</span>
      <div class="fake-select" role="combobox" aria-label="适用部门" tabindex="0">请选择</div>
    </div>
  </div>
  <div class="portal-root">
    <div role="option" class="select-option">全部部门</div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select, .select-option { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_UNIQUE_VISIBLE_TEXT = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <span>适用部门</span>
      <div class="fake-select" role="combobox" aria-label="适用部门" tabindex="0">请选择</div>
    </div>
  </div>
  <div class="portal-root">
    <div>全部部门</div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select, .portal-root div { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_POPUP_OPTION_WITH_TABLE_DUPLICATES = """<!doctype html>
<html>
<body>
  <table>
    <tbody>
      <tr><td><button>全部部门</button></td></tr>
      <tr><td><button>全部部门</button></td></tr>
      <tr><td><button>全部部门</button></td></tr>
    </tbody>
  </table>
  <div class="ud__trigger-popup">
    <div class="ud__tree">
      <div class="ud__tree-node">
        <label class="ud__checkbox">
          <input class="ud__checkbox__input" type="checkbox" />
          <span>全部部门</span>
        </label>
      </div>
    </div>
  </div>
  <style>
    .ud__trigger-popup { position: fixed; left: 300px; top: 120px; border: 1px solid #ccc; padding: 8px; }
    .ud__tree-node, .ud__checkbox { display: block; padding: 4px 12px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_UNIQUE_COMMON_TEXT = """<!doctype html>
<html>
<body>
  <div class="portal-root">
    <div>提交</div>
  </div>
  <style>
    .portal-root div { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_STABLE_ATTR = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <span id="dept-label">适用部门</span>
      <div class="fake-select" tabindex="0" data-test-id="dept-select">请选择</div>
    </div>
    <div style="margin-top:20px"><span>适用部门</span></div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_LABEL_FOR = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <label for="dept-select">适用部门</label>
      <input id="dept-select" value="请选择" />
    </div>
    <div style="margin-top:20px"><span>适用部门</span></div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
  </style>
</body>
</html>"""


_HTML_ROLE_COMBOBOX = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <span>适用部门</span>
      <div class="fake-select" role="combobox" aria-label="适用部门" tabindex="0">请选择</div>
    </div>
    <div style="margin-top:20px"><span>适用部门</span></div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_ROLE_COMBOBOX_LOOSE = """<!doctype html>
<html>
<body>
  <div class="modal">
    <div class="form-item">
      <div class="fake-select" role="combobox" aria-label="适用部门 请选择" tabindex="0">请选择</div>
    </div>
  </div>
  <style>
    .form-item { display: flex; gap: 12px; margin: 8px; }
    .fake-select { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; }
  </style>
</body>
</html>"""


_HTML_COMPONENT_SELECT_CONTAINER = """<!doctype html>
<html>
<body>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="ud__form-item">
      <div class="ud__form-item-label">适用部门</div>
      <div class="lark-select">
        <input class="lark-select-hidden-input" type="hidden" value="" />
        <div class="lark-select-selection" aria-haspopup="listbox">
          <span class="lark-select-placeholder">请选择</span>
        </div>
      </div>
    </div>
  </div>
  <style>
    .ud__form-item { display: flex; gap: 12px; margin: 8px; align-items: center; }
    .ud__form-item-label { width: 90px; }
    .lark-select-selection { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; min-width: 200px; }
    .lark-select-hidden-input { display: none; }
  </style>
</body>
</html>"""


_HTML_POINTER_LABEL_SELECT = """<!doctype html>
<html>
<body>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="ud__form-item">
      <span class="ud__form-item-label">适用部门</span>
      <div class="lark-select">
        <div class="lark-select-selection" aria-haspopup="listbox">
          <span class="lark-select-placeholder">请选择</span>
        </div>
      </div>
    </div>
  </div>
  <style>
    .ud__form-item { display: flex; gap: 12px; margin: 8px; align-items: center; }
    .ud__form-item-label { width: 90px; cursor: pointer; }
    .lark-select-selection { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; min-width: 200px; }
  </style>
</body>
</html>"""


_HTML_OFFSCREEN_DEPT_SELECT = """<!doctype html>
<html>
<body>
  <div style="height: 1200px;">顶部占位内容</div>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="ud__form-item">
      <span class="ud__form-item-label">适用部门</span>
      <div class="lark-select">
        <div class="lark-select-selection" aria-haspopup="listbox" tabindex="0">
          <span class="lark-select-placeholder">请选择</span>
        </div>
      </div>
    </div>
  </div>
  <style>
    .ud__form-item { display: flex; gap: 12px; margin: 8px; align-items: center; }
    .ud__form-item-label { width: 90px; }
    .lark-select-selection { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; min-width: 200px; }
  </style>
</body>
</html>"""


_HTML_FORM_ITEM_CONTROL_FAR_BELOW = """<!doctype html>
<html>
<body>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="ud__form-item">
      <div class="ud__form-item-label">适用部门</div>
      <div class="ud__form-item-extra">请选择可使用该订单分类的部门范围</div>
      <div class="ud__form-item-control">
        <div class="lark-select">
          <div class="lark-select-selection" aria-haspopup="listbox" tabindex="0">
            <span class="lark-select-placeholder">请选择</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <style>
    .ud__form-item { width: 420px; margin: 8px; }
    .ud__form-item-label { height: 24px; }
    .ud__form-item-extra { margin-top: 20px; color: #999; }
    .ud__form-item-control { margin-top: 120px; }
    .lark-select-selection { border: 1px solid #ccc; padding: 4px 16px; cursor: pointer; min-width: 200px; }
  </style>
</body>
</html>"""


_HTML_BYTE_FORM_UD_SELECT = """<!doctype html>
<html>
<body>
  <div class="byte-form-item byte-form-layout-vertical">
    <div class="byte-form-label-item">
      <label>
        <div class="style__UIDepartmentTitle-jdcPXk cODJde">
          适用部门
          <span class="universe-icon style__UIInfoOutlined-hzRvwy eDVxlK">
            <svg width="1em" height="1em" viewBox="0 0 24 24" data-icon="InfoOutlined">
              <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"></path>
            </svg>
          </span>
          <strong class="style__UIRequiredIcon-WGOUW eHzLFv"></strong>
        </div>
      </label>
    </div>
    <div class="byte-form-item-wrapper">
      <div class="byte-form-item-control-wrapper">
        <div class="byte-form-item-control">
          <div class="byte-form-item-control-children">
            <div class="ud__select" style="width: 100%;">
              <div class="ud__select__selector ud__select__selector-md ud__select__selector-border-normal ud__select__selector-multiple" style="max-height: 188px;">
                <span class="ud__empty-inline-element">&nbsp;</span>
                <div class="ud__select__selector__content">
                  <div class="ud__text ud__select__selector__placeholder">请选择适用部门</div>
                  <div class="ud__overflow ud__select__selector__search">
                    <div class="ud__select__selector__search__suffix ud__overflow__suffix">
                      <span class="ud__select__selector__search__input_container">
                        <input class="ud__select__selector__search__input ud__native-input" role="combobox" autocomplete="off" type="search" value="" />
                        <span class="ud__select__selector__search__measure" aria-hidden="true">&nbsp;</span>
                      </span>
                    </div>
                  </div>
                </div>
                <div class="ud__select__selector__arrow">
                  <span class="universe-icon">∨</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <style>
    .byte-form-item { width: 480px; padding: 8px; }
    .byte-form-label-item { margin-bottom: 8px; }
    .ud__select__selector { border: 1px solid #ccc; min-height: 32px; padding: 4px 12px; cursor: pointer; }
    .ud__select__selector__content { display: flex; align-items: center; min-height: 24px; }
    .ud__select__selector__placeholder { color: #999; }
    .ud__select__selector__search__input { width: 6px; border: 0; outline: 0; }
  </style>
</body>
</html>"""


_HTML_DISABLED_LABEL_CONTROL = """<!doctype html>
<html>
<body>
  <div class="ud__modal" role="dialog" aria-modal="true">
    <div class="ud__form-item">
      <div class="ud__form-item-label">适用部门</div>
      <button disabled>请选择</button>
    </div>
  </div>
  <style>
    .ud__form-item { display: flex; gap: 12px; margin: 8px; align-items: center; }
    .ud__form-item-label { width: 90px; }
  </style>
</body>
</html>"""


def _chrome_path():
    candidates = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    ]
    return next((path for path in candidates if Path(path).exists()), None)


def _assert_target_text_candidate():
    texts = UiElementLocatorEngine._target_texts(_Element())
    assert texts[0] == '适用部门', texts
    assert UiElementLocatorEngine._playwright_text_sub_score('适用部门', 3, 0) == 86
    assert UiElementLocatorEngine._playwright_text_sub_score('适用部门', 3, 1) == 76
    candidates = UiElementLocatorEngine._normalize_dom_candidates(
        [{'source': 'playwright_text_sub', 'exp': 'text', 'loc': '适用部门', 'sub': 1, 'score': 86}],
        [],
    )
    assert candidates[0]['exp'] == ElementExpEnum.TEXT.value
    assert candidates[0]['loc'] == '适用部门'
    assert candidates[0]['sub'] == 1
    assert candidates[0]['score'] == 86


def _assert_candidate_diagnostics():
    candidates = UiElementLocatorEngine._normalize_dom_candidates(
        [{
            'source': 'dom_stable_attr',
            'exp': 'css',
            'loc': 'div[data-test-id="dept-select"]',
            'sub': None,
            'score': 92,
            'matched_label': '适用部门',
            'candidate_text': '请选择',
            'reason': 'same-form-item matched by label proximity',
        }],
        [],
    )
    candidate = candidates[0]
    assert candidate['matched_label'] == '适用部门'
    assert candidate['candidate_text'] == '请选择'
    assert candidate['reason'] == 'same-form-item matched by label proximity'
    summary = UiElementLocatorEngine._candidate_summary(
        [
            {'source': 'prompt_text_candidate', 'exp': 2, 'loc': '创建一级订单类型-适用部门'},
            {'source': 'playwright_text_sub', 'exp': 3, 'loc': '适用部门', 'sub': 1},
            {'source': 'label_relative_xpath', 'exp': 0, 'loc': '//label/following::*[2]'},
        ],
        [
            {
                'source': 'prompt_text_candidate',
                'exp': 2,
                'loc': '创建一级订单类型-适用部门',
                'verified': False,
                'count': 0,
                'reject_reason': 'count=0',
            },
            {
                'source': 'playwright_text_sub',
                'exp': 3,
                'loc': '适用部门',
                'sub': 1,
                'verified': False,
                'count': 3,
                'reject_reason': 'text click candidate rejected: text node has no interactive signal',
            },
            {
                'source': 'label_relative_xpath',
                'exp': 0,
                'loc': '//label/following::*[2]',
                'verified': True,
                'count': 1,
            },
        ],
        ['prompt_text_candidate:创建一级订单类型-适用部门 count=0'],
    )
    assert summary['total'] == 3
    assert summary['checked'] == 3
    assert summary['verified'] == 1
    assert summary['by_source']['prompt_text_candidate']['reasons']['count=0'] == 1
    assert summary['by_source']['playwright_text_sub']['reasons']['text_not_interactive'] == 1
    assert summary['by_source']['label_relative_xpath']['verified'] == 1
    assert summary['top_rejections'][0]['source'] == 'prompt_text_candidate'


def _assert_candidate_source_priority():
    candidates = UiElementLocatorEngine._normalize_dom_candidates(
        [
            {
                'source': 'dom_stable_attr',
                'exp': 'css',
                'loc': 'div[aria-label="适用部门"]',
                'score': 99,
            },
            {
                'source': 'playwright_role',
                'exp': 'locator',
                'loc': "get_by_role('combobox', name='适用部门', exact=True)",
                'score': 99,
            },
        ],
        [],
    )
    assert candidates[0]['source'] == 'playwright_role', candidates


def _assert_trigger_context():
    error = RuntimeError('fixed locator is not editable')
    trigger = UiElementLocatorEngine._trigger_context(
        error,
        ['get_by_role("cobox")', 'get_by_role("cox")'],
        {'ope_key': 'w_click', 'loc': 'get_by_role("cobox")', 'exp': 2, 'sub': None},
    )
    assert trigger['error'] == 'fixed locator is not editable'
    assert trigger['failed_expression'] == ['get_by_role("cobox")', 'get_by_role("cox")']
    assert trigger['ope_key'] == 'w_click'
    assert trigger['origin_loc'] == 'get_by_role("cobox")'


def _assert_latest_success_element():
    elements = [
        _RuntimeElement('get_by_role("cobox")', 0, False),
        _RuntimeElement('get_by_text("适用部门")', 3, True),
        _RuntimeElement('xpath=//div[1]', 1, True),
    ]
    selected = UiElementSnapshotReporter._latest_success_element(elements)
    assert selected.loc == 'xpath=//div[1]', selected.loc
    assert UiElementSnapshotReporter._latest_success_element(elements[:1]) is None


def _assert_ambiguous_locator_refine_gate():
    async_element = object.__new__(AsyncElement)
    sync_element = object.__new__(SyncElement)
    for instance in (async_element, sync_element):
        instance.base_data = SimpleNamespace(locator_engine=object())
        instance.element_model = SimpleNamespace(type=ElementOperationEnum.OPE)
    async_gate = getattr(async_element, '_AsyncElement__should_refine_ambiguous_locator')
    sync_gate = getattr(sync_element, '_SyncElement__should_refine_ambiguous_locator')
    for gate in (async_gate, sync_gate):
        assert gate(2, None) is True
        assert gate(2, '') is True
        assert gate(2, 0) is True
        assert gate(2, 1) is False
        assert gate(1, None) is False
        assert gate(0, None) is False

    async_element.base_data = SimpleNamespace(locator_engine=None)
    assert async_gate(2, None) is False
    async_element.base_data = SimpleNamespace(locator_engine=object())
    async_element.element_model = SimpleNamespace(type=ElementOperationEnum.ASS)
    assert async_gate(2, None) is False


async def _assert_fixed_locator_actionability_gate():
    async_element = object.__new__(AsyncElement)
    sync_element = object.__new__(SyncElement)
    for instance in (async_element, sync_element):
        instance.base_data = SimpleNamespace(locator_engine=object())
        instance.element_model = SimpleNamespace(type=ElementOperationEnum.OPE, ope_key='w_click')

    async_check = getattr(async_element, '_AsyncElement__fixed_locator_actionability_error')
    sync_check = getattr(sync_element, '_SyncElement__fixed_locator_actionability_error')

    assert await async_check(_AsyncFirstLocator(), 1) is None
    assert sync_check(_SyncFirstLocator(), 1) is None
    assert 'not clickable' in await async_check(_AsyncFirstLocator(RuntimeError('not clickable')), 1)
    assert 'not clickable' in sync_check(_SyncFirstLocator(RuntimeError('not clickable')), 1)

    async_element.base_data = SimpleNamespace(locator_engine=None)
    assert await async_check(_AsyncFirstLocator(RuntimeError('not clickable')), 1) is None

    async_element.base_data = SimpleNamespace(locator_engine=object())
    async_element.element_model = SimpleNamespace(type=ElementOperationEnum.OPE, ope_key='w_input')
    assert await async_check(_AsyncFirstLocator(enabled=True, editable=False), 1) == 'fixed locator is not editable'


async def _assert_failed_report_does_not_run_locator_again():
    locator_engine = _FakeLocatorEngine()
    element_result = _ElementResult([
        _RuntimeElement('get_by_role("cobox")', 0, False),
        _RuntimeElement('get_by_role("cox")', 0, False),
    ])
    page = SimpleNamespace(
        url='https://example.test/page',
        is_closed=lambda: False,
        title=AsyncMock(return_value='Example'),
    )
    original_config = get_ai_config()
    try:
        set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
        with patch(
            'src.services.ui.element_snapshot.UiElementSnapshotReporter._build_accessibility_digest',
            new=AsyncMock(return_value={}),
        ), patch(
            'src.services.ui.element_snapshot.HTTP.ui_element.save_heal_record',
            new=AsyncMock(return_value={'id': 1}),
        ):
            await UiElementSnapshotReporter.report_failed_heal_record(
                page,
                SimpleNamespace(test_env=0, id=3, case_steps_id=None),
                _Element(),
                element_result,
                locator_engine,
            )
    finally:
        set_ai_config(original_config)
    assert locator_engine.calls == [], 'reporting must reuse the execution trace instead of locating again'


async def _assert_snapshot_background_concurrency_is_bounded():
    blocker = asyncio.Event()
    tasks = {asyncio.create_task(blocker.wait()) for _ in range(UiElementSnapshotReporter.MAX_BACKGROUND_TASKS)}
    original_tasks = UiElementSnapshotReporter._background_tasks
    original_ids = UiElementSnapshotReporter._background_element_ids
    try:
        UiElementSnapshotReporter._background_tasks = set(tasks)
        UiElementSnapshotReporter._background_element_ids = set(range(100, 104))
        UiElementSnapshotReporter.schedule_success_snapshot(
            None,
            SimpleNamespace(),
            _Element(),
            _ElementResult([]),
        )
        assert UiElementSnapshotReporter._background_tasks == tasks
    finally:
        blocker.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        UiElementSnapshotReporter._background_tasks = original_tasks
        UiElementSnapshotReporter._background_element_ids = original_ids


async def _assert_browser_candidate():
    chrome = _chrome_path()
    if not chrome:
        print('未找到系统 Chrome，跳过浏览器级定位引擎验证')
        return
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path=chrome)
        try:
            page = await browser.new_page()
            await page.set_content(_HTML)
            engine = UiElementLocatorEngine(test_env=0)
            candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert candidates[0]['source'] == 'label_relative_xpath', candidates
            assert candidates[0]['exp'] == ElementExpEnum.XPATH.value, candidates
            assert 'following::*' in candidates[0]['loc'], candidates
            assert candidates[0]['loc'].endswith('[2]'), candidates
            assert candidates[0]['score'] >= 90, candidates
            assert any(
                candidate['source'] == 'dom_proximity_xpath'
                and candidate['exp'] == ElementExpEnum.XPATH.value
                and candidate['loc'].startswith('/html/body/')
                for candidate in candidates
            ), candidates
            assert any(
                candidate['source'] == 'playwright_text_sub'
                and candidate['exp'] == ElementExpEnum.TEXT.value
                and candidate['loc'] == '适用部门'
                and candidate['sub'] == 1
                for candidate in candidates
            ), candidates
            assert all(
                not (
                    candidate['source'] == 'dom_proximity'
                    and candidate['loc'] == 'input[placeholder="请输入订单类型名称"]'
                    and candidate['score'] > 70
                )
                for candidate in candidates
            ), candidates

            candidate_results = []
            reject_reasons = []
            ai_text_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                [{
                    'source': 'ai_accessibility',
                    'score': 40,
                    'exp': ElementExpEnum.LOCATOR.value,
                    'loc': 'get_by_text("适用部门")',
                    'sub': None,
                    'used_ai': True,
                }],
                candidate_results,
                reject_reasons,
                heal_mode=3,
                total_count=1,
                find_params={'ope_key': 'w_click'},
            )
            assert ai_text_result is None, candidate_results
            assert candidate_results[0]['reject_reason'] == 'ambiguous count=3', candidate_results

            candidate_results = []
            reject_reasons = []
            ai_text_with_sub_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                [{
                    'source': 'ai_accessibility',
                    'score': 70,
                    'exp': ElementExpEnum.LOCATOR.value,
                    'loc': 'get_by_text("适用部门")',
                    'sub': 1,
                    'used_ai': True,
                }],
                candidate_results,
                reject_reasons,
                heal_mode=3,
                total_count=1,
                find_params={'ope_key': 'w_click'},
            )
            assert ai_text_with_sub_result is None, candidate_results
            assert candidate_results[0]['reject_code'] == 'operation_mismatch', candidate_results
            assert 'requires an interactive element' in candidate_results[0]['reject_reason'], candidate_results

            candidate_results = []
            reject_reasons = []
            result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                candidates,
                candidate_results,
                reject_reasons,
                heal_mode=3,
                total_count=len(candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert result is not None, reject_reasons
            assert result['exp'] == ElementExpEnum.XPATH.value
            assert 'following::*' in result['loc']
            assert result['loc'].endswith('[2]')
            assert result['text'] == '请选择'
            assert result['metadata']['used_source'] == 'label_relative_xpath'
            assert result['metadata']['final_score'] >= 90
            assert result['metadata']['candidates'][0]['actionability_checked'] is True
            assert result['metadata']['candidate_summary']['verified'] == 1
            assert result['metadata']['candidate_summary']['by_source']['label_relative_xpath']['verified'] == 1

            await page.set_viewport_size({'width': 800, 'height': 500})
            await page.set_content(_HTML_OFFSCREEN_DEPT_SELECT)
            await page.evaluate('window.scrollTo(0, 0)')
            offscreen_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert offscreen_candidates[0]['source'] == 'label_relative_xpath', offscreen_candidates
            offscreen_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                offscreen_candidates,
                [],
                [],
                heal_mode=3,
                total_count=len(offscreen_candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert offscreen_result is not None, offscreen_candidates
            assert offscreen_result['metadata']['used_source'] == 'label_relative_xpath'

            await page.set_content(_HTML_FORM_ITEM_CONTROL_FAR_BELOW)
            far_below_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert far_below_candidates[0]['source'] == 'label_relative_xpath', far_below_candidates
            assert 'same-form-item-control' in far_below_candidates[0]['reason'], far_below_candidates
            far_below_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                far_below_candidates,
                [],
                [],
                heal_mode=3,
                total_count=len(far_below_candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert far_below_result is not None, far_below_candidates
            assert far_below_result['metadata']['used_source'] == 'label_relative_xpath'

            await page.set_content(_HTML_BYTE_FORM_UD_SELECT)
            byte_form_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert byte_form_candidates[0]['source'] == 'label_relative_xpath', byte_form_candidates
            byte_form_locator = engine.create_locator(page, byte_form_candidates[0])
            assert await byte_form_locator.count() == 1, byte_form_candidates
            byte_form_class = await byte_form_locator.first.get_attribute('class')
            assert 'ud__select__selector' in (byte_form_class or ''), byte_form_candidates
            byte_form_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                byte_form_candidates,
                [],
                [],
                heal_mode=3,
                total_count=len(byte_form_candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert byte_form_result is not None, byte_form_candidates
            assert byte_form_result['metadata']['used_source'] == 'label_relative_xpath'
            engine._ai_info_cache[(15, 0)] = (9999999999, {})
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                byte_form_locate_result = await engine.locate_async(
                    page,
                    _Element(),
                    failed_locator=None,
                    failed_expression=['get_by_role("cobox")'],
                    find_params={'ope_key': 'w_click', 'loc': 'get_by_role("cobox")', 'exp': 2, 'sub': None},
                    error=RuntimeError('fixed locator failed'),
                )
            finally:
                set_ai_config(original_config)
            assert byte_form_locate_result is not None, engine.get_last_attempt(15)
            assert byte_form_locate_result['metadata']['used_source'] == 'label_relative_xpath'
            byte_form_locate_class = await byte_form_locate_result['locator'].get_attribute('class')
            assert 'ud__select__selector' in (byte_form_locate_class or ''), byte_form_locate_result
            original_get_ai_info = engine._get_ai_info
            async def _raise_ai_info(_element_id):
                raise RuntimeError('ai info unavailable')
            engine._get_ai_info = _raise_ai_info
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                degraded_locate_result = await engine.locate_async(
                    page,
                    _Element(),
                    failed_locator=None,
                    failed_expression=['get_by_role("cobox")'],
                    find_params={'ope_key': 'w_click', 'loc': 'get_by_role("cobox")', 'exp': 2, 'sub': None},
                    error=RuntimeError('fixed locator failed'),
                )
            finally:
                set_ai_config(original_config)
                engine._get_ai_info = original_get_ai_info
            assert degraded_locate_result is not None, engine.get_last_attempt(15)
            assert degraded_locate_result['metadata']['used_source'] == 'label_relative_xpath'

            await page.set_content(_HTML_TABLE_BEFORE_MODAL)
            scoped_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert scoped_candidates[0]['source'] == 'label_relative_xpath', scoped_candidates
            assert scoped_candidates[0]['candidate_text'] == '请选择', scoped_candidates
            assert 'active scope' in scoped_candidates[0]['reason'], scoped_candidates
            scoped_locator = engine.create_locator(page, scoped_candidates[0])
            assert await scoped_locator.count() == 1, scoped_candidates
            assert await engine._read_text_async(scoped_locator.first) == '请选择'

            await page.set_content(_HTML_TABLE_HEADER_AND_FORM)
            header_form_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert header_form_candidates[0]['source'] == 'label_relative_xpath', header_form_candidates
            assert header_form_candidates[0]['candidate_text'] == '请选择', header_form_candidates
            assert header_form_candidates[0]['matched_label'] == '适用部门', header_form_candidates
            header_form_locator = engine.create_locator(page, header_form_candidates[0])
            assert await header_form_locator.count() == 1, header_form_candidates
            assert await engine._read_text_async(header_form_locator.first) == '请选择'
            assert not any(
                candidate.get('candidate_text') == '全部部门'
                for candidate in header_form_candidates[:3]
            ), header_form_candidates

            await page.set_content(_HTML_CONTRACT_TYPE_INPUTS)
            name_candidates = await engine._build_dom_proximity_candidates(
                page,
                _NameElement(),
                ['get_by_placeholder("请输入订单类型")'],
            )
            assert name_candidates[0]['source'] in ('label_relative_xpath', 'dom_stable_attr'), name_candidates
            assert name_candidates[0]['matched_label'] == '订单类型名称', name_candidates
            name_locator = engine.create_locator(page, name_candidates[0])
            assert await name_locator.count() == 1, name_candidates
            assert await name_locator.first.get_attribute('placeholder') == '请输入订单类型名称'
            name_result = await engine._verify_candidates_async(
                page,
                12,
                _NameElement(),
                name_candidates,
                [],
                [],
                heal_mode=3,
                total_count=len(name_candidates),
                find_params={'ope_key': 'w_input'},
            )
            assert name_result is not None, name_candidates
            assert name_result['metadata']['used_source'] in ('label_relative_xpath', 'dom_stable_attr')
            assert name_result['metadata']['candidates'][0]['actionability_checked'] is True

            await page.set_content(_HTML_STABLE_ATTR)
            stable_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert stable_candidates[0]['source'] == 'dom_stable_attr', stable_candidates
            assert stable_candidates[0]['exp'] == ElementExpEnum.CSS.value, stable_candidates
            assert stable_candidates[0]['loc'] == 'div[data-test-id="dept-select"]', stable_candidates
            stable_locator = engine.create_locator(page, stable_candidates[0])
            assert await stable_locator.count() == 1, stable_candidates
            assert await engine._read_text_async(stable_locator.first) == '请选择'

            await page.set_content(_HTML_LABEL_FOR)
            label_for_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert label_for_candidates[0]['source'] == 'playwright_label', label_for_candidates
            assert label_for_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, label_for_candidates
            assert label_for_candidates[0]['loc'] == "get_by_label('适用部门', exact=True)", label_for_candidates
            assert label_for_candidates[0]['reason'] == 'Playwright get_by_label 语义定位命中'
            assert any(
                candidate['source'] == 'dom_stable_attr'
                and candidate['exp'] == ElementExpEnum.CSS.value
                and candidate['loc'] == '#dept-select'
                for candidate in label_for_candidates
            ), label_for_candidates
            label_for_locator = engine.create_locator(page, label_for_candidates[0])
            assert await label_for_locator.count() == 1, label_for_candidates
            assert await engine._read_text_async(label_for_locator.first) == '请选择'

            await page.set_content(_HTML_ROLE_COMBOBOX)
            role_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert role_candidates[0]['source'] == 'playwright_role', role_candidates
            assert role_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, role_candidates
            assert role_candidates[0]['loc'] == "get_by_role('combobox', name='适用部门', exact=True)", role_candidates
            role_locator = engine.create_locator(page, role_candidates[0])
            assert await role_locator.count() == 1, role_candidates
            assert await engine._read_text_async(role_locator.first) == '请选择'

            await page.set_content(_HTML_ROLE_COMBOBOX_LOOSE)
            loose_role_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert loose_role_candidates[0]['source'] == 'playwright_role', loose_role_candidates
            assert loose_role_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, loose_role_candidates
            assert loose_role_candidates[0]['loc'] == "get_by_role('combobox', name='适用部门')", loose_role_candidates
            loose_role_locator = engine.create_locator(page, loose_role_candidates[0])
            assert await loose_role_locator.count() == 1, loose_role_candidates
            assert await engine._read_text_async(loose_role_locator.first) == '请选择'

            await page.set_content(_HTML_COMPONENT_SELECT_CONTAINER)
            component_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert component_candidates[0]['source'] == 'label_relative_xpath', component_candidates
            assert component_candidates[0]['exp'] == ElementExpEnum.XPATH.value, component_candidates
            assert 'active scope' in component_candidates[0]['reason'], component_candidates
            component_locator = engine.create_locator(page, component_candidates[0])
            assert await component_locator.count() == 1, component_candidates
            assert await component_locator.first.get_attribute('class') == 'lark-select-selection', component_candidates
            assert await engine._read_text_async(component_locator.first) == '请选择'
            component_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                component_candidates,
                [],
                [],
                heal_mode=3,
                total_count=len(component_candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert component_result is not None, component_candidates
            assert component_result['metadata']['candidates'][0]['actionability_checked'] is True

            await page.set_content(_HTML_POINTER_LABEL_SELECT)
            pointer_label_results = []
            pointer_label_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                [{
                    'source': 'ai_accessibility',
                    'score': 70,
                    'exp': ElementExpEnum.LOCATOR.value,
                    'loc': 'get_by_text("适用部门")',
                    'sub': None,
                    'used_ai': True,
                }],
                pointer_label_results,
                [],
                heal_mode=3,
                total_count=1,
                find_params={'ope_key': 'w_click'},
            )
            assert pointer_label_result is None, pointer_label_results
            assert pointer_label_results[0]['reject_reason'] == 'text click candidate rejected: text node has no interactive signal'
            pointer_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_text("适用部门")'],
            )
            assert pointer_candidates[0]['source'] == 'label_relative_xpath', pointer_candidates
            pointer_locator = engine.create_locator(page, pointer_candidates[0])
            assert await pointer_locator.count() == 1, pointer_candidates
            assert await pointer_locator.first.get_attribute('class') == 'lark-select-selection', pointer_candidates

            await page.set_content(_HTML_DISABLED_LABEL_CONTROL)
            disabled_candidates = await engine._build_dom_proximity_candidates(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            disabled_results = []
            disabled_reasons = []
            disabled_result = await engine._verify_candidates_async(
                page,
                15,
                _Element(),
                disabled_candidates,
                disabled_results,
                disabled_reasons,
                heal_mode=3,
                total_count=len(disabled_candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert disabled_result is None, disabled_results
            assert any(
                item.get('source') == 'label_relative_xpath' and
                item.get('reject_code') == 'operation_mismatch' and
                'requires an interactive element' in item.get('reject_reason', '')
                for item in disabled_results
            ), disabled_results
            assert any(
                item.get('source') in ('unique_visible_text', 'playwright_text_sub') and
                item.get('reject_code') == 'operation_mismatch'
                for item in disabled_results
            ), disabled_results

            await page.set_content(_HTML_PORTAL_OPTION)
            option_candidates = await engine._build_dom_proximity_candidates(
                page,
                _OptionElement(),
                ['get_by_role("option", name="部门")'],
            )
            assert option_candidates[0]['source'] == 'playwright_role', option_candidates
            assert option_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, option_candidates
            assert option_candidates[0]['loc'] == "get_by_role('option', name='全部部门', exact=True)", option_candidates
            assert any(
                candidate['source'] == 'portal_text_option'
                and candidate['candidate_text'] == '全部部门'
                for candidate in option_candidates
            ), option_candidates
            option_locator = engine.create_locator(page, option_candidates[0])
            assert await option_locator.count() == 1, option_candidates
            assert await engine._read_text_async(option_locator.first) == '全部部门'

            await page.set_content(_HTML_UNIQUE_VISIBLE_TEXT)
            unique_text_candidates = await engine._build_dom_proximity_candidates(
                page,
                _OptionElement(),
                ['get_by_role("option", name="部门")'],
            )
            assert unique_text_candidates[0]['source'] == 'unique_visible_text', unique_text_candidates
            assert unique_text_candidates[0]['exp'] == ElementExpEnum.XPATH.value, unique_text_candidates
            assert unique_text_candidates[0]['candidate_text'] == '全部部门', unique_text_candidates
            unique_text_locator = engine.create_locator(page, unique_text_candidates[0])
            assert await unique_text_locator.count() == 1, unique_text_candidates
            assert await engine._read_text_async(unique_text_locator.first) == '全部部门'

            await page.set_content(_HTML_POPUP_OPTION_WITH_TABLE_DUPLICATES)
            popup_option_candidates = await engine._build_dom_proximity_candidates(
                page,
                _OptionElement(),
                ['get_by_role("button", name="全部部门")'],
            )
            assert popup_option_candidates[0]['source'] in (
                'playwright_label', 'playwright_role', 'portal_text_option', 'popup_text_option'
            ), popup_option_candidates
            assert not (
                popup_option_candidates[0]['source'] == 'playwright_role' and
                popup_option_candidates[0]['loc'].startswith("get_by_role('button'")
            ), popup_option_candidates
            assert any(
                candidate['source'] in ('portal_text_option', 'popup_text_option')
                and candidate['candidate_text'] == '全部部门'
                for candidate in popup_option_candidates
            ), popup_option_candidates
            popup_option_locator = engine.create_locator(page, popup_option_candidates[0])
            assert await popup_option_locator.count() == 1, popup_option_candidates
            popup_result = await engine._verify_candidates_async(
                page,
                16,
                _OptionElement(),
                popup_option_candidates,
                [],
                [],
                heal_mode=3,
                total_count=len(popup_option_candidates),
                find_params={'ope_key': 'w_click'},
            )
            assert popup_result is not None, popup_option_candidates
            assert popup_result['metadata']['used_source'] in (
                'playwright_label', 'playwright_role', 'portal_text_option', 'popup_text_option'
            )
            assert not (
                popup_result['metadata']['used_source'] == 'playwright_role' and
                str(popup_result['metadata'].get('selected_loc') or '').startswith("get_by_role('button'")
            )

            await page.set_content(_HTML_UNIQUE_COMMON_TEXT)
            common_text_candidates = await engine._build_dom_proximity_candidates(
                page,
                _SubmitElement(),
                ['get_by_role("button", name="提交")'],
            )
            assert not any(
                candidate['source'] == 'unique_visible_text'
                for candidate in common_text_candidates
            ), common_text_candidates
        finally:
            await browser.close()


def _assert_sync_browser_candidate():
    chrome = _chrome_path()
    if not chrome:
        print('未找到系统 Chrome，跳过同步浏览器级定位引擎验证')
        return
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=chrome)
        try:
            page = browser.new_page()
            page.set_content(_HTML)
            engine = UiElementLocatorEngine(test_env=0)
            candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert candidates[0]['source'] == 'label_relative_xpath', candidates
            assert candidates[0]['exp'] == ElementExpEnum.XPATH.value, candidates
            assert 'following::*' in candidates[0]['loc'], candidates
            assert candidates[0]['loc'].endswith('[2]'), candidates
            assert candidates[0]['score'] >= 90, candidates

            locator = engine.create_locator(page, candidates[0])
            assert locator.count() >= 1, candidates
            selected = locator.first
            assert engine._is_visible_sync(selected), candidates
            assert engine._read_text_sync(selected) == '请选择'

            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                result = engine.locate_sync(
                    page,
                    _Element(),
                    failed_locator=None,
                    failed_expression=['get_by_role("cobox")'],
                    find_params={'ope_key': 'w_click'},
                )
            finally:
                set_ai_config(original_config)
            assert result is not None, engine.get_last_attempt(15)
            assert result['exp'] == ElementExpEnum.XPATH.value
            assert 'following::*' in result['loc']
            assert result['loc'].endswith('[2]')
            assert result['text'] == '请选择'
            assert result['metadata']['used_source'] == 'label_relative_xpath'
            assert result['metadata']['final_score'] >= 90
            assert result['metadata']['candidates'][0]['actionability_checked'] is True

            page.set_viewport_size({'width': 800, 'height': 500})
            page.set_content(_HTML_OFFSCREEN_DEPT_SELECT)
            page.evaluate('window.scrollTo(0, 0)')
            offscreen_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert offscreen_candidates[0]['source'] == 'label_relative_xpath', offscreen_candidates
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                offscreen_result = engine.locate_sync(
                    page,
                    _Element(),
                    failed_locator=None,
                    failed_expression=['get_by_role("cobox")'],
                    find_params={'ope_key': 'w_click'},
                )
            finally:
                set_ai_config(original_config)
            assert offscreen_result is not None, engine.get_last_attempt(15)
            assert offscreen_result['metadata']['used_source'] == 'label_relative_xpath'

            page.set_content(_HTML_FORM_ITEM_CONTROL_FAR_BELOW)
            far_below_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert far_below_candidates[0]['source'] == 'label_relative_xpath', far_below_candidates
            assert 'same-form-item-control' in far_below_candidates[0]['reason'], far_below_candidates
            far_below_locator = engine.create_locator(page, far_below_candidates[0])
            assert far_below_locator.count() == 1, far_below_candidates

            page.set_content(_HTML_BYTE_FORM_UD_SELECT)
            byte_form_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert byte_form_candidates[0]['source'] == 'label_relative_xpath', byte_form_candidates
            byte_form_locator = engine.create_locator(page, byte_form_candidates[0])
            assert byte_form_locator.count() == 1, byte_form_candidates
            byte_form_class = byte_form_locator.first.get_attribute('class')
            assert 'ud__select__selector' in (byte_form_class or ''), byte_form_candidates

            page.set_content(_HTML_TABLE_BEFORE_MODAL)
            scoped_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert scoped_candidates[0]['source'] == 'label_relative_xpath', scoped_candidates
            assert scoped_candidates[0]['candidate_text'] == '请选择', scoped_candidates
            assert 'active scope' in scoped_candidates[0]['reason'], scoped_candidates
            scoped_locator = engine.create_locator(page, scoped_candidates[0])
            assert scoped_locator.count() == 1, scoped_candidates
            assert engine._read_text_sync(scoped_locator.first) == '请选择'

            page.set_content(_HTML_TABLE_HEADER_AND_FORM)
            header_form_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert header_form_candidates[0]['source'] == 'label_relative_xpath', header_form_candidates
            assert header_form_candidates[0]['candidate_text'] == '请选择', header_form_candidates
            assert header_form_candidates[0]['matched_label'] == '适用部门', header_form_candidates
            header_form_locator = engine.create_locator(page, header_form_candidates[0])
            assert header_form_locator.count() == 1, header_form_candidates
            assert engine._read_text_sync(header_form_locator.first) == '请选择'
            assert not any(
                candidate.get('candidate_text') == '全部部门'
                for candidate in header_form_candidates[:3]
            ), header_form_candidates

            page.set_content(_HTML_CONTRACT_TYPE_INPUTS)
            name_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _NameElement(),
                ['get_by_placeholder("请输入订单类型")'],
            )
            assert name_candidates[0]['source'] in ('label_relative_xpath', 'dom_stable_attr'), name_candidates
            assert name_candidates[0]['matched_label'] == '订单类型名称', name_candidates
            name_locator = engine.create_locator(page, name_candidates[0])
            assert name_locator.count() == 1, name_candidates
            assert name_locator.first.get_attribute('placeholder') == '请输入订单类型名称'
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                name_result = engine.locate_sync(
                    page,
                    _NameElement(),
                    failed_locator=None,
                    failed_expression=['get_by_placeholder("请输入订单类型")'],
                    find_params={'ope_key': 'w_input'},
                )
            finally:
                set_ai_config(original_config)
            assert name_result is not None, engine.get_last_attempt(12)
            assert name_result['metadata']['used_source'] in ('label_relative_xpath', 'dom_stable_attr')
            assert name_result['metadata']['candidates'][0]['actionability_checked'] is True
            assert name_result['metadata']['candidate_summary']['verified'] == 1

            page.set_content(_HTML_STABLE_ATTR)
            stable_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert stable_candidates[0]['source'] == 'dom_stable_attr', stable_candidates
            assert stable_candidates[0]['exp'] == ElementExpEnum.CSS.value, stable_candidates
            assert stable_candidates[0]['loc'] == 'div[data-test-id="dept-select"]', stable_candidates
            stable_locator = engine.create_locator(page, stable_candidates[0])
            assert stable_locator.count() == 1, stable_candidates
            assert engine._read_text_sync(stable_locator.first) == '请选择'

            page.set_content(_HTML_LABEL_FOR)
            label_for_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert label_for_candidates[0]['source'] == 'playwright_label', label_for_candidates
            assert label_for_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, label_for_candidates
            assert label_for_candidates[0]['loc'] == "get_by_label('适用部门', exact=True)", label_for_candidates
            assert label_for_candidates[0]['reason'] == 'Playwright get_by_label 语义定位命中'
            assert any(
                candidate['source'] == 'dom_stable_attr'
                and candidate['exp'] == ElementExpEnum.CSS.value
                and candidate['loc'] == '#dept-select'
                for candidate in label_for_candidates
            ), label_for_candidates
            label_for_locator = engine.create_locator(page, label_for_candidates[0])
            assert label_for_locator.count() == 1, label_for_candidates
            assert engine._read_text_sync(label_for_locator.first) == '请选择'

            page.set_content(_HTML_ROLE_COMBOBOX)
            role_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert role_candidates[0]['source'] == 'playwright_role', role_candidates
            assert role_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, role_candidates
            assert role_candidates[0]['loc'] == "get_by_role('combobox', name='适用部门', exact=True)", role_candidates
            role_locator = engine.create_locator(page, role_candidates[0])
            assert role_locator.count() == 1, role_candidates
            assert engine._read_text_sync(role_locator.first) == '请选择'

            page.set_content(_HTML_ROLE_COMBOBOX_LOOSE)
            loose_role_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert loose_role_candidates[0]['source'] == 'playwright_role', loose_role_candidates
            assert loose_role_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, loose_role_candidates
            assert loose_role_candidates[0]['loc'] == "get_by_role('combobox', name='适用部门')", loose_role_candidates
            loose_role_locator = engine.create_locator(page, loose_role_candidates[0])
            assert loose_role_locator.count() == 1, loose_role_candidates
            assert engine._read_text_sync(loose_role_locator.first) == '请选择'

            page.set_content(_HTML_COMPONENT_SELECT_CONTAINER)
            component_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_role("cobox")'],
            )
            assert component_candidates[0]['source'] == 'label_relative_xpath', component_candidates
            assert component_candidates[0]['exp'] == ElementExpEnum.XPATH.value, component_candidates
            assert 'active scope' in component_candidates[0]['reason'], component_candidates
            component_locator = engine.create_locator(page, component_candidates[0])
            assert component_locator.count() == 1, component_candidates
            assert component_locator.first.get_attribute('class') == 'lark-select-selection', component_candidates
            assert engine._read_text_sync(component_locator.first) == '请选择'

            page.set_content(_HTML_POINTER_LABEL_SELECT)
            pointer_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _Element(),
                ['get_by_text("适用部门")'],
            )
            assert pointer_candidates[0]['source'] == 'label_relative_xpath', pointer_candidates
            pointer_locator = engine.create_locator(page, pointer_candidates[0])
            assert pointer_locator.count() == 1, pointer_candidates
            assert pointer_locator.first.get_attribute('class') == 'lark-select-selection', pointer_candidates
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                pointer_result = engine.locate_sync(
                    page,
                    _Element(),
                    failed_locator=None,
                    failed_expression=['get_by_text("适用部门")'],
                    find_params={'ope_key': 'w_click'},
                )
            finally:
                set_ai_config(original_config)
            assert pointer_result is not None, engine.get_last_attempt(15)
            assert pointer_result['metadata']['used_source'] == 'label_relative_xpath'

            page.set_content(_HTML_PORTAL_OPTION)
            option_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _OptionElement(),
                ['get_by_role("option", name="部门")'],
            )
            assert option_candidates[0]['source'] == 'playwright_role', option_candidates
            assert option_candidates[0]['exp'] == ElementExpEnum.LOCATOR.value, option_candidates
            assert option_candidates[0]['loc'] == "get_by_role('option', name='全部部门', exact=True)", option_candidates
            assert any(
                candidate['source'] == 'portal_text_option'
                and candidate['candidate_text'] == '全部部门'
                for candidate in option_candidates
            ), option_candidates
            option_locator = engine.create_locator(page, option_candidates[0])
            assert option_locator.count() == 1, option_candidates
            assert engine._read_text_sync(option_locator.first) == '全部部门'

            page.set_content(_HTML_UNIQUE_VISIBLE_TEXT)
            unique_text_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _OptionElement(),
                ['get_by_role("option", name="部门")'],
            )
            assert unique_text_candidates[0]['source'] == 'unique_visible_text', unique_text_candidates
            assert unique_text_candidates[0]['exp'] == ElementExpEnum.XPATH.value, unique_text_candidates
            assert unique_text_candidates[0]['candidate_text'] == '全部部门', unique_text_candidates
            unique_text_locator = engine.create_locator(page, unique_text_candidates[0])
            assert unique_text_locator.count() == 1, unique_text_candidates
            assert engine._read_text_sync(unique_text_locator.first) == '全部部门'
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                unique_text_result = engine.locate_sync(
                    page,
                    _OptionElement(),
                    failed_locator=None,
                    failed_expression=['get_by_role("option", name="部门")'],
                    find_params={'ope_key': 'w_click'},
                )
            finally:
                set_ai_config(original_config)
            assert unique_text_result is not None, engine.get_last_attempt(16)
            assert unique_text_result['metadata']['used_source'] == 'unique_visible_text'
            assert unique_text_result['metadata']['candidates'][0]['actionability_checked'] is True

            page.set_content(_HTML_POPUP_OPTION_WITH_TABLE_DUPLICATES)
            popup_option_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _OptionElement(),
                ['get_by_role("button", name="全部部门")'],
            )
            assert popup_option_candidates[0]['source'] in (
                'playwright_label', 'playwright_role', 'portal_text_option', 'popup_text_option'
            ), popup_option_candidates
            assert not (
                popup_option_candidates[0]['source'] == 'playwright_role' and
                popup_option_candidates[0]['loc'].startswith("get_by_role('button'")
            ), popup_option_candidates
            assert any(
                candidate['source'] in ('portal_text_option', 'popup_text_option')
                and candidate['candidate_text'] == '全部部门'
                for candidate in popup_option_candidates
            ), popup_option_candidates
            popup_option_locator = engine.create_locator(page, popup_option_candidates[0])
            assert popup_option_locator.count() == 1, popup_option_candidates
            original_config = get_ai_config()
            try:
                set_ai_config(AiRuntimeConfig(locator_enabled=True, locator_mode=3))
                popup_result = engine.locate_sync(
                    page,
                    _OptionElement(),
                    failed_locator=None,
                    failed_expression=['get_by_role("button", name="全部部门")'],
                    find_params={'ope_key': 'w_click'},
                )
            finally:
                set_ai_config(original_config)
            assert popup_result is not None, engine.get_last_attempt(16)
            assert popup_result['metadata']['used_source'] in (
                'playwright_label', 'playwright_role', 'portal_text_option', 'popup_text_option'
            )
            assert not (
                popup_result['metadata']['used_source'] == 'playwright_role' and
                str(popup_result['metadata'].get('selected_loc') or '').startswith("get_by_role('button'")
            )

            page.set_content(_HTML_UNIQUE_COMMON_TEXT)
            common_text_candidates = engine._build_dom_proximity_candidates_sync(
                page,
                _SubmitElement(),
                ['get_by_role("button", name="提交")'],
            )
            assert not any(
                candidate['source'] == 'unique_visible_text'
                for candidate in common_text_candidates
            ), common_text_candidates
        finally:
            browser.close()


def main():
    _assert_target_text_candidate()
    _assert_candidate_diagnostics()
    _assert_candidate_source_priority()
    _assert_trigger_context()
    _assert_latest_success_element()
    _assert_ambiguous_locator_refine_gate()
    asyncio.run(_assert_fixed_locator_actionability_gate())
    asyncio.run(_assert_failed_report_does_not_run_locator_again())
    asyncio.run(_assert_snapshot_background_concurrency_is_bounded())
    asyncio.run(_assert_browser_candidate())
    _assert_sync_browser_candidate()
    print('UI定位引擎适用部门自愈场景验证通过')


if __name__ == '__main__':
    main()
