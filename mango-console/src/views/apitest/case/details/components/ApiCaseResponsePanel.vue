<template>
  <a-tabs :key="renderKey" :active-key="selectedTab" @tab-click="emit('change', String($event))">
    <a-tab-pane
      key="20"
      title="基础信息"
      data-testid="qa-views-apitest-case-details-tab-pane-基础信息"
    >
      <section class="mango-api-case-response-summary">
        <div class="mango-api-case-response-summary__url">
          <span>请求 URL</span>
          <a-tooltip :content="request.url || '-'" position="top" mini
            ><strong>{{ request.url || '-' }}</strong></a-tooltip
          >
        </div>
        <div class="mango-api-case-response-summary__metrics">
          <div class="mango-api-case-response-summary__metric"
            ><span>请求方法</span
            ><a-tag size="small" color="arcoblue">{{ request.method || '-' }}</a-tag></div
          >
          <div class="mango-api-case-response-summary__metric"
            ><span>响应状态码</span
            ><a-tag size="small" :color="httpStatusColor(response.code)">{{
              response.code ?? '-'
            }}</a-tag></div
          >
          <div class="mango-api-case-response-summary__metric"
            ><span>响应耗时</span><strong>{{ responseTime }}</strong></div
          >
          <div class="mango-api-case-response-summary__metric"
            ><span>测试时间</span><strong>{{ result.test_time || '-' }}</strong></div
          >
          <div
            v-for="metric in extraMetrics"
            :key="metric.key"
            class="mango-api-case-response-summary__metric"
          >
            <span>{{ metric.label }}</span>
            <a-tag v-if="metric.tagColor" size="small" :color="metric.tagColor">{{
              metric.value
            }}</a-tag>
            <a-tooltip v-else :content="String(metric.value)" position="top" mini
              ><strong>{{ metric.value }}</strong></a-tooltip
            >
          </div>
        </div>
        <a-tooltip v-if="result.error_message" :content="result.error_message" position="top" mini>
          <div class="mango-api-case-failure-reason"
            ><span>失败原因</span><strong>{{ result.error_message }}</strong></div
          >
        </a-tooltip>
      </section>
    </a-tab-pane>
    <a-tab-pane
      key="21"
      title="请求/响应头"
      data-testid="qa-views-apitest-case-details-tab-pane-请求-响应头"
    >
      <div v-if="isActive('21')" class="mango-response-headers">
        <section class="mango-response-headers__section"
          ><div class="mango-response-headers__title">请求头</div
          ><JsonDisplay :data="response.request_headers" :default-expanded="false"
        /></section>
        <section class="mango-response-headers__section"
          ><div class="mango-response-headers__title">响应头</div
          ><JsonDisplay :data="response.headers" :default-expanded="false"
        /></section>
      </div>
    </a-tab-pane>
    <a-tab-pane
      key="25"
      title="请求数据"
      data-testid="qa-views-apitest-case-details-tab-pane-请求数据"
    >
      <div v-if="isActive('25')" class="mango-request-data">
        <section v-if="hasValue(requestParams)" class="mango-request-data__section"
          ><div class="mango-request-data__head"
            ><strong>Query 参数</strong><a-tag size="small">URL Query</a-tag></div
          ><JsonDisplay :data="requestParams"
        /></section>
        <section v-if="hasValue(requestBody)" class="mango-request-data__section"
          ><div class="mango-request-data__head"
            ><strong>请求体</strong
            ><a-space size="mini"
              ><a-tag size="small" color="arcoblue">{{ requestBodyTypeLabel }}</a-tag
              ><span v-if="requestContentType">{{ requestContentType }}</span></a-space
            ></div
          ><JsonDisplay :data="requestBody"
        /></section>
        <section v-if="hasValue(requestFiles)" class="mango-request-data__section"
          ><div class="mango-request-data__head"
            ><strong>上传文件</strong><a-tag size="small" color="purple">Multipart</a-tag></div
          ><JsonDisplay :data="requestFiles"
        /></section>
      </div>
    </a-tab-pane>
    <a-tab-pane
      v-if="standardResponse && hasJson"
      key="23"
      title="响应JSON"
      data-testid="qa-views-apitest-case-details-tab-pane-响应json"
    >
      <div class="m-2"
        ><JsonDisplay
          v-if="isActive('23')"
          :data="response.json"
          :extract-text="response.text"
          :jsonpath="true"
      /></div>
    </a-tab-pane>
    <a-tab-pane
      v-else-if="standardResponse"
      key="24"
      title="响应文本"
      data-testid="qa-views-apitest-case-details-tab-pane-响应文本"
    >
      <div class="m-2"><JsonDisplay v-if="isActive('24')" :data="response.text" /></div>
    </a-tab-pane>
    <a-tab-pane
      v-if="responseMode === 'sse'"
      key="26"
      title="SSE事件"
      data-testid="qa-views-apitest-case-details-tab-pane-sse事件"
    >
      <div class="m-2"><JsonDisplay v-if="isActive('26')" :data="response.sse_events" /></div>
    </a-tab-pane>
    <a-tab-pane
      v-if="responseMode === 'websocket'"
      key="27"
      title="WebSocket消息"
      data-testid="qa-views-apitest-case-details-tab-pane-websocket消息"
    >
      <div class="m-2"
        ><JsonDisplay
          v-if="isActive('27')"
          :data="{
            stop_reason: response.ws_stop_reason,
            close_code: response.ws_close_code,
            close_reason: response.ws_close_reason,
            messages: response.ws_messages,
          }"
      /></div>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  type ResponseMetric = { key: string; label: string; value: string | number; tagColor?: string }
  const props = withDefaults(
    defineProps<{
      item: any
      activeKey: string
      activeRoot: boolean
      protocolType?: string
      bodyType?: string
    }>(),
    { protocolType: 'http', bodyType: 'none' }
  )
  const emit = defineEmits<{ (event: 'change', value: string): void }>()
  const result = computed(() => props.item?.result_data || {})
  const request = computed(() => result.value.request || {})
  const response = computed(() => result.value.response || {})
  const hasJson = computed(() => hasValue(response.value.json))
  const responseMode = computed(() =>
    String(
      response.value.response_mode ||
        response.value.request_protocol_type ||
        props.protocolType ||
        'http'
    ).toLowerCase()
  )
  const standardResponse = computed(() => responseMode.value !== 'websocket')
  const defaultResultTab = computed(() =>
    responseMode.value === 'sse'
      ? '26'
      : responseMode.value === 'websocket'
      ? '27'
      : hasJson.value
      ? '23'
      : '24'
  )
  const selectedTab = computed(() => {
    const key = String(props.activeKey)
    if (['20', '21', '25'].includes(key)) return key
    if (key === '23' && standardResponse.value && hasJson.value) return key
    if (key === '24' && standardResponse.value && !hasJson.value) return key
    if (key === '26' && responseMode.value === 'sse') return key
    if (key === '27' && responseMode.value === 'websocket') return key
    return defaultResultTab.value
  })
  const renderKey = computed(
    () => `${props.item?.id || 'scenario'}:${responseMode.value}:${hasJson.value ? 'json' : 'text'}`
  )
  const requestParams = computed(() => response.value.request_params ?? request.value.params)
  const requestBody = computed(
    () =>
      response.value.request_body ??
      request.value.request_body ??
      request.value.data ??
      request.value.json
  )
  const requestFiles = computed(
    () => response.value.request_file ?? request.value.request_files ?? request.value.file
  )
  const requestContentType = computed(
    () => response.value.request_content_type ?? request.value.request_content_type ?? ''
  )
  const requestBodyTypeLabel = computed(() =>
    bodyTypeLabel(response.value.request_body_type ?? request.value.body_type ?? props.bodyType)
  )
  const responseTime = computed(() => {
    const value = Number(response.value.time)
    return Number.isFinite(value) ? `${value.toFixed(2)} 秒` : '-'
  })
  const extraMetrics = computed<ResponseMetric[]>(buildExtraMetrics)

  function hasValue(value: any) {
    if (value === undefined || value === null || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return true
  }
  function isActive(key: string) {
    return props.activeRoot && selectedTab.value === key
  }
  function httpStatusColor(value: any) {
    const status = Number(value)
    if (!Number.isFinite(status)) return 'gray'
    if (status >= 200 && status < 300) return 'green'
    if (status >= 300 && status < 400) return 'orange'
    if (status >= 400) return 'red'
    return 'arcoblue'
  }
  function protocolLabel(value: any) {
    const protocol = String(value || 'http').toLowerCase()
    return (
      (
        { http: 'HTTP', sse: 'SSE', websocket: 'WebSocket', grpc: 'gRPC', mcp: 'MCP' } as Record<
          string,
          string
        >
      )[protocol] || String(value || '-').toUpperCase()
    )
  }
  function protocolColor(value: any) {
    return (
      ({ http: 'arcoblue', sse: 'orange', grpc: 'purple', mcp: 'green' } as Record<string, string>)[
        String(value || 'http').toLowerCase()
      ] || 'gray'
    )
  }
  function bodyTypeLabel(value: any) {
    const type = String(value || 'none').toLowerCase()
    return (
      (
        {
          none: '无请求体',
          json: 'JSON',
          form: 'Form',
          raw: 'Raw',
          multipart: 'Multipart',
        } as Record<string, string>
      )[type] || String(value || '-')
    )
  }
  function headerValue(headers: any, name: string) {
    if (!headers || typeof headers !== 'object' || Array.isArray(headers)) return ''
    const entry = Object.entries(headers).find(([key]) => key.toLowerCase() === name.toLowerCase())
    return entry?.[1] == null ? '' : String(entry[1])
  }
  function responseDataType() {
    if (responseMode.value === 'sse') return 'SSE 事件流'
    if (responseMode.value === 'websocket') return 'WebSocket 消息'
    if (responseMode.value === 'grpc') return 'gRPC Message'
    if (responseMode.value === 'mcp') return 'MCP Content'
    if (hasJson.value) return 'JSON'
    if (hasValue(response.value.text)) return 'Text'
    if (hasValue(response.value.headers)) return 'Headers'
    return '无响应体'
  }
  function buildExtraMetrics() {
    const protocol =
      request.value.protocol_type ||
      response.value.request_protocol_type ||
      response.value.response_mode ||
      props.protocolType
    const type = request.value.body_type || response.value.request_body_type || props.bodyType
    const metrics: ResponseMetric[] = [
      {
        key: 'protocol',
        label: '协议类型',
        value: protocolLabel(protocol),
        tagColor: protocolColor(protocol),
      },
      { key: 'body-type', label: '请求体类型', value: bodyTypeLabel(type) },
      { key: 'response-type', label: '响应数据类型', value: responseDataType() },
    ]
    const append = (key: string, label: string, value: any, tagColor?: string) => {
      if (value !== undefined && value !== null && value !== '')
        metrics.push({ key, label, value: String(value), tagColor })
    }
    append(
      'request-content-type',
      '请求 Content-Type',
      response.value.request_content_type || request.value.request_content_type
    )
    append(
      'response-content-type',
      '响应 Content-Type',
      headerValue(response.value.headers, 'content-type')
    )
    if (responseMode.value === 'sse') {
      append(
        'sse-event-count',
        'SSE 事件数',
        Array.isArray(response.value.sse_events) ? response.value.sse_events.length : null
      )
      append('sse-stop-reason', 'SSE 停止原因', response.value.sse_stop_reason)
    }
    if (responseMode.value === 'websocket') {
      append(
        'ws-message-count',
        'WebSocket 消息数',
        Array.isArray(response.value.ws_messages) ? response.value.ws_messages.length : null
      )
      append(
        'ws-close-code',
        'WebSocket 关闭码',
        response.value.ws_close_code,
        Number(response.value.ws_close_code) === 1000 ? 'green' : 'orange'
      )
      append('ws-close-reason', 'WebSocket 关闭原因', response.value.ws_close_reason)
      append('ws-stop-reason', 'WebSocket 停止原因', response.value.ws_stop_reason)
    }
    if (responseMode.value === 'grpc') {
      append(
        'grpc-full-method',
        'gRPC 方法',
        response.value.grpc_full_method || request.value.grpc_full_method
      )
      append(
        'grpc-status-code',
        'gRPC 状态码',
        response.value.grpc_status_code,
        String(response.value.grpc_status_code).toUpperCase() === 'OK' ? 'green' : 'red'
      )
      append('grpc-status-details', 'gRPC 状态详情', response.value.grpc_status_details)
    }
    if (responseMode.value === 'mcp') {
      append(
        'mcp-tool-name',
        'MCP 工具',
        response.value.mcp_tool_name || request.value.mcp_tool_name
      )
      append('mcp-protocol-version', 'MCP 协议版本', response.value.mcp_protocol_version)
      if (typeof response.value.mcp_is_error === 'boolean')
        append(
          'mcp-result',
          'MCP 调用结果',
          response.value.mcp_is_error ? '失败' : '成功',
          response.value.mcp_is_error ? 'red' : 'green'
        )
    }
    return metrics
  }
</script>

<style scoped>
  .mango-api-case-response-summary {
    display: flex;
    min-width: 0;
    margin: 8px;
    flex-direction: column;
    gap: 10px;
  }
  .mango-api-case-response-summary__url {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }
  .mango-api-case-response-summary__url > span {
    flex: none;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }
  .mango-api-case-response-summary__url strong {
    display: block;
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-api-case-response-summary__metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 8px;
  }
  .mango-api-case-response-summary__metric {
    display: flex;
    min-width: 0;
    min-height: 68px;
    padding: 10px 12px;
    flex-direction: column;
    align-items: flex-start;
    justify-content: space-between;
    gap: 6px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-api-case-response-summary__metric > span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .mango-api-case-response-summary__metric > strong {
    max-width: 100%;
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    font-variant-numeric: tabular-nums;
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-api-case-failure-reason {
    display: flex;
    min-width: 0;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid color-mix(in srgb, var(--m-danger) 28%, var(--m-border));
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-danger) 8%, var(--m-surface));
    line-height: 20px;
  }
  .mango-api-case-failure-reason > span {
    flex: none;
    color: var(--m-danger);
    font-size: 12px;
    font-weight: 600;
  }
  .mango-api-case-failure-reason > strong {
    display: -webkit-box;
    overflow: hidden;
    min-width: 0;
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 500;
    word-break: break-word;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }
  .mango-response-headers,
  .mango-request-data {
    display: grid;
    gap: 10px;
    padding: 8px;
  }
  .mango-response-headers__section,
  .mango-request-data__section {
    min-width: 0;
    padding: 8px 10px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }
  .mango-response-headers__title {
    margin-bottom: 4px;
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }
  .mango-request-data__head {
    display: flex;
    min-width: 0;
    margin-bottom: 4px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .mango-request-data__head strong {
    flex: none;
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }
  .mango-request-data__head span {
    display: block;
    max-width: 240px;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
