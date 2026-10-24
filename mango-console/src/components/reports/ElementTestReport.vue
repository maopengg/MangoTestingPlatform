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
          <span v-if="resultData?.test_time">执行时间：{{ resultData.test_time }}</span>
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
  import { computed, ref } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { useArtifactUrl } from '@/hooks/use-artifact-url'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'

  const props = defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })

  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()
  const cachePanelVisible = ref(false)

  const stepList = computed(() => normalizeStepList(props.resultData))
  const timelineRows = computed(() =>
    stepList.value.flatMap((step: any, stepIndex: number) =>
      runtimeResultRows(step).map((runtime: any, runtimeIndex: number) => ({
        step,
        runtime,
        stepIndex,
        runtimeIndex,
      }))
    )
  )
  const operationTotal = computed(() => timelineRows.value.length)
  const passedCount = computed(() => timelineRows.value.filter((item: any) => item.runtime?.status === 1).length)
  const failedCount = computed(() => timelineRows.value.filter((item: any) => item.runtime?.status === 0).length)
  const pendingCount = computed(() =>
    timelineRows.value.filter((item: any) => item.runtime?.status !== 0 && item.runtime?.status !== 1).length
  )
  const passRate = computed(() => {
    if (!operationTotal.value) return 0
    return Math.round((passedCount.value / operationTotal.value) * 100)
  })
  const firstFailedStep = computed(() => stepList.value.find((item: any) => item.status === 0))
  const firstFailedPicturePath = computed(() => firstFailedStep.value?.picture_path || '')
  const firstFailedPictureUrl = useArtifactUrl(firstFailedPicturePath)
  const resultStatusType = computed(() => stepStatusType(props.resultData?.status))
  const resultStatusText = computed(() => {
    if (props.resultData?.status === 1) return '测试通过'
    if (props.resultData?.status === 0) return '测试失败'
    return '未测试'
  })
  const resultStatusColor = computed(() => statusColor(props.resultData?.status))
  const resultStatusClass = computed(() => `mango-ui-report__progress-card--${resultStatusType.value}`)

  type RuntimeSection = {
    key: string
    title: string
    description: string
    data: unknown
  }

  const hasValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  }

  const runtimeSections = computed<RuntimeSection[]>(() => {
    const sections: RuntimeSection[] = [
      {
        key: 'cache',
        title: '缓存数据',
        description: '本次 UI 执行过程中写入或读取的缓存上下文。',
        data: props.resultData?.cache_data,
      },
      {
        key: 'factory',
        title: '数据工厂',
        description: '数据工厂生成或注入到 UI 执行器的上下文。',
        data: props.resultData?.data_factory_cache_data,
      },
    ]
    return sections.filter((item) => hasValue(item.data))
  })

  function stepName(item: any) {
    return (
      item?.name ||
      item?.ele_name?.name ||
      useSelectValue.getSelectLabel(item?.ope_key) ||
      enumStore.element_ope?.[item?.type]?.title ||
      '未命名步骤'
    )
  }

  function operationLabel(item: any) {
    return (
      useSelectValue.getSelectLabel(item?.ope_key) ||
      enumStore.element_ope?.[item?.type]?.title ||
      '-'
    )
  }

  function stepStatusType(status: any) {
    if (status === 1) return 'success'
    if (status === 0) return 'danger'
    return 'muted'
  }

  function stepStatusText(status: any) {
    if (status === 1) return '通过'
    if (status === 0) return '失败'
    return '未测试'
  }

  function statusColor(status: any) {
    if (status === 1) return 'green'
    if (status === 0) return 'red'
    return 'gray'
  }

  function timelineDotColor(status: any) {
    if (status === 1) return 'green'
    if (status === 0) return 'red'
    return 'gray'
  }

  function timelineLabel(item: any, index: number) {
    const time = item?.stop_time || item?.test_time || ''
    const match = String(time).match(/\d{2}:\d{2}:\d{2}/)
    return match?.[0] || ''
  }

  function elementRows(item: any) {
    if (Array.isArray(item?.elements) && item.elements.length) return item.elements
    if (Array.isArray(item?.element_result) && item.element_result.length) return item.element_result
    if (Array.isArray(item?.element_list) && item.element_list.length) return item.element_list
    if (Array.isArray(item?.element) && item.element.length) return item.element
    if (item?.ele_name) return [item.ele_name]
    if (item?.loc) {
      return [
        {
          name: item.name,
          exp: item.exp,
          loc: item.loc,
          sub: item.sub,
          ele_quantity: item.ele_quantity,
          element_text: item.element_text,
        },
      ]
    }
    return []
  }

  function normalizeStepList(data: any) {
    if (Array.isArray(data?.steps) && data.steps.length) return data.steps
    if (Array.isArray(data?.element_result_list) && data.element_result_list.length) {
      return data.element_result_list
    }
    if (Array.isArray(data?.children) && data.children.length) return data.children
    return []
  }

  function runtimeResultRows(item: any) {
    if (Array.isArray(item?.element_result_list) && item.element_result_list.length) {
      return item.element_result_list
    }
    if (Array.isArray(item?.children) && item.children.length) {
      return item.children
    }
    return [item]
  }

  function timelineRowKey(row: any, index: number) {
    return String(
      row?.runtime?.id ??
        row?.runtime?.page_step_details_id ??
        `${row?.step?.id || row.stepIndex}-${row?.runtime?.name || index}`
    )
  }

  function runtimeResultName(runtime: any, step: any, index: number) {
    return runtime?.name || runtime?.ele_name?.name || stepName(runtime) || `${stepName(step)}-${index + 1}`
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
