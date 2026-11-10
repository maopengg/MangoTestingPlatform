<template>
  <section class="mango-ui-report">
    <div class="mango-ui-report__hero">
      <div class="mango-ui-report__title-block">
        <div class="mango-ui-report__title-top">
          <span class="mango-ui-report__eyebrow">UI 执行明细</span>
          <a-button type="primary" size="medium" shape="square" @click="cachePanelVisible = true" data-testid="qa-components-reports-elementtestreport-button-查看缓存变量">
            查看缓存变量
          </a-button>
        </div>
        <div class="mango-ui-report__title-row">
          <h2>{{ resultData?.name || resultData?.case_name || 'UI 自动化执行结果' }}</h2>
          <a-tag :color="resultStatusColor" size="large">{{ resultStatusText }}</a-tag>
        </div>
        <p>
          <span v-if="resultData.test_time !== null && resultData.test_time !== ''">执行时间：{{ resultData.test_time }}</span>
          <span>测试对象：{{ resultData?.test_object || '-' }}</span>
        </p>
      </div>

      <div class="mango-ui-report__progress-card" :class="resultStatusClass">
        <span>操作通过率</span>
        <strong>{{ passRate }}%</strong>
        <div class="mango-ui-report__progress-track">
          <div class="mango-ui-report__progress-bar" :style="{ width: `${passRate}%` }"></div>
        </div>
      </div>
    </div>

    <div class="mango-ui-report__metrics">
      <div class="mango-ui-report__metric">
        <span>操作总数</span>
        <strong>{{ operationTotal }}</strong>
      </div>
      <div class="mango-ui-report__metric">
        <span>通过操作</span>
        <strong class="mango-ui-report__metric-value--success">{{ passedCount }}</strong>
      </div>
      <div class="mango-ui-report__metric">
        <span>失败操作</span>
        <strong class="mango-ui-report__metric-value--danger">{{ failedCount }}</strong>
      </div>
      <div class="mango-ui-report__metric">
        <span>未测试</span>
        <strong>{{ pendingCount }}</strong>
      </div>
    </div>

    <article v-if="firstFailedStep" class="mango-ui-report__focus">
      <div class="mango-ui-report__focus-head">
        <div>
          <span>失败定位</span>
          <h3>{{ stepName(firstFailedStep) }}</h3>
        </div>
        <a-tag color="red">失败</a-tag>
      </div>
      <div class="mango-ui-report__focus-grid">
        <div>
          <span>操作类型</span>
          <strong>{{ operationLabel(firstFailedStep) }}</strong>
        </div>
        <div>
          <span>错误提示</span>
          <a-tooltip :content="firstFailedStep?.error_message || firstFailedStep?.ass_msg || '-'">
            <strong>{{ firstFailedStep?.error_message || firstFailedStep?.ass_msg || '-' }}</strong>
          </a-tooltip>
        </div>
        <div v-if="firstFailedStep?.picture_path" class="mango-ui-report__focus-shot">
          <span>失败截图</span>
          <a-image :src="firstFailedPictureUrl" width="132" />
        </div>
      </div>
    </article>

    <div v-if="timelineRows.length === 0" class="mango-empty-state">暂无执行过程</div>
    <a-timeline v-else class="mango-ui-report__timeline">
      <a-timeline-item
        v-for="(row, index) in timelineRows"
        :key="timelineRowKey(row, index)"
        :label="timelineLabel(row.runtime, index)"
        :dot-color="timelineDotColor(row.runtime?.status)"
      >
        <div class="mango-ui-report__operation-item">
          <div class="mango-ui-report__timeline-head">
            <div class="mango-ui-report__timeline-title">
              <strong :title="runtimeResultName(row.runtime, row.step, row.runtimeIndex)">
                {{ runtimeResultName(row.runtime, row.step, row.runtimeIndex) }}
              </strong>
            </div>
            <div class="mango-ui-report__timeline-tags">
              <a-tag size="small" color="arcoblue">元素 {{ elementRows(row.runtime).length }}</a-tag>
              <a-tag size="small" :color="statusColor(row.runtime?.status)">
                {{ stepStatusText(row.runtime?.status) }}
              </a-tag>
            </div>
          </div>

          <UiStepRuntimeResult
            :result="row.runtime"
            :fallback-ope-key="row.runtime?.ope_key || row.step?.ope_key"
            :fallback-element-name="runtimeResultName(row.runtime, row.step, row.runtimeIndex)"
            empty-text="暂无执行结果"
            :image-width="220"
            frameless
            :show-header="false"
          />
        </div>
      </a-timeline-item>
    </a-timeline>

    <BaseSidePanel
      :visible="cachePanelVisible"
      title="缓存变量"
      width="50%"
      @update:visible="(val) => { cachePanelVisible = val }"
      @cancel="cachePanelVisible = false"
    >
      <div class="mango-ui-report__cache-panel">
        <template v-if="runtimeSections.length">
          <section
            v-for="section in runtimeSections"
            :key="section.key"
            class="mango-ui-report__cache-section"
          >
            <div class="mango-ui-report__cache-section-head">
              <strong>{{ section.title }}</strong>
              <span>{{ section.description }}</span>
            </div>
            <JsonDisplay :data="section.data" :show-drawer-button="false" :default-expanded="true" />
          </section>
        </template>
        <div v-else class="mango-empty-state">暂无缓存变量</div>
      </div>
    </BaseSidePanel>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch, onMounted, onBeforeUnmount, onDeactivated } from 'vue'
  import { useRoute } from 'vue-router'
  import { useUserStoreContext } from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { useArtifactUrl } from '@/hooks/use-artifact-url'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { normalizeUiReport, type UiRuntimeView } from './ui-report'

  const props = defineProps<{ resultData: unknown }>()
  const resultData = computed(() => normalizeUiReport(props.resultData))
  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()
  const route = useRoute()
  const user = useUserStoreContext()
  const cachePanelVisible = ref(false)
  const closeCachePanel = () => { cachePanelVisible.value = false }
  watch([
    () => props.resultData, () => route.fullPath, () => user.userId, () => user.roleId,
    () => user.token, () => user.selected_environment,
  ], closeCachePanel, { flush: 'sync' })
  function visibilityChanged() { if (globalThis.document?.visibilityState === 'hidden') closeCachePanel() }
  onMounted(() => globalThis.document?.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(closeCachePanel)
  onBeforeUnmount(() => {
    closeCachePanel()
    globalThis.document?.removeEventListener('visibilitychange', visibilityChanged)
  })
  const stepList = computed(() => resultData.value.steps)
  const timelineRows = computed(() => stepList.value.flatMap((step, stepIndex) =>
    step.runtimeRows.map((runtime, runtimeIndex) => ({ step, runtime, stepIndex, runtimeIndex }))
  ))
  interface TimelineRow { step: UiRuntimeView; runtime: UiRuntimeView; stepIndex: number; runtimeIndex: number }
  const operationTotal = computed(() => timelineRows.value.length)
  const passedCount = computed(() => timelineRows.value.filter(item => item.runtime.status === 1).length)
  const failedCount = computed(() => timelineRows.value.filter(item => item.runtime.status === 0).length)
  const pendingCount = computed(() => operationTotal.value - passedCount.value - failedCount.value)
  const passRate = computed(() => operationTotal.value ? Math.round(passedCount.value / operationTotal.value * 100) : 0)
  const firstFailedStep = computed(() => stepList.value.find(item => item.status === 0))
  const firstFailedPicturePath = computed(() => firstFailedStep.value?.picture_path || '')
  const firstFailedPictureUrl = useArtifactUrl(firstFailedPicturePath)
  const resultStatusType = computed(() => resultData.value.status === 1 ? 'success' : resultData.value.status === 0 ? 'danger' : 'muted')
  const resultStatusText = computed(() => resultData.value.status === 1 ? '测试通过' : resultData.value.status === 0 ? '测试失败' : '未测试')
  const resultStatusColor = computed(() => statusColor(resultData.value.status))
  const resultStatusClass = computed(() => `mango-ui-report__progress-card--${resultStatusType.value}`)
  const hasValue = (value: unknown): boolean => {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return true
  }
  const runtimeSections = computed(() => [
    { key: 'cache', title: '缓存数据', description: '本次 UI 执行过程中写入或读取的缓存上下文。', data: resultData.value.cache_data },
    { key: 'factory', title: '数据工厂', description: '数据工厂生成或注入到 UI 执行器的上下文。', data: resultData.value.data_factory_cache_data },
  ].filter(item => hasValue(item.data)))
  function operationLabel(item: UiRuntimeView): string {
    const label: unknown = useSelectValue.getSelectLabel(item.ope_key)
    return typeof label === 'string' && label ? label : enumStore.element_ope?.find(option => option.key === item.type)?.title || '-'
  }
  function stepName(item: UiRuntimeView): string {
    const label = operationLabel(item)
    return item.name || item.elementName || (label === '-' ? '未命名步骤' : label)
  }
  function stepStatusText(status: number | null): string {
    return status === 1 ? '通过' : status === 0 ? '失败' : '未测试'
  }
  function statusColor(status: number | null) {
    return status === 1 ? 'green' : status === 0 ? 'red' : 'gray'
  }
  const timelineDotColor = statusColor
  function timelineLabel(item: UiRuntimeView, _index: number): string {
    return String(item.stop_time ?? item.test_time ?? '').match(/\d{2}:\d{2}:\d{2}/)?.[0] || ''
  }
  function elementRows(item: UiRuntimeView) { return item.elements }
  function timelineRowKey(row: TimelineRow, _index: number): string {
    return `${row.stepIndex}-${row.runtimeIndex}-${row.runtime.id ?? row.runtime.page_step_details_id ?? ''}`
  }
  function runtimeResultName(runtime: UiRuntimeView, step: UiRuntimeView, index: number): string {
    const label = operationLabel(runtime)
    return runtime.name || runtime.elementName || (label === '-' ? `${stepName(step)}-${index + 1}` : label)
  }
</script>

<style scoped lang="less">
  .mango-ui-report {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
    color: var(--m-text);
  }

  .mango-ui-report__hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 180px;
    gap: 12px;
    align-items: stretch;
  }

  .mango-ui-report__title-block,
  .mango-ui-report__progress-card,
  .mango-ui-report__metric,
  .mango-ui-report__focus,
  .mango-ui-report__detail-panel {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-ui-report__title-block {
    min-width: 0;
    padding: 14px 16px;
  }

  .mango-ui-report__title-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .mango-ui-report__eyebrow,
  .mango-ui-report__progress-card span,
  .mango-ui-report__metric span,
  .mango-ui-report__focus-head span,
  .mango-ui-report__focus-grid span,
  .mango-ui-report__info-grid span,
  .mango-ui-report__element-row span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-ui-report__title-row {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
    margin-top: 4px;
  }

  .mango-ui-report__title-row h2 {
    min-width: 0;
    margin: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 18px;
    font-weight: 600;
    line-height: 26px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-report__title-block p {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin: 6px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-ui-report__progress-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 12px 14px;
    border-left-width: 4px;
  }

  .mango-ui-report__progress-card strong {
    margin-top: 4px;
    color: var(--m-text);
    font-size: 24px;
    line-height: 32px;
  }

  .mango-ui-report__progress-card--success {
    border-left-color: var(--m-success);
  }

  .mango-ui-report__progress-card--danger {
    border-left-color: var(--m-danger);
  }

  .mango-ui-report__progress-card--muted {
    border-left-color: var(--m-border-strong);
  }

  .mango-ui-report__progress-track {
    height: 6px;
    margin-top: 8px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-surface-soft);
  }

  .mango-ui-report__progress-bar {
    height: 100%;
    border-radius: inherit;
    background: var(--m-success);
    transition: width 0.2s ease;
  }

  .mango-ui-report__metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .mango-ui-report__metric {
    min-width: 0;
    padding: 10px 12px;
  }

  .mango-ui-report__metric strong {
    display: block;
    margin-top: 4px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 16px;
    line-height: 24px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-report__metric-value--success {
    color: var(--m-success) !important;
  }

  .mango-ui-report__metric-value--danger,
  .mango-ui-report__danger-text {
    color: var(--m-danger) !important;
  }

  .mango-ui-report__focus {
    padding: 12px;
    border-color: color-mix(in srgb, var(--m-danger) 34%, var(--m-border));
    background: color-mix(in srgb, var(--m-danger) 7%, var(--m-surface));
  }

  .mango-ui-report__focus-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-ui-report__focus-head h3 {
    margin: 2px 0 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-ui-report__focus-grid {
    display: grid;
    grid-template-columns: minmax(140px, 220px) minmax(0, 1fr) max-content;
    gap: 10px;
    align-items: start;
    padding-top: 10px;
  }

  .mango-ui-report__focus-grid strong,
  .mango-ui-report__info-grid strong,
  .mango-ui-report__element-row strong,
  .mango-ui-report__runtime-value {
    display: block;
    min-width: 0;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 500;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-report__focus-shot {
    min-width: 132px;
  }

  .mango-ui-report__timeline {
    margin-top: 4px;
  }

  .mango-ui-report__timeline :deep(.arco-timeline-item-label) {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-report__timeline :deep(.arco-timeline-item-content) {
    min-width: 0;
  }

  .mango-ui-report__operation-item {
    min-width: 0;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-ui-report__timeline-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 8px;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-ui-report__timeline-title {
    display: grid;
    min-width: 0;
    gap: 2px;
  }

  .mango-ui-report__timeline-title strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-report__timeline-tags {
    display: flex;
    flex-shrink: 0;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .mango-ui-report__cache-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-ui-report__cache-section {
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-ui-report__cache-section-head {
    display: grid;
    gap: 2px;
    padding-bottom: 8px;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-ui-report__cache-section-head strong {
    color: var(--m-text);
    font-size: 14px;
    line-height: 22px;
  }

  .mango-ui-report__cache-section-head span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-ui-report__detail-panel {
    min-width: 0;
    padding: 10px;
  }

  .mango-ui-report__section-head {
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-ui-report__section-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-ui-report__section-head p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 19px;
  }

  .mango-ui-report__info-grid {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mango-ui-report__info-wide,
  .mango-ui-report__screenshot-panel,
  .mango-ui-report__runtime-wide {
    grid-column: 1 / -1;
  }

  .mango-ui-report__danger-text {
    overflow: visible !important;
    white-space: normal !important;
    word-break: break-word;
  }

  .mango-ui-report__mono {
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  }

  .mango-ui-report__element-panel {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    max-height: 360px;
  }

  .mango-ui-report__element-list {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
    overflow: auto;
    padding-right: 2px;
  }

  .mango-ui-report__element-card {
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-ui-report__element-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }

  .mango-ui-report__element-card-head strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-report__element-row + .mango-ui-report__element-row {
    margin-top: 6px;
  }

  .mango-ui-report__element-empty {
    flex: 1;
  }

  .mango-ui-report__runtime-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  @media (max-width: 1024px) {
    .mango-ui-report__metrics,
    .mango-ui-report__runtime-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-ui-report__step-detail,
    .mango-ui-report__focus-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .mango-ui-report__hero,
    .mango-ui-report__metrics,
    .mango-ui-report__runtime-grid {
      grid-template-columns: 1fr;
    }

    .mango-ui-report__step-header {
      grid-template-columns: max-content minmax(0, 1fr);
    }

    .mango-ui-report__step-op,
    .mango-ui-report__step-meta {
      grid-column: 2;
    }

    .mango-ui-report__info-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
