<template>
  <section
    class="mango-api-report"
    :class="{ 'mango-api-report--contained': contained }"
  >
    <div class="mango-api-report__hero">
      <div class="mango-api-report__title-block">
        <span class="mango-api-report__eyebrow">API 调用明细</span>
        <div class="mango-api-report__title-row">
          <h2>{{ resultData?.name || '未命名接口' }}</h2>
          <a-tag v-if="resultData?.is_recovery" size="small">最终恢复</a-tag>
          <a-tag class="mango-api-report__method" color="arcoblue">{{ requestMethod }}</a-tag>
        </div>
        <p>
          <span>接口 ID：{{ resultData.id ?? '-' }}</span>
          <span v-if="resultData?.test_time">执行时间：{{ resultData.test_time }}</span>
        </p>
      </div>

      <div class="mango-api-report__status-card" :class="statusClass">
        <span class="mango-api-report__status-label">测试结论</span>
        <strong>{{ statusText }}</strong>
      </div>
    </div>

    <a-space v-if="resultData?.recovery_status !== undefined && resultData?.recovery_status !== null" wrap>
      <span>主流程：{{ resultData.main_status === 1 ? '成功' : resultData.main_status === 5 ? '已停止' : '未通过' }}</span>
      <span>最终恢复：{{ resultData.recovery_status === 1 ? '成功' : '失败' }}</span>
      <span v-if="resultData.recovery_errors?.length">{{ resultData.recovery_errors.join('；') }}</span>
    </a-space>
    <div class="mango-api-report__request-line">
      <span class="mango-api-report__request-method">{{ requestMethod }}</span>
      <a-tooltip :content="requestUrl" position="top" mini>
        <span class="mango-api-report__request-url">{{ requestUrl }}</span>
      </a-tooltip>
    </div>

    <div v-if="isSnapshot" class="mango-api-report__snapshot">
      <div>
        <span>执行中快照</span>
        <strong>{{ snapshotSummary }}</strong>
      </div>
      <a-tag color="orange" size="small">最终结果以执行完成后为准</a-tag>
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
      <a-tab-pane
        key="response"
        title="响应结果"
        data-testid="qa-components-reports-apitestreport-tab-pane-响应结果"
      >
        <div
          class="mango-api-report__tab-scroll mango-native-scrollbar"
          role="region"
          aria-label="响应结果内容"
          tabindex="0"
        >
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
                :show-toolbar="section.showToolbar !== false"
              />
            </article>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane
        key="request"
        title="请求信息"
        data-testid="qa-components-reports-apitestreport-tab-pane-请求信息"
      >
        <div
          class="mango-api-report__tab-scroll mango-native-scrollbar"
          role="region"
          aria-label="请求信息内容"
          tabindex="0"
        >
          <div class="mango-api-report__section-grid">
            <article
              v-for="section in requestSections"
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
                :show-toolbar="section.showToolbar !== false"
              />
            </article>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane
        key="assertion"
        title="断言数据"
        data-testid="qa-components-reports-apitestreport-tab-pane-断言数据"
      >
        <div
          class="mango-api-report__tab-scroll mango-native-scrollbar"
          role="region"
          aria-label="断言数据内容"
          tabindex="0"
        >
          <article class="mango-api-report__evidence-card mango-api-report__evidence-card--wide">
            <AssertionResult :data="resultData?.ass" />
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane
        key="cache"
        title="缓存数据"
        data-testid="qa-components-reports-apitestreport-tab-pane-缓存数据"
      >
        <div
          class="mango-api-report__tab-scroll mango-native-scrollbar"
          role="region"
          aria-label="缓存数据内容"
          tabindex="0"
        >
          <article class="mango-api-report__evidence-card mango-api-report__evidence-card--wide">
            <div class="mango-api-report__section-head">
              <div>
                <h3>缓存数据</h3>
                <p>本次接口执行过程中写入或读取的缓存上下文。</p>
              </div>
            </div>
            <JsonDisplay :data="cacheData" />
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane
        v-if="hasDataFactory"
        key="factory"
        title="数据工厂"
        data-testid="qa-components-reports-apitestreport-tab-pane-数据工厂"
      >
        <div
          class="mango-api-report__tab-scroll mango-native-scrollbar"
          role="region"
          aria-label="数据工厂内容"
          tabindex="0"
        >
          <article class="mango-api-report__evidence-card mango-api-report__evidence-card--wide">
            <div class="mango-api-report__section-head">
              <div>
                <h3>数据工厂</h3>
                <p>数据工厂生成或传递给接口调用的上下文。</p>
              </div>
            </div>
            <JsonDisplay :data="dataFactoryData" />
          </article>
        </div>
      </a-tab-pane>
    </a-tabs>
  </section>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import { apiReport } from './api-report'

  type EvidenceSection = {
    key: string
    title: string
    description: string
    data: unknown
    wide?: boolean
    defaultExpanded?: boolean | string
    showToolbar?: boolean
  }

  const props = withDefaults(defineProps<{ resultData: unknown; contained?: boolean }>(), { contained: false })
  const resultData = computed(() => apiReport(props.resultData))

  const activeTab = ref('response')

  const hasValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  }

  const hasResponseJson = (response: { json?: unknown }) => response.json !== null && response.json !== undefined

  const cacheData = computed(() => resultData.value.cache_data ?? {})
  const dataFactoryData = computed(() => resultData.value?.data_factory_cache_data)
  const hasDataFactory = computed(() => hasValue(dataFactoryData.value))

  const requestMethod = computed(() => resultData.value?.request?.method || '-')
  const requestUrl = computed(() => resultData.value?.request?.url || '-')
  const statusCode = computed(() => resultData.value.response.code ?? '-')
  const isSnapshot = computed(() => resultData.value?.result_mode === 'snapshot')
  const failureMessage = computed(
    () => resultData.value?.error_message || '接口调用失败，请检查响应结果与断言数据。'
  )
  const snapshotSummary = computed(() => {
    const retry = resultData.value?.snapshot_retry || {}
    const progress = resultData.value?.snapshot_progress || {}
    const parts: string[] = []
    if (progress.done || progress.total) {
      parts.push(`进度 ${progress.done || 0}/${progress.total || '-'}`)
    }
    if (retry.current || retry.max) {
      parts.push(`重试 ${retry.current || 0}/${retry.max || '-'}`)
    }
    if (resultData.value?.snapshot_updated_at) {
      parts.push(`更新于 ${resultData.value.snapshot_updated_at}`)
    }
    return parts.join('，') || '当前用例仍在执行'
  })

  const responseTime = computed(() => {
    const value = resultData.value?.response?.time
    if (value === null || value === undefined || value === '') return '-'
    const numberValue = Number(value)
    if (Number.isFinite(numberValue)) return `${numberValue.toFixed(2)} 秒`
    return String(value)
  })

  const responseType = computed(() => {
    if (hasValue(resultData.value?.response?.ws_messages)) return 'WebSocket'
    if (hasValue(resultData.value?.response?.sse_events)) return 'SSE'
    if (hasResponseJson(resultData.value?.response)) return 'JSON'
    if (hasValue(resultData.value?.response?.text)) return 'Text'
    if (hasValue(resultData.value?.response?.headers)) return 'Headers'
    return '-'
  })

  const assertionSummary = computed(() => {
    const list = resultData.value?.ass || []
    if (!Array.isArray(list) || list.length === 0) return '暂无'
    const failed = list.filter((item) => item.status !== 1).length
    if (failed > 0) return `${failed} 失败 / ${list.length} 总数`
    return `${list.length} 全部通过`
  })

  const statusText = computed(() => {
    if (resultData.value?.status === 3 || isSnapshot.value) return '执行中'
    if (resultData.value?.status === 1) return '测试通过'
    if (resultData.value?.status === 0) return '测试失败'
    return '未测试'
  })

  const statusClass = computed(() => {
    if (resultData.value?.status === 3 || isSnapshot.value)
      return 'mango-api-report__status-card--warning'
    if (resultData.value?.status === 1) return 'mango-api-report__status-card--success'
    if (resultData.value?.status === 0) return 'mango-api-report__status-card--danger'
    return 'mango-api-report__status-card--muted'
  })

  const statusCodeClass = computed(() => {
    const value = resultData.value.response.code
    if (value === null || value === '') return ''
    const code = Number(value)
    if (!Number.isFinite(code)) return ''
    if (code >= 200 && code < 400) return 'mango-api-report__metric-value--success'
    if (code >= 400) return 'mango-api-report__metric-value--danger'
    return 'mango-api-report__metric-value--warning'
  })

  const requestSections = computed<EvidenceSection[]>(() => {
    const request = resultData.value?.request || {}
    const response = resultData.value?.response || {}
    const sections: EvidenceSection[] = [
      {
        key: 'headers',
        title: '请求头',
        description: 'Headers 信息，常用于排查鉴权、租户和内容类型。',
        data: response.request_headers ?? request.headers,
        wide: true,
        defaultExpanded: false,
        showToolbar: false,
      },
      {
        key: 'params',
        title: '参数',
        description: 'Query 参数，适合检查分页、过滤和路径查询。',
        data: response.request_params ?? request.params,
        wide: true,
      },
      {
        key: 'body',
        title: '请求体',
        description: '实际发送的 Body，包含 JSON、Form、Raw 或 Multipart 字段。',
        data: response.request_body ?? request.request_body ?? request.data ?? request.json,
        wide: true,
      },
      {
        key: 'sse',
        title: 'SSE 配置',
        description: 'SSE 最大读取时长、事件数量及流结束条件。',
        data: request.sse_config,
        wide: true,
      },
      {
        key: 'file',
        title: '文件',
        description: '上传文件相关配置。',
        data: response.request_file ?? request.request_files ?? request.file,
        wide: true,
      },
    ]
    return sections.filter((item) => hasValue(item.data))
  })

  const responseSections = computed<EvidenceSection[]>(() => {
    const response = resultData.value?.response || {}
    const responseJsonAvailable = hasResponseJson(response)
    const sections: EvidenceSection[] = [
      {
        key: 'headers',
        title: '响应头',
        description: '响应 Headers 默认收起，按需查看服务端元信息。',
        data: response.headers,
        wide: true,
        defaultExpanded: false,
        showToolbar: false,
      },
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
        data: responseJsonAvailable ? null : response.text,
        wide: true,
      },
      {
        key: 'sse',
        title: 'SSE事件',
        description: '事件流响应中已收集的事件列表。',
        data: response.sse_events,
        wide: true,
      },
      {
        key: 'websocket',
        title: 'WebSocket消息',
        description: 'WebSocket执行过程中发送和接收的消息明细。',
        data: response.ws_messages
          ? {
              stop_reason: response.ws_stop_reason,
              close_code: response.ws_close_code,
              close_reason: response.ws_close_reason,
              messages: response.ws_messages,
            }
          : null,
        wide: true,
      },
    ]
    const visibleSections = sections.filter((item) =>
      item.key === 'json' ? responseJsonAvailable : hasValue(item.data)
    )
    return visibleSections.length
      ? visibleSections
      : [
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

  watch(
    () => props.resultData,
    () => {
      activeTab.value = resultData.value?.status === 0 ? 'response' : 'assertion'
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

  .mango-api-report--contained {
    height: 100%;
    min-height: 0;
    overflow: hidden;
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

  .mango-api-report__status-card--warning {
    border-left-color: var(--m-warning);
  }

  .mango-api-report__status-card--warning strong {
    color: var(--m-warning);
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

  .mango-api-report__snapshot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid color-mix(in srgb, var(--m-warning) 34%, var(--m-border));
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-warning) 8%, var(--m-surface));
  }

  .mango-api-report__snapshot span {
    display: block;
    color: var(--m-warning);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-api-report__snapshot strong {
    display: block;
    margin-top: 2px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 500;
    line-height: 20px;
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

  .mango-api-report--contained .mango-api-report__tabs {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;

    :deep(> .arco-tabs-nav) {
      flex: 0 0 auto;
    }

    :deep(> .arco-tabs-content),
    :deep(> .arco-tabs-content > .arco-tabs-content-list),
    :deep(> .arco-tabs-content > .arco-tabs-content-list > .arco-tabs-content-item),
    :deep(> .arco-tabs-content > .arco-tabs-content-list > .arco-tabs-content-item > .arco-tabs-pane) {
      height: 100%;
      min-height: 0;
    }

    :deep(> .arco-tabs-content) {
      flex: 1;
      overflow: hidden;
    }
  }

  .mango-api-report__tab-scroll {
    min-height: 0;
  }

  .mango-api-report--contained .mango-api-report__tab-scroll {
    box-sizing: border-box;
    height: 100%;
    padding-right: 4px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
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
