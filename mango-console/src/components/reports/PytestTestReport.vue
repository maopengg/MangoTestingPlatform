<template>
  <section class="mango-pytest-report">
    <div class="mango-pytest-report__hero">
      <div class="mango-pytest-report__title-block">
        <span class="mango-pytest-report__eyebrow">Pytest 执行明细</span>
        <div class="mango-pytest-report__title-row">
          <h2>{{ resultData?.name || '未命名 Pytest 用例' }}</h2>
          <a-tag color="arcoblue" size="small">{{ evidenceTypeText }}</a-tag>
          <a-tag :color="statusColor" size="large">{{ statusText }}</a-tag>
        </div>
        <p>
          <span>{{ resultData?.fullName || resultData?.description || '-' }}</span>
        </p>
      </div>

      <div class="mango-pytest-report__status-card" :class="statusClass">
        <span>执行耗时</span>
        <strong>{{ durationText }}</strong>
      </div>
    </div>

    <div class="mango-pytest-report__metrics">
      <div class="mango-pytest-report__metric">
        <span>开始时间</span>
        <strong>{{ startTime }}</strong>
      </div>
      <div class="mango-pytest-report__metric">
        <span>{{ secondMetricLabel }}</span>
        <strong :class="secondMetricClass">{{ secondMetricValue }}</strong>
      </div>
      <div class="mango-pytest-report__metric">
        <span>{{ thirdMetricLabel }}</span>
        <strong>{{ thirdMetricValue }}</strong>
      </div>
      <div class="mango-pytest-report__metric">
        <span>附件数量</span>
        <strong>{{ attachments.length }}</strong>
      </div>
    </div>

    <div class="mango-pytest-report__labels">
      <a-tag v-for="item in visibleLabels" :key="`${item.name}-${item.value}`" size="small">
        {{ item.name }}：{{ item.value }}
      </a-tag>
      <span v-if="visibleLabels.length === 0" class="mango-pytest-report__muted">暂无标签</span>
    </div>

    <a-tabs v-model:active-key="activeTab" class="mango-pytest-report__tabs" lazy-load>
      <a-tab-pane v-if="hasApiEvidence" key="http" title="接口证据">
        <div class="mango-pytest-report__http-layout">
          <article class="mango-pytest-report__evidence-card mango-pytest-report__request-card">
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>请求信息</h3>
                <p>从 Allure 附件中提取 URL、方法和请求头。</p>
              </div>
            </div>
            <div class="mango-pytest-report__request-line">
              <span>{{ attachmentValue('请求方法') || '-' }}</span>
              <a-tooltip :content="attachmentValue('请求URL') || '-'">
                <strong>{{ attachmentValue('请求URL') || '-' }}</strong>
              </a-tooltip>
            </div>
            <JsonDisplay :data="parsedAttachment('请求头')" />
          </article>

          <article class="mango-pytest-report__evidence-card">
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>响应数据</h3>
                <p>优先查看业务响应体，定位状态码、消息和数据结构。</p>
              </div>
            </div>
            <JsonDisplay :data="parsedAttachment('响应数据')" />
          </article>

          <article class="mango-pytest-report__evidence-card">
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>响应头</h3>
                <p>默认收起，只在排查服务端元信息时查看。</p>
              </div>
            </div>
            <JsonDisplay :data="parsedAttachment('响应头')" :default-expanded="false" />
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane v-if="hasUiEvidence" key="ui" title="元素证据">
        <div class="mango-pytest-report__ui-layout">
          <article
            v-for="item in uiElementAttachments"
            :key="item.name"
            class="mango-pytest-report__evidence-card"
          >
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>{{ item.name }}</h3>
                <p>Playwright / UI 自动化元素查找结果。</p>
              </div>
            </div>
            <div class="mango-pytest-report__element-grid">
              <div>
                <span>定位方式</span>
                <strong>{{ item.method || '-' }}</strong>
              </div>
              <div>
                <span>元素个数</span>
                <strong>{{ item.count || '-' }}</strong>
              </div>
              <div>
                <span>元素下标</span>
                <strong>{{ item.index || '-' }}</strong>
              </div>
              <div>
                <span>元素文本</span>
                <a-tooltip :content="item.text || '-'">
                  <strong>{{ item.text || '-' }}</strong>
                </a-tooltip>
              </div>
              <div class="mango-pytest-report__element-wide">
                <span>元素表达式</span>
                <a-tooltip :content="item.loc || '-'">
                  <strong class="mango-pytest-report__mono">{{ item.loc || '-' }}</strong>
                </a-tooltip>
              </div>
            </div>
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane key="attachments" title="附件详情">
        <div class="mango-pytest-report__attachment-list">
          <article
            v-for="attachment in normalAttachments"
            :key="attachment.name"
            class="mango-pytest-report__evidence-card"
          >
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>{{ attachment.name }}</h3>
                <p>{{ attachment.type || 'text/plain' }}</p>
              </div>
            </div>
            <JsonDisplay
              v-if="isJsonAttachment(attachment)"
              :data="parseSource(attachment.source)"
            />
            <pre v-else>{{ attachment.source || '-' }}</pre>
          </article>
        </div>
      </a-tab-pane>

      <a-tab-pane key="logs" title="日志与错误">
        <div class="mango-pytest-report__log-layout">
          <article
            v-if="resultData?.statusDetails?.message"
            class="mango-pytest-report__evidence-card"
          >
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>报错类型</h3>
                <p>Pytest / Allure 捕获的失败消息。</p>
              </div>
            </div>
            <pre>{{ resultData.statusDetails.message }}</pre>
          </article>
          <article
            v-if="resultData?.statusDetails?.trace"
            class="mango-pytest-report__evidence-card"
          >
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>报错代码行</h3>
                <p>异常堆栈和代码定位。</p>
              </div>
            </div>
            <pre>{{ resultData.statusDetails.trace }}</pre>
          </article>
          <article
            v-for="attachment in logAttachments"
            :key="attachment.name"
            class="mango-pytest-report__evidence-card mango-pytest-report__evidence-card--wide"
          >
            <div class="mango-pytest-report__section-head">
              <div>
                <h3>{{ attachment.name }}</h3>
                <p>执行日志输出。</p>
              </div>
            </div>
            <pre>{{ cleanAnsi(attachment.source || '-') }}</pre>
          </article>
          <div
            v-if="!resultData?.statusDetails?.message && !resultData?.statusDetails?.trace && !logAttachments.length"
            class="mango-empty-state"
          >
            暂无日志与错误信息
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="raw" title="完整数据">
        <article class="mango-pytest-report__evidence-card">
          <div class="mango-pytest-report__section-head">
            <div>
              <h3>原始结果</h3>
              <p>保留完整 Pytest / Allure 结果数据，便于深度排查。</p>
            </div>
          </div>
          <JsonDisplay :data="resultData" />
        </article>
      </a-tab-pane>
    </a-tabs>
  </section>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'

  type Attachment = {
    name: string
    type?: string
    source?: string
  }

  type LabelItem = {
    name: string
    value: string
  }

  const props = defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })

  const activeTab = ref('http')
  const httpAttachmentNames = ['请求URL', '请求方法', '请求头', 'HTTP状态码', '响应时长(ms)', '响应数据', '响应头']
  const logAttachmentNames = ['log', 'stdout', 'stderr']

  const attachments = computed<Attachment[]>(() => props.resultData?.attachments || [])
  const labels = computed<LabelItem[]>(() => props.resultData?.labels || [])
  const hasApiEvidence = computed(() =>
    httpAttachmentNames.some((name) => Boolean(attachmentValue(name)))
  )
  const uiElementAttachments = computed(() =>
    attachments.value
      .filter((item) => isUiElementAttachment(item))
      .map((item) => ({
        name: item.name,
        ...parseUiElementSource(item.source || ''),
      }))
  )
  const hasUiEvidence = computed(() => uiElementAttachments.value.length > 0)
  const evidenceTypeText = computed(() => {
    if (hasApiEvidence.value) return 'API 证据'
    if (hasUiEvidence.value) return 'UI 证据'
    return '通用证据'
  })

  const visibleLabels = computed(() =>
    labels.value.filter((item) =>
      ['epic', 'feature', 'story', 'tag', 'suite', 'package', 'framework'].includes(item.name)
    )
  )

  const statusText = computed(() => {
    if (props.resultData?.status === 1 || props.resultData?.status === 'passed') return '测试通过'
    if (props.resultData?.status === 0 || props.resultData?.status === 'failed') return '测试失败'
    if (props.resultData?.status === 'skipped') return '已跳过'
    return '未测试'
  })

  const statusColor = computed(() => {
    if (props.resultData?.status === 1 || props.resultData?.status === 'passed') return 'green'
    if (props.resultData?.status === 0 || props.resultData?.status === 'failed') return 'red'
    return 'gray'
  })

  const statusClass = computed(() => {
    if (props.resultData?.status === 1 || props.resultData?.status === 'passed') {
      return 'mango-pytest-report__status-card--success'
    }
    if (props.resultData?.status === 0 || props.resultData?.status === 'failed') {
      return 'mango-pytest-report__status-card--danger'
    }
    return 'mango-pytest-report__status-card--muted'
  })

  const durationText = computed(() => {
    const start = Number(props.resultData?.start)
    const stop = Number(props.resultData?.stop)
    if (!Number.isFinite(start) || !Number.isFinite(stop) || stop < start) return '-'
    const duration = stop - start
    if (duration >= 1000) return `${(duration / 1000).toFixed(2)} 秒`
    return `${duration} ms`
  })

  const startTime = computed(() => formatTimestamp(props.resultData?.start))

  const responseDuration = computed(() => {
    const value = attachmentValue('响应时长(ms)')
    if (!value) return '-'
    const numberValue = Number(value)
    if (Number.isFinite(numberValue)) return `${numberValue.toFixed(2)} ms`
    return value
  })

  const secondMetricLabel = computed(() => {
    if (hasApiEvidence.value) return 'HTTP 状态码'
    if (hasUiEvidence.value) return '元素数量'
    return '日志数量'
  })

  const secondMetricValue = computed(() => {
    if (hasApiEvidence.value) return attachmentValue('HTTP状态码') || '-'
    if (hasUiEvidence.value) return String(uiElementAttachments.value.length)
    return String(logAttachments.value.length)
  })

  const secondMetricClass = computed(() => {
    if (hasApiEvidence.value) return httpStatusClass.value
    return ''
  })

  const thirdMetricLabel = computed(() => {
    if (hasApiEvidence.value) return '响应时长'
    if (hasUiEvidence.value) return '元素文本'
    return '附件类型'
  })

  const thirdMetricValue = computed(() => {
    if (hasApiEvidence.value) return responseDuration.value
    if (hasUiEvidence.value) {
      const withText = uiElementAttachments.value.filter((item) => Boolean(item.text)).length
      return `${withText} / ${uiElementAttachments.value.length}`
    }
    return `${new Set(attachments.value.map((item) => item.type || 'text/plain')).size} 类`
  })

  const httpStatusClass = computed(() => {
    const code = Number(attachmentValue('HTTP状态码'))
    if (!Number.isFinite(code)) return ''
    if (code >= 200 && code < 400) return 'mango-pytest-report__metric-value--success'
    if (code >= 400) return 'mango-pytest-report__metric-value--danger'
    return 'mango-pytest-report__metric-value--warning'
  })

  const normalAttachments = computed(() =>
    attachments.value.filter(
      (item) =>
        !httpAttachmentNames.includes(item.name) &&
        !logAttachmentNames.includes(item.name) &&
        !isUiElementAttachment(item)
    )
  )

  const logAttachments = computed(() =>
    attachments.value.filter((item) => logAttachmentNames.includes(item.name))
  )

  function attachmentValue(name: string) {
    return attachments.value.find((item) => item.name === name)?.source || ''
  }

  function parseSource(value?: string) {
    if (!value) return {}
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }

  function parsedAttachment(name: string) {
    return parseSource(attachmentValue(name))
  }

  function isJsonAttachment(attachment: Attachment) {
    return attachment.type?.includes('json') || isJsonString(attachment.source)
  }

  function isJsonString(value?: string) {
    if (!value) return false
    try {
      JSON.parse(value)
      return true
    } catch {
      return false
    }
  }

  function isUiElementAttachment(attachment: Attachment) {
    const source = attachment.source || ''
    return (
      attachment.type?.includes('text/plain') &&
      source.includes('元素表达式：') &&
      source.includes('元素定位方法：')
    )
  }

  function parseUiElementSource(source: string) {
    const read = (label: string) => {
      const line = source.split('\n').find((item) => item.startsWith(`${label}：`))
      return line?.replace(`${label}：`, '').trim() || ''
    }
    return {
      loc: read('元素表达式'),
      method: read('元素定位方法'),
      index: normalizeEmpty(read('元素下标')),
      text: normalizeEmpty(read('元素文本内容')),
      count: normalizeEmpty(read('元素个数')),
    }
  }

  function normalizeEmpty(value: string) {
    return !value || value === 'None' || value === 'null' ? '' : value
  }

  function cleanAnsi(value: string) {
    return value.replace(/\u001b\[[0-9;]*m/g, '')
  }

  function formatTimestamp(value: unknown) {
    const timestamp = Number(value)
    if (!Number.isFinite(timestamp)) return '-'
    const date = new Date(timestamp)
    const pad = (num: number) => String(num).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
      date.getHours()
    )}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  }

  watch(
    () => props.resultData,
    () => {
      if (hasApiEvidence.value) {
        activeTab.value = 'http'
      } else if (hasUiEvidence.value) {
        activeTab.value = 'ui'
      } else {
        activeTab.value = logAttachments.value.length ? 'logs' : 'attachments'
      }
    },
    { immediate: true }
  )
</script>

<style scoped lang="less">
  .mango-pytest-report {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
    color: var(--m-text);
  }

  .mango-pytest-report__hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 160px;
    gap: 12px;
    align-items: stretch;
  }

  .mango-pytest-report__title-block,
  .mango-pytest-report__status-card,
  .mango-pytest-report__metric,
  .mango-pytest-report__labels,
  .mango-pytest-report__evidence-card {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-pytest-report__title-block {
    min-width: 0;
    padding: 14px 16px;
  }

  .mango-pytest-report__eyebrow,
  .mango-pytest-report__status-card span,
  .mango-pytest-report__metric span,
  .mango-pytest-report__muted {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-pytest-report__title-row {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
    margin-top: 4px;
  }

  .mango-pytest-report__title-row h2 {
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

  .mango-pytest-report__title-block p {
    margin: 6px 0 0;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__status-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 12px 14px;
    border-left-width: 4px;
  }

  .mango-pytest-report__status-card strong {
    margin-top: 4px;
    color: var(--m-text);
    font-size: 20px;
    line-height: 28px;
  }

  .mango-pytest-report__status-card--success {
    border-left-color: var(--m-success);
  }

  .mango-pytest-report__status-card--danger {
    border-left-color: var(--m-danger);
  }

  .mango-pytest-report__status-card--muted {
    border-left-color: var(--m-border-strong);
  }

  .mango-pytest-report__metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .mango-pytest-report__metric {
    min-width: 0;
    padding: 10px 12px;
  }

  .mango-pytest-report__metric strong {
    display: block;
    margin-top: 4px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 15px;
    line-height: 23px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__metric-value--success {
    color: var(--m-success) !important;
  }

  .mango-pytest-report__metric-value--danger {
    color: var(--m-danger) !important;
  }

  .mango-pytest-report__metric-value--warning {
    color: var(--m-warning) !important;
  }

  .mango-pytest-report__labels {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 9px 10px;
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__tabs {
    :deep(.arco-tabs-nav) {
      margin-bottom: 10px;
    }

    :deep(.arco-tabs-content) {
      padding-top: 0;
    }
  }

  .mango-pytest-report__http-layout,
  .mango-pytest-report__ui-layout,
  .mango-pytest-report__attachment-list,
  .mango-pytest-report__log-layout {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .mango-pytest-report__evidence-card {
    min-width: 0;
    padding: 12px;
  }

  .mango-pytest-report__evidence-card--wide,
  .mango-pytest-report__request-card {
    grid-column: 1 / -1;
  }

  .mango-pytest-report__section-head {
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-pytest-report__section-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-pytest-report__section-head p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 19px;
  }

  .mango-pytest-report__request-line {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__request-line span {
    height: 24px;
    padding: 0 9px;
    border-radius: 999px;
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 600;
    line-height: 24px;
  }

  .mango-pytest-report__request-line strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 12px;
    font-weight: 500;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__element-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 12px;
  }

  .mango-pytest-report__element-grid span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-pytest-report__element-grid strong {
    display: block;
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 500;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__element-wide {
    grid-column: 1 / -1;
  }

  .mango-pytest-report__mono {
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  }

  .mango-pytest-report pre {
    max-height: 420px;
    margin: 0;
    overflow: auto;
    padding: 10px 12px;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius-md);
    background: var(--m-code-bg);
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 12px;
    line-height: 20px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  @media (max-width: 1024px) {
    .mango-pytest-report__metrics,
    .mango-pytest-report__http-layout,
    .mango-pytest-report__ui-layout,
    .mango-pytest-report__attachment-list,
    .mango-pytest-report__log-layout {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 768px) {
    .mango-pytest-report__hero,
    .mango-pytest-report__metrics,
    .mango-pytest-report__http-layout,
    .mango-pytest-report__ui-layout,
    .mango-pytest-report__attachment-list,
    .mango-pytest-report__log-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
