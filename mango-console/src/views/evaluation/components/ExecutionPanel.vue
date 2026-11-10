<template>
  <section
    class="mango-case-execution-panel"
    :class="{
      'mango-case-execution-panel--history': history,
      'mango-case-execution-panel--flat': flat,
    }"
  >
    <template v-if="history">
      
      <div class="mango-evaluation-history">
        <aside class="mango-evaluation-history-sidebar"
          ><ExecutionHistoryList
            :items="historyItems"
            :selected-id="selectedHistoryId"
            :loading="historyLoading"
            @select="selectedHistoryId = Number($event)"
        /></aside>
        <div class="mango-evaluation-history-detail">
          <EvaluationItemBrowser
            v-if="selectedHistoryId"
            :case-id="caseId"
            :execution-id="selectedHistoryId"
            :initial-item-id="selectedHistoryId === executionId ? initialItemId : undefined"
            :dataset-name="datasetName"
            :dataset-id="datasetId"
          />
          <div v-else class="mango-empty-state">请选择执行记录</div>
        </div>
      </div>
    </template>
    <template v-else>
      <section class="mango-section-card mango-execution-card" aria-label="执行概况">
        <div class="mango-section-title mango-execution-card-title mango-execution-heading"
          ><div class="mango-execution-identity"
            ><h3 class="mango-execution-item-heading">执行概况</h3
            ><span :title="record?.execution_no">{{
              record?.execution_no || '当前环境尚未执行'
            }}</span></div
          ><a-space wrap>
            <a-button v-if="record" size="small" @click="snapshotVisible = true">执行快照</a-button>
            <a-button
              v-if="record && !isTerminal(record.status)"
              size="small"
              status="danger"
              :loading="stopping"
              @click="stop"
              >停止</a-button
            >
            <a-button
              v-if="
                record &&
                isTerminal(record.status) &&
                (record.summary?.failed || record.summary?.invalid || record.summary?.warning)
              "
              size="small"
              :loading="retrying"
              @click="retry"
              >重试失败条目</a-button
            >
          </a-space></div
        >
        <MangoPanelSpin :loading="recordLoading" class="mango-execution-record-spin">
          
          <div v-if="!record" class="mango-empty-state"
            >此 Case 在当前环境尚无执行结果，可从“执行”开始。</div
          >
          <template v-else>
            <a-descriptions :column="2" size="small" class="mango-execution-summary">
              <a-descriptions-item label="状态"
                ><a-tag size="small" :color="statusColor(record.status)">{{
                  enumTitle('evaluation_execution_status', record.status)
                }}</a-tag>
                {{ record.progress }}%</a-descriptions-item
              >
              <a-descriptions-item label="执行环境">{{ environmentTitle }}</a-descriptions-item>
              <a-descriptions-item label="结论"
                ><a-tag size="small" :color="statusColor(record.verdict)">{{
                  enumTitle('evaluation_verdict', record.verdict)
                }}</a-tag></a-descriptions-item
              >
              <a-descriptions-item label="有效测次"
                >{{ record.summary?.valid ?? '-' }} /
                {{ record.summary?.total ?? '-' }}</a-descriptions-item
              >
              <a-descriptions-item label="通过率">{{
                percent(record.summary?.effect_pass_rate)
              }}</a-descriptions-item>
              <a-descriptions-item label="平均分">{{
                record.summary?.average_score ?? '-'
              }}</a-descriptions-item>
            </a-descriptions>
            <a-descriptions
              v-if="record.summary?.memory_qa"
              :column="2"
              size="small"
              class="mango-execution-summary"
              ><a-descriptions-item
                v-for="(count, key) in record.summary.memory_qa.counts"
                :key="key"
                :label="enumTitle('evaluation_answer_verdict', key)"
                >{{ count }} 条 ·
                {{ percent(record.summary.memory_qa.rates[key]) }}</a-descriptions-item
              ></a-descriptions
            >
            <a-alert v-if="record.details?.error_message" type="error">{{
              record.details.error_message
            }}</a-alert>
            <a-alert v-if="record.snapshot?.selection?.scope === 'retry_subset'" type="warning"
              >这是失败子集重试，不能作为完整数据集的回归通过率。</a-alert
            >
          </template>
        </MangoPanelSpin>
        <section v-if="record?.summary?.ai_summary" class="mango-soft-panel">
          <h4 class="mango-execution-summary-heading">本次结果 AI 总结</h4>
          <template v-if="record.summary.ai_summary.status === 'completed'">
            <p>{{ record.summary.ai_summary.overview }}</p>
            <p v-for="finding in record.summary.ai_summary.findings" :key="finding">{{
              finding
            }}</p>
            <p v-for="tip in record.summary.ai_summary.recommendations" :key="tip">{{ tip }}</p>
          </template>
          <a-alert v-else type="warning"
            >总结生成失败，不影响评分结果。{{ record.summary.ai_summary.error_message }}</a-alert
          >
        </section>
      </section>
      <template v-if="!history">
        <section class="mango-section-card mango-execution-card" aria-label="条目结果">
          <div class="mango-section-title mango-execution-card-title mango-execution-item-toolbar"
            ><h3 class="mango-execution-item-heading">条目结果</h3
            ><div class="mango-execution-item-tools">
              <a-button
                v-if="record?.details?.workflow?.length"
                size="small"
                @click="workflowVisible = true"
                >查看执行流程</a-button
              >
              <a-form v-if="record" layout="inline" :model="{ verdictFilter }">
                <a-form-item label="效果结论"
                  ><a-select
                    v-model="verdictFilter"
                    :options="resultFilters"
                    multiple
                    :max-tag-count="1"
                    allow-clear
                    placeholder="全部结论"
                    size="small"
                    @change="filterItems"
                /></a-form-item>
              </a-form>
              <a-button
                v-if="true"
                size="small"
                :loading="gradingLoading || previewLoading"
                :disabled="recordLoading"
                @click="toggleGrading"
                >{{
                  showGrading ? '收起评分配置' : record ? '查看本次评分配置' : '预览评分配置'
                }}</a-button
              ></div
            ></div
          >
          <p v-if="showGrading" class="mango-grading-config-hint">{{
            record
              ? '以下评分配置来自本次执行快照，修改当前用例不会改变历史结果。'
              : '以下为当前用例的评分配置，尚未执行，不代表实际得分。'
          }}</p>
          
          
          <a-table
            :columns="displayColumns"
            :data="displayRows"
            :loading="itemsLoading || gradingLoading || previewLoading"
            :pagination="false"
            :scroll="{ x: record ? (showGrading ? 1760 : 1250) : 810 }"
            row-key="id"
            size="small"
          >
            <template #graders="{ record: item }"
              ><div
                v-for="(grader, index) in rowGraders(item)"
                :key="index"
                class="mango-grading-config-value"
                >{{ graderName(grader) }} @{{ formatVersion(grader.grader_version) }}</div
              ><span v-if="!rowGraders(item).length">—</span></template
            >
            <template #thresholds="{ record: item }"
              ><div
                v-for="(grader, index) in rowGraders(item)"
                :key="index"
                class="mango-grading-config-value"
                >{{ grader.threshold }}</div
              ><span v-if="!rowGraders(item).length">—</span></template
            >
            <template #weights="{ record: item }"
              ><div
                v-for="(grader, index) in rowGraders(item)"
                :key="index"
                class="mango-grading-config-value"
                >{{ grader.weight }}</div
              ><span v-if="!rowGraders(item).length">—</span></template
            >
            <template #gradingModes="{ record: item }"
              ><div
                v-for="(grader, index) in rowGraders(item)"
                :key="index"
                class="mango-grading-config-value"
                >{{ grader.hard_gate ? '必须通过' : '加权评分' }}</div
              ><span v-if="!rowGraders(item).length">—</span></template
            >
            <template #unexecuted><a-tag size="small">未执行</a-tag></template>
            <template #empty>{{
              record
                ? '暂无条目结果'
                : showGrading
                ? '暂无评分配置，请先在“用例配置”中完善后重试'
                : '尚无执行结果，可点击“预览评分配置”查看待测条目'
            }}</template>
            <template #verdict="{ record: item }"
              ><a-tag size="small" :color="statusColor(item.verdict)">{{
                enumTitle('evaluation_verdict', item.verdict)
              }}</a-tag></template
            >
            <template #executionStatus="{ record: item }"
              ><a-tag size="small" :color="statusColor(item.execution_status)">{{
                enumTitle('evaluation_item_execution_status', item.execution_status)
              }}</a-tag></template
            >
            <template #gradeStatus="{ record: item }"
              ><a-tag size="small" :color="statusColor(item.grade_status)">{{
                enumTitle('evaluation_grade_status', item.grade_status)
              }}</a-tag></template
            >
            <template #duration="{ record: item }"
              >{{ item.details?.timing?.execution_ms ?? '-' }} ms</template
            >
            <template #error="{ record: item }">{{
              item.details?.error_message ||
              skippedReasons[item.error_category] ||
              item.error_category ||
              '-'
            }}</template>
            <template #actions="{ record: item }"
              ><MangoTableActions
                :actions="[
                  {
                    label: '详情',
                    onClick: () => showItem(item.id),
                  },
                ]"
            /></template>
          </a-table>
          <TableFooter v-if="record" :pagination="itemPagination" />
        </section>
      </template>
    </template>
    <EvaluationDrawer
      v-model:visible="snapshotVisible"
      title="执行快照（JSON）"
      :width="900"
      :footer="false"
      unmount-on-close
      ><JsonDisplay :data="record?.snapshot" :show-drawer-button="false"
    /></EvaluationDrawer>
    <EvaluationDrawer
      v-model:visible="workflowVisible"
      title="本次执行流程"
      :width="900"
      :footer="false"
      unmount-on-close
      ><WorkflowResult v-if="record" :records="record.details?.workflow || []"
    /></EvaluationDrawer>
    <EvaluationDrawer
      v-model:visible="itemVisible"
      contained
      title="测评执行历史"
      :width="1300"
      :footer="false"
      unmount-on-close
    >
      <ExecutionPanel
        v-if="itemVisible && record"
        :case-id="caseId"
        :execution-id="record.id"
        :initial-item-id="selectedItemId"
        :dataset-name="datasetName"
        :dataset-id="datasetId"
        history
      />
    </EvaluationDrawer>
  </section>
</template>
<script setup lang="ts">
import { reportLoadError, runLoadRequest } from '@/utils/load-error'

  import { usePagePolling, type PollingContext } from '@/hooks/use-page-polling'
  import WorkflowResult from './WorkflowResult.vue'
  import EvaluationDrawer from './EvaluationDrawer.vue'
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import ExecutionHistoryList from '@/components/business/ExecutionHistoryList.vue'
  import { useEvaluationEnums } from './useEvaluationEnums'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import EvaluationItemBrowser from './EvaluationItemBrowser.vue'
  import { formatVersion } from './presentation'
  import {
    getLatestCaseExecution,
    getCaseExecution,
    getCaseExecutions,
    getCaseExecutionItems,
    getCaseExecutionItem,
    stopCaseExecution,
    retryCaseExecution,
  } from '@/api/evaluation'
  import { isTerminal } from '../case/config'
  import { itemColumns, gradingColumns, unexecutedColumns } from '../case/details/config'
  import { useEvaluationScope } from '../composables/useEvaluationScope'
  import type {
    ExecutionRecord,
    ItemResult,
    GraderBinding,
    GraderCatalogEntry,
    GradingPreview,
    ResultPage,
  } from '../types'
  const props = defineProps<{
    caseId: number
    executionId?: number
    initialItemId?: number
    history?: boolean
    flat?: boolean
    datasetName?: string
    datasetId?: number
    gradingPreview?: GradingPreview
    previewLoading?: boolean
    graderCatalog?: GraderCatalogEntry[]
  }>()
  const emit = defineEmits<{
    (event: 'selected', execution: number): void
    (event: 'preview'): void
  }>()
  const user = useUserStore()
  const workflowVisible = ref(false),
    showGrading = ref(false),
    gradingLoading = ref(false),
    gradingError = ref(false)
  const frozenGraders = ref<Record<number, GraderBinding[]>>({})
  const record = ref<ExecutionRecord | null>(null),
    itemRows = ref<ItemResult[]>([]),
    historyRows = ref<ExecutionRecord[]>([]),
    verdictFilter = ref<string[]>([])
  const selectedHistoryId = ref<number>(),
    selectedItemId = ref<number>(),
    itemVisible = ref(false),
    snapshotVisible = ref(false)
  const recordLoading = ref(false),
    itemsLoading = ref(false),
    historyLoading = ref(false),
    stopping = ref(false),
    retrying = ref(false)
  const recordError = ref(false),
    itemsError = ref(false),
    historyError = ref(false)
  let generation = 0,
    itemRequest = 0,
    historyRequest = 0,
    gradingRequest = 0
  const retryKeys = new Map<string, string>()
  const recordReads = new Set<number>()
  const displayColumns = computed(() =>
    record.value
      ? showGrading.value
        ? [itemColumns[0], ...gradingColumns, ...itemColumns.slice(1)]
        : itemColumns
      : unexecutedColumns
  )
  const displayRows = computed(() =>
    record.value
      ? itemRows.value
      : showGrading.value
      ? (props.gradingPreview?.items || []).map((item) => ({
          ...item,
          id: item.item_id,
          dataset_item_id: item.item_id,
        }))
      : []
  )
  function rowGraders(item: { id: number; graders?: GraderBinding[] }): GraderBinding[] {
    return record.value ? frozenGraders.value[item.id] || [] : item.graders || []
  }
  function graderName(grader: GraderBinding) {
    return (
      props.graderCatalog?.find(
        (entry) =>
          entry.grader_key === grader.grader_key &&
          Number(entry.grader_version) === Number(grader.grader_version)
      )?.name || grader.grader_key
    )
  }
  const { title: enumTitle, color: statusColor, options: enumOptions } = useEvaluationEnums()
  const resultFilters = computed(() => enumOptions('evaluation_verdict'))
  const environmentTitle = computed(() =>
    Number(user.selected_environment) === Number(record.value?.test_env)
      ? user.selected_environment_title || record.value?.test_env
      : record.value?.test_env
  )
  const historyItems = computed(() =>
    historyRows.value.map((item) => ({
      id: item.id,
      title: item.execution_no,
      sourceText: item.execution_no,
      time: item.create_time,
      statusText: enumTitle('evaluation_verdict', item.verdict),
      statusColor: statusColor(item.verdict),
      latest: item.id === historyRows.value[0]?.id,
    }))
  )
  const skippedReasons: Record<string, string> = {
    critical_gate_stopped: '硬门禁未通过，后续条目未执行',
    execution_stopped: '执行已停止，条目未执行',
  }
  const itemPagination = reactive({
    page: 1,
    pageSize: 10,
    pageCount: 0,
    pageSizes: [10, 20, 50],
    showSizePicker: true,
    onChange: () => loadItems(),
  })
  const percent = (value: number | null | undefined) =>
    value == null ? '-' : `${(value * 100).toFixed(1)}%`
  const pagePolling = usePagePolling(
    (context) =>
      props.history ? undefined : loadRecord(record.value?.id || props.executionId, true, context),
    () => {
      ++generation
      ++itemRequest
      ++gradingRequest
      recordLoading.value = false
      itemsLoading.value = false
      gradingLoading.value = false
    }
  )
  const scope = useEvaluationScope(
    () => [props.caseId, props.executionId, props.history],
    reset,
    resume
  )
  function reset() {
    pagePolling.stop()
    ++generation
    ++itemRequest
    ++historyRequest
    ++gradingRequest
    record.value = null
    itemRows.value = []
    historyRows.value = []
    frozenGraders.value = {}
    showGrading.value = false
    gradingLoading.value = false
    gradingError.value = false
    recordLoading.value = false
    itemsLoading.value = false
    historyLoading.value = false
    recordError.value = false
    itemsError.value = false
    historyError.value = false
    selectedHistoryId.value = undefined
    selectedItemId.value = undefined
    itemVisible.value = false
    snapshotVisible.value = false
    workflowVisible.value = false
    itemPagination.page = 1
    itemPagination.pageCount = 0
    verdictFilter.value = []
  }
  function resume() {
    if (!Number.isSafeInteger(props.caseId) || props.caseId <= 0) return
    if (props.history) void loadHistory()
    else {
      pagePolling.start()
      void loadRecord(props.executionId)
    }
  }
  async function loadFrozenGraders() {
    if (!scope.isActive()) return false
    const request = ++gradingRequest,
      execution = record.value?.id,
      version = scope.snapshot()
    if (!execution) return false
    const bindings = record.value?.snapshot?.grader_bindings || {}
    const missing = itemRows.value.filter(
      (item) => !Object.prototype.hasOwnProperty.call(frozenGraders.value, item.id)
    )
    gradingLoading.value = Boolean(missing.length)
    gradingError.value = false
    if (!missing.length) return true
    try {
      const caseId = props.caseId
      const responses = await Promise.allSettled(
        missing.map(async (item) => {
          const response: { data?: ItemResult } = await getCaseExecutionItem(
            caseId,
            execution,
            item.id
          )
          if (!response.data) throw Error('条目结果为空')
          return [
            item.id,
            (response.data.item_snapshot?.effective_graders || [])
              .map((ref) => bindings[ref.binding_hash])
              .filter((binding): binding is GraderBinding => Boolean(binding)),
          ] as const
        })
      )
      if (!scope.current(version) || request !== gradingRequest || record.value?.id !== execution)
        return false
      frozenGraders.value = {
        ...frozenGraders.value,
        ...Object.fromEntries(
          responses.flatMap((result) => (result.status === 'fulfilled' ? [result.value] : []))
        ),
      }
      gradingError.value = responses.some((result) => result.status === 'rejected')
      return !gradingError.value
    } finally {
      if (request === gradingRequest) gradingLoading.value = false
    }
  }
  function toggleGrading() {
    if (!scope.isActive()) return
    showGrading.value = !showGrading.value
    if (!showGrading.value) {
      ++gradingRequest
      gradingLoading.value = false
      return
    }
    if (record.value) void loadFrozenGraders()
    else emit('preview')
  }
  async function loadRecord(id?: number, silent = false, context?: PollingContext) {
    if (!scope.isActive()) return false
    const version = scope.snapshot()
    if (recordReads.has(version)) return false
    recordReads.add(version)
    const request = ++generation,
      caseId = props.caseId,
      environment = user.selected_environment
    let loaded = false
    if (!silent) {
      recordLoading.value = true
      recordError.value = false
    }
    try {
      const response: { data?: ExecutionRecord | null } = id
        ? await runLoadRequest(silent, () => getCaseExecution(caseId, id))
        : await runLoadRequest(silent, () => getLatestCaseExecution(caseId, environment ? Number(environment) : undefined))
      if (!scope.current(version) || request !== generation || (context && !context.isCurrent()))
        return false
      if (record.value?.id !== response.data?.id) {
        frozenGraders.value = {}
        ++gradingRequest
        gradingLoading.value = false
        itemVisible.value = false
        snapshotVisible.value = false
        workflowVisible.value = false
        itemPagination.page = 1
      }
      record.value = response.data || null
      recordError.value = false
      // The overview is ready independently of the item list.
      if (!silent) recordLoading.value = false
      loaded = await loadItems(silent, context)
      return loaded
    } catch (loadFailure0) {
      if (scope.current(version) && request === generation && !silent) (reportLoadError(loadFailure0, "加载失败，请重试", silent), recordError.value = true)
      return false
    } finally {
      recordReads.delete(version)
      if (request === generation) {
        recordLoading.value = false
        if (
          !props.history &&
          scope.current(version) &&
          (!loaded || (record.value && !isTerminal(record.value.status)))
        )
          pagePolling.start()
        else pagePolling.stop()
      }
    }
  }
  async function loadItems(silent = false, context?: PollingContext) {
    if (!scope.isActive()) return false
    const request = ++itemRequest,
      id = record.value?.id,
      version = scope.snapshot()
    if (!id) {
      itemRows.value = []
      itemsLoading.value = false
      return true
    }
    if (!silent) {
      itemsLoading.value = true
      itemsError.value = false
    }
    try {
      const response: ResultPage<ItemResult> = await runLoadRequest(silent, () => getCaseExecutionItems(props.caseId, id, {
        page: itemPagination.page,
        pageSize: itemPagination.pageSize,
        verdict__in: verdictFilter.value.length ? verdictFilter.value.join(',') : undefined,
      }))
      if (
        !scope.current(version) ||
        request !== itemRequest ||
        record.value?.id !== id ||
        (context && !context.isCurrent())
      )
        return false
      itemRows.value = response.data?.items || []
      itemPagination.pageCount = response.data?.count || 0
      itemsError.value = false
      if (showGrading.value && !silent) await loadFrozenGraders()
      return true
    } catch (loadFailure1) {
      if (scope.current(version) && request === itemRequest && !silent) (reportLoadError(loadFailure1, "加载失败，请重试", silent), itemsError.value = true)
      return false
    } finally {
      if (request === itemRequest && !silent) itemsLoading.value = false
    }
  }
  async function loadHistory() {
    if (!scope.isActive()) return false
    const request = ++historyRequest,
      version = scope.snapshot(),
      caseId = props.caseId,
      environment = user.selected_environment
    historyLoading.value = true
    historyError.value = false
    try {
      const response: ResultPage<ExecutionRecord> = await getCaseExecutions(caseId, {
        page: 1,
        pageSize: 20,
        test_env: environment || undefined,
      })
      if (!scope.current(version) || request !== historyRequest) return false
      historyRows.value = response.data?.items || []
      if (
        !selectedHistoryId.value &&
        props.executionId &&
        !historyRows.value.some((item) => item.id === props.executionId)
      ) {
        try {
          const selected: { data?: ExecutionRecord } = await getCaseExecution(
            caseId,
            props.executionId
          )
          if (!scope.current(version) || request !== historyRequest) return false
          if (selected.data && Number(selected.data.test_env) === Number(environment))
            historyRows.value.push(selected.data)
        } catch (loadFailure2) {
          if (scope.current(version) && request === historyRequest) (reportLoadError(loadFailure2, "加载失败，请重试", false), historyError.value = true)
        }
      }
      const preferred = selectedHistoryId.value || props.executionId
      selectedHistoryId.value = historyRows.value.some((item) => item.id === preferred)
        ? preferred
        : historyRows.value[0]?.id
      return true
    } catch (loadFailure3) {
      if (scope.current(version) && request === historyRequest) (reportLoadError(loadFailure3, "加载失败，请重试", false), historyError.value = true)
      return false
    } finally {
      if (request === historyRequest) historyLoading.value = false
    }
  }
  function refresh() {
    return loadRecord(record.value?.id || props.executionId)
  }
  function filterItems() {
    itemPagination.page = 1
    ++gradingRequest
    gradingLoading.value = false
    return loadItems()
  }
  function select(id: number) {
    if (!scope.isActive()) return
    itemPagination.page = 1
    itemRows.value = []
    selectedItemId.value = undefined
    emit('selected', id)
    void loadRecord(id)
  }
  function showItem(id: number) {
    if (scope.isActive()) {
      selectedItemId.value = id
      itemVisible.value = true
    }
  }
  async function stop() {
    if (!scope.isActive() || !record.value || stopping.value || retrying.value) return false
    const caseId = props.caseId,
      execution = record.value.id,
      version = scope.snapshot()
    stopping.value = true
    try {
      await stopCaseExecution(caseId, execution)
      if (scope.current(version) && record.value?.id === execution) {
        await refresh()
        return true
      }
      return false
    } catch {
      return false
    } finally {
      stopping.value = false
    }
  }
  async function retry() {
    if (!scope.isActive() || !record.value || retrying.value || stopping.value) return false
    const caseId = props.caseId,
      execution = record.value.id,
      version = scope.snapshot()
    const retryScope = `${user.userId}:${user.roleId}:${caseId}:${execution}:${user.selected_environment}`
    if (!retryKeys.has(retryScope)) retryKeys.set(retryScope, crypto.randomUUID())
    const key = retryKeys.get(retryScope)!
    retrying.value = true
    try {
      const response: { data: { id: number } } = await retryCaseExecution(caseId, execution, key)
      if (retryKeys.get(retryScope) === key) retryKeys.delete(retryScope)
      if (!scope.current(version) || record.value?.id !== execution) return false
      Message.success('已提交失败子集重试')
      select(response.data.id)
      return true
    } catch {
      return false
    } finally {
      retrying.value = false
    }
  }
  scope.start()
</script>
<style scoped>
  .mango-case-execution-panel {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-execution-card {
    padding: var(--m-card-padding);
    min-width: 0;
    margin-top: 0;
    box-shadow: none;
  }
  .mango-case-execution-panel--flat > .mango-execution-card {
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
  }
  .mango-case-execution-panel--flat > .mango-execution-card + .mango-execution-card {
    padding-top: var(--m-card-padding);
    border-top: 1px solid var(--m-border);
  }
  .mango-case-execution-panel--flat .mango-execution-summary {
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-sm);
  }
  .mango-case-execution-panel--flat .mango-empty-state {
    background: var(--m-surface-soft);
    border: 0;
  }
  .mango-execution-card-title {
    margin: 0 0 12px;
    font-size: 14px;
    align-items: center;
    flex-wrap: wrap;
  }
  .mango-execution-item-tools {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    flex: 0 1 auto;
    gap: var(--m-page-gap);
    min-width: 0;
    font-weight: 400;
  }
  .mango-execution-item-toolbar {
    flex-wrap: wrap;
  }
  .mango-execution-item-tools :deep(.arco-form) {
    width: auto;
    flex: 0 0 auto;
  }
  .mango-execution-item-heading {
    margin: 0;
    font-size: var(--m-font-body);
    line-height: var(--m-line-body);
    font-weight: 600;
    white-space: nowrap;
  }
  .mango-execution-summary-heading {
    margin: 0 0 var(--m-space-sm);
    color: var(--m-text-2);
    font-size: var(--m-font-body);
    line-height: var(--m-line-body);
    font-weight: 500;
  }
  .mango-execution-item-tools :deep(.arco-form-item) {
    margin: 0;
  }
  .mango-execution-item-tools :deep(.arco-select) {
    width: 160px;
  }
  .mango-grading-config-hint {
    color: var(--m-muted);
    margin: 0 0 var(--m-page-gap);
  }
  .mango-grading-config-value {
    min-height: 24px;
    line-height: 24px;
    white-space: nowrap;
  }
  .mango-execution-record-spin {
    width: 100%;
  }
  .mango-execution-heading {
    flex-wrap: wrap;
    align-items: center;
    padding-bottom: var(--m-page-gap);
    border-bottom: 1px solid var(--m-border);
  }
  .mango-execution-identity {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-execution-identity > span {
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-execution-summary {
    padding: var(--m-page-gap);
    background: var(--m-surface);
  }
  .mango-evaluation-history {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: var(--m-page-gap);
    min-height: 0;
    flex: 1;
  }
  .mango-case-execution-panel--history {
    height: 100%;
    min-height: 0;
  }
  .mango-evaluation-history-sidebar {
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .mango-evaluation-history-sidebar > :deep(.mango-execution-history-list) {
    flex: 1;
  }
  .mango-evaluation-history-detail {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    container-type: inline-size;
  }
  @container (max-width: 900px) {
    .mango-evaluation-history {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: minmax(160px, 30%) minmax(0, 1fr);
    }
  }
</style>
