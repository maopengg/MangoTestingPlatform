<template>
  <a-drawer
    v-model:visible="visible"
    :title="`${subject?.case_no || ''} ${subject?.title || ''} · 历史版本`"
    :width="920"
    :footer="false"
    @cancel="closeHistory"
  >
    <MangoPanelSpin :loading="historyLoading" class="mango-case-library__history-spin">
      <a-alert class="mango-case-library__history-notice" type="info">
        每条用例最多保留最近 20 个历史版本，超过后会自动清理最早版本。
      </a-alert>
      
      <div v-if="historyVersions.length" class="mango-case-library__history">
        <div class="mango-case-library__history-list">
          <button
            v-for="item in historyVersions"
            :key="item.id"
            type="button"
            class="mango-case-library__history-item"
            :class="{ 'is-active': item.id === activeHistory?.id }"
            @click="activeHistory = item"
          >
            <strong>V{{ item.version_no }}</strong>
            <span>{{ item.source_name }}</span>
            <small>{{ item.create_time || '-' }}</small>
            <small>{{ item.changed_by?.name || item.changed_by?.username || '系统' }}</small>
          </button>
        </div>
        <div v-if="activeHistory" class="mango-case-library__history-detail">
          <div class="mango-section-title">
            <span>V{{ activeHistory.version_no }} 快照</span>
            <a-tag>{{ activeHistory.source_name }}</a-tag>
          </div>
          <a-descriptions :column="2" bordered size="small">
            <a-descriptions-item label="用例编号">{{
              historySnapshot.case_no
            }}</a-descriptions-item>
            <a-descriptions-item label="优先级">{{
              enumLabel(enumStore.case_level, historySnapshot.priority)
            }}</a-descriptions-item>
            <a-descriptions-item label="测试类型">{{
              enumLabels(enumStore.manual_test_type, historySnapshot.test_types)
            }}</a-descriptions-item>
            <a-descriptions-item label="用例标题" :span="2">{{
              historySnapshot.title
            }}</a-descriptions-item>
            <a-descriptions-item label="项目产品">{{
              historySnapshot.project_product_name || `ID ${historySnapshot.project_product_id}`
            }}</a-descriptions-item>
            <a-descriptions-item label="模块">{{
              historySnapshot.module_path || `ID ${historySnapshot.module_id}`
            }}</a-descriptions-item>
            <a-descriptions-item label="分类一">{{
              historySnapshot.category_level_1 || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="分类二">{{
              historySnapshot.category_level_2 || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="分类三">{{
              historySnapshot.category_level_3 || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="负责人">{{
              historySnapshot.owner_name || `ID ${historySnapshot.owner_id}`
            }}</a-descriptions-item>
            <a-descriptions-item label="测试层级">{{
              enumLabel(enumStore.api_case_scenario_layer, historySnapshot.scenario_layer)
            }}</a-descriptions-item>
            <a-descriptions-item label="验证类型">{{
              enumLabel(enumStore.api_case_scenario_type, historySnapshot.scenario_type)
            }}</a-descriptions-item>
            <a-descriptions-item label="执行场景">{{
              enumLabels(enumStore.api_case_scenario_tag, historySnapshot.scenario_tags)
            }}</a-descriptions-item>
            <a-descriptions-item label="自动化状态">{{
              automationStatusLabel(historySnapshot.automation_status)
            }}</a-descriptions-item>
            <a-descriptions-item label="资产状态">{{
              enumLabel(enumStore.functional_case_status, historySnapshot.status)
            }}</a-descriptions-item>
            <a-descriptions-item label="自动化绑定" :span="2">{{
              formatAutomationBindings(historySnapshot.automation_bindings)
            }}</a-descriptions-item>
            <a-descriptions-item label="前置条件" :span="2">{{
              historySnapshot.precondition || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="测试场景" :span="2">{{
              historySnapshot.test_point || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="预期结果" :span="2">{{
              historySnapshot.expected_result || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="备注" :span="2">{{
              historySnapshot.remark || '-'
            }}</a-descriptions-item>
          </a-descriptions>
          <div class="mango-case-library__history-steps">
            <strong>测试步骤</strong>
            <div
              v-for="(step, index) in historySnapshot.test_steps || []"
              :key="index"
              class="mango-soft-panel"
            >
              <span>{{ index + 1 }}. {{ step.action || '-' }}</span>
              <span>预期：{{ step.expected || '-' }}</span>
            </div>
            <div v-if="!historySnapshot.test_steps?.length" class="mango-empty-state"
              >暂无测试步骤</div
            >
          </div>
        </div>
      </div>
      
    </MangoPanelSpin>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { getManualCaseVersions } from '@/api/functional-test'
  import type { ManualCaseVersion } from '@/api/functional-test/types'
  import { useEnum } from '@/store/modules/get-enum'
  import { AUTOMATION_STATUS_OPTIONS, formatAutomationBindings } from '../config'
  import type { CaseHistorySubject } from '../types'

  const props = defineProps<{ contextKey: string }>()
  const visible = ref(false)
  const subject = ref<CaseHistorySubject | null>(null)
  const historyVersions = ref<ManualCaseVersion[]>([])
  const activeHistory = ref<ManualCaseVersion | null>(null)
  const historyLoading = ref(false)
  const loadError = ref(false)
  const enumStore = useEnum()
  const historySnapshot = computed(() => activeHistory.value?.snapshot ?? {})
  let active = true
  let requestSequence = 0

  function closeHistory() {
    ++requestSequence
    visible.value = false
    subject.value = null
    historyVersions.value = []
    activeHistory.value = null
    historyLoading.value = false
    loadError.value = false
  }

  async function open(record: CaseHistorySubject) {
    if (!active) return
    closeHistory()
    subject.value = { id: record.id, title: record.title, case_no: record.case_no }
    visible.value = true
    await loadHistory()
  }

  async function loadHistory() {
    if (!active || !visible.value || !subject.value) return
    const id = subject.value.id
    const request = ++requestSequence
    const current = () =>
      active && visible.value && subject.value?.id === id && request === requestSequence
    historyLoading.value = true
    loadError.value = false
    try {
      const response = await getManualCaseVersions(id)
      if (current()) {
        historyVersions.value = response.data ?? []
        activeHistory.value =
          historyVersions.value.find((item) => item.id === activeHistory.value?.id) ??
          historyVersions.value[0] ??
          null
      }
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current()) historyLoading.value = false
    }
  }

  function enumLabel(
    options: ReadonlyArray<{ key: string | number; title: string }> = [],
    value: string | number | undefined
  ) {
    if (value === undefined || value === null || value === '') return '-'
    return options.find((item) => String(item.key) === String(value))?.title ?? String(value)
  }
  const enumLabels = (
    options: ReadonlyArray<{ key: string | number; title: string }> = [],
    values: Array<string | number> = []
  ) => (values.length ? values.map((value) => enumLabel(options, value)).join('、') : '-')
  const automationStatusLabel = (value?: string) =>
    AUTOMATION_STATUS_OPTIONS.find((item) => item.value === value)?.label ?? value ?? '-'

  watch(() => props.contextKey, closeHistory, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    closeHistory()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    closeHistory()
  })
  defineExpose({ open })
</script>

<style scoped lang="less">
  .mango-case-library__history-spin {
    width: 100%;
    min-height: 320px;
  }
  .mango-case-library__history-notice {
    margin-bottom: 10px;
  }
  .mango-case-library__history {
    display: grid;
    grid-template-columns: 190px minmax(0, 1fr);
    gap: var(--m-page-gap);
    min-height: 520px;
  }
  .mango-case-library__history-list,
  .mango-case-library__history-detail,
  .mango-case-library__history-steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mango-case-library__history-list {
    overflow: auto;
    padding-right: 4px;
    border-right: 1px solid var(--m-border);
  }
  .mango-case-library__history-item {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 8px;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    background: var(--m-surface);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.2s ease, background-color 0.2s ease;
  }
  .mango-case-library__history-item:hover,
  .mango-case-library__history-item:focus-visible,
  .mango-case-library__history-item.is-active {
    border-color: var(--m-primary);
    background: var(--m-surface-soft);
    outline: none;
  }
  .mango-case-library__history-item small {
    color: var(--m-text-3);
  }
  .mango-case-library__history-detail {
    min-width: 0;
  }
  .mango-case-library__history-steps {
    margin-top: 4px;
  }
  .mango-case-library__history-steps .mango-soft-panel {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 8px;
  }
</style>
