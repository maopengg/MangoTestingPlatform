"""Mango Mock UI 靶场的稳定离线测试夹具。

页面结构对应 Mango Mock 靶场，地址使用保留域名。这里仅保存测试需要的
稳定定位契约，单元测试不访问外部网络。
"""

LAB_URL = "http://mock.example.com:8003/#components"
LAB_PAGE_NAME = "Mango Mock UI 自动化"

BUTTON_ELEMENTS = {
    "ui_tab": {
        "name": "UI 自动化页签",
        "test_id": "nav-components",
        "locator": 'get_by_test_id("nav-components")',
        "operation": "w_click",
    },
    "single_click": {
        "name": "单击",
        "test_id": "single-click-target",
        "locator": 'get_by_test_id("single-click-target")',
        "operation": "w_click",
    },
    "show_delayed": {
        "name": "2 秒后显示元素",
        "test_id": "show-delayed-element",
        "locator": 'get_by_test_id("show-delayed-element")',
        "operation": "w_click",
    },
    "capture_healing_baseline": {
        "name": "记录基线",
        "test_id": "capture-healing-baseline",
        "locator": 'get_by_test_id("capture-healing-baseline")',
        "operation": "w_click",
    },
    "apply_healing_mutation": {
        "name": "应用变化",
        "test_id": "apply-healing-mutation",
        "locator": 'get_by_test_id("apply-healing-mutation")',
        "operation": "w_click",
    },
    "restore_healing_baseline": {
        "name": "恢复 V1",
        "test_id": "restore-healing-baseline",
        "locator": 'get_by_test_id("restore-healing-baseline")',
        "operation": "w_click",
    },
}

FIND_TARGETS = {
    "delayed_element": {
        "name": "延迟元素",
        "test_id": "delayed-element",
        "locator": 'get_by_test_id("delayed-element")',
        "expected_text": "延迟元素已出现",
    },
    "healing_result": {
        "name": "自愈操作结果",
        "test_id": "healing-interaction-result",
        "locator": 'get_by_test_id("healing-interaction-result")',
        "expected_text": "操作成功",
    },
}

HEALING_TARGET = {
    "name": "提交审批",
    "baseline_test_id": "healing-submit-v1",
    "baseline_locator": 'get_by_test_id("healing-submit-v1")',
    "current_test_id": "healing-submit-v2",
    "current_locator": 'get_by_test_id("healing-submit-v2")',
    "semantic_name": "提交审批",
}

HEALING_SCENARIOS = {
    "attribute_drift": {
        "candidate_count": 1,
        "verified": True,
        "auto_apply_eligible": True,
        "expected": "auto_apply",
    },
    "relocated": {
        "candidate_count": 1,
        "verified": True,
        "auto_apply_eligible": True,
        "expected": "auto_apply",
    },
    "ambiguous": {
        "candidate_count": 2,
        "verified": True,
        "auto_apply_eligible": False,
        "expected": "reject",
    },
    "incompatible": {
        "candidate_count": 1,
        "verified": True,
        "operation_compatible": False,
        "auto_apply_eligible": False,
        "expected": "reject",
    },
    "missing": {
        "candidate_count": 0,
        "verified": True,
        "auto_apply_eligible": False,
        "expected": "reject",
    },
}

PAGE_STEP_SCENARIO = {
    "name": "Mango Mock 按钮与自愈调试",
    "url": LAB_URL,
    "steps": [
        "ui_tab",
        "single_click",
        "capture_healing_baseline",
        "apply_healing_mutation",
    ],
}

CASE_SCENARIO = {
    "name": "Mango Mock UI 执行与直播",
    "url": LAB_URL,
    "page_steps": [PAGE_STEP_SCENARIO["name"]],
}

LIVE_CONTROL_EVENTS = {
    "element_identification": "pick_element",
    "locator_check": "check_locator",
    "page_tabs": "list_pages",
}
