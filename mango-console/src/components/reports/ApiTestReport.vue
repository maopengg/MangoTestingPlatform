<template>
  <section class="mango-api-report">
    <div class="mango-api-report__hero">
      <div class="mango-api-report__title-block">
        <span class="mango-api-report__eyebrow">API 调用明细</span>
        <div class="mango-api-report__title-row">
          <h2>{{ resultData?.name || '未命名接口' }}</h2>
          <a-tag class="mango-api-report__method" color="arcoblue">{{ requestMethod }}</a-tag>
        </div>
        <p>
          <span>接口 ID：{{ resultData?.id || '-' }}</span>
          <span v-if="resultData?.test_time">执行时间：{{ resultData.test_time }}</span>
        </p>
      </div>

      <div class="mango-api-report__status-card" :class="statusClass">
        <span class="mango-api-report__status-label">测试结论</span>
        <strong>{{ statusText }}</strong>
      </div>
    </div>

    <div class="mango-api-report__request-line">
      <span class="mango-api-report__request-method">{{ requestMethod }}</span>
      <a-tooltip :content="requestUrl" position="top" mini>
        <span class="mango-api-report__request-url">{{ requestUrl }}</span>
      </a-tooltip>
    </div>

    <div class="mango-api-report__metrics">
      <div class="mango-api-report__metric">
        <span>状态码</span>
        <strong :class="statusCodeClass">{{ statusCode }}</strong>
      </div>
      <div class="mango-api-report__metric">
        <span>响应时间</span>
        <strong>{{ responseTime }}</strong>
      </div>
      <div class="mango-api-report__metric">
        <span>响应类型</span>
        <strong>{{ responseType }}</strong>
      </div>
      <div class="mango-api-report__metric">
        <span>断言结果</span>
        <strong>{{ assertionSummary }}</strong>
      </div>
    </div>

    <div v-if="resultData?.status === 0" class="mango-api-report__error">
      <div>
        <span>失败提示</span>
        <a-tooltip :content="failureMessage" position="top" mini>
          <strong>{{ failureMessage }}</strong>
        </a-tooltip>
      </div>
    </div>

    <a-tabs v-model:active-key="activeTab" class="mango-api-report__tabs" lazy-load>
      <a-tab-pane key="response" title="响应结果">
        <div class="mango-api-report__section-grid">
          <article
            v-for="section in responseSections"
            :key="section.key"
            class="mango-api-report__evidence-card"
            :class="{ 'mango-api-report__evidence-card--wide': section.wide }"
          >
            <div class="mango-api-report__section-head">
              <div>
                <h3>{{ section.title }}</h3>
                <p>{{ section.description }}</p>
              </div>
            </div>
            <JsonDisplay
              :data="section.data"
              :default-expanded="section.defaultExpanded"
            />
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane key="request" title="请求信息">
        <div class="mango-api-report__section-grid">
          <article
            v-for="section in requestSections"
            :key="section.key"
            class="mango-api-report__evidence-card"
          >
            <div class="mango-api-report__section-head">
              <div>
                <h3>{{ section.title }}</h3>
                <p>{{ section.description }}</p>
              </div>
            </div>
            <JsonDisplay :data="section.data" />
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane key="assertion" title="断言数据">
        <article class="mango-api-report__evidence-card mango-api-report__evidence-card--wide">
          <div class="mango-api-report__section-head">
            <div>
              <h3>断言结果</h3>
              <p>展示实际值、预期值和断言执行消息，用于定位校验失败原因。</p>
            </div>
          </div>
          <AssertionResult :data="resultData?.ass" />
        </article>
      </a-tab-pane>

      <a-tab-pane key="runtime" title="运行缓存">
        <div class="mango-api-report__section-grid">
          <article
            v-for="section in runtimeSections"
            :key="section.key"
            class="mango-api-report__evidence-card"
          >
            <div class="mango-api-report__section-head">
              <div>
                <h3>{{ section.title }}</h3>
                <p>{{ section.description }}</p>
              </div>
            </div>
            <JsonDisplay :data="section.data" />
          </article>
        </div>
      </a-tab-pane>
    </a-tabs>
  </section>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import AssertionResult from '@/components/feedback/AssertionResult.vue'

  type EvidenceSection = {
    key: string
    title: string
    description: string
    data: unknown
    wide?: boolean
    defaultExpanded?: boolean | string
  }

  const props = defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })

  const activeTab = ref('response')

  const hasValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  }

  const requestMethod = computed(() => props.resultData?.request?.method || '-')
  const requestUrl = computed(() => props.resultData?.request?.url || '-')
  const statusCode = computed(() => props.resultData?.response?.code || '-')
  const failureMessage = computed(
    () => props.resultData?.error_message || '接口调用失败，请检查响应结果与断言数据。'
  )

  const responseTime = computed(() => {
    const value = props.resultData?.response?.time
    if (value === null || value === undefined || value === '') return '-'
    const numberValue = Number(value)
    if (Number.isFinite(numberValue)) return `${numberValue.toFixed(2)} 秒`
    return String(value)
  })

  const responseType = computed(() => {
    if (hasValue(props.resultData?.response?.json)) return 'JSON'
    if (hasValue(props.resultData?.response?.text)) return 'Text'
    if (hasValue(props.resultData?.response?.headers)) return 'Headers'
    return '-'
  })

  const assertionSummary = computed(() => {
    const list = props.resultData?.ass || []
    if (!Array.isArray(list) || list.length === 0) return '暂无'
    const failed = list.filter((item: any) => item.status !== 1).length
    if (failed > 0) return `${failed} 失败 / ${list.length} 总数`
    return `${list.length} 全部通过`
  })

  const statusText = computed(() => {
    if (props.resultData?.status === 1) return '测试通过'
    if (props.resultData?.status === 0) return '测试失败'
    return '未测试'
  })

  const statusClass = computed(() => {
    if (props.resultData?.status === 1) return 'mango-api-report__status-card--success'
    if (props.resultData?.status === 0) return 'mango-api-report__status-card--danger'
    return 'mango-api-report__status-card--muted'
  })

  const statusCodeClass = computed(() => {
    const code = Number(props.resultData?.response?.code)
    if (!Number.isFinite(code)) return ''
    if (code >= 200 && code < 400) return 'mango-api-report__metric-value--success'
    if (code >= 400) return 'mango-api-report__metric-value--danger'
    return 'mango-api-report__metric-value--warning'
  })

  const requestSections = computed<EvidenceSection[]>(() => {
    const request = props.resultData?.request || {}
    const sections: EvidenceSection[] = [
      {
        key: 'headers',
        title: '请求头',
        description: 'Headers 信息，常用于排查鉴权、租户和内容类型。',
        data: request.headers,
      },
      {
        key: 'params',
        title: '参数',
        description: 'Query 参数，适合检查分页、过滤和路径查询。',
        data: request.params,
      },
      {
        key: 'data',
        title: '表单',
        description: 'Form Data 请求体。',
        data: request.data,
      },
      {
        key: 'json',
        title: 'JSON',
        description: 'JSON 请求体，默认展示第一层便于快速定位字段。',
        data: request.json,
      },
      {
        key: 'file',
        title: '文件',
        description: '上传文件相关配置。',
        data: request.file,
      },
    ]
    return sections.filter((item) => hasValue(item.data))
  })

  const responseSections = computed<EvidenceSection[]>(() => {
    const response = props.resultData?.response || {}
    const sections: EvidenceSection[] = [
      {
        key: 'json',
        title: '响应 JSON',
        description: '接口返回的结构化数据，优先用于排查字段、状态和断言。',
        data: response.json,
        wide: true,
      },
      {
        key: 'text',
        title: '响应文本',
        description: '非 JSON 响应、异常文本或原始返回内容。',
        data: response.text,
        wide: true,
      },
      {
        key: 'headers',
        title: '响应头',
        description: '响应 Headers 默认收起，按需查看服务端元信息。',
        data: response.headers,
        defaultExpanded: false,
      },
    ]
    const visibleSections = sections.filter((item) => hasValue(item.data))
    return visibleSections.length ? visibleSections : [
      {
        key: 'empty',
        title: '暂无响应数据',
        description: '本次调用没有记录响应 JSON、文本或响应头。',
        data: {},
        wide: true,
        defaultExpanded: false,
      },
    ]
  })

  const runtimeSections = computed<EvidenceSection[]>(() => {
    const sections: EvidenceSection[] = [
      {
        key: 'cache',
        title: '缓存数据',
        description: '本次接口执行过程中写入或读取的缓存上下文。',
        data: props.resultData?.cache_data,
      },
      {
        key: 'factory',
        title: '数据工厂',
        description: '数据工厂生成或传递给接口调用的上下文。',
        data: props.resultData?.data_factory_cache_data,
      },
    ]
    const visibleSections = sections.filter((item) => hasValue(item.data))
    return visibleSections.length ? visibleSections : [
      {
        key: 'empty',
        title: '暂无运行缓存',
        description: '本次调用没有记录缓存数据或数据工厂上下文。',
        data: {},
        defaultExpanded: false,
      },
    ]
  })

  watch(
    () => props.resultData,
    () => {
      activeTab.value = props.resultData?.status === 0 ? 'response' : 'assertion'
    },
    { immediate: true }
  )
</script>

<style scoped lang="less">
  .mango-api-report {
    display: flex;
    flex-direction: column;
    gap: 12px;
    color: var(--m-text);
  }

  .mango-api-report__hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 152px;
    gap: 12px;
    align-items: stretch;
  }

  .mango-api-report__title-block,
  .mango-api-report__status-card,
  .mango-api-report__request-line,
  .mango-api-report__metric,
  .mango-api-report__error,
  .mango-api-report__evidence-card {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-api-report__title-block {
    min-width: 0;
    padding: 14px 16px;
  }

  .mango-api-report__eyebrow {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-api-report__title-row {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
    margin-top: 4px;
  }

  .mango-api-report__title-row h2 {
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

  .mango-api-report__method {
    flex: none;
  }

  .mango-api-report__title-block p {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin: 6px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-api-report__status-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 12px 14px;
    border-left-width: 4px;
  }

  .mango-api-report__status-label {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-api-report__status-card strong {
    margin-top: 4px;
    font-size: 18px;
    line-height: 26px;
  }

  .mango-api-report__status-card--success {
    border-left-color: var(--m-success);
  }

  .mango-api-report__status-card--success strong,
  .mango-api-report__metric-value--success {
    color: var(--m-success);
  }

  .mango-api-report__status-card--danger {
    border-left-color: var(--m-danger);
  }

  .mango-api-report__status-card--danger strong,
  .mango-api-report__metric-value--danger {
    color: var(--m-danger);
  }

  .mango-api-report__status-card--muted {
    border-left-color: var(--m-border-strong);
  }

  .mango-api-report__metric-value--warning {
    color: var(--m-warning);
  }

  .mango-api-report__request-line {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: 10px;
    align-items: center;
    padding: 9px 12px;
    background: var(--m-surface-soft);
  }

  .mango-api-report__request-method {
    height: 24px;
    padding: 0 9px;
    border-radius: 999px;
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 600;
    line-height: 24px;
  }

  .mango-api-report__request-url {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-api-report__metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .mango-api-report__metric {
    min-width: 0;
    padding: 10px 12px;
  }

  .mango-api-report__metric span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-api-report__metric strong {
    display: block;
    min-width: 0;
    margin-top: 4px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 16px;
    line-height: 24px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-api-report__error {
    padding: 10px 12px;
    border-color: color-mix(in srgb, var(--m-danger) 34%, var(--m-border));
    background: color-mix(in srgb, var(--m-danger) 8%, var(--m-surface));
  }

  .mango-api-report__error span {
    display: block;
    color: var(--m-danger);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-api-report__error strong {
    display: -webkit-box;
    margin-top: 4px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 500;
    line-height: 22px;
    word-break: break-word;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }

  .mango-api-report__tabs {
    :deep(.arco-tabs-nav) {
      margin-bottom: 10px;
    }

    :deep(.arco-tabs-content) {
      padding-top: 0;
    }
  }

  .mango-api-report__section-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .mango-api-report__evidence-card {
    min-width: 0;
    padding: 12px;
  }

  .mango-api-report__evidence-card--wide {
    grid-column: 1 / -1;
  }

  .mango-api-report__section-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-api-report__section-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-api-report__section-head p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 19px;
  }

  @media (max-width: 1px) {
    .mango-api-report__metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-api-report__section-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 1px) {
    .mango-api-report__hero {
      grid-template-columns: 1fr;
    }

    .mango-api-report__metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
