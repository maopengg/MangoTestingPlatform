from pathlib import Path

from django.test import SimpleTestCase

REPOSITORY_ROOT = Path(__file__).resolve().parents[6]


class UiFrontendProgressContractTest(SimpleTestCase):
    def test_page_step_list_requests_all_steps_after_navigation_initializes(self):
        source = (
                REPOSITORY_ROOT / "mango-console/src/views/uitest/page-steps/index.vue"
        ).read_text(encoding="utf-8")

        workbench = source.split("<ProjectProductNavigationWorkbench", 1)[1].split(
            ">", 1
        )[0]
        self.assertIn("emit-initial-filter", workbench)
        self.assertIn('@filter-change="onSidebarFilterChange"', workbench)
        self.assertIn("getUiSteps(value)", source)

    def test_page_step_canvas_consumes_incremental_results(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("handleStepResultMessage", source)
        self.assertIn("mango:websocket-message", source)
        self.assertIn("data.result_data = result", source)

    def test_embedded_page_step_also_listens_for_element_check_results(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/index.vue"
        ).read_text(encoding="utf-8")

        mounted = source.split("onMounted(async () => {", 1)[1].split(
            "watch(", 1
        )[0]
        unmounted = source.split("onBeforeUnmount(() => {", 1)[1].split(
            "</script>", 1
        )[0]
        self.assertIn(
            "window.addEventListener('mango:websocket-message', handleStepResultMessage)",
            mounted,
        )
        self.assertNotIn("if (!props.caseInputMode)", mounted.split("await doRefreshSteps", 1)[0])
        self.assertIn(
            "window.removeEventListener('mango:websocket-message', handleStepResultMessage)",
            unmounted,
        )

    def test_single_step_progress_uses_one_expected_node(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("await prepareDebugPolling(executableNodeCount.value)", source)
        self.assertIn("await prepareDebugPolling(1)", source)
        self.assertIn("debugExpectedNodeCount.value", source)
        self.assertIn("const total = debugExpectedNodeCount.value", source)

    def test_page_step_polling_retries_network_failures_without_ending_task(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("function scheduleDebugPolling", source)
        self.assertIn("DEBUG_POLL_MAX_BACKOFF_MS", source)
        self.assertIn("Math.min(", source)
        self.assertIn("scheduleDebugPolling(retryDelay)", source)
        poll_handler = source.split("async function pollDebugResult()", 1)[1].split(
            "function applyRuntimeStepRecord", 1
        )[0]
        catch_handler = poll_handler.split("} catch (error) {", 1)[1].split(
            "} finally {", 1
        )[0]
        self.assertIn("debugPollFailures.value += 1", catch_handler)
        self.assertNotIn("stopDebugPolling()", catch_handler)
        self.assertNotIn("setInterval(pollDebugResult", source)

    def test_node_copy_shortcuts_only_capture_after_explicit_node_click(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/FlowChart.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("const shortcutNodeId = ref('')", source)
        self.assertIn('@pointerdown.capture="activateNodeShortcut(id)"', source)
        self.assertIn("activateNodeShortcut(event.node.id)", source)
        self.assertIn("shortcutNodeId.value = nodeId", source)
        self.assertIn("if (!shortcutNodeId.value || !getLegacyNode(shortcutNodeId.value)) return", source)
        self.assertIn("window.getSelection()?.toString()", source)
        self.assertIn("handleShortcutPointerDown", source)
        self.assertIn("!target.closest('.vue-flow__node')", source)

    def test_node_popover_opens_only_after_pointer_stays_still_for_one_second(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/FlowChart.vue"
        ).read_text(encoding="utf-8")

        self.assertIn('@mouseenter="startNodePopoverTimer(id)"', source)
        self.assertIn('@mousemove="restartNodePopoverTimer(id)"', source)
        self.assertIn('@mouseleave="hideNodePopover(id)"', source)
        self.assertIn('@mouseenter="keepNodePopover(id)"', source)
        restart_handler = source.split('function restartNodePopoverTimer', 1)[1].split(
            'function keepNodePopover', 1
        )[0]
        self.assertIn('startNodePopoverTimer(nodeId)', restart_handler)
        start_handler = source.split('function startNodePopoverTimer', 1)[1].split(
            'function restartNodePopoverTimer', 1
        )[0]
        self.assertIn('}, 1000)', start_handler)
        hide_handler = source.split('function hideNodePopover', 1)[1].split(
            'function clearNodePopoverTimer', 1
        )[0]
        self.assertIn('setTimeout', hide_handler)
        self.assertIn('}, 50)', hide_handler)
        self.assertIn("activePopoverNodeId.value = ''", hide_handler)

    def test_only_active_runtime_edge_is_animated(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/FlowChart.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("animated: runtimeStatus === 'running'", source)
        self.assertIn("getActiveRuntimeNodeId", source)
        self.assertNotIn(
            "props.debugRunning ? 'flow-edge-running'",
            source,
        )

    def test_case_page_consumes_lightweight_node_progress(self):
        page = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/index.vue").read_text(encoding="utf-8")
        runtime = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/composables/useCaseRuntimeResults.ts").read_text(encoding="utf-8")
        self.assertIn("useCaseRuntimeResults", page)
        self.assertIn("u_page_step_node_progress", runtime)
        self.assertIn("acceptNode(data.func_args)", runtime)
        self.assertIn("if (!current()) return", runtime)


    def test_case_execution_resets_pending_states_and_only_polls_while_running(self):
        page = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/index.vue").read_text(encoding="utf-8")
        reset = page.split("function resetCaseRuntimeState(executionId: string)", 1)[1].split("function refreshCaseRecord", 1)[0]
        self.assertIn("resetCaseResults(executionId)", reset)
        self.assertIn("status: 2, error_message: null", reset)
        self.assertIn("caseSteps.value.some(isPendingExecution)", page)
        self.assertIn("loadCaseSteps(showLoading, context?.isCurrent)", page)
        polling = (REPOSITORY_ROOT / "mango-console/src/utils/page-polling.ts").read_text(encoding="utf-8")
        self.assertIn("[2, 3].includes(Number(record?.status))", polling)


    def test_case_runtime_status_cannot_regress_when_a_stale_list_response_arrives(self):
        rows = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/step-list.ts").read_text(encoding="utf-8")
        loader = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/composables/useCaseStepList.ts").read_text(encoding="utf-8")
        self.assertIn("[0, 1].includes(current.status) ? current.status", rows)
        self.assertIn("current.status === 3 && incomingTerminal", rows)
        self.assertIn("current.status === 3 || row.status === 3", rows)
        self.assertIn("request === sequence", loader)
        self.assertIn("if (!current()) return", loader)
        self.assertIn("options.running() ? mergeActiveCaseSteps(incoming, rows.value) : incoming", loader)


    def test_case_polling_notifies_each_terminal_task_only_once(self):
        execution = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/composables/useCaseExecution.ts").read_text(encoding="utf-8")
        notify = execution.split("function notify(job: Job", 1)[1].split("async function poll(job: Job)", 1)[0]
        self.assertIn("if (!claimExecutorTaskNotification(job.taskId)) return", notify)
        for kind in ("success", "warning", "error"):
            self.assertIn(f"Notification.{kind}", notify)
        self.assertIn("job.handled = true", execution)
        self.assertIn("notify(job, task)", execution)


    def test_case_canvas_prefers_case_result_and_does_not_wait_twice_to_close_live(self):
        page = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/index.vue").read_text(encoding="utf-8")
        live = (REPOSITORY_ROOT / "mango-console/src/views/uitest/case/details/composables/useCaseLiveStream.ts").read_text(encoding="utf-8")
        step = (REPOSITORY_ROOT / "mango-console/src/views/uitest/page-steps/details/index.vue").read_text(encoding="utf-8")
        self.assertIn("if (current()) caseLive.finish(caseExecutionId.value)", page)
        finish = live.split("function finish(completedExecutionId: string)", 1)[1].split("function pause()", 1)[0]
        self.assertIn("completedExecutionId !== executionId.value", finish)
        self.assertIn("close()", finish)
        self.assertNotIn("setTimeout", finish)
        self.assertIn("props.caseInputMode ? props.caseResult?.status : currentStepRecord.value?.status", step)


    def test_page_step_element_ai_heal_reuses_shared_panel(self):
        step_source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/index.vue"
        ).read_text(encoding="utf-8")
        panel_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementAiHealPanel.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("AI自愈", step_source)
        self.assertIn("v-if=\"hasSelectedNodeElement\"", step_source)
        self.assertIn("openSelectedElementAiHeal", step_source)
        self.assertIn("<UiElementAiHealPanel", step_source)
        self.assertIn("getUiElementAiInfo", panel_source)
        self.assertIn("putUiElementAiHealApply", panel_source)
        self.assertIn("候选定位器", panel_source)
        self.assertIn("基线历史", panel_source)
        self.assertIn("自愈历史", panel_source)
        self.assertNotIn("调试数据", panel_source)

    def test_case_embedded_node_keeps_element_actions_for_name_only_cache(self):
        step_source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page-steps/details/index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "props.caseInputMode && getElementName(data.selectData?.ele_name) !== '-'",
            step_source,
        )
        lookup = step_source.split("async function loadSelectedNodeElement()", 1)[1].split("async function openSelectedElementEditPanel()", 1)[0]
        self.assertIn("uiCaseAssetId(data.selectData?.id)", lookup)
        self.assertIn("getUiPageStepsDetailedById(id)", lookup)
        self.assertIn("if (!current()) return null", lookup)
        self.assertIn("openSelectedElementEditPanel", step_source)
        self.assertIn("runSelectedElementDeepCheck", step_source)
        self.assertIn("openSelectedElementAiHeal", step_source)

    def test_baseline_history_exposes_structured_half_screen_detail(self):
        panel_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementAiHealPanel.vue"
        ).read_text(encoding="utf-8")
        detail_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementBaselineDetailPanel.vue"
        ).read_text(encoding="utf-8")
        api_source = (
                REPOSITORY_ROOT
                / "mango-console/src/api/uitest/element.ts"
        ).read_text(encoding="utf-8")

        self.assertIn("openSnapshotDetail(record)", panel_source)
        self.assertIn("<UiElementBaselineDetailPanel", panel_source)
        self.assertIn("width=\"50%\"", detail_source)
        self.assertIn("detailSections", detail_source)
        self.assertIn("jsonSections", detail_source)
        self.assertIn("htmlSections", detail_source)
        self.assertNotIn("<h3>完整数据</h3>", detail_source)
        self.assertIn("定位表达式", detail_source)
        self.assertIn("可访问性语义摘要", detail_source)
        self.assertIn("getUiElementAiSnapshotDetail", detail_source)
        self.assertIn("/ui/element/ai/snapshot/detail", api_source)

    def test_element_ai_panel_uses_split_history_endpoints(self):
        panel_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementAiHealPanel.vue"
        ).read_text(encoding="utf-8")
        api_source = (
                REPOSITORY_ROOT
                / "mango-console/src/api/uitest/element.ts"
        ).read_text(encoding="utf-8")

        self.assertIn("getUiElementAiSnapshots", panel_source)
        self.assertIn("getUiElementAiHealRecords", panel_source)
        self.assertIn("pageSize: 10", panel_source)
        self.assertIn("pageSize: 20", panel_source)
        self.assertIn("/ui/element/ai/snapshots", api_source)
        self.assertIn("/ui/element/ai/heal-records", api_source)

    def test_heal_history_exposes_structured_detail_without_duplicate_snapshot_card(self):
        panel_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementAiHealPanel.vue"
        ).read_text(encoding="utf-8")
        detail_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementHealRecordDetailPanel.vue"
        ).read_text(encoding="utf-8")
        api_source = (
                REPOSITORY_ROOT
                / "mango-console/src/api/uitest/element.ts"
        ).read_text(encoding="utf-8")

        self.assertNotIn("title: '最近快照'", panel_source)
        self.assertIn("openHealDetail(record)", panel_source)
        self.assertIn("<UiElementHealRecordDetailPanel", panel_source)
        self.assertIn('width="50%"', detail_source)
        self.assertIn('当前页面上下文', detail_source)
        self.assertIn('AI 输入摘要', detail_source)
        self.assertIn('候选定位器', detail_source)
        self.assertNotIn('<h3>完整数据</h3>', detail_source)
        self.assertIn('/ui/element/ai/heal-record/detail', api_source)

    def test_ai_detail_lists_use_structured_tables(self):
        baseline_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementBaselineDetailPanel.vue"
        ).read_text(encoding="utf-8")
        heal_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementHealRecordDetailPanel.vue"
        ).read_text(encoding="utf-8")
        structured_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/display/UiStructuredDataView.vue"
        ).read_text(encoding="utf-8")
        table_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/display/UiStructuredDataTable.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("label: '可访问性语义摘要'", baseline_source)
        self.assertIn("value: item.accessibility_digest || {}, structured: true", baseline_source)
        self.assertIn("label: '候选定位器'", heal_source)
        self.assertIn("value: item.candidates || [], structured: true", heal_source)
        self.assertIn('UiStructuredDataTable', structured_source)
        self.assertIn('v-for="column in columns"', table_source)
        self.assertIn('v-if="item.structured"', baseline_source)
        self.assertIn('v-if="item.structured"', heal_source)

    def test_element_locator_cards_use_soft_nested_surface(self):
        source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementEditPanel.vue"
        ).read_text(encoding="utf-8")

        locator_style = source.split('.mango-ui-element-locator-card {', 1)[1].split('}', 1)[0]
        self.assertIn('background: var(--m-surface-soft)', locator_style)
        self.assertIn('border-radius: var(--m-radius-lg)', locator_style)
        self.assertNotIn('var(--m-fill-1)', locator_style)
        locator_row_style = source.split('.mango-ui-element-locator-row {', 1)[1].split('}', 1)[0]
        self.assertIn('grid-template-columns: 210px minmax(0, 1fr) 170px', locator_row_style)

    def test_ai_heal_candidates_emphasize_success_and_collapse_failures(self):
        candidate_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementHealCandidatePanel.vue"
        ).read_text(encoding="utf-8")
        shared_panel_source = (
                REPOSITORY_ROOT
                / "mango-console/src/components/business/UiElementAiHealPanel.vue"
        ).read_text(encoding="utf-8")
        element_page_source = (
                REPOSITORY_ROOT
                / "mango-console/src/views/uitest/page/elements/index.vue"
        ).read_text(encoding="utf-8")

        self.assertIn('自愈成功：AI候选匹配', candidate_source)
        self.assertIn('诊断过程（', candidate_source)
        self.assertIn('verifiedRows', candidate_source)
        self.assertIn('failedRows', candidate_source)
        self.assertIn('{{ successText }}', candidate_source)
        self.assertIn('{{ emptyText }}', candidate_source)
        self.assertNotIn(':content="successText"', candidate_source)
        self.assertNotIn(':content="emptyText"', candidate_source)
        self.assertIn('提示词文本直查', shared_panel_source)
        self.assertIn('提示词文本直查', element_page_source)
        self.assertNotIn('AI提示词文本', shared_panel_source)
        self.assertNotIn('AI提示词文本', element_page_source)
