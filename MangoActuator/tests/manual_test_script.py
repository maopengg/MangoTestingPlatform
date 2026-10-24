# -*- coding: utf-8 -*-
"""Run a UI case JSON locally for locator-healing regression checks.

Usage:
    .venv/bin/python tests/manual_test_script.py
    .venv/bin/python tests/manual_test_script.py /path/to/case.json
"""

import argparse
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
import json
import os
import sys
from pathlib import Path
from types import MethodType
from unittest.mock import AsyncMock, patch

from mangotools.mangos import Mango
from mangoautomation.element_healing.agent.web.response_schema import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mangoautomation.models import CaseModel
from src.network import HTTP, socket_conn
from src.services.runtime_config import AiRuntimeConfig, get_ai_config, set_ai_config
from src.services.ui.case_flow import CaseFlow
from src.services.ui.element_healing.platform_memory_provider import PlatformMemoryProvider
from src.services.ui.element_healing.platform_model_client import PlatformModelClient
from src.settings import settings
from src.tools.log_collector import log
from src.tools.send_global_msg import global_consumer_news
from src.tools.set_config import SetConfig


DEFAULT_CASE_JSON = Path(__file__).with_name('test.json')
SCENARIOS = (
    'raw',
    'fixed_primary',
    'fixed_backup',
    'zero_match',
    'applied_record',
    'baseline_latest',
    'baseline_history',
    'dom_heal',
    'agent_heal',
    'agent_real',
    'auto_apply',
    'malformed_locator',
    'ambiguous_match',
    'wrong_target',
    'assertion_zero_match',
)
FINAL_CASE_RESULTS = []
RUNTIME_RESULTS = []
SNAPSHOT_PAYLOADS = []
HEAL_RECORD_PAYLOADS = []


class DemoParent:
    def __init__(self):
        self.loop = Mango.t()

    def handle_notification(self, value):
        print(value.msg)


async def _print_socket_send(self, msg="", code=200, is_notice=0, func_name=None, func_args=None, user=None, **kwargs):
    payload = func_args.model_dump(mode="json") if hasattr(func_args, "model_dump") else func_args
    status = payload.get("status") if isinstance(payload, dict) else None
    error_message = payload.get("error_message") if isinstance(payload, dict) else None
    print(
        "[demo socket send]",
        json.dumps(
            {
                "code": code,
                "msg": msg,
                "func_name": func_name,
                "user": user,
                "status": status,
                "error_message": error_message,
            },
            ensure_ascii=False,
        ),
    )
    if func_name == 'u_test_case':
        FINAL_CASE_RESULTS.append({'status': status, 'code': code, 'msg': msg})
    return {"code": code, "msg": msg}


def load_case_payload(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("func_args"), dict):
        return data["func_args"]
    return data


def apply_scenario(case_payload: dict, scenario: str) -> dict:
    payload = deepcopy(case_payload)
    if scenario == 'raw':
        return payload
    details = {
        item['id']: item
        for step in payload.get('steps') or []
        for item in step.get('element_list') or []
    }
    input_element = details[123]
    result_element = details[122]
    correct_input = {
        'exp': 2,
        'loc': 'get_by_role("textbox", name="键盘输入测试")',
        'sub': None,
        'is_iframe': 0,
        'prompt': '按键输入框',
    }
    if scenario == 'fixed_primary':
        input_element['elements'] = [correct_input]
    elif scenario == 'fixed_backup':
        input_element['elements'] = [{
            **correct_input,
            'loc': 'get_by_role("textbox", name="不存在的输入框", exact=True)',
        }, correct_input]
    elif scenario in {
        'zero_match', 'applied_record', 'baseline_latest', 'baseline_history',
        'dom_heal', 'agent_heal', 'agent_real', 'auto_apply',
    }:
        input_element['elements'] = [{
            **correct_input,
            'loc': 'get_by_role("textbox", name="不存在的输入框", exact=True)',
            'prompt': (
                '键盘输入测试'
                if scenario in {'dom_heal', 'agent_heal', 'agent_real', 'auto_apply'}
                else correct_input['prompt']
            ),
        }]
    elif scenario == 'malformed_locator':
        input_element['elements'] = [{**correct_input, 'loc': '错误的定位表达式'}]
    elif scenario == 'ambiguous_match':
        input_element['elements'] = [{**correct_input, 'loc': 'locator("button")'}]
    elif scenario == 'wrong_target':
        input_element['elements'] = [{
            **correct_input,
            'loc': 'get_by_role("heading", name="键盘操作测试")',
        }]
    elif scenario == 'assertion_zero_match':
        input_element['elements'] = [correct_input]
        result_element['elements'] = [{
            **result_element['elements'][0],
            'loc': '//div[@id="missingKeyCapture"]',
        }]
    else:
        raise ValueError(f'不支持的测试场景：{scenario}')
    payload['name'] = f"{payload.get('name')} [{scenario}]"
    return payload


def _scenario_memory(data: dict, scenario: str) -> dict:
    value = deepcopy(data or {})
    snapshots = value.get('snapshots') or []
    valid_snapshot = next(
        (item for item in snapshots if '键盘输入测试' in str(item.get('loc') or '')),
        None,
    )
    if scenario == 'baseline_latest':
        return {
            'latest_snapshot': valid_snapshot or value.get('latest_snapshot'),
            'snapshots': [],
            'heal_records': [],
        }
    if scenario == 'baseline_history':
        history = [valid_snapshot] if valid_snapshot else snapshots[-1:]
        return {'latest_snapshot': None, 'snapshots': history, 'heal_records': []}
    if scenario in {'dom_heal', 'agent_heal', 'agent_real', 'auto_apply'}:
        return {}
    return value


async def _strict_schema_agent_response(self, messages, **kwargs):
    target_ref = None
    for item in messages:
        try:
            payload = json.loads(item.get('content') or '{}')
        except (TypeError, json.JSONDecodeError):
            continue
        nodes = ((payload.get('accessibility_snapshot') or {}).get('nodes') or [])
        target = next((
            node for node in nodes
            if node.get('role') == 'textbox' and
            '键盘输入测试' in str(node.get('name') or node.get('placeholder') or '')
        ), None)
        if target:
            target_ref = target.get('ref')
            break
    if not target_ref:
        raise RuntimeError('严格 Schema 假模型未在 Accessibility Snapshot 中找到目标 ref')
    return json.dumps({
        'schema_version': SCHEMA_VERSION,
        'candidates': [{
            'source': 'ai_accessibility',
            'target_ref': target_ref,
            'reason': 'exact textbox from current accessibility snapshot',
            'confidence': 95,
        }],
    })


def _expected_sources(scenario: str) -> set[str] | None:
    historical = {'applied_heal_record', 'latest_snapshot_locator', 'baseline_semantic'}
    return {
        'zero_match': historical,
        'applied_record': {'applied_heal_record'},
        'baseline_latest': {'latest_snapshot_locator', 'baseline_semantic'},
        'baseline_history': {'history_snapshot_locator', 'baseline_semantic'},
        'dom_heal': {
            'dom_proximity', 'playwright_label', 'playwright_role', 'playwright_text_sub',
            'unique_visible_text', 'portal_text_option', 'popup_text_option',
        },
        'agent_heal': {'ai_accessibility'},
        'agent_real': {'ai_accessibility'},
        'auto_apply': {
            'dom_proximity', 'playwright_label', 'playwright_role', 'playwright_text_sub',
        },
        'malformed_locator': historical,
        'ambiguous_match': historical,
        'wrong_target': historical,
        'assertion_zero_match': historical,
    }.get(scenario)


def _target_runtime_result(scenario: str) -> dict | None:
    target_id = 109 if scenario == 'assertion_zero_match' else 108
    return next(
        (item for item in reversed(RUNTIME_RESULTS) if item.get('element') == target_id),
        None,
    )


def _assert_scenario_result(scenario: str):
    if scenario == 'raw':
        print('[demo] 原始 UI Case 执行通过')
        return
    runtime = _target_runtime_result(scenario)
    if runtime is None:
        raise RuntimeError('未捕获目标元素 108 的运行结果')
    if runtime.get('status') != 1:
        raise RuntimeError(f'目标元素执行未通过：{runtime.get("error_message")}')
    locator_engine = runtime.get('locator_engine') or {}
    expected = _expected_sources(scenario)
    if expected and locator_engine.get('used_source') not in expected:
        raise RuntimeError(
            f'场景 {scenario} 修复来源不符合预期：'
            f'{locator_engine.get("used_source")} not in {sorted(expected)}'
        )
    if expected and not locator_engine.get('temporary_heal_used'):
        raise RuntimeError(f'场景 {scenario} 未标记为临时自愈')
    if scenario == 'auto_apply' and not any(
        item.get('auto_apply') for item in HEAL_RECORD_PAYLOADS
    ):
        raise RuntimeError('auto_apply 场景未提交自动写回修复记录')
    print(
        '[demo healing summary]',
        json.dumps({
            'scenario': scenario,
            'used_source': locator_engine.get('used_source') or 'fixed_locator',
            'used_ai': locator_engine.get('used_ai', False),
            'temporary_heal_used': locator_engine.get('temporary_heal_used', False),
            'final_score': locator_engine.get('final_score'),
            'candidate_count': locator_engine.get('candidate_count', 0),
            'heal_record_requests': len(HEAL_RECORD_PAYLOADS),
            'snapshot_requests': len(SNAPSHOT_PAYLOADS),
        }, ensure_ascii=False),
    )


def _install_http_capture():
    original_runtime = HTTP.ui_element.save_runtime_result
    original_snapshot = HTTP.ui_element.save_snapshot
    original_heal_record = HTTP.ui_element.save_heal_record

    async def save_runtime_result(self, data):
        RUNTIME_RESULTS.append(deepcopy(data))
        return await original_runtime(data)

    async def save_snapshot(self, data):
        SNAPSHOT_PAYLOADS.append(deepcopy(data))
        return await original_snapshot(data)

    async def save_heal_record(self, data):
        HEAL_RECORD_PAYLOADS.append(deepcopy(data))
        return await original_heal_record(data)

    HTTP.ui_element.save_runtime_result = MethodType(save_runtime_result, HTTP.ui_element)
    HTTP.ui_element.save_snapshot = MethodType(save_snapshot, HTTP.ui_element)
    HTTP.ui_element.save_heal_record = MethodType(save_heal_record, HTTP.ui_element)


def enable_local_ai_locator_defaults():
    """Enable locator healing without requiring a live server config refresh."""
    set_ai_config(
        AiRuntimeConfig(
            locator_enabled=True,
            locator_mode=3,
            provider_type="openai_compatible",
            api_key=None,
            base_url=None,
            model=None,
            timeout=60,
        )
    )


async def prepare_platform(host: str, username: str, password: str, auth_config_id: int | None) -> dict | None:
    SetConfig.set_host(host)
    SetConfig.set_username(username)
    SetConfig.set_password(password)
    response = await HTTP.system.login(username, password)
    if response.code != 200:
        raise RuntimeError(f'测试平台登录失败：{response.msg}')
    HTTP.refresh()
    await HTTP.system.refresh_runtime_config()
    if auth_config_id is None:
        return None
    result = await HTTP.system.client.get(
        'ui/auth/config/cache',
        params={'id': auth_config_id},
        headers=HTTP.system._headers(),
    )
    if result.get('code') != 200:
        raise RuntimeError(f'获取UI授权缓存失败：{result.get("msg")}')
    data = result.get('data') or {}
    cache_data = data.get('cache_data') or {}
    if not cache_data:
        raise RuntimeError(f'UI授权配置 {auth_config_id} 没有可用缓存')
    print(
        f'[demo] auth_config={auth_config_id}, expires_at={data.get("expires_at")}, '
        f'cookies={len(cache_data.get("cookies") or [])}'
    )
    return cache_data


async def run_case(case_json: Path, host: str, username: str, password: str,
                   auth_config_id: int | None, scenario: str):
    settings.IS_DEBUG = True
    settings.IS_OPEN = False
    log.set_debug(True)
    enable_local_ai_locator_defaults()
    SetConfig.set_web_parallel(1)

    socket_conn.async_send = MethodType(_print_socket_send, socket_conn)

    asyncio.create_task(global_consumer_news())

    FINAL_CASE_RESULTS.clear()
    case_payload = apply_scenario(load_case_payload(case_json), scenario)
    current_auth_cache = await prepare_platform(host, username, password, auth_config_id)
    set_ai_config(replace(get_ai_config(), locator_mode=3 if scenario == 'auto_apply' else 2))
    _install_http_capture()
    if current_auth_cache:
        case_payload['ui_auth_cache'] = current_auth_cache
    case_model = CaseModel(**case_payload)
    CaseFlow.parent = DemoParent()
    CaseFlow.reset_web_runtime()

    print(
        f"[demo] case={case_model.name}, scenario={scenario}, "
        f"steps={len(case_model.steps)}, json={case_json}"
    )
    original_load_async = PlatformMemoryProvider.load_async

    async def load_scenario_memory(provider, element_id, test_env=None):
        value = await original_load_async(provider, element_id, test_env)
        if element_id != 108:
            return value
        return _scenario_memory(value, scenario)

    with ExitStack() as stack:
        if scenario in {
            'baseline_latest', 'baseline_history', 'dom_heal', 'agent_heal', 'agent_real',
            'auto_apply',
        }:
            stack.enter_context(patch.object(
                PlatformMemoryProvider, 'load_async', new=load_scenario_memory,
            ))
        if scenario in {'agent_heal', 'agent_real'}:
            from mangoautomation.element_healing.candidates import CandidateRegistry
            from mangoautomation.element_healing.policy import AgentCircuitBreaker
            AgentCircuitBreaker.reset()
            stack.enter_context(patch.object(
                CandidateRegistry, 'current_page_async', new=AsyncMock(return_value=[]),
            ))
        if scenario == 'agent_heal':
            stack.enter_context(patch.object(
                PlatformModelClient, 'available', new=property(lambda self: True),
            ))
            stack.enter_context(patch.object(
                PlatformModelClient, 'complete_async', new=_strict_schema_agent_response,
            ))
        await CaseFlow.execute_task(0, case_model)
    if not FINAL_CASE_RESULTS:
        raise RuntimeError('未收到 UI case 最终执行结果')
    if FINAL_CASE_RESULTS[-1]['status'] != 1:
        raise RuntimeError(f'UI case 执行未通过：{FINAL_CASE_RESULTS[-1]}')
    _assert_scenario_result(scenario)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case_json", nargs="?", default=str(DEFAULT_CASE_JSON))
    parser.add_argument(
        '--host',
        default=os.getenv('MANGO_SERVER_HOST') or SetConfig.get_host() or 'http://127.0.0.1:8000',
    )
    parser.add_argument(
        '--username',
        default=os.getenv('MANGO_EXECUTOR_USERNAME') or SetConfig.get_username() or 'maopeng',
    )
    parser.add_argument(
        '--password',
        default=os.getenv('MANGO_EXECUTOR_PASSWORD') or SetConfig.get_password() or '123456',
    )
    parser.add_argument('--scenario', choices=SCENARIOS, default='raw')
    auth_config_id = os.getenv('UI_AUTH_CONFIG_ID')
    parser.add_argument(
        '--auth-config-id',
        type=int,
        default=int(auth_config_id) if auth_config_id else None,
        help='可选的 UI 授权配置 ID；未传时直接使用 case JSON 中的授权数据',
    )
    args = parser.parse_args()
    case_json = Path(args.case_json).expanduser().resolve()
    if not case_json.exists():
        raise FileNotFoundError(case_json)
    asyncio.run(run_case(
        case_json,
        args.host,
        args.username,
        args.password,
        args.auth_config_id,
        args.scenario,
    ))


if __name__ == "__main__":
    main()
