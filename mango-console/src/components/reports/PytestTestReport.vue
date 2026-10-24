<template>
  <section class="mango-pytest-report">
    <div class="mango-pytest-report__overview">
      <div class="mango-pytest-report__title-block">
        <span class="mango-pytest-report__eyebrow">Pytest 执行明细</span>
        <div class="mango-pytest-report__title-row">
          <h2>{{ resultData?.name || '未命名 Pytest 用例' }}</h2>
          <a-tag color="arcoblue" size="small">{{ evidenceTypeText }}</a-tag>
          <a-tag :color="statusColor" size="small">{{ statusText }}</a-tag>
        </div>
        <div class="mango-pytest-report__title-subrow">
          <p>{{ resultData?.fullName || resultData?.description || '-' }}</p>
          <div class="mango-pytest-report__title-metrics">
            <span><small>开始</small>{{ startTime }}</span>
          </div>
        </div>
      </div>
      <div
        v-if="collectedAttachments.length || compactLabels.length"
        class="mango-pytest-report__summary"
      >
        <a-tag v-if="collectedAttachments.length" size="small">
          采集内容：{{ collectedAttachments.length }}
        </a-tag>
        <a-tag v-for="item in compactLabels" :key="`${item.name}-${item.value}`" size="small">
          {{ item.name }}：{{ item.value }}
        </a-tag>
        <a-tooltip v-if="hiddenLabels.length" :content="hiddenLabelText" position="bottom">
          <a-tag size="small">+{{ hiddenLabels.length }}</a-tag>
        </a-tooltip>
      </div>
    </div>

    <a-tabs v-model:active-key="activeTab" class="mango-pytest-report__tabs" lazy-load>
      <a-tab-pane
        v-if="hasApiEvidence"
        key="http"
        :title="hasUiEvidence ? '辅助接口' : '接口证据'"
        data-testid="qa-components-reports-pytesttestreport-tab-pane-接口证据"
      >
        <div class="mango-pytest-report__http-list">
          <details
            v-for="(evidence, index) in httpEvidence"
            :key="`${evidence.context}-${index}`"
            class="mango-pytest-report__http-call"
            :open="index === 0"
          >
            <summary class="mango-pytest-report__result-row">
              <span class="mango-pytest-report__result-index">{{ index + 1 }}</span>
              <span class="mango-pytest-report__method">
                {{ evidence.request?.method || 'HTTP' }}
              </span>
              <span class="mango-pytest-report__result-main">
                <strong :title="evidence.request?.url || evidence.context">
                  {{ evidence.request?.url || evidence.context || `HTTP 请求 ${index + 1}` }}
                </strong>
                <small v-if="evidence.request?.url && evidence.context">
                  {{ evidence.context }}
                </small>
              </span>
              <span class="mango-pytest-report__result-meta">
                <a-tag v-if="evidence.phase" size="small">{{ evidence.phase }}</a-tag>
                <a-tag :color="httpCodeColor(evidence.response?.status)" size="small">
                  {{ evidence.response?.status ?? '-' }}
                </a-tag>
                <span class="mango-pytest-report__result-duration">
                  {{ formatElapsed(evidence.response?.elapsed_ms) }}
                </span>
                <i class="mango-pytest-report__result-chevron" aria-hidden="true"></i>
              </span>
            </summary>
            <div class="mango-pytest-report__result-body mango-pytest-report__http-grid">
              <section>
                <h4>请求详情</h4>
                <JsonDisplay v-if="evidence.available" :data="evidence.request || {}" />
                <div v-else class="mango-pytest-report__missing-evidence">
                  <strong>该历史记录未保存请求内容</strong>
                  <span>当时只保存了临时附件名，附件已被执行器清理。</span>
                </div>
              </section>
              <section>
                <h4>响应详情</h4>
                <JsonDisplay v-if="evidence.available" :data="evidence.response || {}" />
                <div v-else class="mango-pytest-report__missing-evidence">
                  <strong>该历史记录未保存响应内容</strong>
                  <span>重启执行器并重新执行后，这里会直接展示状态码、耗时和响应体。</span>
                </div>
              </section>
            </div>
          </details>
        </div>
      </a-tab-pane>

      <a-tab-pane
        v-if="hasUiEvidence"
        key="ui"
        title="UI 操作"
        data-testid="qa-components-reports-pytesttestreport-tab-pane-元素证据"
      >
        <div class="mango-pytest-report__ui-layout">
          <details
            v-for="(operation, index) in uiOperations"
            :key="`${operation.context}-${index}`"
            class="mango-pytest-report__evidence-card mango-pytest-report__evidence-card--wide"
            :open="index === 0"
          >
            <summary class="mango-pytest-report__result-row">
              <span class="mango-pytest-report__result-index">{{ index + 1 }}</span>
              <span class="mango-pytest-report__result-main">
                <strong>{{ operationName(operation, index) }}</strong>
                <small>
                  <code>{{ operationMethod(operation) }}</code>
                  <span v-if="operationTarget(operation)"> · {{ operationTarget(operation) }}</span>
                </small>
              </span>
              <span class="mango-pytest-report__result-meta">
                <a-tag v-if="operation.phase" size="small">{{ operation.phase }}</a-tag>
                <a-tag :color="operationStatusColor(operation.result?.status)" size="small">
                  {{ operationStatusText(operation.result?.status) }}
                </a-tag>
                <span class="mango-pytest-report__result-duration">
                  {{ formatElapsed(operation.result?.duration_ms) }}
                </span>
                <i class="mango-pytest-report__result-chevron" aria-hidden="true"></i>
              </span>
            </summary>
            <div
              v-if="operation.available"
              class="mango-pytest-report__result-body mango-pytest-report__operation-grid"
            >
              <section>
                <h4>操作输入</h4>
                <JsonDisplay :data="operation.input" />
              </section>
              <section>
                <h4>执行结果</h4>
                <JsonDisplay :data="operation.result" />
              </section>
            </div>
            <div v-else class="mango-pytest-report__missing-evidence">
              <strong>该历史记录未保存 UI 操作明细</strong>
              <span>重新执行后可查看操作参数、元素信息、执行状态和耗时。</span>
            </div>
          </details>
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

      <a-tab-pane
        v-if="hasLineage"
        key="lineage"
        title="数据血缘"
        data-testid="qa-components-reports-pytesttestreport-tab-pane-数据血缘"
      >
        <PytestDataLineage :graph="lineageGraph" />
      </a-tab-pane>

      <a-tab-pane
        v-if="collectedAttachments.length"
        key="attachments"
        title="采集内容"
        data-testid="qa-components-reports-pytesttestreport-tab-pane-附件详情"
      >
        <div class="mango-pytest-report__attachment-list">
          <details
            v-for="(attachment, index) in collectedAttachments"
            :key="attachment.key"
            class="mango-pytest-report__attachment-item"
          >
            <summary class="mango-pytest-report__attachment-summary">
              <span class="mango-pytest-report__attachment-index">{{ index + 1 }}</span>
              <span class="mango-pytest-report__attachment-kind">
                {{ attachmentKind(attachment) }}
              </span>
              <span class="mango-pytest-report__attachment-main">
                <strong>{{ attachment.name || `采集内容 ${index + 1}` }}</strong>
                <small>
                  {{ [attachment.phase, attachment.context].filter(Boolean).join(' / ') || '用例' }}
                </small>
              </span>
              <span class="mango-pytest-report__attachment-meta">
                <small>{{ attachment.type || 'text/plain' }}</small>
                <span>{{ attachmentSummary(attachment) }}</span>
                <i class="mango-pytest-report__result-chevron" aria-hidden="true"></i>
              </span>
            </summary>
            <div class="mango-pytest-report__attachment-body">
              <JsonDisplay
                v-if="isJsonAttachment(attachment)"
                :data="parseSource(attachment.source)"
                :default-expanded="shouldExpandAttachmentJson(attachment)"
              />
              <pre v-else>{{ attachment.source || '-' }}</pre>
            </div>
          </details>
        </div>
      </a-tab-pane>

      <a-tab-pane
        key="logs"
        title="日志与错误"
        data-testid="qa-components-reports-pytesttestreport-tab-pane-日志与错误"
      >
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
            v-if="
              !resultData?.statusDetails?.message &&
              !resultData?.statusDetails?.trace &&
              !logAttachments.length
            "
            class="mango-empty-state"
          >
            暂无日志与错误信息
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane
        key="raw"
        title="完整数据"
        data-testid="qa-components-reports-pytesttestreport-tab-pane-完整数据"
      >
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
  import PytestDataLineage from './PytestDataLineage.vue'

  type Attachment = {
    name: string
    type?: string
    source?: string
  }

  type CollectedAttachment = Attachment & {
    key: string
    phase: string
    context: string
  }

  type LabelItem = {
    name: string
    value: string
  }

  type HttpEvidence = {
    context: string
    phase: string
    request: Record<string, any>
    response: Record<string, any>
    available: boolean
  }

  type UiOperationEvidence = {
    context: string
    phase: string
    input: Record<string, any>
    result: Record<string, any>
    available: boolean
  }

  const props = defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })

  const activeTab = ref('http')
  const httpAttachmentNames = [
    '请求URL',
    '请求方法',
    '请求头',
    'HTTP状态码',
    '响应时长(ms)',
    '响应数据',
    '响应头',
  ]
  const logAttachmentNames = ['log', 'stdout', 'stderr']
  const uiOperationLabels: Record<string, string> = {
    w_goto: '打开页面',
    w_wait_for_load_state: '等待页面加载',
    w_click: '点击元素',
    w_dblclick: '双击元素',
    w_force_click: '强制点击元素',
    w_input: '输入内容',
    w_type: '逐字输入',
    w_clear: '清空内容',
    w_clear_input: '清空输入框',
    w_hover: '悬停元素',
    w_get_text: '读取文本',
    w_upload_files: '上传文件',
    w_download: '下载文件',
    w_scroll_to_element: '滚动到元素',
    w_right_click: '右键点击元素',
    w_drag_to: '拖拽元素',
    w_press: '键盘按键',
    w_press_sequentially: '连续按键',
    w_focus: '聚焦元素',
    w_blur: '取消聚焦',
    w_check: '勾选元素',
    w_uncheck: '取消勾选',
    w_set_checked: '设置选中状态',
    w_select_option: '选择下拉选项',
    w_ele_screenshot: '元素截图',
  }

  const attachments = computed<Attachment[]>(() => props.resultData?.attachments || [])
  const collectedAttachments = computed<CollectedAttachment[]>(() => {
    const result: CollectedAttachment[] = []
    const append = (items: unknown, phase: string, context: string) => {
      if (!Array.isArray(items)) return
      items.forEach((item, index) => {
        if (!item || typeof item !== 'object') return
        const attachment = item as Attachment
        result.push({
          ...attachment,
          key: `${phase}-${context}-${attachment.name || 'attachment'}-${result.length}-${index}`,
          phase,
          context,
        })
      })
    }
    const walk = (steps: any[], phase: string, parentContext = '') => {
      if (!Array.isArray(steps)) return
      steps.forEach((step) => {
        if (!step || typeof step !== 'object') return
        const stepName = String(step.name || '未命名步骤')
        const context = parentContext ? `${parentContext} / ${stepName}` : stepName
        append(step.attachments, phase, context)
        walk(step.steps, phase, context)
      })
    }

    append(props.resultData?.attachments, '用例', '')
    walk(props.resultData?.steps, '步骤')
    walk(props.resultData?.fixtures?.befores, '前置')
    walk(props.resultData?.fixtures?.afters, '清理')
    return result
  })
  const labels = computed<LabelItem[]>(() => props.resultData?.labels || [])
  const lineageGraph = computed<Record<string, any>>(() => {
    const attachment = [...attachments.value].reverse().find((item) => item.name === '数据血缘')
    const graph = parseSource(attachment?.source)
    return isRecord(graph) ? graph : {}
  })
  const hasLineage = computed(
    () => Array.isArray(lineageGraph.value.nodes) && lineageGraph.value.nodes.length > 0
  )
  const httpEvidence = computed<HttpEvidence[]>(() => {
    const stepEvidence: HttpEvidence[] = []
    walkEvidenceSteps((step, phase) => {
      const requestAttachment = findStepAttachment(step, '请求信息')
      const responseAttachment = findStepAttachment(step, '响应信息')
      const request = parsedStepAttachment(step, '请求信息')
      const response = parsedStepAttachment(step, '响应信息')
      if (requestAttachment || responseAttachment) {
        stepEvidence.push({
          context: String(step?.name || ''),
          phase,
          request: isRecord(request) ? request : requestFromStepName(step?.name),
          response: isRecord(response) ? response : {},
          available: isRecord(request) || isRecord(response),
        })
      }
    })
    if (stepEvidence.length) return stepEvidence

    if (!httpAttachmentNames.some((name) => Boolean(attachmentValue(name)))) return []
    return [
      {
        context: '接口调用',
        phase: '',
        request: {
          method: attachmentValue('请求方法'),
          url: attachmentValue('请求URL'),
          headers: parsedAttachment('请求头'),
        },
        response: {
          status: attachmentValue('HTTP状态码'),
          elapsed_ms: attachmentValue('响应时长(ms)'),
          headers: parsedAttachment('响应头'),
          body: parsedAttachment('响应数据'),
        },
        available: true,
      },
    ]
  })
  const hasApiEvidence = computed(() => httpEvidence.value.length > 0)
  const uiOperations = computed<UiOperationEvidence[]>(() => {
    const operations: UiOperationEvidence[] = []
    walkEvidenceSteps((step, phase) => {
      const inputAttachment = findStepAttachment(step, '操作信息')
      const resultAttachment = findStepAttachment(step, '操作结果')
      if (!inputAttachment && !resultAttachment) return
      const input = parseSource(inputAttachment?.source)
      const result = parseSource(resultAttachment?.source)
      operations.push({
        context: String(step?.name || ''),
        phase,
        input: isRecord(input) ? input : {},
        result: isRecord(result) ? result : {},
        available: isRecord(input) || isRecord(result),
      })
    })
    return operations
  })
  const uiElementAttachments = computed(() =>
    attachments.value
      .filter((item) => isUiElementAttachment(item))
      .map((item) => ({
        name: item.name,
        ...parseUiElementSource(item.source || ''),
      }))
  )
  const hasUiEvidence = computed(
    () => uiOperations.value.length > 0 || uiElementAttachments.value.length > 0
  )
  const evidenceTypeText = computed(() => {
    if (hasUiEvidence.value) return 'UI 证据'
    if (hasApiEvidence.value) return 'API 证据'
    return '通用证据'
  })

  const visibleLabels = computed(() =>
    labels.value.filter((item) =>
      ['epic', 'feature', 'story', 'tag', 'suite', 'package', 'framework'].includes(item.name)
    )
  )
  const compactLabels = computed(() => visibleLabels.value.slice(0, 4))
  const hiddenLabels = computed(() => visibleLabels.value.slice(4))
  const hiddenLabelText = computed(() =>
    hiddenLabels.value.map((item) => `${item.name}：${item.value}`).join('  ·  ')
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

  const startTime = computed(() => formatTimestamp(props.resultData?.start))

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

  function parsedStepAttachment(step: any, name: string) {
    const attachment = findStepAttachment(step, name)
    return parseSource(attachment?.source)
  }

  function findStepAttachment(step: any, name: string): Attachment | null {
    if (!Array.isArray(step?.attachments)) return null
    return step.attachments.find((item: Attachment) => item?.name === name) || null
  }

  function requestFromStepName(stepName: unknown) {
    const match = String(stepName || '').match(/^HTTP\s+(\S+)\s+(.+)$/i)
    return match ? { method: match[1], url: match[2] } : {}
  }

  function walkSteps(steps: any[], visit: (step: any) => void) {
    if (!Array.isArray(steps)) return
    steps.forEach((step) => {
      if (!step || typeof step !== 'object') return
      visit(step)
      walkSteps(step.steps, visit)
    })
  }

  function walkEvidenceSteps(visit: (step: any, phase: string) => void) {
    const walk = (steps: any[], phase: string) => {
      walkSteps(steps, (step) => visit(step, phase))
    }
    walk(props.resultData?.steps || [], '')
    walk(props.resultData?.fixtures?.befores || [], '前置')
    walk(props.resultData?.fixtures?.afters || [], '清理')
  }

  function isRecord(value: unknown): value is Record<string, any> {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
  }

  function formatElapsed(value: unknown) {
    if (value === null || value === undefined || value === '') return '-'
    const numberValue = Number(value)
    return Number.isFinite(numberValue) ? `${numberValue.toFixed(2)} ms` : '-'
  }

  function httpCodeColor(value: unknown) {
    const code = Number(value)
    if (code >= 200 && code < 400) return 'green'
    if (code >= 400) return 'red'
    return 'gray'
  }

  function operationStatusText(value: unknown) {
    if (value === 'passed') return '成功'
    if (value === 'failed') return '失败'
    return '未知'
  }

  function operationStatusColor(value: unknown) {
    if (value === 'passed') return 'green'
    if (value === 'failed') return 'red'
    return 'gray'
  }

  function operationMethod(item: UiOperationEvidence) {
    const contextMethod = String(item.context || '')
      .replace(/^UI\s*操作\s*·\s*/i, '')
      .split('·')[0]
      .trim()
    return String(item.input?.operation || contextMethod || 'unknown')
  }

  function operationName(item: UiOperationEvidence, index: number) {
    const method = operationMethod(item)
    if (method === 'unknown') return `UI 操作 ${index + 1}`
    return uiOperationLabels[method] || `执行 ${method.replace(/^w_/, '').replaceAll('_', ' ')}`
  }

  function operationTarget(item: UiOperationEvidence) {
    const namedElement = item.input?.named_elements?.[0]?.name
    const value =
      namedElement ??
      item.input?.arguments?.[0] ??
      item.input?.keyword_arguments?.locator ??
      item.input?.keyword_arguments?.text ??
      ''
    if (value === null || typeof value === 'object') return ''
    return String(value)
  }

  function isJsonAttachment(attachment: Attachment) {
    return attachment.type?.includes('json') || isJsonString(attachment.source)
  }

  function attachmentKind(attachment: Attachment) {
    const type = String(attachment.type || '').toLowerCase()
    if (isJsonAttachment(attachment)) return 'JSON'
    if (type.includes('xml')) return 'XML'
    if (type.includes('html')) return 'HTML'
    if (type.includes('csv')) return 'CSV'
    if (type.includes('image')) return 'IMG'
    return 'TEXT'
  }

  function attachmentSummary(attachment: Attachment) {
    const value = parseSource(attachment.source)
    if (Array.isArray(value)) return `${value.length} 项`
    if (isRecord(value)) return `${Object.keys(value).length} 个字段`
    return `${String(attachment.source || '').length} 字符`
  }

  function shouldExpandAttachmentJson(attachment: Attachment) {
    return countJsonFields(parseSource(attachment.source), 50) < 50
  }

  function countJsonFields(value: unknown, limit: number): number {
    if (!value || typeof value !== 'object') return 0
    const children = Array.isArray(value) ? value : Object.values(value)
    let count = children.length
    for (const child of children) {
      if (count >= limit) return count
      count += countJsonFields(child, limit - count)
    }
    return count
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
      if (hasUiEvidence.value) {
        activeTab.value = 'ui'
      } else if (hasApiEvidence.value) {
        activeTab.value = 'http'
      } else if (hasLineage.value) {
        activeTab.value = 'lineage'
      } else if (collectedAttachments.value.length) {
        activeTab.value = 'attachments'
      } else if (logAttachments.value.length) {
        activeTab.value = 'logs'
      } else {
        activeTab.value = 'raw'
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

  .mango-pytest-report__overview,
  .mango-pytest-report__title-block,
  .mango-pytest-report__http-call,
  .mango-pytest-report__evidence-card {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-pytest-report__overview {
    flex: 0 0 auto;
    min-width: 0;
    overflow: hidden;
  }

  .mango-pytest-report__title-block {
    padding: 10px 12px 8px;
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .mango-pytest-report__eyebrow,
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
    margin-top: 2px;
  }

  .mango-pytest-report__title-row h2 {
    min-width: 0;
    margin: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 17px;
    font-weight: 600;
    line-height: 26px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__title-subrow {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 16px;
    margin-top: 2px;
  }

  .mango-pytest-report__title-block p {
    min-width: 120px;
    flex: 1 1 auto;
    margin: 0;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__title-metrics {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 10px;
  }

  .mango-pytest-report__title-metrics > span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--m-text);
    font-size: 12px;
    line-height: 20px;
    white-space: nowrap;
  }

  .mango-pytest-report__title-metrics small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-pytest-report__summary {
    display: flex;
    min-width: 0;
    min-height: 36px;
    align-items: center;
    flex: 0 0 auto;
    flex-wrap: wrap;
    gap: 6px 12px;
    padding: 6px 12px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__summary :deep(.arco-tag) {
    max-width: min(190px, 100%);
    flex: 0 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__tabs {
    flex: 0 0 auto;

    :deep(.arco-tabs-nav) {
      margin-bottom: 10px;
    }

    :deep(.arco-tabs-content) {
      padding-top: 0;
    }
  }

  .mango-pytest-report__http-grid,
  .mango-pytest-report__ui-layout,
  .mango-pytest-report__log-layout {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .mango-pytest-report__attachment-list {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 8px;
  }

  .mango-pytest-report__attachment-item {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-pytest-report__attachment-summary {
    display: flex;
    min-height: 52px;
    box-sizing: border-box;
    align-items: center;
    gap: 10px;
    padding: 7px 12px;
    cursor: pointer;
    list-style: none;
    transition: background var(--m-motion-duration-fast);
  }

  .mango-pytest-report__attachment-summary::-webkit-details-marker {
    display: none;
  }

  .mango-pytest-report__attachment-summary:hover {
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__attachment-summary:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }

  .mango-pytest-report__attachment-index {
    width: 22px;
    flex: 0 0 22px;
    color: var(--m-muted);
    font-size: 12px;
    text-align: center;
  }

  .mango-pytest-report__attachment-kind {
    min-width: 44px;
    flex: 0 0 auto;
    padding: 2px 7px;
    border-radius: var(--m-radius-sm);
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 10px;
    font-weight: 600;
    line-height: 18px;
    text-align: center;
  }

  .mango-pytest-report__attachment-main {
    display: flex;
    min-width: 0;
    flex: 1 1 auto;
    flex-direction: column;
  }

  .mango-pytest-report__attachment-main strong,
  .mango-pytest-report__attachment-main small,
  .mango-pytest-report__attachment-meta small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__attachment-main strong {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-pytest-report__attachment-main small {
    color: var(--m-muted);
    font-size: 11px;
    line-height: 17px;
  }

  .mango-pytest-report__attachment-meta {
    display: inline-flex;
    min-width: 0;
    flex: 0 1 auto;
    align-items: center;
    gap: 10px;
    color: var(--m-muted);
    font-size: 11px;
    white-space: nowrap;
  }

  .mango-pytest-report__attachment-meta small {
    max-width: 150px;
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-pytest-report__attachment-body {
    min-width: 0;
    padding: 4px 12px 12px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__attachment-body :deep(.mango-json-display-toolbar) {
    margin: 8px 0;
  }

  .mango-pytest-report__attachment-body :deep(.arco-btn) {
    height: 28px;
    padding: 0 10px;
    font-size: 12px;
  }

  .mango-pytest-report__attachment-item[open] > .mango-pytest-report__attachment-summary {
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__attachment-item[open]
    > .mango-pytest-report__attachment-summary
    .mango-pytest-report__result-chevron {
    transform: rotate(225deg);
  }

  .mango-pytest-report__operation-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  .mango-pytest-report__operation-grid > section {
    min-width: 0;
  }

  .mango-pytest-report__operation-grid h4 {
    margin: 0 0 7px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-pytest-report__http-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mango-pytest-report__http-call {
    min-width: 0;
    overflow: hidden;
    padding: 0;
  }

  .mango-pytest-report__result-row {
    display: flex;
    min-height: 54px;
    box-sizing: border-box;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--m-surface);
    cursor: pointer;
    list-style: none;
    transition: background var(--m-motion-duration-fast);
  }

  .mango-pytest-report__result-row::-webkit-details-marker {
    display: none;
  }

  .mango-pytest-report__result-row:hover {
    background: var(--m-surface-soft);
  }

  .mango-pytest-report__result-row:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }

  .mango-pytest-report__result-index {
    display: inline-flex;
    width: 24px;
    height: 24px;
    flex: 0 0 24px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 600;
  }

  .mango-pytest-report__method {
    min-width: 48px;
    flex: 0 0 auto;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 11px;
    font-weight: 600;
    line-height: 20px;
    text-align: center;
  }

  .mango-pytest-report__result-main {
    display: flex;
    min-width: 0;
    flex: 1 1 auto;
    flex-direction: column;
  }

  .mango-pytest-report__result-main strong,
  .mango-pytest-report__result-main small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-report__result-main strong {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-pytest-report__result-main small {
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-pytest-report__result-main code {
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  }

  .mango-pytest-report__result-meta {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 8px;
  }

  .mango-pytest-report__result-duration {
    min-width: 66px;
    color: var(--m-muted);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 11px;
    text-align: right;
    white-space: nowrap;
  }

  .mango-pytest-report__result-chevron {
    width: 7px;
    height: 7px;
    flex: 0 0 7px;
    border-right: 1.5px solid var(--m-muted);
    border-bottom: 1.5px solid var(--m-muted);
    transform: rotate(45deg);
    transition: transform var(--m-motion-duration-fast);
  }

  details[open] > .mango-pytest-report__result-row {
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  details[open] > .mango-pytest-report__result-row .mango-pytest-report__result-chevron {
    transform: rotate(225deg);
  }

  .mango-pytest-report__result-body {
    padding: 12px;
    background: var(--m-surface);
  }

  .mango-pytest-report__http-grid > section {
    min-width: 0;
  }

  .mango-pytest-report__http-grid h4 {
    margin: 0 0 7px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-pytest-report__missing-evidence {
    display: flex;
    min-height: 132px;
    box-sizing: border-box;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 18px;
    border: 1px dashed var(--m-border-strong);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    text-align: center;
  }

  .mango-pytest-report__missing-evidence strong {
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-pytest-report__missing-evidence span {
    max-width: 360px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-pytest-report__evidence-card {
    min-width: 0;
    padding: 12px;
  }

  details.mango-pytest-report__evidence-card {
    overflow: hidden;
    padding: 0;
  }

  .mango-pytest-report__evidence-card--wide {
    grid-column: 1 / -1;
  }

  .mango-pytest-report__section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-pytest-report__http-status {
    display: flex;
    flex: none;
    align-items: center;
    gap: 8px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-pytest-report__section-head h3 {
    display: flex;
    align-items: center;
    gap: 6px;
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

  @media (max-width: 1100px) {
    .mango-pytest-report__http-grid,
    .mango-pytest-report__ui-layout,
    .mango-pytest-report__log-layout {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .mango-pytest-report__http-grid,
    .mango-pytest-report__ui-layout,
    .mango-pytest-report__log-layout {
      grid-template-columns: 1fr;
    }

    .mango-pytest-report__attachment-meta small {
      display: none;
    }

    .mango-pytest-report__summary {
      flex-wrap: wrap;
      overflow: visible;
    }

    .mango-pytest-report__title-subrow {
      align-items: flex-start;
      flex-direction: column;
      gap: 4px;
    }

    .mango-pytest-report__title-metrics {
      width: 100%;
      flex-wrap: wrap;
    }

    .mango-pytest-report__result-row {
      align-items: flex-start;
      flex-wrap: wrap;
    }

    .mango-pytest-report__result-main {
      min-width: calc(100% - 100px);
    }

    .mango-pytest-report__result-meta {
      width: 100%;
      justify-content: flex-end;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-pytest-report__result-row,
    .mango-pytest-report__result-chevron {
      transition: none;
    }
  }
</style>
