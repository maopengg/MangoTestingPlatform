<template>
  <aside class="api-response-panel">
    <div class="api-response-head">
      <div>
        <div class="api-response-title">调用结果</div>
        <div class="api-response-subtitle">执行后固定展示最近一次响应</div>
      </div>
      <a-spin v-if="loading" :loading="true" />
    </div>
    <div class="api-response-summary">
      <div>
        <span>状态码</span>
        <strong>{{ result?.code ?? '-' }}</strong>
      </div>
      <div>
        <span>响应时间</span>
        <strong>{{ responseTimeText }}</strong>
      </div>
      <div>
        <span>执行状态</span>
        <a-tag size="small" :color="responseStatusColor">{{ responseStatusText }}</a-tag>
      </div>
    </div>
    <div v-if="result?.error_msg" class="api-response-error">
      {{ result.error_msg }}
    </div>
    <a-tabs default-active-key="response" class="api-response-tabs">
      <a-tab-pane
        key="response"
        title="响应"
        data-testid="qa-views-apitest-info-details-tab-pane-响应"
      >
        <div class="response-section">
          <div
            v-if="result?.headers && Object.keys(result.headers).length > 0"
            class="response-item"
          >
            <span class="response-label">响应头</span>
            <div class="response-value">
              <JsonDisplay :data="result.headers" :default-expanded="false" />
            </div>
          </div>
          <div class="response-item">
            <span class="response-label">响应体</span>
            <div class="response-value">
              <JsonDisplay :data="responseBodyData" />
            </div>
          </div>
        </div>
      </a-tab-pane>
      <a-tab-pane
        key="request"
        title="请求"
        data-testid="qa-views-apitest-info-details-tab-pane-请求"
      >
        <div class="response-section">
          <div v-if="result?.url" class="response-item">
            <span class="response-label">URL</span>
            <span class="response-value">{{ result.url }}</span>
          </div>
          <div
            v-if="result?.request_headers && Object.keys(result.request_headers).length > 0"
            class="response-item"
          >
            <span class="response-label">请求头</span>
            <div class="response-value">
              <JsonDisplay :data="result.request_headers" />
            </div>
          </div>
          <div
            v-if="result?.request_params && Object.keys(result.request_params).length > 0"
            class="response-item"
          >
            <span class="response-label">查询参数</span>
            <div class="response-value">
              <JsonDisplay :data="result.request_params" />
            </div>
          </div>
          <div v-if="hasValue(result?.request_body)" class="response-item">
            <span class="response-label">请求体</span>
            <div class="response-value">
              <JsonDisplay :data="result.request_body" />
            </div>
          </div>
          <div class="response-item">
            <span class="response-label">请求类型</span>
            <span class="response-value">
              {{ result?.request_protocol_type || '-' }} /
              {{ result?.request_body_type || '-' }}
            </span>
          </div>
        </div>
      </a-tab-pane>
      <a-tab-pane
        v-if="hasValue(result?.sse_events)"
        key="sse"
        title="SSE"
        data-testid="qa-views-apitest-info-details-tab-pane-sse"
      >
        <JsonDisplay :data="result?.sse_events" />
      </a-tab-pane>
      <a-tab-pane
        v-if="hasValue(result?.ws_messages)"
        key="websocket"
        title="WebSocket"
        data-testid="qa-views-apitest-info-details-tab-pane-websocket"
      >
        <JsonDisplay
          :data="{
            stop_reason: result?.ws_stop_reason,
            close_code: result?.ws_close_code,
            close_reason: result?.ws_close_reason,
            messages: result?.ws_messages,
          }"
        />
      </a-tab-pane>
      <a-tab-pane
        v-if="result?.response_mode === 'grpc'"
        key="grpc"
        title="gRPC"
        data-testid="qa-views-apitest-info-details-tab-pane-grpc"
      >
        <JsonDisplay
          :data="{
            full_method: result?.grpc_full_method,
            status_code: result?.grpc_status_code,
            status_details: result?.grpc_status_details,
            initial_metadata: result?.grpc_initial_metadata,
            trailing_metadata: result?.grpc_trailing_metadata,
            request_message: result?.request_body,
            response_message: result?.json,
          }"
        />
      </a-tab-pane>
      <a-tab-pane
        v-if="hasValue(result?.cache_all)"
        key="cache"
        title="缓存"
        data-testid="qa-views-apitest-info-details-tab-pane-缓存"
      >
        <JsonDisplay :data="result?.cache_all" />
      </a-tab-pane>
    </a-tabs>
  </aside>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import type { ApiResponseData } from '../types'
  const props = defineProps<{ result: ApiResponseData | null; loading: boolean }>()
  const responseTimeText = computed(() => {
    const time = props.result?.time
    if (time == null || time === '') return '-'
    const value = Number(time)
    return Number.isFinite(value) ? `${value.toFixed(2)} 秒` : `${time} 秒`
  })
  const responseStatusText = computed(() =>
    props.result?.error_msg ? '调用失败' : props.result?.code != null ? '调用完成' : '未执行'
  )
  const responseStatusColor = computed(() =>
    props.result?.error_msg ? 'red' : props.result?.code != null ? 'green' : 'gray'
  )
  const responseBodyData = computed(() => {
    const value = props.result
    return value && Object.prototype.hasOwnProperty.call(value, 'json') ? value.json : value?.text
  })
  function hasValue(value: unknown) {
    if (value == null || value === '') return false
    if (typeof value === 'object') return Object.keys(value).length > 0
    return true
  }
</script>
<style scoped>
  .api-response-panel {
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .api-response-panel {
    display: flex;
    overflow: hidden;
    flex-direction: column;
  }

  .api-response-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .api-response-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-response-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-response-summary {
    display: grid;
    flex-shrink: 0;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-response-summary > div {
    min-width: 0;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .api-response-summary span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-response-summary strong {
    display: block;
    overflow: hidden;
    margin-top: 3px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-response-error {
    flex-shrink: 0;
    margin: 12px 12px 0;
    padding: 8px 10px;
    border: 1px solid color-mix(in srgb, var(--m-danger) 28%, var(--m-border));
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-danger) 8%, var(--m-surface));
    color: var(--m-danger);
    font-size: 12px;
    line-height: 18px;
    word-break: break-word;
  }

  .api-response-tabs {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    padding: 0 12px 12px;
  }

  .api-response-tabs :deep(.arco-tabs-content) {
    height: calc(100% - 42px);
    min-height: 0;
    padding-top: 8px;
  }

  .api-response-tabs :deep(.arco-tabs-content-list),
  .api-response-tabs :deep(.arco-tabs-content-item),
  .api-response-tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }

  .response-section {
    height: 100%;
    overflow: auto;
    padding: 0;
    background-color: var(--m-surface);
  }

  .response-item {
    display: block;
    margin-bottom: 12px;
    padding: 10px 12px;
    background-color: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
    border: 1px solid var(--m-border);
    transition: all 0.2s ease;
  }

  .response-item:hover {
    background-color: var(--m-surface);
    border-color: var(--m-border-strong);
    box-shadow: var(--m-shadow);
  }

  .response-item:last-child {
    margin-bottom: 0;
  }

  .response-label {
    display: block;
    font-weight: 500;
    color: var(--m-text);
    margin-bottom: 8px;
    font-size: 13px;
    line-height: 20px;
  }

  .response-value {
    display: block;
    min-width: 0;
    word-break: break-word;
    font-size: 13px;
    color: var(--m-text-2);
  }

  .error-item .response-label {
    color: var(--m-warning);
  }
</style>
