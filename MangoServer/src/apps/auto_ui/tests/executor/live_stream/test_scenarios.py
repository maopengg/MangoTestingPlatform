import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import time
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from src.apps.auto_ui.enums.live_stream import LiveStreamExecutionType
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.live_stream.session_service import LiveStreamSessionService
from src.apps.auto_ui.services.live_stream.workspace_service import (
    LiveWorkspaceRecord,
    LiveWorkspaceService,
)
from src.processes.realtime.live_stream.protocol import (
    ALLOWED_CONTROL_TYPES,
    LiveStreamControlEventValidator,
)
from src.processes.realtime.live_stream.registry import LiveStreamRegistry


class FrontendWorkspaceReconnectContractTest(SimpleTestCase):
    @staticmethod
    def _component_source(name: str) -> str:
        repository_root = Path(__file__).resolve().parents[7]
        return (
                repository_root
                / "mango-console"
                / "src"
                / "components"
                / "business"
                / name
        ).read_text(encoding="utf-8")

    @staticmethod
    def _view_source(relative_path: str) -> str:
        repository_root = Path(__file__).resolve().parents[7]
        return (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / relative_path
        ).read_text(encoding="utf-8")

    def test_step_cache_panel_only_displays_runtime_cache(self):
        repository_root = Path(__file__).resolve().parents[7]
        case_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "case"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        step_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")

        self.assertNotIn(':configured-cache-data="configuredCaseCacheData"', case_source)
        self.assertNotIn("configuredCacheData?: Record<string, unknown>", step_source)
        self.assertNotIn("normalizeRuntimeObject(props.configuredCacheData)", step_source)
        self.assertIn("normalizeRuntimeObject(data.result_data?.cache_data)", step_source)
        self.assertNotIn("...normalizeRuntimeObject(data.selectResultData?.cache_data)", step_source)
        self.assertIn("步骤执行完成后的运行时缓存", step_source)

    def test_all_ui_live_entry_buttons_have_shared_delayed_loading_guard(self):
        repository_root = Path(__file__).resolve().parents[7]
        console_root = repository_root / "mango-console" / "src"
        page_sources = {
            "element": (
                    console_root / "views" / "uitest" / "page" / "elements" / "index.vue"
            ).read_text(encoding="utf-8"),
            "step": (
                    console_root
                    / "views"
                    / "uitest"
                    / "page-steps"
                    / "details"
                    / "index.vue"
            ).read_text(encoding="utf-8"),
            "case": (
                    console_root / "views" / "uitest" / "case" / "details" / "index.vue"
            ).read_text(encoding="utf-8"),
        }

        self.assertIn(':loading="liveWorkbenchOpening"', page_sources["element"])
        self.assertIn("useUiLiveWorkbench", page_sources["element"])
        self.assertIn(':loading="liveWorkbenchOpening"', page_sources["step"])
        self.assertIn("useUiLiveWorkbench", page_sources["step"])
        self.assertIn(':loading="caseLiveOpening"', page_sources["case"])
        self.assertIn("if (caseLiveOpening.value) return", page_sources["case"])

        live_workbench_hook = (
                console_root / "hooks" / "use-ui-live-workbench.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("if (opening.value || !(await canOpen())) return false", live_workbench_hook)
        self.assertIn("waitForMinimumLoading(startedAt)", live_workbench_hook)
        self.assertIn("waitForMinimumLoading(startedAt)", page_sources["case"])

        loading_source = (console_root / "utils" / "minimum-loading.ts").read_text(
            encoding="utf-8"
        )
        self.assertIn("LIVE_ENTRY_MINIMUM_LOADING_MS = 1200", loading_source)

    def test_step_cache_actions_use_the_requested_labels_and_positions(self):
        repository_root = Path(__file__).resolve().parents[7]
        console_root = repository_root / "mango-console" / "src"
        step_source = (
                console_root
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        flow_source = (
                console_root
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "FlowChart.vue"
        ).read_text(encoding="utf-8")

        toolbar = step_source.split('<a-space class="mango-detail-actions"', 1)[1].split(
            "</a-space>", 1
        )[0]
        inspector = step_source.split('<div class="inspector-head-actions">', 1)[1].split(
            "</div>", 1
        )[0]
        self.assertLess(toolbar.index("缓存数据"), toolbar.index("<VariableReferencePanel"))
        self.assertNotIn("查看步骤缓存数据", step_source)
        self.assertNotIn("stepCachePanel.visible", inspector)

        flow_actions = flow_source.split('<div class="flow-actions">', 1)[1].split(
            '<template v-if="!compact">', 1
        )[0]
        self.assertLess(flow_actions.index("步骤详情"), flow_actions.index("缓存数据"))

    def test_element_tools_are_enabled_by_page_context_for_element_and_step_workspace(self):
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        stream_source = self._component_source("UiLiveStreamPanel.vue")
        repository_root = Path(__file__).resolve().parents[7]
        step_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        case_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "case"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("Boolean(props.pageId)", workbench_source)
        self.assertIn(':allow-operate="supportsElementTools"', workbench_source)
        self.assertIn(':allow-record="supportsElementTools"', workbench_source)
        self.assertIn(
            'v-if="supportsElementTools && interactionMode !== \'record\'"',
            workbench_source,
        )
        self.assertIn('v-if="props.allowOperate" value="operate"', stream_source)
        self.assertIn('v-if="props.allowRecord" value="record"', stream_source)
        self.assertIn(':page-id="currentPageId"', step_source)
        self.assertIn(':page-step-id="currentPageStepsId"', step_source)
        self.assertIn('@element-saved="handleStepWorkbenchElementSaved"', step_source)
        self.assertNotIn("read-only", case_source)

    def test_step_debug_and_element_results_share_live_workbench_components(self):
        repository_root = Path(__file__).resolve().parents[7]
        console_root = repository_root / "mango-console" / "src"
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        result_source = self._component_source("UiElementCheckResultPanel.vue")
        step_source = (
                console_root
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        element_source = (
                console_root / "views" / "uitest" / "page" / "elements" / "index.vue"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(step_source.count("startStepDebug("), 2)
        self.assertIn("startStepDebug(detailId)", step_source)
        self.assertIn("<UiElementCheckResultPanel", workbench_source)
        self.assertIn("<UiElementCheckResultPanel", element_source)
        self.assertIn("putUiElementDeepCheckApply", workbench_source)
        self.assertIn("locator_engine", result_source)
        self.assertIn("emit('element-saved', record)", workbench_source)
        self.assertIn("emit('page-step-saved', result)", workbench_source)

    def test_step_node_element_actions_require_binding_and_reuse_live_deep_check(self):
        repository_root = Path(__file__).resolve().parents[7]
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        step_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        check_handler = workbench_source.split("async function checkElementInWorkspace", 1)[1].split(
            "function checkEditedElement", 1
        )[0]

        self.assertIn('v-if="hasSelectedNodeElement"', step_source)
        self.assertIn("查看元素", step_source)
        self.assertIn("深度检测", step_source)
        self.assertIn('v-if="!caseInputMode"', step_source)
        self.assertIn("AI自愈", step_source)
        self.assertIn("getElementIdFromCascader(data.selectData?.ele_name)", step_source)
        self.assertIn("postUiElementCheck", step_source)
        self.assertIn("<UiElementDeepCheckVariablesDialog", step_source)
        self.assertIn("deepCheckVariablesDialogRef.value?.open", step_source)
        self.assertIn("runtimeVariables || {}", step_source)
        self.assertIn('@element-check-result="handleStepElementCheckResult"', step_source)
        self.assertIn('@element-check-started="handleStepElementCheckStarted"', step_source)
        self.assertNotIn('@element-check-finished="handleStepElementCheckFinished"', step_source)
        self.assertIn("<UiElementCheckResultPanel", step_source)
        self.assertIn("function handleStepElementCheckResult", step_source)
        self.assertIn("applyStepElementDeepCheckUpdates", step_source)
        self.assertIn("getExecutorTask", workbench_source)
        self.assertNotIn("funcName === 'u_element_check_result'", workbench_source)
        self.assertIn('v-if="mode !== \'step\'"', workbench_source)
        self.assertIn("await ensureWorkspaceReady()", check_handler)
        self.assertLess(
            check_handler.index("deepCheckVariablesDialogRef.value?.open"),
            check_handler.index("await ensureWorkspaceReady()"),
        )
        deep_check_handler = step_source.split(
            "async function runSelectedElementDeepCheck", 1
        )[1].split("async function openSelectedElementAiHeal", 1)[0]
        self.assertIn("elementCheckResult.visible = false", deep_check_handler)
        self.assertLess(
            deep_check_handler.index("deepCheckVariablesDialogRef.value?.open"),
            deep_check_handler.index("elementDeepCheckLoading.value = true"),
        )
        self.assertIn("check_mode: 'deep'", deep_check_handler)
        self.assertIn("runtime_variables: runtimeVariables || {}", deep_check_handler)
        self.assertIn("scheduleElementDeepCheckPoll(0)", deep_check_handler)
        self.assertIn("async function pollElementDeepCheckResult", deep_check_handler)
        self.assertIn("const element = await loadSelectedNodeElement()", deep_check_handler)
        self.assertIn("getExecutorTask(elementDeepCheckTaskId.value)", deep_check_handler)
        self.assertIn("elementCheckResult.visible = true", deep_check_handler)
        self.assertNotIn("openStepLiveWorkbench()", deep_check_handler)
        self.assertIn("if (liveWorkbenchVisible.value)", deep_check_handler)
        self.assertIn("checkElementInWorkspace", deep_check_handler)
        self.assertIn("typeof started === 'string'", deep_check_handler)
        self.assertIn("elementCheckResult.visible = false", deep_check_handler)
        self.assertIn('@element-check-result="handleStepElementCheckResult"', step_source)
        self.assertIn("return elementCheckRequestId || true", workbench_source)
        result_handler = step_source.split(
            "function handleStepElementCheckResult", 1
        )[1].split("async function applyStepElementDeepCheckUpdates", 1)[0]
        self.assertIn("clearElementDeepCheckTimer()", result_handler)
        self.assertIn("elementDeepCheckLoading.value = false", result_handler)
        self.assertIn("elementDeepCheckElementId.value = null", result_handler)
        self.assertIn("elementCheckResult.visible = true", result_handler)
        self.assertIn("elementDeepCheckSession.accept(result)", result_handler)
        task_poll_handler = step_source.split(
            "async function pollElementDeepCheckResult()", 1
        )[1].split("function handleStepElementCheckResult", 1)[0]
        self.assertIn("getExecutorTask(elementDeepCheckTaskId.value)", task_poll_handler)
        self.assertIn("executor_task_id: elementDeepCheckTaskId.value", task_poll_handler)
        self.assertIn("handleStepElementCheckResult({", task_poll_handler)
        self.assertIn("elementCheckResult.visible = true", result_handler)

    def test_deep_check_variable_dialog_supports_manual_multiple_rows(self):
        source = self._component_source("UiElementDeepCheckVariablesDialog.vue")

        self.assertIn("新增变量", source)
        self.assertIn("function addVariable()", source)
        self.assertIn("function removeVariable(index: number)", source)
        self.assertIn("variables.value.push", source)
        self.assertIn("variables.value.splice(index, 1)", source)
        self.assertIn("Value 留空时不替换", source)

    def test_page_step_debug_keeps_live_workspace_after_full_or_single_execution(self):
        repository_root = Path(__file__).resolve().parents[7]
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        flow_chart_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "FlowChart.vue"
        ).read_text(encoding="utf-8")
        result_handler = workbench_source.split("if (funcName === 'u_page_steps')", 1)[1].split(
            "onMounted(() =>", 1
        )[0]

        self.assertIn("livePanelRef.value?.resumeControlAfterAutomation()", result_handler)
        self.assertNotIn("resetWorkspace(", result_handler)
        self.assertNotIn("直播执行后关闭", flow_chart_source)

    def test_embedded_page_step_detail_keeps_canvas_height_and_uses_panel_scroll(self):
        repository_root = Path(__file__).resolve().parents[7]
        step_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("'page-steps-workbench-page--embedded-scroll': embedded && !compact", step_source)
        self.assertIn(".page-steps-workbench-page--embedded-scroll .steps-workbench", step_source)
        self.assertIn("min-height: min(760px, calc(100vh - 128px));", step_source)
        embedded_style = step_source.split(
            ".page-steps-workbench-page--embedded-scroll {", 1
        )[1].split(
            ".steps-workbench {", 1
        )[0]
        self.assertIn("height: auto;", embedded_style)
        self.assertIn("min-height: 0;", embedded_style)
        self.assertIn("overflow: hidden;", embedded_style)
        case_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "case"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        panel_style = case_source.split(".mango-ui-case-page-step-panel {", 1)[1].split(
            ".ui-case-live-area", 1
        )[0]
        self.assertIn("flex: 1 1 auto;", panel_style)
        self.assertIn("height: 100%;", panel_style)
        self.assertIn("min-height: 0;", panel_style)

    def test_platform_websocket_reconnect_does_not_recreate_workspace(self):
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        handler = source.split(
            "function handlePlatformWebsocketOpen()", 1
        )[1].split("function actuatorLabel", 1)[0]

        self.assertNotIn("openWorkspace(", handler)
        self.assertNotIn("reopenWorkspace(", handler)
        self.assertNotIn("scheduleWorkspaceRetry(", handler)

    def test_expired_workspace_waits_for_manual_reconnect(self):
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        recovery = workbench_source.split(
            "async function recoverExpiredWorkspace", 1
        )[1].split("function handlePlatformWebsocketOpen", 1)[0]
        self.assertIn("实时工作区已断开，请点击“重新连接”", recovery)
        self.assertNotIn("openWorkspace(", recovery)

        stream_source = self._component_source("UiLiveStreamPanel.vue")
        restart = stream_source.split("async function restart()", 1)[1].split(
            "function updateVisible", 1
        )[0]
        self.assertIn("workspaceExpired.value", restart)
        self.assertIn("emit('reconnect-workspace')", restart)

    def test_workspace_business_error_stops_retry_and_unmount_invalidates_pending_request(self):
        repository_root = Path(__file__).resolve().parents[7]
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        live_api_source = (
                repository_root
                / "mango-console"
                / "src"
                / "api"
                / "uitest"
                / "live-stream.ts"
        ).read_text(encoding="utf-8")
        open_workspace = workbench_source.split(
            "async function openWorkspace", 1
        )[1].split("function clearWorkspaceRetryTimer", 1)[0]
        unmount_handler = workbench_source.split("onBeforeUnmount(() => {", 1)[1].split(
            "})", 1
        )[0]

        self.assertNotIn("scheduleWorkspaceRetry", open_workspace)
        self.assertIn("!workspaceMounted", open_workspace)
        self.assertIn("workspaceAutoRetryBlocked = true", open_workspace)
        self.assertIn("UI授权.*缓存已过期", open_workspace)
        self.assertIn("workspaceMounted = false", unmount_handler)
        self.assertIn("workspaceRequestSeq += 1", unmount_handler)
        create_workspace_api = live_api_source.split(
            "export function createUiLiveWorkspace", 1
        )[1].split("export function closeUiLiveWorkspace", 1)[0]
        self.assertIn("silentError: true", create_workspace_api)

    def test_live_stream_waits_until_element_workspace_is_ready(self):
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        open_workspace = source.split("async function openWorkspace", 1)[1].split(
            "function clearWorkspaceRetryTimer", 1
        )[0]

        self.assertIn("await waitForWorkspaceReady()", open_workspace)
        self.assertLess(
            open_workspace.index("await waitForWorkspaceReady()"),
            open_workspace.index("liveVisible.value = true"),
        )

    def test_workspace_ready_wait_uses_http_status_as_websocket_fallback(self):
        repository_root = Path(__file__).resolve().parents[7]
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        live_api_source = (
                repository_root
                / "mango-console"
                / "src"
                / "api"
                / "uitest"
                / "live-stream.ts"
        ).read_text(encoding="utf-8")
        ready_wait = source.split("function waitForWorkspaceReady", 1)[1].split(
            "async function ensureWorkspaceReady", 1
        )[0]

        self.assertIn("getUiLiveWorkspaceStatus(workspaceId)", ready_wait)
        self.assertIn("status === 'ready'", ready_wait)
        self.assertIn("status === 'failed' || status === 'closed'", ready_wait)
        self.assertIn("workspaceStatusPollTimer", ready_wait)
        self.assertIn("export function getUiLiveWorkspaceStatus", live_api_source)

    def test_element_page_refreshes_live_element_options_after_create(self):
        repository_root = Path(__file__).resolve().parents[7]
        page_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page"
                / "elements"
                / "index.vue"
        ).read_text(encoding="utf-8")
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        saved_handler = page_source.split("async function handleElementSaved()", 1)[1].split(
            "function aiHealStatusMeta", 1
        )[0]

        self.assertIn('ref="liveWorkbenchRef"', page_source)
        self.assertIn("refreshElements: loadElements", workbench_source)
        self.assertIn("liveWorkbenchRef.value?.refreshElements?.()", saved_handler)

    def test_table_element_check_does_not_repeat_global_http_error(self):
        repository_root = Path(__file__).resolve().parents[7]
        page_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page"
                / "elements"
                / "index.vue"
        ).read_text(encoding="utf-8")
        check_handler = page_source.split("function onCheck(record: any,", 1)[1].split(
            "async function openElementPageBrowser", 1
        )[0]
        catch_handler = check_handler.split(".catch((error)", 1)[1]

        self.assertNotIn("Message.error", catch_handler)
        self.assertIn("elementCheck.loadingKey = ''", catch_handler)
        self.assertIn("elementCheck.currentElement = null", catch_handler)

    def test_live_element_check_opens_result_only_after_executor_callback(self):
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        check_handler = source.split("async function checkSelectedElement(", 1)[1].split(
            "function getSelectedElementId", 1
        )[0]
        task_poll_handler = source.split("async function pollElementCheckTask()", 1)[1].split(
            "function acceptElementCheckResult", 1
        )[0]

        request_success = check_handler.split("const res = await postUiElementCheck", 1)[1].split(
            "} catch", 1
        )[0]
        request_failure = check_handler.split("} catch (error)", 1)[1]
        self.assertNotIn("emit('element-check-result'", request_success)
        self.assertNotIn("emit('element-check-result'", request_failure)
        self.assertNotIn(
            "emit('element-check-result', latestElementResult.value)", check_handler
        )
        self.assertIn("emit('element-check-finished')", check_handler)
        self.assertIn("elementCheckRequestId = String(res.data?.check_id || '')", request_success)
        self.assertIn("getExecutorTask(elementCheckTaskId)", task_poll_handler)
        self.assertIn("saveExecutorTaskObservation('element-check'", check_handler)
        self.assertIn("const taskResult = { ...result, executor_task_id: elementCheckTaskId }", task_poll_handler)
        self.assertIn("if (!acceptElementCheckResult(taskResult)) return", task_poll_handler)
        self.assertIn("emit('element-check-result', taskResult)", task_poll_handler)
        self.assertIn(
            "if (props.inlineElementResult !== false) showElementCheckDetail(taskResult)",
            task_poll_handler,
        )
        self.assertNotIn("funcName === 'u_element_check_result'", source)
        accept_handler = source.split("function acceptElementCheckResult", 1)[1].split(
            "function selectedElementRecord", 1
        )[0]
        self.assertIn("clearExecutorTaskObservation('element-check'", accept_handler)

        page_source = self._view_source('uitest/page/elements/index.vue')
        parent_handler = page_source.split(
            'function handleWorkbenchElementCheckResult(result: any)', 1
        )[1].split('function handleWorkbenchElementCheckFinished', 1)[0]
        self.assertIn('applyElementCheckResult(result)', parent_handler)
        self.assertNotIn('applyElementCheckResult(result, false)', parent_handler)

        apply_handler = page_source.split(
            'function applyElementCheckResult(result: any, showPanel = true)', 1
        )[1].split('async function applyDeepCheckUpdates', 1)[0]
        self.assertIn('if (showPanel) elementCheck.visible = true', apply_handler)
        self.assertIn('elementCheck.currentElement ||', apply_handler)
        self.assertIn('liveWorkbenchRef.value?.acceptElementCheckResult?.(result)', page_source)

        check_handler = source.split('async function checkSelectedElement(', 1)[1].split(
            'async function checkElementInWorkspace', 1
        )[0]
        self.assertIn(
            'const requestToken = elementCheckSession.start(elementId, workspace.workspaceId)',
            check_handler,
        )
        self.assertIn('if (!elementCheckSession.isActive(requestToken)) return', check_handler)
        self.assertIn(
            "elementCheckSession.bindCheckId(requestToken, res.data?.check_id || '')",
            check_handler,
        )
        self.assertNotIn('elementCheckSequence', check_handler)

    def test_live_stream_wheel_is_buffered_and_targets_pointer_position(self):
        source = self._component_source("UiLiveStreamPanel.vue")
        wheel_handler = source.split("async function onWheel(event: WheelEvent)", 1)[1].split(
            "function onKeyDown", 1
        )[0]
        flush_handler = source.split("function flushWheel()", 1)[1].split(
            "async function refreshPages", 1
        )[0]

        self.assertIn("const currentPointer = pointer(event)", wheel_handler)
        self.assertIn("wheelDeltaY += delta.deltaY", wheel_handler)
        self.assertIn("scheduleWheelFlush()", wheel_handler)
        self.assertIn("pendingControlEvents.size > 0", flush_handler)
        self.assertIn("...wheelPointer", flush_handler)
        self.assertIn('@wheel.prevent.stop="onWheel"', source)

    def test_live_control_renews_without_five_minute_countdown(self):
        source = self._component_source("UiLiveStreamPanel.vue")
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")

        self.assertIn("controlling ? ' · 自动续租' : ''", source)
        self.assertNotIn("leaseRemaining", source)
        self.assertIn("message.reason === 'idle_takeover'", source)
        self.assertIn("断开且无任务后空闲 5 分钟自动回收", workbench_source)
        replace_frame = source.split("function replaceFrame", 1)[1].split(
            "function clearFrame", 1
        )[0]
        self.assertNotIn("ensureControl()", replace_frame)
        self.assertIn("controlAcquirePromise", source)
        self.assertIn("finishControlAcquire(true)", source)

    def test_element_workspace_has_explicit_recording_mode_and_recorder_panel(self):
        stream_source = self._component_source("UiLiveStreamPanel.vue")
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        recorder_source = self._component_source("UiStepRecorderPanel.vue")

        self.assertIn("'select' | 'operate' | 'record'", stream_source)
        self.assertIn('v-if="props.allowRecord" value="record"', stream_source)
        self.assertIn('>录制步骤</a-radio>', stream_source)
        self.assertIn("event_type: 'record_action'", stream_source)
        self.assertIn("<UiStepRecorderPanel", workbench_source)
        self.assertIn("sessionStorage.setItem", workbench_source)
        self.assertIn("@dragstart.stop=\"onDragStart(index)\"", recorder_source)
        self.assertIn("保存为页面步骤", recorder_source)
        self.assertIn("postUiPageStepRecordingCommit", recorder_source)

    def test_element_collection_and_scan_expose_ai_locator_recommendation(self):
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        panel_source = self._component_source("UiAiLocatorRecommendationPanel.vue")

        self.assertGreaterEqual(workbench_source.count("AI 推荐"), 2)
        self.assertIn("postUiElementAiLocatorRecommend", workbench_source)
        self.assertIn("check_locator", workbench_source)
        self.assertIn("换一批", panel_source)
        self.assertIn("candidate.verified", panel_source)
        self.assertIn("浏览器校验全部失败", panel_source)
        self.assertIn("candidateFailureReason", panel_source)
        self.assertIn("匹配到 ${count} 个元素", panel_source)
        self.assertIn("aiLocator.candidates.slice(0, 5)", workbench_source)
        self.assertIn("selectedCandidates.length", panel_source)
        self.assertIn("补充定位描述", panel_source)
        self.assertIn("元素位置与周边文字", panel_source)
        self.assertIn("排除项", panel_source)
        self.assertIn("location_description", panel_source)
        self.assertIn("location_description: aiLocator.locationDescription", workbench_source)
        self.assertIn("@refresh=\"handleAiLocatorRefresh\"", workbench_source)
        self.assertIn("<Scrollbar", panel_source)
        self.assertIn("mango-ai-locator-panel__candidate-scroll", panel_source)
        self.assertNotIn("个通过浏览器校验", panel_source)

    def test_element_description_separates_positive_context_and_exclusions(self):
        panel_source = self._component_source("UiElementEditPanel.vue")

        self.assertIn('label="元素位置与周边文字"', panel_source)
        self.assertIn('label="排除项"', panel_source)
        self.assertNotIn('label="周边文字与排除项"', panel_source)
        self.assertIn("后者只填写不能选择的同名或相似元素", panel_source)
        self.assertIn("normalizeDescriptionFields(record)", panel_source)
        self.assertIn("(?:排除|不是)", panel_source)

    def test_recorder_supports_manual_nodes_and_passive_browser_events(self):
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        recorder_source = self._component_source("UiStepRecorderPanel.vue")

        self.assertIn("插入节点", recorder_source)
        self.assertNotIn("校验录制", recorder_source)
        self.assertNotIn("validateDraft", recorder_source)
        self.assertNotIn("录制节点校验通过", recorder_source)
        self.assertIn("元素操作", recorder_source)
        self.assertIn("断言操作", recorder_source)
        self.assertIn("SQL 操作", recorder_source)
        self.assertIn("自定义变量", recorder_source)
        self.assertIn("Python 代码", recorder_source)
        self.assertIn("强制等待", recorder_source)
        self.assertIn("insertNode(6)", recorder_source)
        self.assertNotIn("insertNode(4)", recorder_source)
        self.assertIn("UiStepNodeConfigForm", recorder_source)
        self.assertIn(':field-prefix="String(item.client_id)"', recorder_source)
        node_form_source = self._component_source("UiStepNodeConfigForm.vue")
        self.assertIn(":input-attrs=\"fieldAttrs(item)\"", node_form_source)
        self.assertIn(":textarea-attrs=\"fieldAttrs(item)\"", node_form_source)
        self.assertIn(":key=\"controlKey(item, 'textarea')\"", node_form_source)
        self.assertIn("item.type === 'input-number'", node_form_source)
        self.assertIn("const reactiveItems = reactive(items)", recorder_source)
        self.assertIn("mango-step-recorder__node-card", recorder_source)
        self.assertIn('@dragstart.stop="onDragStart(index)"', recorder_source)
        self.assertIn('@dragend="onDragEnd"', recorder_source)
        self.assertIn("nodeSummary(item)", recorder_source)
        self.assertNotIn("methodName(item)", recorder_source)
        self.assertIn("`元素 ${nodeUsesElement(item) ? 1 : 0} 个`", recorder_source)
        self.assertIn("`定位 ${locators} 组`", recorder_source)
        self.assertNotIn("`入参 ${parameterCount} 项`", recorder_source)
        self.assertIn("元素名称", recorder_source)
        self.assertIn(">元素</a-button", recorder_source)
        self.assertIn(">检测</a-button", recorder_source)
        self.assertIn("emit('check-element', item)", recorder_source)
        self.assertIn('@check-element="checkRecordedElement"', workbench_source)
        self.assertIn("function checkRecordedElement", workbench_source)
        self.assertIn("'check_locator'", workbench_source)
        self.assertIn("_checkStatus, _checkDuration", workbench_source)
        self.assertIn("Object.assign(current, normalizeRecordedAction", workbench_source)
        self.assertIn("Object.assign(previous, normalizeRecordedAction", workbench_source)
        self.assertIn("label: '分类'", recorder_source)
        self.assertIn("key: 'recorded_element_category'", recorder_source)
        self.assertIn("value: node?.category || '未分类'", recorder_source)
        self.assertGreaterEqual(recorder_source.count("compactHalf: true"), 2)
        self.assertIn("compactNarrow: true", recorder_source)
        self.assertIn("compactWideLabel: true", recorder_source)
        self.assertNotIn("新元素分类", recorder_source)
        self.assertNotIn("页面名称", recorder_source)
        self.assertNotIn("pageDisplayName(item)", recorder_source)
        self.assertIn("key: 'recorded_element_name'", recorder_source)
        self.assertIn("required: true", recorder_source)
        self.assertIn("!String(item.name || '').trim()", recorder_source)
        self.assertNotIn("mango-step-recorder__node-meta", recorder_source)
        self.assertIn('@change="syncInlineConfig(item)"', recorder_source)
        self.assertNotIn("mango-step-recorder__table", recorder_source)
        self.assertNotIn('title="编辑步骤节点"', recorder_source)
        self.assertNotIn("录制结果", recorder_source)
        self.assertNotIn("保存后操作", recorder_source)
        self.assertNotIn("立即在当前浏览器中试运行", recorder_source)
        self.assertNotIn("debugAfterSave", recorder_source)
        self.assertNotIn("debug_after_save", workbench_source)
        self.assertIn("settings-change", recorder_source)
        self.assertIn("record_poll", workbench_source)
        self.assertIn("data.passive_actions", workbench_source)
        self.assertRegex(
            workbench_source,
            r"data\?\.status\s*\|\|\s*\(\s*data\?\.sensitive",
        )
        self.assertIn("queuedRecordEvents", self._component_source("UiLiveStreamPanel.vue"))

    def test_live_recording_uses_ime_proxy_for_chinese_composition(self):
        source = self._component_source("UiLiveStreamPanel.vue")

        self.assertIn('aria-label="直播画面输入法代理"', source)
        self.assertIn('@compositionstart.stop="onCompositionStart"', source)
        self.assertIn('@compositionend.stop="onCompositionEnd"', source)
        self.assertIn("function commitImeText", source)
        self.assertIn("event_type: 'record_action', action: 'input', text", source)
        self.assertIn("skipNextImeInput", source)
        self.assertIn("event.isComposing", source)

    def test_recording_waits_for_control_and_keeps_only_session_draft(self):
        stream_source = self._component_source("UiLiveStreamPanel.vue")
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")

        send_command = stream_source.split("async function sendWorkspaceCommand", 1)[1].split(
            "function pointer", 1
        )[0]
        self.assertIn("await ensureControl()", send_command)
        self.assertNotIn("请先申请远程控制", send_command)
        self.assertIn("controllingValue: controlling", stream_source)
        interaction_watch = stream_source.split("watch(interactionMode", 1)[1].split(
            "watch(", 1
        )[0]
        self.assertIn("void ensureControl()", interaction_watch)
        self.assertIn("livePanelRef.value?.controllingValue", workbench_source)
        self.assertIn("sessionStorage.setItem(recordingStorageKey.value", workbench_source)
        self.assertIn("sessionStorage.removeItem(recordingStorageKey.value)", workbench_source)

    def test_live_element_scan_supports_deep_mode_and_verified_metadata(self):
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        editor_source = self._component_source("UiElementEditPanel.vue")
        runtime_meta_source = self._component_source("UiLocatorRuntimeMeta.vue")
        locator_group_source = self._component_source("UiLocatorGroupCell.vue")
        scan_handler = source.split("function scanPageElements()", 1)[1].split(
            "function clearScanTimer", 1
        )[0]

        self.assertIn("v-model=\"scanMode\"", source)
        self.assertIn('value="deep"', source)
        self.assertIn('>深度扫描</a-option>', source)
        self.assertIn('value="region"', source)
        self.assertIn('>区域扫描</a-option>', source)
        self.assertIn("postUiElementScan({", scan_handler)
        self.assertIn("mode: scanMode.value", scan_handler)
        self.assertIn("workspace_id: workspace.workspaceId", scan_handler)
        self.assertIn("scheduleScanTaskPoll(0)", scan_handler)
        self.assertIn("loadExecutorTaskObservation('page-scan'", source)
        self.assertIn("restorePageScanTask()", source)
        self.assertIn("scanMode.value === 'region' && !pickedElement.value", scan_handler)
        self.assertIn("setInteractionMode?.('select')", scan_handler)
        self.assertEqual(source.count("<UiLocatorGroupCell"), 3)
        self.assertIn(':match-count="getScannedLocatorGroup(record, 1)?.match_count"', source)
        self.assertIn(':text-summary="getScannedElementText(record)"', source)
        self.assertIn('match-label="元素"', source)
        self.assertIn("文本摘要", locator_group_source)
        self.assertIn("record.frame_depth", source)
        self.assertIn("data.baseline_snapshot", source)
        self.assertNotIn("selectedElementLocatorGroups", source)
        self.assertIn("深度检测", editor_source)
        self.assertEqual(editor_source.count("<UiLocatorRuntimeMeta"), 3)
        self.assertIn("最近匹配", runtime_meta_source)
        self.assertIn("文本摘要", runtime_meta_source)

    def test_element_check_supports_normal_and_deep_modes(self):
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        editor_source = self._component_source("UiElementEditPanel.vue")
        recorder_source = self._component_source("UiStepRecorderPanel.vue")
        repository_root = Path(__file__).resolve().parents[7]
        page_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page"
                / "elements"
                / "index.vue"
        ).read_text(encoding="utf-8")

        self.assertNotIn('<strong>元素检测</strong>', source)
        self.assertNotIn('placeholder="选择一个元素"', source)
        self.assertIn("async function checkElementInWorkspace", source)
        self.assertIn("checkElementInWorkspace,", source)
        self.assertIn("check_mode: checkMode", source)
        self.assertIn("checkMode: 'normal' | 'deep' = 'normal'", source)
        self.assertIn("emit('check', { ...form }, 'deep')", editor_source)
        self.assertIn("label: '深度检测'", page_source)
        self.assertIn("liveWorkbenchRef.value.checkElementInWorkspace(record, checkMode, runtimeVariables)",
                      page_source)
        variable_dialog_source = self._component_source("UiElementDeepCheckVariablesDialog.vue")
        self.assertIn("深度检测临时变量", variable_dialog_source)
        self.assertIn("['page_url', '页面 URL']", variable_dialog_source)
        self.assertIn("['name', '元素名称']", variable_dialog_source)
        self.assertIn("['prompt', 'AI 提示词']", variable_dialog_source)
        self.assertIn("['loc3', '第三组定位表达式']", variable_dialog_source)
        self.assertIn("Value 留空时不替换", variable_dialog_source)
        self.assertIn("runtime_variables: runtimeVariables", source)
        self.assertIn("runtime_variables: runtimeVariables || {}", page_source)
        self.assertIn("if (liveWorkbenchVisible.value)", page_source)
        self.assertIn("putUiElementDeepCheckApply", page_source)
        result_source = self._component_source("UiElementCheckResultPanel.vue")
        self.assertIn("写入定位组", result_source)
        self.assertIn('picture-title="检测截图"', result_source)
        self.assertIn('screenshot_error', result_source)
        self.assertIn("check_mode: checkMode", page_source)
        self.assertIn("loading: elementCheckLoading", page_source)
        self.assertIn(':check-loading="elementCheckLoading"', page_source)
        self.assertIn("Boolean(elementCheck.loadingKey)", page_source)
        self.assertIn("if (elementCheckLoading.value) return", page_source)
        self.assertIn("Boolean(props.checkLoading)", source)
        self.assertIn("scannedElements.value.some", source)
        self.assertIn("recordedActions.value.some", source)
        self.assertIn("emit('element-check-finished')", source)
        self.assertIn("props.checkLoading ||", editor_source)
        self.assertIn(':loading="checkLoading"', recorder_source)
        self.assertIn(':disabled="checkLoading"', recorder_source)

    def test_element_editor_auto_resolves_create_or_update_by_page_identity(self):
        editor_source = self._component_source("UiElementEditPanel.vue")
        repository_root = Path(__file__).resolve().parents[7]
        page_step_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page-steps"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        case_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "case"
                / "details"
                / "index.vue"
        ).read_text(encoding="utf-8")
        element_page_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page"
                / "elements"
                / "index.vue"
        ).read_text(encoding="utf-8")
        live_workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        api_source = (
                repository_root
                / "mango-console"
                / "src"
                / "api"
                / "uitest"
                / "element.ts"
        ).read_text(encoding="utf-8")

        self.assertIn("元素基本信息", editor_source)
        self.assertIn("getUiElementIdentity", editor_source)
        self.assertIn("form.page, form.name, form.category", editor_source)
        self.assertIn("当前页面已存在相同名称和分类的元素", editor_source)
        self.assertIn("当前页面不存在相同名称和分类的元素", editor_source)
        self.assertIn("await runIdentityCheck(true)", editor_source)
        self.assertIn("mode.value === 'create' &&", editor_source)
        self.assertIn("identityCheck.record?.id", editor_source)
        self.assertIn("mode.value === 'edit' ? form.id : identityCheck.record?.id", editor_source)
        self.assertIn("修改名称或分类不会创建新元素", editor_source)
        self.assertIn("targetId ? await putUiElement(payload) : await postUiElement(payload)", editor_source)
        self.assertIn("elementEditPanelRef.value?.openEdit(element)", page_step_source)
        self.assertIn("elementEditPanelRef.value?.openEdit(element)", case_source)
        self.assertIn(
            "elementEditPanelRef.value?.openCreate(currentPageId.value, activeCategoryName.value)",
            element_page_source,
        )
        self.assertGreaterEqual(live_workbench_source.count("elementEditPanelRef.value?.openCreate("), 3)
        self.assertIn("elementEditPanelRef.value?.openEditById(action.element_id)", live_workbench_source)
        self.assertIn("url: '/ui/element/identity'", api_source)

    def test_scanned_element_check_opens_shared_detail_after_executor_result(self):
        workbench_source = self._component_source("UiLiveWorkbenchPanel.vue")
        repository_root = Path(__file__).resolve().parents[7]
        element_page_source = (
                repository_root
                / "mango-console"
                / "src"
                / "views"
                / "uitest"
                / "page"
                / "elements"
                / "index.vue"
        ).read_text(encoding="utf-8")
        check_handler = workbench_source.split("function checkScannedElement", 1)[1].split(
            "function resolveRuntimeResult", 1
        )[0]
        result_handler = workbench_source.split("if (data.scan_check_result)", 1)[1].split(
            "if (data.elements)", 1
        )[0]

        self.assertIn("element-check-started", check_handler)
        self.assertIn("buildScannedCheckDetail", check_handler)
        self.assertIn("locator_groups", workbench_source)
        self.assertIn("emit(", result_handler)
        self.assertIn("'element-check-result'", result_handler)
        self.assertIn("scan_row_key", element_page_source)
        self.assertIn("UiElementCheckResultPanel", element_page_source)
        self.assertIn("UiElementCheckResultPanel", workbench_source)

    def test_element_save_only_backfills_missing_baseline_for_captured_element(self):
        source = self._component_source("UiLiveWorkbenchPanel.vue")
        saved_handler = source.split("async function handleElementSaved", 1)[1].split(
            "function showElementCheckDetail", 1
        )[0]

        self.assertIn("capturedElementSave && !hasCapturedBaseline && lacksStoredBaseline", saved_handler)
        self.assertNotIn("\n    triggerElementBaselineCheck(record?.id)", saved_handler)
        self.assertIn("void triggerElementBaselineCheck(record?.id)", saved_handler)

    def test_stack_scripts_disable_vite_browser_open_without_changing_manual_default(self):
        repository_root = Path(__file__).resolve().parents[7]
        vite_source = (
                repository_root / "mango-console" / "vite.config.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("open: process.env.MANGO_VITE_AUTO_OPEN !== 'false'", vite_source)

        for script_name in ("启动-后端+前端+WebSocket服务.sh", "启动-全部服务.sh"):
            script_source = (
                    repository_root / "scripts" / script_name
            ).read_text(encoding="utf-8")
            self.assertIn(
                "env MANGO_VITE_AUTO_OPEN=false npm run dev",
                script_source,
            )


class FakeConsumer:
    def __init__(self):
        self.json_messages = []
        self.binary_messages = []
        self.closed = False

    async def send_json(self, payload):
        self.json_messages.append(payload)

    async def send(self, *, bytes_data=None, **kwargs):
        if bytes_data is not None:
            self.binary_messages.append(bytes_data)

    async def close(self, code=None):
        self.closed = True


def stream_claims(
        *,
        stream_id: str = "stream-1",
        user_id: int = 1,
        execution_type: str = "page_step_workspace",
        execution_id: str = "workspace-1",
) -> dict:
    return {
        "stream_id": stream_id,
        "user_id": user_id,
        "executor_username": "open",
        "connection_id": "actuator-connection",
        "execution_type": execution_type,
        "execution_id": execution_id,
        "slot_id": f"slot-{user_id}",
    }


def runtime_model() -> SimpleNamespace:
    model = SimpleNamespace(workspace_id=None, send_user=None)
    model.model_dump = lambda: {
        "workspace_id": model.workspace_id,
        "send_user": model.send_user,
    }
    return model


class MigratedLiveWorkspaceProbeTest(SimpleTestCase):
    def setUp(self):
        ExecutorSlotLeaseService.reset_for_tests()
        LiveWorkspaceService._workspace_by_id.clear()
        LiveWorkspaceService._workspace_by_key.clear()
        self.connection = SimpleNamespace(
            connection_id="actuator-connection",
            user=SimpleNamespace(username="open"),
            user_id=9,
            is_open=True,
        )

    def tearDown(self):
        ExecutorSlotLeaseService.reset_for_tests()
        LiveWorkspaceService._workspace_by_id.clear()
        LiveWorkspaceService._workspace_by_key.clear()

    @patch.object(LiveWorkspaceService, "available_actuators", return_value=[])
    @patch.object(LiveWorkspaceService, "_send_workspace_start")
    @patch.object(LiveWorkspaceService, "_runtime_model", side_effect=lambda *args: runtime_model())
    @patch.object(LiveWorkspaceService, "_resolve_executor")
    def test_same_user_reopens_same_workspace_without_replacing_it(
            self,
            resolve_executor,
            runtime_model_mock,
            send_workspace_start,
            available_actuators,
    ):
        resolve_executor.return_value = self.connection
        user = {"id": 1, "username": "maopeng"}

        first = LiveWorkspaceService.create_workspace(
            user,
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
            7,
            1,
            "open",
        )
        reopened = LiveWorkspaceService.create_workspace(
            user,
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
            7,
            1,
            "open",
        )

        self.assertEqual(reopened["workspace_id"], first["workspace_id"])
        self.assertTrue(reopened["reused"])
        self.assertEqual(len(LiveWorkspaceService._workspace_by_id), 1)
        self.assertEqual(send_workspace_start.call_count, 2)

    @patch.object(LiveWorkspaceService, "available_actuators", return_value=[])
    @patch.object(LiveWorkspaceService, "_send_workspace_start")
    @patch.object(LiveWorkspaceService, "_runtime_model", side_effect=lambda *args: runtime_model())
    @patch.object(LiveWorkspaceService, "_resolve_executor")
    def test_different_users_receive_isolated_workspaces_on_same_executor(
            self,
            resolve_executor,
            runtime_model_mock,
            send_workspace_start,
            available_actuators,
    ):
        resolve_executor.return_value = self.connection

        owner = LiveWorkspaceService.create_workspace(
            {"id": 1, "username": "owner"},
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
            7,
            1,
            "open",
        )
        viewer = LiveWorkspaceService.create_workspace(
            {"id": 2, "username": "viewer"},
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
            7,
            1,
            "open",
        )

        self.assertNotEqual(viewer["workspace_id"], owner["workspace_id"])
        self.assertFalse(viewer["reused"])
        self.assertEqual(send_workspace_start.call_count, 2)
        self.assertEqual(len(LiveWorkspaceService._workspace_by_id), 2)

    @patch.object(LiveWorkspaceService, "available_actuators", return_value=[])
    @patch.object(LiveWorkspaceService, "_send_workspace_start")
    @patch.object(LiveWorkspaceService, "_runtime_model", side_effect=lambda *args: runtime_model())
    @patch.object(LiveWorkspaceService, "_resolve_executor")
    def test_sixth_user_is_rejected_without_sending_workspace_command(
            self,
            resolve_executor,
            runtime_model_mock,
            send_workspace_start,
            available_actuators,
    ):
        resolve_executor.return_value = self.connection
        for user_id in range(1, 6):
            LiveWorkspaceService.create_workspace(
                {"id": user_id, "username": f"user-{user_id}"},
                LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
                user_id,
                1,
                "open",
            )

        with self.assertRaisesRegex(AutoUiError, "已有 5/5 位用户"):
            LiveWorkspaceService.create_workspace(
                {"id": 6, "username": "user-6"},
                LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
                8,
                1,
                "open",
            )

        self.assertEqual(send_workspace_start.call_count, 5)
        self.assertEqual(len(LiveWorkspaceService._workspace_by_id), 5)

    @patch.object(LiveWorkspaceService, "available_actuators", return_value=[])
    @patch.object(LiveWorkspaceService, "_send_workspace_start")
    @patch.object(LiveWorkspaceService, "_runtime_model", side_effect=lambda *args: runtime_model())
    @patch.object(LiveWorkspaceService, "_resolve_executor")
    def test_same_user_uses_one_slot_across_element_and_step_workspaces(
            self,
            resolve_executor,
            runtime_model_mock,
            send_workspace_start,
            available_actuators,
    ):
        resolve_executor.return_value = self.connection
        first = LiveWorkspaceService.create_workspace(
            {"id": 1, "username": "owner"},
            LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
            6,
            1,
            "open",
        )
        second = LiveWorkspaceService.create_workspace(
            {"id": 1, "username": "owner"},
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
            8,
            1,
            "open",
        )

        self.assertEqual(first["slot_id"], second["slot_id"])
        self.assertEqual(second["active_user_count"], 1)
        self.assertEqual(send_workspace_start.call_count, 2)


@override_settings(CACHES={
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "live-workspace-cross-process-tests",
    }
})
class SharedLiveWorkspaceStoreTest(SimpleTestCase):
    def tearDown(self):
        cache.clear()

    @patch.object(LiveWorkspaceService, "_use_local_store", return_value=False)
    def test_element_workspace_is_available_to_another_backend_process(self, use_local_store):
        record = LiveWorkspaceRecord(
            workspace_id="element-workspace-1",
            workspace_type=LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
            resource_id=6,
            test_env=1,
            username="maopeng",
            executor_username="open",
            connection_id="connection-1",
            runtime_data={"workspace_id": "element-workspace-1"},
        )

        LiveWorkspaceService._save_record(record)
        LiveWorkspaceService._workspace_by_id.clear()
        LiveWorkspaceService._workspace_by_key.clear()

        restored = LiveWorkspaceService._get_record(record.workspace_id)

        self.assertIsNotNone(restored)
        self.assertEqual(restored.workspace_type, LiveStreamExecutionType.ELEMENT_WORKSPACE.value)
        self.assertEqual(restored.resource_id, 6)
        self.assertEqual(restored.runtime_data["workspace_id"], record.workspace_id)

    @patch.object(LiveWorkspaceService, "_use_local_store", return_value=False)
    def test_shared_workspace_index_can_reuse_element_workspace(self, use_local_store):
        record = LiveWorkspaceRecord(
            workspace_id="element-workspace-2",
            workspace_type=LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
            resource_id=7,
            test_env=2,
            username="maopeng",
            executor_username="open",
            connection_id="connection-2",
        )
        workspace_key = LiveWorkspaceService._workspace_key(
            record.username,
            record.test_env,
            record.executor_username,
            record.workspace_type,
            record.resource_id,
        )

        LiveWorkspaceService._save_record(record)
        restored = LiveWorkspaceService._get_workspace_by_key(workspace_key)

        self.assertIsNotNone(restored)
        self.assertEqual(restored.workspace_id, record.workspace_id)

    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamPermissionService.validate_execution"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamSessionStore.create"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.SocketConnectionService.require_actuator"
    )
    @patch.object(LiveWorkspaceService, "_use_local_store", return_value=False)
    def test_element_workspace_can_create_stream_session_from_shared_store(
            self,
            use_local_store,
            require_actuator,
            create_session_record,
            validate_execution,
    ):
        connection = SimpleNamespace(connection_id="connection-3")
        require_actuator.return_value = connection
        record = LiveWorkspaceRecord(
            workspace_id="element-workspace-3",
            workspace_type=LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
            resource_id=8,
            test_env=1,
            username="maopeng",
            executor_username="open",
            connection_id="connection-3",
            user_id=1,
            slot_id="slot-1",
            idle_deadline=9999999999,
        )
        LiveWorkspaceService._save_record(record)

        result = LiveStreamSessionService.create_session(
            {"id": 1, "username": "maopeng"},
            LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
            record.workspace_id,
            resource_id=str(record.resource_id),
        )

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["slot_id"], record.slot_id)
        claims = create_session_record.call_args.args[0]
        self.assertEqual(claims["execution_id"], record.workspace_id)
        self.assertEqual(claims["executor_username"], record.executor_username)


class MigratedLiveControlProtocolProbeTest(SimpleTestCase):
    def test_all_frontend_probe_control_types_are_accepted(self):
        payloads = {
            "mouse_move": {"x": 0.5, "y": 0.5},
            "mouse_click": {"x": 0.5, "y": 0.5, "button": "left"},
            "mouse_down": {"x": 0.5, "y": 0.5, "button": "left"},
            "mouse_up": {"x": 0.5, "y": 0.5, "button": "left"},
            "mouse_wheel": {"delta_x": 0, "delta_y": 80, "x": 0.5, "y": 0.5},
            "keyboard_press": {"key": "Escape"},
            "keyboard_down": {"key": "Shift"},
            "keyboard_up": {"key": "Shift"},
            "text_input": {"text": "mango-live-probe"},
            "pick_element": {"x": 0.5, "y": 0.5},
            "check_locator": {
                "row_key": "probe-row",
                "name": "探针元素",
                "locators": [{"exp": 2, "loc": "get_by_text('探针元素')"}],
            },
            "record_action": {"action": "click", "x": 0.5, "y": 0.5},
            "record_poll": {},
            "list_pages": {},
            "switch_page": {"page_id": "page-1"},
            "close_page": {"page_id": "page-1"},
        }

        self.assertEqual(set(payloads), ALLOWED_CONTROL_TYPES)
        for sequence, (event_type, payload) in enumerate(payloads.items(), start=1):
            with self.subTest(event_type=event_type):
                normalized = LiveStreamControlEventValidator.validate({
                    "event_type": event_type,
                    "sequence": sequence,
                    **payload,
                })
                self.assertEqual(normalized["event_type"], event_type)
                self.assertEqual(normalized["sequence"], sequence)

    def test_invalid_frontend_probe_controls_are_rejected(self):
        invalid_events = [
            {"event_type": "mouse_click", "x": 1.2, "y": 0.5, "sequence": 1},
            {"event_type": "unknown_event", "sequence": 2},
            {"event_type": "switch_page", "page_id": "", "sequence": 3},
            {"event_type": "record_action", "action": "unknown", "sequence": 5},
        ]

        for event in invalid_events:
            with self.subTest(event_type=event["event_type"]):
                with self.assertRaises(RuntimeError):
                    LiveStreamControlEventValidator.validate(event)

    def test_mouse_wheel_coordinates_are_optional_but_validated_together(self):
        without_pointer = LiveStreamControlEventValidator.validate({
            "event_type": "mouse_wheel",
            "sequence": 1,
            "delta_x": 0,
            "delta_y": 120,
        })
        self.assertNotIn("x", without_pointer)
        self.assertNotIn("y", without_pointer)

        with self.assertRaisesRegex(RuntimeError, "纵坐标格式无效"):
            LiveStreamControlEventValidator.validate({
                "event_type": "mouse_wheel",
                "sequence": 2,
                "delta_x": 0,
                "delta_y": 120,
                "x": 0.5,
            })


class MigratedLiveStreamProbeTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = LiveStreamRegistry()
        self.owner = FakeConsumer()
        self.publisher = FakeConsumer()
        self.owner_id, _ = await self.registry.register_subscriber(
            stream_claims(),
            self.owner,
        )
        self.publisher_id = await self.registry.register_publisher(
            stream_claims(),
            self.publisher,
        )

    async def asyncTearDown(self):
        await self.registry.close_all()

    async def test_multiple_viewers_receive_the_same_frame(self):
        viewer = FakeConsumer()
        await self.registry.register_subscriber(stream_claims(), viewer)

        viewer_count = await self.registry.publish_frame(
            "stream-1",
            self.publisher_id,
            b"jpeg-frame",
        )
        await asyncio.sleep(0)

        self.assertEqual(viewer_count, 2)
        self.assertEqual(self.owner.binary_messages[-1], b"jpeg-frame")
        self.assertEqual(viewer.binary_messages[-1], b"jpeg-frame")

    async def test_late_viewer_receives_the_latest_frame(self):
        await self.registry.publish_frame("stream-1", self.publisher_id, b"latest-frame")
        viewer = FakeConsumer()

        await self.registry.register_subscriber(stream_claims(), viewer)
        await asyncio.sleep(0.01)

        self.assertEqual(viewer.binary_messages[-1], b"latest-frame")

    async def test_control_ack_data_is_returned_only_to_the_controller(self):
        viewer = FakeConsumer()
        await self.registry.register_subscriber(stream_claims(), viewer)
        await self.registry.acquire_control("stream-1", self.owner_id)
        await self.registry.relay_control(
            "stream-1",
            self.owner_id,
            {"event_type": "list_pages", "sequence": 1},
        )

        await self.registry.relay_publisher_status(
            "stream-1",
            self.publisher_id,
            {
                "type": "control_ack",
                "sequence": 1,
                "success": True,
                "data": {"pages": [{"page_id": "page-1", "active": True}]},
            },
        )

        self.assertEqual(self.owner.json_messages[-1]["data"]["pages"][0]["page_id"], "page-1")
        self.assertEqual(viewer.json_messages, [])

    async def test_read_only_stream_rejects_control(self):
        await self.registry.close_all()
        self.registry = LiveStreamRegistry()
        read_only_claims = {**stream_claims(), "read_only": True}
        viewer = FakeConsumer()
        viewer_id, _ = await self.registry.register_subscriber(read_only_claims, viewer)

        with self.assertRaisesRegex(RuntimeError, "只读"):
            await self.registry.acquire_control("stream-1", viewer_id)


class LiveStreamControlOwnershipContractTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = LiveStreamRegistry()
        self.owner = FakeConsumer()
        self.viewer = FakeConsumer()
        self.publisher = FakeConsumer()
        self.owner_id, _ = await self.registry.register_subscriber(
            stream_claims(),
            self.owner,
        )
        self.viewer_id, _ = await self.registry.register_subscriber(
            stream_claims(),
            self.viewer,
        )
        self.publisher_id = await self.registry.register_publisher(
            stream_claims(),
            self.publisher,
        )

    async def asyncTearDown(self):
        await self.registry.close_all()

    async def test_same_user_multiple_pages_have_only_one_controller(self):
        await self.registry.acquire_control("stream-1", self.owner_id)

        with self.assertRaisesRegex(RuntimeError, "已有其他用户正在控制"):
            await self.registry.acquire_control("stream-1", self.viewer_id)

    async def test_control_lease_can_renew_after_five_minutes(self):
        await self.registry.acquire_control("stream-1", self.owner_id)
        state = self.registry._streams["stream-1"]
        state.control_started_at = time.monotonic() - 600
        state.control_expires_at = time.monotonic() + 10

        lease = await self.registry.renew_control("stream-1", self.owner_id)

        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)
        self.assertGreater(state.control_expires_at, time.monotonic())

    async def test_idle_controller_can_be_replaced_on_demand(self):
        await self.registry.acquire_control("stream-1", self.owner_id)
        state = self.registry._streams["stream-1"]
        state.last_control_activity_at = (
                time.monotonic() - self.registry.CONTROL_IDLE_TAKEOVER_SECONDS - 1
        )

        lease = await self.registry.acquire_control("stream-1", self.viewer_id)

        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)
        self.assertEqual(state.controller_id, self.viewer_id)
        self.assertEqual(self.owner.json_messages[-1]["reason"], "idle_takeover")

    async def test_control_event_keeps_controller_active_for_competing_request(self):
        await self.registry.acquire_control("stream-1", self.owner_id)
        state = self.registry._streams["stream-1"]
        state.last_control_activity_at = 0
        await self.registry.relay_control(
            "stream-1",
            self.owner_id,
            {"event_type": "list_pages", "sequence": 1},
        )

        with self.assertRaisesRegex(RuntimeError, "已有其他用户正在控制"):
            await self.registry.acquire_control("stream-1", self.viewer_id)

        self.assertGreater(state.last_control_activity_at, 0)

    async def test_release_allows_another_viewer_to_take_control(self):
        await self.registry.acquire_control("stream-1", self.owner_id)
        await self.registry.release_control("stream-1", self.owner_id)

        lease = await self.registry.acquire_control("stream-1", self.viewer_id)

        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)
        self.assertEqual(self.owner.json_messages[-1]["type"], "control_stopped")
        self.assertEqual(self.owner.json_messages[-1]["reason"], "released")

    async def test_controller_disconnect_allows_another_viewer_to_take_control(self):
        await self.registry.acquire_control("stream-1", self.owner_id)
        await self.registry.remove_subscriber("stream-1", self.owner_id)

        lease = await self.registry.acquire_control("stream-1", self.viewer_id)

        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)

    async def test_expired_lease_allows_another_viewer_to_take_control(self):
        await self.registry.acquire_control("stream-1", self.owner_id)
        self.registry._streams["stream-1"].control_expires_at = 0
        await self.registry.cleanup_expired()

        lease = await self.registry.acquire_control("stream-1", self.viewer_id)

        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)

    async def test_different_user_cannot_join_another_users_stream(self):
        different_user = FakeConsumer()
        with self.assertRaisesRegex(RuntimeError, "令牌与当前会话不匹配"):
            await self.registry.register_subscriber(
                stream_claims(user_id=2),
                different_user,
            )

    async def test_different_user_slots_can_control_different_workspaces_simultaneously(self):
        second_stream_claims = stream_claims(
            stream_id="stream-2",
            user_id=2,
            execution_id="workspace-2",
        )
        second_viewer = FakeConsumer()
        second_viewer_id, _ = await self.registry.register_subscriber(
            second_stream_claims,
            second_viewer,
        )
        second_publisher = FakeConsumer()
        await self.registry.register_publisher(second_stream_claims, second_publisher)
        await self.registry.acquire_control("stream-1", self.owner_id)

        lease = await self.registry.acquire_control("stream-2", second_viewer_id)
        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)

    async def test_same_user_cannot_control_two_tabs_with_separate_streams(self):
        second_stream_claims = stream_claims(
            stream_id="stream-2",
            execution_id="workspace-1",
        )
        second_viewer = FakeConsumer()
        second_viewer_id, _ = await self.registry.register_subscriber(
            second_stream_claims,
            second_viewer,
        )
        await self.registry.register_publisher(second_stream_claims, FakeConsumer())
        await self.registry.acquire_control("stream-1", self.owner_id)

        with self.assertRaisesRegex(RuntimeError, "已有其他页面正在控制"):
            await self.registry.acquire_control("stream-2", second_viewer_id)

    async def test_idle_control_in_another_tab_can_be_replaced_on_demand(self):
        second_stream_claims = stream_claims(
            stream_id="stream-2",
            execution_id="workspace-1",
        )
        second_viewer = FakeConsumer()
        second_viewer_id, _ = await self.registry.register_subscriber(
            second_stream_claims,
            second_viewer,
        )
        await self.registry.register_publisher(second_stream_claims, FakeConsumer())
        await self.registry.acquire_control("stream-1", self.owner_id)
        self.registry._streams["stream-1"].last_control_activity_at = (
                time.monotonic() - self.registry.CONTROL_IDLE_TAKEOVER_SECONDS - 1
        )

        lease = await self.registry.acquire_control("stream-2", second_viewer_id)

        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)
        self.assertIsNone(self.registry._streams["stream-1"].controller_id)
        self.assertEqual(self.registry._streams["stream-2"].controller_id, second_viewer_id)
