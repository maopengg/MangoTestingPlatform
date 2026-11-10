<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="调用 Mock 接口"
    :width="560"
    ok-text="发送请求"
    cancel-text="关闭"
    :ok-loading="loading"
    :on-before-ok="runDebug"
    :closable="!loading"
    :mask-closable="!loading"
    :cancel-button-props="{ disabled: loading }"
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="loading" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="请求方法">
        <a-select
          v-model="draft.method"
          :options="methodOptions"
          :disabled="methodOptions.length === 1"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="请求路径"><a-input v-model="draft.path" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="Query(JSON)"
        ><a-textarea v-model="draft.query" :auto-size="{ minRows: 2, maxRows: 4 }"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="请求头(JSON)"
        ><a-textarea v-model="draft.headers" :auto-size="{ minRows: 2, maxRows: 4 }"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="请求体"
        ><a-textarea v-model="draft.body" :auto-size="{ minRows: 4, maxRows: 8 }"
      /></a-form-item>
    </a-form>
  </a-modal>

  <BaseSidePanel
    v-model:visible="resultVisible"
    :title="result ? `Mock 调用结果 · HTTP ${result.status}` : 'Mock 调用结果'"
    width="1080px"
    :show-footer="false"
  >
    <div v-if="result" class="mango-mock-side-panel-content mango-mock-invoke-result">
      <a-descriptions class="mango-mock-invoke-summary" :column="4" size="small" bordered>
        <a-descriptions-item label="调用结果">
          <a-tag size="small" :color="result.ok ? 'green' : 'red'">{{
            result.ok ? '成功' : '失败'
          }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="HTTP 状态"
          >{{ result.status }} {{ result.status_text }}</a-descriptions-item
        >
        <a-descriptions-item label="耗时">{{ result.duration_ms }} ms</a-descriptions-item>
        <a-descriptions-item label="Trace ID">{{ result.trace_id || '-' }}</a-descriptions-item>
        <a-descriptions-item label="请求方法">{{ result.request_method }}</a-descriptions-item>
        <a-descriptions-item label="请求 URL" :span="3">{{
          result.request_url
        }}</a-descriptions-item>
      </a-descriptions>

      <a-tabs class="mango-section-card mango-mock-result-tabs" default-active-key="request">
        <a-tab-pane key="request" title="请求信息">
          <div class="mango-mock-result-tab-description">本次真实发送到 Mock 服务的请求内容</div>
          <div class="mango-mock-result-grid">
            <div>
              <div class="mango-mock-result-label">Query 参数</div>
              <div class="mango-mock-json-panel">
                <JsonDisplay
                  :data="result.request_query || {}"
                  :show-drawer-button="false"
                  :default-expanded="false"
                />
              </div>
            </div>
            <div>
              <div class="mango-mock-result-label">请求头</div>
              <div class="mango-mock-json-panel">
                <JsonDisplay
                  :data="result.request_headers || {}"
                  :show-drawer-button="false"
                  :default-expanded="false"
                />
              </div>
            </div>
            <div class="mango-mock-result-grid__full">
              <div class="mango-mock-result-label">请求体</div>
              <div class="mango-mock-json-panel">
                <JsonDisplay
                  :data="result.request_body"
                  :show-drawer-button="false"
                  :default-expanded="false"
                />
              </div>
            </div>
          </div>
        </a-tab-pane>
        <a-tab-pane key="response" title="响应信息">
          <div class="mango-mock-result-tab-description">Mock 服务实际返回的响应内容</div>
          <div class="mango-mock-result-grid mango-mock-result-grid--fill">
            <div>
              <div class="mango-mock-result-label">响应头</div>
              <div class="mango-mock-json-panel mango-mock-json-panel--headers">
                <JsonDisplay
                  :data="result.response_headers || {}"
                  :show-drawer-button="false"
                  :default-expanded="false"
                />
              </div>
            </div>
            <div class="mango-mock-result-grid__item--fill">
              <div class="mango-mock-result-label">响应体</div>
              <div class="mango-mock-json-panel mango-mock-json-panel--fill">
                <JsonDisplay
                  :data="result.response_body"
                  :show-drawer-button="false"
                  :default-expanded="false"
                />
              </div>
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { computed, reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { invokeMockEndpoint } from '@/api/apitest/mock'
  import type { MockInvokeResult } from '@/api/apitest/mock'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { debugMethodOptions, methodOptions as allMethods } from '../config'
  import type { MockDebugTarget } from '../types'
  const visible = ref(false),
    resultVisible = ref(false),
    loading = ref(false)
  const result = ref<MockInvokeResult | null>(null)
  const draft = reactive({ method: 'GET', path: '/', query: '{}', headers: '{}', body: '' })
  const allowedMethods = ref<number[]>([])
  let session = 0
  const methodOptions = computed(() =>
    allowedMethods.value.length
      ? debugMethodOptions.filter((option) =>
          allMethods.some(
            (item) => item.label === option.value && allowedMethods.value.includes(item.value)
          )
        )
      : debugMethodOptions
  )
  function close() {
    session++
    visible.value = false
    resultVisible.value = false
    result.value = null
  }
  function open(target: MockDebugTarget) {
    if (loading.value) return
    close()
    allowedMethods.value = [...target.methods]
    Object.assign(draft, {
      method: methodOptions.value[0]?.value || 'GET',
      path: target.requestPath.replace(/\{[^}]+\}/g, 'value'),
      query: '{}',
      headers: '{}',
      body: '',
    })
    visible.value = true
  }
  function jsonObject(value: string): Record<string, unknown> {
    const parsed: unknown = JSON.parse(value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw Error()
    return parsed as Record<string, unknown>
  }
  async function runDebug(): Promise<boolean> {
    if (!visible.value || loading.value) return false
    let query: Record<string, unknown>, headers: Record<string, unknown>
    try {
      query = jsonObject(draft.query)
      headers = jsonObject(draft.headers)
    } catch {
      Message.error('Query和请求头必须是合法JSON对象')
      return false
    }
    const token = session,
      payload = { method: draft.method, requestPath: draft.path, query, headers, body: draft.body }
    loading.value = true
    try {
      const response = await invokeMockEndpoint(payload)
      if (token !== session) return false
      result.value = response
      visible.value = false
      resultVisible.value = true
      if (response.ok) Message.success(`调用成功，HTTP ${response.status}`)
      else Message.warning(`接口已返回，HTTP ${response.status}`)
      return true
    } catch {
      if (token === session) Message.error('Mock 接口调用失败，请检查服务地址或网络状态')
      return false
    } finally {
      loading.value = false
    }
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close, loading })
</script>
<style scoped>
  .mango-mock-side-panel-content {
    box-sizing: border-box;
    width: 100%;
    min-height: 100%;
    padding: 0;
    container-type: inline-size;
  }

  .mango-mock-invoke-result {
    display: flex;
    height: 100%;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-mock-invoke-summary {
    flex: none;
  }
  .mango-mock-result-tabs {
    min-height: 0;
    padding: 0 12px 12px;
  }
  .mango-mock-invoke-result .mango-mock-result-tabs {
    display: flex;
    flex: 1;
    flex-direction: column;
  }
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
  }
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-content-list),
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-content-item-active),
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-pane) {
    height: 100%;
  }
  .mango-mock-invoke-result .mango-mock-result-tabs :deep(.arco-tabs-pane) {
    display: flex;
    min-height: 0;
    flex-direction: column;
    overflow: auto;
  }
  .mango-mock-result-tabs :deep(.arco-tabs-nav) {
    margin-bottom: 10px;
  }
  .mango-mock-result-tab-description {
    margin-bottom: 10px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .mango-mock-result-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  .mango-mock-result-grid--fill {
    flex: 1;
    min-height: 0;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
  }
  .mango-mock-result-grid__item--fill {
    display: flex;
    min-height: 0;
    flex-direction: column;
  }
  .mango-mock-result-grid__full {
    grid-column: 1 / -1;
  }
  .mango-mock-result-label {
    margin-bottom: 5px;
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 600;
    line-height: 18px;
  }
  .mango-mock-json-panel {
    min-height: 96px;
    max-height: 320px;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-mock-json-panel--headers {
    max-height: 160px;
  }
  .mango-mock-json-panel--fill {
    flex: 1;
    min-height: 0;
    max-height: none;
  }
  .mango-mock-json-panel :deep(.mango-json-display-toolbar) {
    padding: 8px 10px 0;
  }
  .mango-mock-json-panel :deep(.mango-json-display-content) {
    min-height: 64px;
    border: 0;
    border-radius: 0;
  }
  .mango-mock-structured-panel {
    min-height: 96px;
    max-height: 300px;
    overflow: auto;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }
  .mango-mock-structured-panel--detail {
    max-height: 520px;
  }
  .mango-mock-structured-panel :deep(.mango-structured-data__kv) {
    background: var(--m-surface);
  }

  @container (max-width:860px) {
    .mango-mock-result-grid {
      grid-template-columns: 1fr;
    }
    .mango-mock-result-grid__full {
      grid-column: auto;
    }
  }
</style>
