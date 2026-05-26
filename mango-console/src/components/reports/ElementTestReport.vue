<template>
  <section class="mango-ui-report">
    <div class="mango-ui-report__hero">
      <div class="mango-ui-report__title-block">
        <span class="mango-ui-report__eyebrow">UI 执行明细</span>
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
        <span>步骤通过率</span>
        <strong>{{ passRate }}%</strong>
        <div class="mango-ui-report__progress-track">
          <div class="mango-ui-report__progress-bar" :style="{ width: `${passRate}%` }"></div>
        </div>
      </div>
    </div>

    <div class="mango-ui-report__metrics">
      <div class="mango-ui-report__metric">
        <span>步骤总数</span>
        <strong>{{ stepList.length }}</strong>
      </div>
      <div class="mango-ui-report__metric">
        <span>通过步骤</span>
        <strong class="mango-ui-report__metric-value--success">{{ passedCount }}</strong>
      </div>
      <div class="mango-ui-report__metric">
        <span>失败步骤</span>
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
          <a-image :src="`${minioURL}/${firstFailedStep.picture_path}`" width="132" />
        </div>
      </div>
    </article>

    <a-tabs v-model:active-key="activeTab" class="mango-ui-report__tabs" lazy-load>
      <a-tab-pane key="steps" title="执行步骤">
        <div v-if="stepList.length === 0" class="mango-empty-state">暂无执行过程</div>
        <a-collapse
          v-else
          :bordered="false"
          :default-active-key="failedStepKeys"
          destroy-on-hide
          class="mango-ui-report__step-list"
        >
          <a-collapse-item v-for="(item, index) in stepList" :key="stepKey(item, index)">
            <template #header>
              <div class="mango-ui-report__step-header">
                <a-tag size="small" :color="statusColor(item.status)">
                  {{ stepStatusText(item.status) }}
                </a-tag>
                <span class="mango-ui-report__step-name" :title="stepName(item)">
                  {{ stepName(item) }}
                </span>
                <span class="mango-ui-report__step-op">{{ operationLabel(item) }}</span>
                <span class="mango-ui-report__step-meta">
                  元素 {{ elementRows(item).length }}
                </span>
              </div>
            </template>

            <div class="mango-ui-report__step-detail">
              <section class="mango-ui-report__detail-panel">
                <div class="mango-ui-report__section-head">
                  <h3>操作上下文</h3>
                  <p>用于判断步骤动作、等待和断言是否符合预期。</p>
                </div>
                <div class="mango-ui-report__info-grid">
                  <div>
                    <span>操作类型</span>
                    <strong>{{ operationLabel(item) }}</strong>
                  </div>
                  <div v-if="item.sub">
                    <span>元素下标</span>
                    <strong>{{ item.sub }}</strong>
                  </div>
                  <div>
                    <span>等待时间</span>
                    <strong>{{ formatSleep(item.sleep) }}</strong>
                  </div>
                  <div v-if="item.ass_msg" class="mango-ui-report__info-wide">
                    <span>断言提示</span>
                    <a-tooltip :content="item.ass_msg">
                      <strong>{{ item.ass_msg }}</strong>
                    </a-tooltip>
                  </div>
                  <div
                    v-if="item.status === 0 && item?.error_message"
                    class="mango-ui-report__info-wide"
                  >
                    <span>错误提示</span>
                    <a-tooltip :content="item.error_message">
                      <strong class="mango-ui-report__danger-text">{{ item.error_message }}</strong>
                    </a-tooltip>
                  </div>
                  <div
                    v-if="item.status === 0 && item?.video_path"
                    class="mango-ui-report__info-wide"
                  >
                    <span>视频路径</span>
                    <strong class="mango-ui-report__mono">{{ item.video_path }}</strong>
                  </div>
                </div>
              </section>

              <section class="mango-ui-report__detail-panel mango-ui-report__element-panel">
                <div class="mango-ui-report__section-head">
                  <h3>元素信息</h3>
                  <p>多个定位信息可在当前区域内滚动查看。</p>
                </div>
                <div v-if="elementRows(item).length" class="mango-ui-report__element-list">
                  <article
                    v-for="(element, elementIndex) in elementRows(item)"
                    :key="elementIndex"
                    class="mango-ui-report__element-card"
                  >
                    <div class="mango-ui-report__element-card-head">
                      <strong>{{ element.name || `元素信息` }}</strong>
                      <a-tag size="small" color="arcoblue">{{ elementExpText(element.exp) }}</a-tag>
                    </div>
                    <div class="mango-ui-report__element-row">
                      <span>定位表达式</span>
                      <a-tooltip :content="element.loc || '-'">
                        <strong class="mango-ui-report__mono">{{ element.loc || '-' }}</strong>
                      </a-tooltip>
                    </div>
                    <div class="mango-ui-report__element-row">
                      <span>匹配数量</span>
                      <strong>{{ element.ele_quantity ?? '-' }}</strong>
                    </div>
                    <div v-if="element.sub" class="mango-ui-report__element-row">
                      <span>下标</span>
                      <strong>{{ element.sub }}</strong>
                    </div>
                    <div v-if="element.element_text" class="mango-ui-report__element-row">
                      <span>元素文本</span>
                      <a-tooltip :content="element.element_text">
                        <strong>{{ element.element_text }}</strong>
                      </a-tooltip>
                    </div>
                  </article>
                </div>
                <div v-else class="mango-empty-state mango-ui-report__element-empty">
                  暂无元素信息
                </div>
              </section>

              <section
                v-if="item.status === 0 && item?.picture_path"
                class="mango-ui-report__detail-panel mango-ui-report__screenshot-panel"
              >
                <div class="mango-ui-report__section-head">
                  <h3>失败截图</h3>
                  <p>失败发生时的页面截图。</p>
                </div>
                <a-image :src="`${minioURL}/${item.picture_path}`" width="180" />
              </section>
            </div>
          </a-collapse-item>
        </a-collapse>
      </a-tab-pane>

      <a-tab-pane key="runtime" title="运行信息">
        <div class="mango-ui-report__runtime-grid">
          <article class="mango-ui-report__detail-panel">
            <div class="mango-ui-report__section-head">
              <h3>测试对象</h3>
              <p>本次 UI 执行使用的浏览器、环境或目标对象。</p>
            </div>
            <div class="mango-ui-report__runtime-value">{{ resultData?.test_object || '-' }}</div>
          </article>
          <article v-if="resultData?.video_path" class="mango-ui-report__detail-panel">
            <div class="mango-ui-report__section-head">
              <h3>执行视频</h3>
              <p>完整执行过程的视频路径。</p>
            </div>
            <div class="mango-ui-report__runtime-value mango-ui-report__mono">
              {{ resultData.video_path }}
            </div>
          </article>
          <article
            v-for="section in runtimeSections"
            :key="section.key"
            class="mango-ui-report__detail-panel mango-ui-report__runtime-wide"
          >
            <div class="mango-ui-report__section-head">
              <h3>{{ section.title }}</h3>
              <p>{{ section.description }}</p>
            </div>
            <JsonDisplay :data="section.data" />
          </article>
        </div>
      </a-tab-pane>
    </a-tabs>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { minioURL } from '@/api/axios.config'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'

  const props = defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })

  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()
  const activeTab = ref('steps')

  const stepList = computed(() => props.resultData?.element_result_list || [])
  const passedCount = computed(() => stepList.value.filter((item: any) => item.status === 1).length)
  const failedCount = computed(() => stepList.value.filter((item: any) => item.status === 0).length)
  const pendingCount = computed(() =>
    stepList.value.filter((item: any) => item.status !== 0 && item.status !== 1).length
  )
  const passRate = computed(() => {
    if (!stepList.value.length) return 0
    return Math.round((passedCount.value / stepList.value.length) * 100)
  })
  const failedStepKeys = computed(() =>
    stepList.value
      .map((item: any, index: number) => ({ item, index }))
      .filter(({ item }: any) => item.status === 0)
      .map(({ item, index }: any) => stepKey(item, index))
  )
  const firstFailedStep = computed(() => stepList.value.find((item: any) => item.status === 0))
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
    const visibleSections = sections.filter((item) => hasValue(item.data))
    return visibleSections.length ? visibleSections : [
      {
        key: 'empty',
        title: '暂无运行缓存',
        description: '本次 UI 执行没有记录缓存数据或数据工厂上下文。',
        data: {},
      },
    ]
  })

  function stepKey(item: any, index: number) {
    return String(item?.id ?? item?.page_step_details_id ?? index)
  }

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

  function elementExpText(value: any) {
    return enumStore.element_exp?.find((item: any) => item.key === value)?.title || value || '-'
  }

  function formatSleep(value: any) {
    if (value === null || value === undefined || value === '') return '-'
    return `${value} 秒`
  }

  function elementRows(item: any) {
    if (Array.isArray(item?.elements) && item.elements.length) return item.elements
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

  watch(
    () => props.resultData,
    () => {
      activeTab.value = 'steps'
    },
    { immediate: true }
  )
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

  .mango-ui-report__tabs {
    :deep(.arco-tabs-nav) {
      margin-bottom: 10px;
    }

    :deep(.arco-tabs-content) {
      padding-top: 0;
    }
  }

  .mango-ui-report__step-list :deep(.arco-collapse-item) {
    overflow: hidden;
    margin-bottom: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-ui-report__step-list :deep(.arco-collapse-item-header) {
    padding: 8px 10px 8px 32px;
    background: var(--m-surface);
  }

  .mango-ui-report__step-list :deep(.arco-collapse-item-header-title) {
    min-width: 0;
  }

  .mango-ui-report__step-list :deep(.arco-collapse-item-content-box) {
    padding: 10px;
    background: var(--m-surface);
  }

  .mango-ui-report__step-header {
    display: grid;
    align-items: center;
    width: 100%;
    min-width: 0;
    gap: 8px;
    grid-template-columns: max-content minmax(160px, 1fr) minmax(100px, 180px) max-content;
  }

  .mango-ui-report__step-name,
  .mango-ui-report__step-op,
  .mango-ui-report__step-meta {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-report__step-op,
  .mango-ui-report__step-meta {
    color: var(--m-muted);
  }

  .mango-ui-report__step-detail {
    display: grid;
    gap: 10px;
    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
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
