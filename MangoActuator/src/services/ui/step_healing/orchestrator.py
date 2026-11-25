# -*- coding: utf-8 -*-
from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import re
import time
import uuid

from mangoautomation.element_healing.snapshot import DurableLocatorGenerator, SnapshotRefResolver
from mangoautomation.step_healing import (
    ConditionGroup,
    PageStepStateObserver,
    StepHealingOutcome,
    StepHealingPlanner,
    StepHealingPolicy,
    StepHealingResponseError,
    StepRepairGuard,
    StepRepairRejected,
)

from src.network import HTTP
from src.services.ui.element_healing.platform_model_client import PlatformModelClient
from src.storage.sqlite import StepHealReportOutbox
from src.tools.executor_task_context import get_executor_task_context
from src.tools.log_collector import log


class PageStepHealingOrchestrator:
    """Run a temporary, guarded workflow patch without mutating formal configuration."""

    def __init__(self, page, page_step_model, test_data):
        self.page = page
        self.model = page_step_model
        self.test_data = test_data
        self.variables = dict(test_data.get_all() or {})
        self.policy = StepHealingPolicy.model_validate(page_step_model.healing_policy or {})
        self.observer = PageStepStateObserver(
            page,
            variables=self.variables,
            elements=page_step_model.element_list,
        )
        self.planner = StepHealingPlanner(PlatformModelClient(
            '页面步骤自愈',
            max_timeout_seconds=self.policy.total_timeout_seconds,
        ))
        self.node_map = self._node_map()
        self.checkpoints = self._checkpoints()
        self.started_at = time.monotonic()
        self.rounds = 0
        self.seen_recovery_states = set()

    @property
    def enabled(self):
        return bool(
            self.model.healing_enabled
            and self.policy.mode != 'off'
            and self.page
            and self.planner.available
        )

    async def recover(
        self,
        current_element,
        *,
        trigger: str,
        error_message: str | None = None,
        execution_history: list[dict] | None = None,
    ):
        trace_id = str(uuid.uuid4())
        base = dict(
            trace_id=trace_id,
            trigger=trigger,
            source_version=self.model.config_version,
            failed_node_id=str(current_element.id) if current_element else None,
        )
        if not self.enabled:
            return StepHealingOutcome(status='disabled', **base)
        if self.rounds >= self.policy.max_recovery_rounds:
            return StepHealingOutcome(
                status='rejected', user_message='已达到本步骤自愈次数上限', **base,
            )
        remaining = self.policy.total_timeout_seconds - (time.monotonic() - self.started_at)
        if remaining <= 0:
            return StepHealingOutcome(status='failed', user_message='页面步骤自愈已超时', **base)
        self.rounds += 1
        try:
            return await asyncio.wait_for(
                self._recover(
                    current_element, error_message, execution_history or [], base,
                ),
                timeout=remaining,
            )
        except asyncio.TimeoutError:
            error = f'页面步骤自愈超过总超时{self.policy.total_timeout_seconds}秒'
            log.warning(f'页面步骤自愈未成功：trace_id={trace_id}，原因={error}')
            outcome = StepHealingOutcome(
                status='failed', error_message=error,
                user_message=error, **base,
            )
            await self._report(outcome)
            return outcome
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/step_healing/orchestrator:recover')
            log.warning(
                f'页面步骤自愈未成功：trace_id={trace_id}，'
                f'异常类型={type(error).__name__}，原因={error}',
            )
            outcome = StepHealingOutcome(
                status='failed', error_message=str(error),
                user_message=self._failure_user_message(error), **base,
            )
            await self._report(outcome)
            return outcome

    async def _recover(self, current_element, error_message, execution_history, base):
        before, snapshot = await self.observer.snapshot(self.checkpoints)
        recovery_key = (
            base['failed_node_id'],
            base['trigger'],
            before.normalized_url_path,
            before.visible_text_digest,
            before.form_state_digest,
        )
        if recovery_key in self.seen_recovery_states:
            raise StepRepairRejected('相同页面状态已经尝试过恢复，为避免循环已停止')
        self.seen_recovery_states.add(recovery_key)
        log.debug(
            f'页面步骤自愈开始：trace_id={base["trace_id"]}，'
            f'page_step_id={self.model.id}，node_id={base["failed_node_id"]}，'
            f'trigger={base["trigger"]}，matched_checkpoints={before.matched_checkpoints}',
        )
        context = {
            'id': self.model.id,
            'name': self.model.name,
            'goal': self.model.goal,
            'config_version': self.model.config_version,
            'failed_node_id': base['failed_node_id'],
            'trigger': base['trigger'],
            'failure_kind': self._failure_kind(base['trigger'], error_message),
            'failure_summary': error_message,
            'nodes': list(self.node_map.values()),
            'execution_history': execution_history,
            'matched_checkpoints': before.matched_checkpoints,
            'available_data': [
                {'name': key, 'value_available': value is not None}
                for key, value in self.variables.items()
            ],
        }
        initial_before = before
        # The DOM snapshot fallback replaces temporary ref markers on every capture.
        # Confirm checkpoint stability before planning so the model always receives
        # the latest snapshot and its refs remain usable until browser validation.
        await asyncio.sleep(.25)
        confirmation, snapshot = await self.observer.snapshot(self.checkpoints)
        stable = set(before.matched_checkpoints).intersection(confirmation.matched_checkpoints)
        before = confirmation
        plan = None
        last_error = None
        for model_call in range(self.policy.max_model_calls):
            context['matched_checkpoints'] = before.matched_checkpoints
            try:
                plan = await self.planner.plan_async(
                    context, snapshot, repair_on_error=False,
                )
                log.debug(
                    f'页面步骤自愈计划：trace_id={base["trace_id"]}，'
                    f'model_call={model_call + 1}，diagnosis_code={plan.diagnosis_code}，'
                    f'confidence={plan.confidence}，actions={[item.action for item in plan.actions]}',
                )
                if base['trigger'] == 'entry_criteria_mismatch' and any(
                    action.action not in {'insert_action', 'abort'} for action in plan.actions
                ):
                    raise StepRepairRejected('入口恢复只允许执行低风险临时动作，不能跳过、替换或重复既有节点')
                self._validate_failure_plan(plan, context['failure_kind'])
                StepRepairGuard.validate(
                    plan,
                    policy=self.policy,
                    current_node_id=base['failed_node_id'],
                    node_map=self.node_map,
                    matched_checkpoints=stable,
                    available_data=set(self.variables),
                    snapshot=snapshot,
                    trusted_text_sources=[self.model.goal],
                    allow_replaced_current_node_skip=(
                        context['failure_kind'] == 'runtime_data_dependency_missing'
                    ),
                )
                if self.policy.mode != 'suggest_only':
                    await self._validate_targets(plan, snapshot)
                self._attach_writeback_targets(plan, snapshot, current_element, base['trigger'])
                break
            except (StepHealingResponseError, StepRepairRejected) as error:
                last_error = error
                retryable = isinstance(error, StepHealingResponseError) or any(
                    marker in str(error) for marker in ('目标', '引用', 'ref')
                )
                if not retryable or model_call + 1 >= self.policy.max_model_calls:
                    raise
                if isinstance(error, StepHealingResponseError):
                    # Give the next bounded model call the concrete protocol error;
                    # repeating the same prompt otherwise tends to reproduce the
                    # same incomplete JSON object.
                    context['previous_response_error'] = str(error)
                log.debug(
                    f'页面步骤自愈重新采集页面并规划：trace_id={base["trace_id"]}，原因={error}',
                )
                previous = before
                await asyncio.sleep(.25)
                before, snapshot = await self.observer.snapshot(self.checkpoints)
                stable = set(previous.matched_checkpoints).intersection(before.matched_checkpoints)
        if plan is None:
            raise last_error or StepRepairRejected('AI没有返回可执行恢复计划')
        if self.policy.mode == 'suggest_only':
            outcome = StepHealingOutcome(
                status='suggested', before_state=initial_before.model_dump(mode='json'),
                proposed_plan=plan.model_dump(mode='json'), confidence=plan.confidence,
                user_message=plan.user_message, **base,
            )
            await self._report(outcome)
            return outcome

        outcome = await self._execute(
            plan, snapshot, current_element, base,
            failure_kind=context['failure_kind'],
        )
        after, _ = await self.observer.snapshot(self.checkpoints)
        outcome.before_state = initial_before.model_dump(mode='json')
        outcome.after_state = after.model_dump(mode='json')
        outcome.proposed_plan = plan.model_dump(mode='json')
        outcome.executed_plan = plan.model_dump(mode='json') if outcome.status == 'recovered' else {}
        outcome.confidence = plan.confidence
        await self._report(outcome)
        return outcome

    @staticmethod
    def _failure_kind(trigger: str, error_message: str | None) -> str:
        if trigger != 'node_failed':
            return trigger
        normalized = ''.join(str(error_message or '').split()).lower()
        if '无法获取缓存的key【' in normalized or 'missingcachekey' in normalized:
            return 'runtime_data_dependency_missing'
        return 'node_execution_failed'

    @staticmethod
    def _validate_failure_plan(plan, failure_kind: str) -> None:
        if failure_kind != 'runtime_data_dependency_missing':
            return
        if any(action.action == 'retry_node' for action in plan.actions):
            raise StepRepairRejected(
                '原节点缺少必要运行数据，重试不会恢复；步骤自愈只能执行安全替代动作',
            )
        if not any(action.action == 'insert_action' for action in plan.actions):
            raise StepRepairRejected('原节点缺少必要运行数据，恢复计划必须提供安全替代动作')
        if not plan.actions or plan.actions[-1].action != 'skip_node':
            raise StepRepairRejected('替代动作完成后必须移除依赖缺失的旧节点')

    @staticmethod
    def _failure_user_message(error: Exception) -> str:
        message = str(error or '').strip()
        error_name = type(error).__name__.lower()
        normalized = message.lower()
        if 'timeout' in error_name or 'timed out' in normalized or '超时' in message:
            return '步骤AI请求超时，本次未执行修复，请稍后重试'
        if '429' in normalized or '余额不足' in message or '资源包' in message:
            return '步骤AI服务暂时不可用，本次未执行修复，请检查AI服务额度'
        if isinstance(error, StepRepairRejected):
            return f'步骤自愈未通过安全校验：{message}'
        if isinstance(error, StepHealingResponseError):
            return f'步骤AI返回的修复计划无法执行：{message}'
        return '步骤自愈执行异常，本次未执行修复，请查看自愈记录'

    async def _validate_targets(self, plan, snapshot):
        """Validate all snapshot refs before the first browser mutation."""
        for action in plan.actions:
            if not action.target_ref:
                continue
            locator = self._locator(snapshot, action.target_ref)
            if await locator.count() != 1 or not await locator.is_visible():
                raise StepRepairRejected('修复动作的目标引用已失效、不唯一或不可见')

    def _attach_writeback_targets(self, plan, snapshot, current_element, trigger):
        """Turn one-run snapshot refs into server-persistable locator metadata."""
        for action in plan.actions:
            if action.action not in {'insert_action', 'replace_target'} or not action.target_ref:
                continue
            node = snapshot.node_by_ref(action.target_ref)
            if node is None:
                continue
            action.target_name = self._writeback_target_name(action, node, current_element)
            action.target_role = node.role or None
            action.target_tag = node.tag or None
            locator_priority = {
                'test_id': 0, 'stable_id': 1, 'label': 2, 'name_attribute': 3,
                'placeholder': 4, 'role_name': 5, 'title': 6, 'alt_text': 7,
                'text': 8, 'xpath_text': 9, 'role': 10, 'tag': 11,
            }
            durable_locators = DurableLocatorGenerator.build_all(
                node, snapshot.nodes, limit=5,
            )
            durable_locators.sort(
                key=lambda item: locator_priority.get(item.strategy, 99),
            )
            action.durable_locators = [
                item.model_dump(mode='json') for item in durable_locators[:3]
            ]
            if action.action != 'insert_action':
                continue
            if trigger == 'entry_criteria_mismatch':
                first = next(iter(self.model.element_list or []), None)
                action.node_id = str(getattr(first, 'id', '') or '') or None
                action.placement = 'before'
            elif trigger == 'success_criteria_mismatch':
                anchor = current_element or ((self.model.element_list or [None])[-1])
                action.node_id = str(getattr(anchor, 'id', '') or '') or None
                action.placement = 'after'
            else:
                action.node_id = str(getattr(current_element, 'id', '') or '') or action.node_id
                action.placement = 'before'

    @staticmethod
    def _writeback_target_name(action, node, current_element) -> str:
        intent = action.operation_intent or ''
        if intent in {'edit', 'select'}:
            explicit_label = str(node.label or '').strip()
            if explicit_label:
                return explicit_label[:256]
            anchor_name = str(getattr(current_element, 'name', '') or '').strip()
            suffix = '输入框' if intent == 'edit' else '下拉框'
            if anchor_name:
                return (
                    anchor_name if anchor_name.endswith(suffix) else f'{anchor_name}{suffix}'
                )[:256]
            return suffix
        return str(
            node.name or node.label or node.text or node.title
            or action.reason or 'AI修复元素'
        ).strip()[:256]

    async def _execute(self, plan, snapshot, current_element, base, *, failure_kind=None):
        outcome = StepHealingOutcome(
            status='recovered', user_message=plan.user_message, **base,
        )
        for action in plan.actions:
            log.debug(
                f'页面步骤自愈动作：trace_id={base["trace_id"]}，action={action.action}，'
                f'node_id={action.node_id}，target_ref={action.target_ref}',
            )
            if action.action == 'abort':
                raise StepRepairRejected(action.reason)
            if action.action == 'retry_node':
                outcome.retry_current_node = True
                continue
            if action.action == 'skip_node':
                outcome.skip_current_node = True
                continue
            if action.action == 'jump_to_node':
                outcome.next_node_id = action.node_id
                continue
            locator = self._locator(snapshot, action.target_ref)
            if await locator.count() != 1 or not await locator.is_visible():
                raise StepRepairRejected('修复动作的目标在浏览器中不唯一或不可见')
            intent = action.operation_intent or self._operation_intent(current_element)
            await self._operate(
                locator, intent, action.value_binding, action.value_literal,
            )
            if action.expected_condition.conditions:
                if not await self.observer.matches(action.expected_condition):
                    raise StepRepairRejected('修复动作执行后未达到预期页面状态')
            if action.action == 'insert_action':
                if failure_kind == 'runtime_data_dependency_missing':
                    # The original node cannot recover without its missing cache value.
                    # A validated replacement action completes that logical node instead.
                    outcome.skip_current_node = True
                else:
                    outcome.retry_current_node = True
        return outcome

    def _locator(self, snapshot, target_ref):
        node = snapshot.node_by_ref(target_ref)
        if node is None:
            raise StepRepairRejected('修复引用的页面元素已失效')
        frames = list(getattr(self.page, 'frames', []) or [])
        scope = frames[node.frame_index] if node.frame_index < len(frames) else self.page
        return scope.locator(SnapshotRefResolver.selector(
            snapshot.snapshot_id, target_ref, snapshot.ref_engine,
        ))

    async def _operate(self, locator, intent, binding, literal=None):
        value = (
            self.variables.get(self._binding_name(binding))
            if binding
            else literal
        )
        if intent == 'edit':
            if binding is None and literal is None:
                raise StepRepairRejected('输入恢复动作没有可用的数据引用')
            if not await locator.is_editable():
                editable = locator.locator('[contenteditable="true"],input,textarea').first
                if await editable.count() < 1:
                    raise StepRepairRejected('修复目标不可输入')
                locator = editable
            await locator.fill(str(value if value is not None else ''))
            return
        if intent == 'select':
            tag = await locator.evaluate('(el) => el.tagName.toLowerCase()')
            if tag == 'select' and value is not None:
                await locator.select_option(str(value))
            else:
                await locator.click()
            return
        await locator.click()

    async def _report(self, outcome):
        task_id, _ = get_executor_task_context()
        payload = {
            'schema_version': 1,
            'page_step_id': self.model.id,
            'executor_task_id': task_id,
            'trace_id': outcome.trace_id,
            'dispatch_id': getattr(self.model, 'execution_id', None),
            'test_env': self.model.test_env,
            'auto_writeback_requested': bool(self.policy.auto_writeback),
            'writeback_status': 'pending_review' if outcome.status in {'recovered', 'suggested'} else 'none',
            **outcome.model_dump(mode='json', exclude={'next_node_id', 'retry_current_node', 'skip_current_node'}),
        }
        queue_id = None
        try:
            queue_id = StepHealReportOutbox.upsert(outcome.trace_id, payload)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/step_healing/orchestrator:_report')
            log.error(f'页面步骤自愈记录写入本地重试队列失败：trace_id={outcome.trace_id}，原因={error}')
        try:
            await HTTP.ui_page_step.save_heal_report(payload)
            if queue_id is not None:
                StepHealReportOutbox.delete(queue_id)
            log.debug(
                f'页面步骤自愈记录已上报：trace_id={outcome.trace_id}，status={outcome.status}',
            )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/step_healing/orchestrator:_report')
            if queue_id is not None:
                StepHealReportOutbox.mark_failed(queue_id, 0, error)
            log.warning(
                f'页面步骤自愈记录保存失败，已进入持久化重试队列：'
                f'trace_id={outcome.trace_id}，原因={error}',
            )

    def _node_map(self):
        result = {}
        for index, element in enumerate(self.model.element_list or []):
            node_id = str(element.id)
            result[node_id] = {
                'node_id': node_id,
                'detail_id': element.id,
                'type': getattr(getattr(element, 'type', None), 'value', getattr(element, 'type', None)),
                'name': element.name or '',
                'operation_key': element.ope_key,
                'operation_intent': self._operation_intent(element),
                'risk_level': self._risk_level(element),
                'precondition': element.precondition or None,
                'postcondition': element.postcondition or None,
                'precondition_keys': [f'node:{node_id}:pre'],
                'later_checkpoints': [
                    f'node:{other.id}:post' for other in (self.model.element_list or [])[index + 1:]
                ] + ['success'],
            }
        return result

    def _checkpoints(self):
        values = {'entry': self.model.entry_criteria, 'success': self.model.success_criteria}
        for element in self.model.element_list or []:
            values[f'node:{element.id}:pre'] = element.precondition
            values[f'node:{element.id}:post'] = element.postcondition
        return {
            key: ConditionGroup.model_validate(value)
            for key, value in values.items() if value and value.get('conditions')
        }

    @staticmethod
    def _binding_name(value):
        match = re.fullmatch(r'\$\{\{\s*([\w.-]+)\s*}}', str(value or ''))
        return match.group(1) if match else str(value or '')

    @staticmethod
    def _operation_intent(element):
        key = str(getattr(element, 'ope_key', '') or '').lower()
        if 'input' in key or 'fill' in key:
            return 'edit'
        if 'select' in key or 'check' in key:
            return 'select'
        if 'goto' in key or 'url' in key:
            return 'navigate'
        return 'activate'

    @staticmethod
    def _risk_level(element):
        text = f'{getattr(element, "name", "")} {getattr(element, "ope_key", "")}'.lower()
        if any(value in text for value in ('delete', '删除', 'publish', '发布', 'submit', '提交', 'approve', '审批', 'pay', '支付')):
            return 'high'
        element_type = getattr(getattr(element, 'type', -1), 'value', getattr(element, 'type', -1))
        if int(element_type) in {1, 2, 5}:
            return 'medium'
        return 'low'
