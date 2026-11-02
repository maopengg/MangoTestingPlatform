<template>
  <BaseSidePanel v-model:visible="visible" title="Mock 调用记录" width="980px" :show-footer="false">
    <div class="mango-mock-side-panel-content mango-mock-side-panel-content--logs">
      <div class="mango-mock-log-layout">
        <div class="mango-soft-panel mango-mock-log-toolbar">
          <a-form class="mango-mock-log-filters" :model="logs.filters" layout="horizontal" @keyup.enter="loadLogs(1)">
            <a-form-item label="Trace ID"><a-input v-model="logs.filters.trace_id" allow-clear /></a-form-item>
            <a-form-item label="请求路径"><a-input v-model="logs.filters.request_path" allow-clear /></a-form-item>
            <a-form-item label="断言结果">
              <a-select v-model="logs.filters.assertion_passed" allow-clear :options="assertionLogOptions" />
            </a-form-item>
            <a-form-item label="状态码"><a-input-number v-model="logs.filters.response_status" :min="100" :max="599" /></a-form-item>
          </a-form>
          <div class="mango-mock-log-toolbar__actions">
            <a-button size="small" type="primary" :loading="logs.loading" @click="loadLogs(1)">查询</a-button>
            <a-button size="small" @click="resetLogFilters">重置</a-button>
            <a-button size="small" :loading="logs.loading" @click="refreshLogs">刷新</a-button>
            <a-button
              size="small"
              :disabled="logs.pagination.pageCount === 0"
              :loading="logs.exporting"
              @click="exportLogs"
            >导出 CSV</a-button>
            <a-button
              size="small"
              status="danger"
              type="outline"
              :disabled="logs.pagination.pageCount === 0"
              :loading="logs.clearing"
              @click="clearLogs"
            >清空所有</a-button>
          </div>
        </div>
        <div class="mango-mock-log-table-region">
          <a-table
            class="mango-native-scroll-table mango-mock-log-table"
            :data="logs.items"
            :loading="logs.loading"
            :pagination="false"
            :scroll="{ x: 1910, y: '100%' }"
            row-key="id"
          >
            <template #columns>
            <a-table-column title="时间" :width="180">
              <template #cell="{ record }"><span class="mango-mock-log-time">{{ record.create_time || '-' }}</span></template>
            </a-table-column>
            <a-table-column title="结果" :width="90" align="center">
              <template #cell="{ record }">
                <a-tag v-if="record.error_message" size="small" color="red">异常</a-tag>
                <a-tag v-else size="small" :color="record.assertion_passed ? 'green' : 'orange'">{{ record.assertion_passed ? '通过' : '警告' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="原因" :width="360" ellipsis tooltip>
              <template #cell="{ record }">
                <span class="mango-mock-log-reason" :title="formatLogResultReason(record)">{{ formatLogResultReason(record) }}</span>
              </template>
            </a-table-column>
            <a-table-column title="方法" data-index="method_name" :width="90" align="center" />
            <a-table-column title="状态码" data-index="response_status" :width="90" align="center" />
            <a-table-column title="请求路径" :width="280" ellipsis tooltip>
              <template #cell="{ record }">{{ displayLogRequestPath(record.request_path) }}</template>
            </a-table-column>
            <a-table-column title="Trace ID" data-index="trace_id" :width="240" ellipsis tooltip />
            <a-table-column title="命中规则" data-index="rule_key" :width="160">
              <template #cell="{ record }">{{ record.rule_key || '-' }}</template>
            </a-table-column>
            <a-table-column title="耗时(ms)" data-index="duration_ms" :width="110" align="center" />
            <a-table-column title="客户端IP" data-index="client_ip" :width="150" />
            <a-table-column title="操作" :width="160" align="center" fixed="right">
              <template #cell="{ record }">
                <MangoTableActions :actions="[{ label: '查看详情', onClick: () => openLogDetail(record) }]" />
              </template>
            </a-table-column>
            </template>
          </a-table>
        </div>
        <div class="mango-mock-log-footer">
          <TableFooter :pagination="logs.pagination" />
        </div>
      </div>
    </div>
  </BaseSidePanel>

  <BaseSidePanel
    v-model:visible="logs.detailVisible"
    :title="logs.selected ? `调用记录详情 #${logs.selected.id}` : '调用记录详情'"
    width="760px"
    :show-footer="false"
  >
    <a-spin class="mango-mock-side-panel-content" :loading="logs.detailLoading" tip="调用详情加载中...">
      <div v-if="logs.selected" class="mango-mock-log-detail">
        <a-descriptions :column="3" size="small" bordered>
          <a-descriptions-item label="调用结果">
            <a-tag v-if="logs.selected.error_message" size="small" color="red">异常</a-tag>
            <a-tag v-else size="small" :color="logs.selected.assertion_passed ? 'green' : 'orange'">
              {{ logs.selected.assertion_passed ? '通过' : '警告' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="请求方法">{{ logs.selected.method_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="状态码">{{ logs.selected.response_status || '-' }}</a-descriptions-item>
          <a-descriptions-item label="耗时">{{ logs.selected.duration_ms ?? '-' }} ms</a-descriptions-item>
          <a-descriptions-item label="客户端 IP">{{ logs.selected.client_ip || '-' }}</a-descriptions-item>
          <a-descriptions-item label="调用时间">{{ logs.selected.create_time || '-' }}</a-descriptions-item>
          <a-descriptions-item label="请求路径" :span="3">{{ displayLogRequestPath(logs.selected.request_path) }}</a-descriptions-item>
          <a-descriptions-item label="Trace ID" :span="3">{{ logs.selected.trace_id || '-' }}</a-descriptions-item>
          <a-descriptions-item label="命中规则" :span="3">{{ logs.selected.rule_key || '-' }}</a-descriptions-item>
        </a-descriptions>

        <a-alert v-if="logs.selected.error_message" type="error">
          {{ logs.selected.error_message }}
        </a-alert>

        <a-tabs class="mango-section-card mango-mock-result-tabs" default-active-key="request">
          <a-tab-pane key="request" title="请求信息">
            <div class="mango-mock-result-tab-description">本次调用收到的请求参数、请求头和请求体</div>
            <div class="mango-mock-result-grid">
              <section>
                <div class="mango-mock-result-label">Query 参数</div>
                <div class="mango-mock-json-panel">
                  <JsonDisplay :data="logs.selected.request_data?.query || {}" :show-drawer-button="false" :default-expanded="false" />
                </div>
              </section>
              <section>
                <div class="mango-mock-result-label">请求头</div>
                <div class="mango-mock-json-panel">
                  <JsonDisplay :data="logs.selected.request_data?.headers || {}" :show-drawer-button="false" :default-expanded="false" />
                </div>
              </section>
              <section class="mango-mock-result-grid__full">
                <div class="mango-mock-result-label">请求体</div>
                <div class="mango-mock-json-panel">
                  <JsonDisplay :data="logs.selected.request_data?.body || {}" :show-drawer-button="false" :default-expanded="false" />
                </div>
              </section>
            </div>
          </a-tab-pane>
          <a-tab-pane key="assertion" title="断言结果">
            <div class="mango-mock-result-tab-description">请求规则的逐项校验结果</div>
            <div class="mango-mock-structured-panel mango-mock-structured-panel--detail">
              <UiStructuredDataView :data="displayAssertionResults" />
            </div>
          </a-tab-pane>
          <a-tab-pane key="response" title="响应数据">
            <div class="mango-mock-result-tab-description">
              Mock 服务最终返回给调用方的数据
              <a-tag v-if="logs.selected.response_data?.content_type" size="small">{{ logs.selected.response_data.content_type }}</a-tag>
            </div>
            <div class="mango-mock-result-grid">
              <section>
                <div class="mango-mock-result-label">响应头</div>
                <div class="mango-mock-json-panel">
                  <JsonDisplay :data="logs.selected.response_data?.headers || {}" :show-drawer-button="false" :default-expanded="false" />
                </div>
              </section>
              <section>
                <div class="mango-mock-result-label">响应体</div>
                <div class="mango-mock-json-panel">
                  <JsonDisplay :data="logs.selected.response_data?.body || {}" :show-drawer-button="false" :default-expanded="false" />
                </div>
              </section>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-spin>
  </BaseSidePanel>
</template>
<script lang="ts" setup>
  import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import UiStructuredDataView from '@/components/display/UiStructuredDataView.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import type { MockAssertionMethodOption } from '@/api/apitest/mock'
  import { clearMockLogs, exportMockLogs, getMockAssertionMethods, getMockLogDetail, getMockLogs } from '@/api/apitest/mock'

  const props = defineProps<{ visible: boolean; mockId: number; mockKey: string }>()
  const emit = defineEmits<{ (e: 'update:visible', value: boolean): void }>()
  const visible = computed({ get: () => props.visible, set: (value) => emit('update:visible', value) })
  const assertionMethods = ref<MockAssertionMethodOption[]>([])
  let listRequest = 0
  let detailRequest = 0
  const assertionMethodLabels = computed(() => {
    const labels = new Map<string, string>()
    const collect = (options: MockAssertionMethodOption[]) => {
      options.forEach((option) => {
        if (option.children?.length) collect(option.children)
        else labels.set(option.value, option.label)
      })
    }
    collect(assertionMethods.value)
    return labels
  })
  const assertionLogOptions = [
    { label: '通过', value: 1 },
    { label: '失败', value: 0 },
  ]
  const logs = reactive({
    loading: false,
    exporting: false,
    clearing: false,
    detailVisible: false,
    detailLoading: false,
    items: [] as any[],
    selected: null as any,
    filters: { trace_id: '', request_path: '', assertion_passed: '', response_status: undefined as number | undefined },
    pagination: {
      page: 1,
      pageSize: 20,
      pageSizes: [20, 50, 100],
      showSizePicker: true,
      pageCount: 0,
      onChange: () => {},
    },
  })
  const displayAssertionResults = computed(() => {
    const results = logs.selected?.assertion_results
    if (!Array.isArray(results)) return []
    return results.map((item: Record<string, unknown>) => ({
      ...item,
      operator: assertionMethodLabels.value.get(String(item.operator)) || item.operator,
    }))
  })
  logs.pagination.onChange = () => { loadLogs(logs.pagination.page) }
  function displayLogRequestPath(value: unknown) {
    const path = String(value || '/')
    const mockKey = String(props.mockKey || '').replace(/^\/+|\/+$/g, '')
    if (!mockKey || path === `/${mockKey}` || path.startsWith(`/${mockKey}/`)) return path
    const suffix = path === '/' ? '' : path.startsWith('/') ? path : `/${path}`
    return `/${mockKey}${suffix}`
  }
  function formatLogResultReason(record: any): string {
    if (record.error_message) return `平台异常：${record.error_message}`
    if (record.assertion_passed) return '-'
    const failures = Array.isArray(record.assertion_results)
      ? record.assertion_results.filter((item: any) => item && item.passed === false)
      : []
    if (!failures.length) return '请求断言未通过，暂无失败明细'
    return `请求断言未通过：${failures.map((item: any) => {
      const name = String(item.name || item.field || item.key || '未命名断言')
      const message = String(item.message || '请求值不符合预期')
      return `${name}（${message}）`
    }).join('；')}`
  }
  async function openLogDetail(record: any) {
    const requestId = ++detailRequest
    logs.selected = record
    logs.detailVisible = true
    logs.detailLoading = true
    try {
      const [response, methods] = await Promise.all([
        getMockLogDetail(record.id),
        assertionMethods.value.length ? Promise.resolve(null) : getMockAssertionMethods(),
      ])
      if (requestId !== detailRequest) return
      logs.selected = response.data
      if (methods) assertionMethods.value = methods.data || []
    }
    finally { if (requestId === detailRequest) logs.detailLoading = false }
  }
  async function resetLogFilters() {
    logs.filters.trace_id = ''
    logs.filters.request_path = ''
    logs.filters.assertion_passed = ''
    logs.filters.response_status = undefined
    await loadLogs(1)
  }
  async function refreshLogs() {
    await loadLogs(logs.pagination.page || 1)
  }
  function buildLogQuery(includePage = false) {
    const params: Record<string, unknown> = { id: props.mockId }
    if (includePage) Object.assign(params, { page: logs.pagination.page, pageSize: logs.pagination.pageSize })
    Object.entries(logs.filters).forEach(([key, value]) => {
      if (value !== '' && value !== undefined && value !== null) params[key] = value
    })
    return params
  }
  async function loadLogs(page = 1) {
    if (!props.mockId) return
    const requestId = ++listRequest
    logs.loading = true
    try {
      logs.pagination.page = page
      const params = buildLogQuery(true)
      const response = await getMockLogs(params)
      if (requestId !== listRequest) return
      logs.items = response.data
      logs.pagination.pageCount = response.totalSize
    }
    finally { if (requestId === listRequest) logs.loading = false }
  }
  async function exportLogs() {
    if (!props.mockId || logs.pagination.pageCount === 0) return
    const fallbackFilename = `mock-${props.mockKey || props.mockId}-logs.csv`
    logs.exporting = true
    try {
      const response = await exportMockLogs(buildLogQuery())
      if (!(response.data instanceof Blob) || response.data.size === 0) {
        throw new Error('导出文件为空')
      }
      const disposition = String(response.headers['content-disposition'] || '')
      const encodedName = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
      const filename = encodedName
        ? decodeURIComponent(encodedName)
        : fallbackFilename
      const href = URL.createObjectURL(response.data)
      const anchor = document.createElement('a')
      anchor.href = href
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(href), 1000)
      Message.success('CSV 导出成功')
    } catch (_error) {
      Message.error('CSV 导出失败，请稍后重试')
    } finally {
      logs.exporting = false
    }
  }
  function clearLogs() {
    if (!props.mockId || logs.pagination.pageCount === 0) return
    const mockId = props.mockId
    Modal.confirm({
      title: '清空调用记录',
      content: `将永久删除当前 Mock 接口的 ${logs.pagination.pageCount} 条调用记录，确认继续吗？`,
      okText: '确认清空',
      okButtonProps: { status: 'danger' },
      async onOk() {
        logs.clearing = true
        try {
          const response = await clearMockLogs(mockId)
          Message.success(`已清空 ${response.data?.deleted_count || 0} 条调用记录`)
          if (props.mockId === mockId && props.visible) {
            detailRequest += 1
            logs.selected = null
            logs.detailVisible = false
            await loadLogs(1)
          }
        } finally {
          logs.clearing = false
        }
      },
    })
  }

  watch([() => props.visible, () => props.mockId], async ([isVisible]) => {
    listRequest += 1
    detailRequest += 1
    logs.loading = false
    logs.detailLoading = false
    if (!isVisible) {
      logs.detailVisible = false
      return
    }
    logs.items = []
    logs.selected = null
    logs.detailVisible = false
    logs.pagination.pageCount = 0
    logs.filters.trace_id = ''
    logs.filters.request_path = ''
    logs.filters.assertion_passed = ''
    logs.filters.response_status = undefined
    await loadLogs(1)
  }, { immediate: true })

  onBeforeUnmount(() => {
    listRequest += 1
    detailRequest += 1
  })
</script>
<style scoped>
  .mango-mock-side-panel-content { box-sizing: border-box; width: 100%; min-height: 100%; padding: 0; container-type: inline-size; }
  .mango-mock-side-panel-content--logs { height: 100%; min-height: 0; overflow: hidden; }
  .mango-mock-result-tabs { min-height: 0; padding: 0 12px 12px; }
  .mango-mock-result-tabs :deep(.arco-tabs-nav) { margin-bottom: 10px; }
  .mango-mock-result-tab-description { margin-bottom: 10px; color: var(--m-muted); font-size: 12px; line-height: 18px; }
  .mango-mock-result-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .mango-mock-result-grid--fill { flex: 1; min-height: 0; grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
  .mango-mock-result-grid__item--fill { display: flex; min-height: 0; flex-direction: column; }
  .mango-mock-result-grid__full { grid-column: 1 / -1; }
  .mango-mock-result-label { margin-bottom: 5px; color: var(--m-text-2); font-size: 13px; font-weight: 600; line-height: 18px; }
  .mango-mock-json-panel { min-height: 96px; max-height: 320px; overflow: auto; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); }
  .mango-mock-json-panel--headers { max-height: 160px; }
  .mango-mock-json-panel--fill { flex: 1; min-height: 0; max-height: none; }
  .mango-mock-json-panel :deep(.mango-json-display-toolbar) { padding: 8px 10px 0; }
  .mango-mock-json-panel :deep(.mango-json-display-content) { min-height: 64px; border: 0; border-radius: 0; }
  .mango-mock-structured-panel { min-height: 96px; max-height: 300px; overflow: auto; padding: 10px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); }
  .mango-mock-structured-panel--detail { max-height: 520px; }
  .mango-mock-structured-panel :deep(.mango-structured-data__kv) { background: var(--m-surface); }
  .mango-mock-log-layout { display: flex; height: 100%; min-height: 0; flex-direction: column; gap: var(--m-page-gap); }
  .mango-mock-log-toolbar { display: flex; align-items: stretch; flex-direction: column; gap: 10px; padding: 10px 12px; }
  .mango-mock-log-filters { display: grid; min-width: 0; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px 12px; }
  .mango-mock-log-filters :deep(.arco-form-item) { min-width: 0; margin: 0; }
  .mango-mock-log-filters :deep(.arco-form-item-label-col) { width: 84px; max-width: 84px; flex: 0 0 84px; padding-right: 10px; white-space: nowrap; }
  .mango-mock-log-filters :deep(.arco-form-item-label) { width: auto; white-space: nowrap; }
  .mango-mock-log-filters :deep(.arco-form-item-wrapper-col) { min-width: 0; }
  .mango-mock-log-filters :deep(.arco-select),
  .mango-mock-log-filters :deep(.arco-input-number) { width: 100%; }
  .mango-mock-log-toolbar__actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; white-space: nowrap; }
  .mango-mock-log-table-region { display: flex; min-height: 0; flex: 1 1 auto; overflow: hidden; }
  .mango-mock-log-table { width: 100%; height: 100%; min-height: 0; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); }
  .mango-mock-log-footer { flex: none; }
  .mango-mock-log-time { white-space: nowrap; }
  .mango-mock-log-reason { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-mock-log-detail { display: flex; flex-direction: column; gap: var(--m-page-gap); }
  @container (max-width: 860px) {
    .mango-mock-log-filters { grid-template-columns: repeat(2, minmax(180px, 1fr)); }
    .mango-mock-result-grid { grid-template-columns: 1fr; }
    .mango-mock-result-grid__full { grid-column: auto; }
  }
</style>
