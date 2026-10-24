<template>
  <TableBody>
    <template #header>
      <TableHeader title="运行中心" />
    </template>

    <template #default>
      <div class="mango-runtime-center">
        <a-spin :loading="loading.overview" class="mango-runtime-spin">
          <section class="mango-section-card mango-runtime-summary">
            <div
              v-for="item in summaryCards"
              :key="item.key"
              class="mango-soft-panel mango-runtime-metric"
            >
              <span class="mango-runtime-metric-label">{{ item.label }}</span>
              <strong class="mango-runtime-metric-value">{{ item.value }}</strong>
              <span class="mango-runtime-metric-sub">{{ item.sub }}</span>
            </div>
          </section>
        </a-spin>

        <section class="mango-section-card mango-runtime-section mango-runtime-diagnostics">
          <div class="mango-section-title">
            <div class="mango-section-title__main">
              <h2>配置诊断</h2>
              <p>{{ diagnosticSummary }}</p>
            </div>
          </div>
          <a-spin :loading="loading.diagnostics">
            <div class="mango-runtime-diagnostic-layout">
              <div class="mango-runtime-diagnostic-list">
                <div
                  v-for="item in normalDiagnostics"
                  :key="item.key"
                  :class="[
                    'mango-soft-panel',
                    'mango-runtime-diagnostic',
                    `mango-runtime-diagnostic-${item.status}`,
                  ]"
                >
                  <span class="mango-runtime-diagnostic-status">{{ item.status_name }}</span>
                  <div class="mango-runtime-diagnostic-main">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.message }}</span>
                  </div>
                </div>
              </div>
              <div class="mango-runtime-diagnostic-worker">
                <div
                  v-for="item in apiWorkerDiagnostics"
                  :key="item.key"
                  :class="[
                    'mango-soft-panel',
                    'mango-runtime-diagnostic',
                    `mango-runtime-diagnostic-${item.status}`,
                  ]"
                >
                  <span class="mango-runtime-diagnostic-status">{{ item.status_name }}</span>
                  <div class="mango-runtime-diagnostic-main">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.message }}</span>
                  </div>
                </div>
                <div
                  v-if="!apiWorkerDiagnostics.length"
                  class="mango-empty-state mango-runtime-empty"
                  >暂无 API Worker 诊断</div
                >
              </div>
            </div>
          </a-spin>
        </section>

        <section class="mango-runtime-grid">
          <div class="mango-section-card mango-runtime-section mango-runtime-section-wide">
            <div class="mango-section-title">
              <div class="mango-section-title__main">
                <h2>服务状态</h2>
                <p>{{ displayServices.length }} 个服务</p>
              </div>
            </div>
            <a-table
              :bordered="false"
              :columns="serviceColumns"
              :data="displayServices"
              :loading="loading.services"
              :pagination="false"
              :scroll="{ x: tableScrollX }"
              row-key="id"
            >
              <template #columns>
                <a-table-column v-for="item in serviceColumns" :key="item.key" v-bind="item">
                  <template v-if="item.key === 'status'" #cell="{ record }">
                    <span
                      :class="['mango-runtime-status', `mango-runtime-status-${record.status}`]"
                    >
                      {{ record.status_name }}
                    </span>
                  </template>
                  <template v-else-if="item.key === 'instances'" #cell="{ record }">
                    <div class="mango-runtime-node">
                      <span>{{ serviceInstanceSummary(record) }}</span>
                      <small>{{ serviceInstanceNames(record) }}</small>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'metadata'" #cell="{ record }">
                    <div class="mango-runtime-meta">
                      <span v-for="meta in serviceMetadata(record)" :key="meta">{{ meta }}</span>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <MangoTableActions
                      :actions="[{ permission: 'system.runtime_center:detail', label: '日志', onClick: () => openLog(record.log_query) }]"
                    />
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </div>
        </section>
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getRuntimeOverview } from '@/api/system/runtime-center'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { serviceColumns, tableScrollX } from './config'

  interface RuntimeService {
    id: number | string
    service_name: string
    instance_name: string
    host_name: string
    pod_name?: string
    process_id?: number
    status: string
    status_name: string
    last_seen_at?: string
    age_seconds?: number
    metadata?: Record<string, any>
    log_query?: string
    online_count?: number
    stale_count?: number
    instance_count?: number
    instances?: RuntimeService[]
  }

  interface RuntimeDiagnostic {
    key: string
    title: string
    status: string
    status_name: string
    message: string
    suggestion?: string
  }

  const summary = ref<Record<string, any>>({})
  const services = ref<RuntimeService[]>([])
  const diagnostics = ref<RuntimeDiagnostic[]>([])
  const loading = reactive({
    overview: false,
    services: false,
    diagnostics: false,
  })

  const summaryCards = computed(() => [
    {
      key: 'services',
      label: '服务健康',
      value: `${summary.value.healthy_service_count || 0}/${
        summary.value.total_service_count || 0
      }`,
      sub: '在线服务类型',
    },
    {
      key: 'workers',
      label: 'API Worker',
      value: `${summary.value.api_worker_count || 0}/${
        summary.value.api_worker_desired_count || 5
      }`,
      sub: `在线 / 期望，线程池 ${summary.value.api_worker_thread_pool_size || 0}`,
    },
    {
      key: 'concurrency',
      label: 'API 总并发',
      value: summary.value.api_total_concurrency || 0,
      sub: '在线实例 x 线程池',
    },
    {
      key: 'pending',
      label: '待执行任务',
      value: summary.value.pending_task_count || 0,
      sub: 'API / UI / Pytest / 定时',
    },
    {
      key: 'errors',
      label: '系统异常',
      value: summary.value.recent_error_count || 0,
      sub: '调度与服务异常',
    },
  ])

  const displayServices = computed(() => normalizeServiceGroups(services.value))

  const diagnosticSummary = computed(() => {
    const errorCount = diagnostics.value.filter((item) => item.status === 'error').length
    const warningCount = diagnostics.value.filter((item) => item.status === 'warning').length
    return `${errorCount} 异常 / ${warningCount} 警告`
  })

  const apiWorkerDiagnostics = computed(() =>
    diagnostics.value.filter(
      (item) => item.key.includes('api_worker') || item.title.includes('API Worker')
    )
  )

  const normalDiagnostics = computed(() =>
    diagnostics.value.filter(
      (item) => !apiWorkerDiagnostics.value.some((workerItem) => workerItem.key === item.key)
    )
  )

  function serviceMetadata(record: RuntimeService) {
    const metadata = record.metadata || {}
    const items: string[] = []
    if (metadata.thread_pool_size !== undefined) items.push(`线程池 ${metadata.thread_pool_size}`)
    if (metadata.running_count !== undefined) items.push(`执行中 ${metadata.running_count}`)
    if (metadata.claim_limit !== undefined) items.push(`领取 ${metadata.claim_limit}`)
    if (metadata.dispatch_batch_size !== undefined)
      items.push(`批次 ${metadata.dispatch_batch_size}`)
    if (metadata.port !== undefined) items.push(`端口 ${metadata.port}`)
    if (metadata.mode !== undefined) items.push(String(metadata.mode))
    return items.length ? items : ['-']
  }

  function normalizeServiceGroups(rows: RuntimeService[]) {
    if (!rows.length) return []
    const groupedRows = rows.filter(
      (item) => Array.isArray(item.instances) && item.online_count !== undefined
    )
    if (groupedRows.length === rows.length) return rows

    const groups = new Map<string, RuntimeService[]>()
    rows.forEach((item) => {
      const serviceName = item.service_name || 'unknown'
      if (!groups.has(serviceName)) groups.set(serviceName, [])
      groups.get(serviceName)?.push(item)
    })

    return Array.from(groups.entries()).map(([serviceName, items]) =>
      buildServiceGroup(serviceName, items)
    )
  }

  function buildServiceGroup(serviceName: string, items: RuntimeService[]): RuntimeService {
    const sortedItems = [...items].sort((prev, next) =>
      String(next.last_seen_at || '').localeCompare(String(prev.last_seen_at || ''))
    )
    const onlineItems = sortedItems.filter((item) => item.status === 'online')
    const staleItems = sortedItems.filter((item) => item.status === 'stale')
    const currentItems = onlineItems.length ? onlineItems : staleItems
    const status = onlineItems.length ? 'online' : staleItems.length ? 'stale' : 'offline'
    const latestItem = sortedItems[0] || ({} as RuntimeService)
    const metadataSource = currentItems[0] || latestItem
    return {
      id: serviceName,
      service_name: serviceName,
      instance_name: serviceName,
      host_name: latestItem.host_name || '',
      status,
      status_name: serviceGroupStatusName(status),
      last_seen_at: latestItem.last_seen_at,
      online_count: onlineItems.length,
      stale_count: staleItems.length,
      instance_count: currentItems.length,
      instances: currentItems,
      metadata: metadataSource.metadata || {},
      log_query: `service="${serviceName}"`,
    }
  }

  function serviceGroupStatusName(status: string) {
    if (status === 'online') return '正常'
    if (status === 'stale') return '心跳延迟'
    return '离线'
  }

  function serviceInstanceSummary(record: RuntimeService) {
    if (record.status === 'online') return `在线 ${record.online_count || 0} 个实例`
    if (record.status === 'stale') return `心跳延迟 ${record.stale_count || 0} 个实例`
    return '当前无在线实例'
  }

  function serviceInstanceNames(record: RuntimeService) {
    const instances = record.instances || []
    if (!instances.length) return '-'
    return instances
      .map((item) => item.pod_name || item.instance_name || item.host_name)
      .filter(Boolean)
      .join('、')
  }

  async function refreshOverview() {
    loading.overview = true
    loading.services = true
    loading.diagnostics = true
    try {
      const res = await getRuntimeOverview()
      const data = res.data || {}
      summary.value = data.summary || {}
      services.value = data.services || []
      diagnostics.value = data.diagnostics || []
    } finally {
      loading.overview = false
      loading.services = false
      loading.diagnostics = false
    }
  }

  function openLog(query?: string) {
    if (!query) {
      Message.warning('暂无日志查询条件')
      return
    }
    const logPlatformUrl = String(import.meta.env.VITE_APP_LOG_PLATFORM_URL || '').trim()
    if (logPlatformUrl) {
      const separator = logPlatformUrl.includes('?') ? '&' : '?'
      window.open(`${logPlatformUrl}${separator}query=${encodeURIComponent(query)}`, '_blank')
      return
    }
    navigator.clipboard?.writeText(query)
    Message.success('日志查询条件已复制')
  }

  onMounted(() => {
    refreshOverview()
  })
</script>

<style scoped lang="less">
  .mango-runtime-center {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding-top: var(--m-page-gap);
    color: var(--m-text);
  }

  .mango-runtime-spin {
    width: 100%;
  }

  .mango-runtime-summary {
    display: grid;
    grid-template-columns: repeat(5, minmax(160px, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-runtime-metric {
    display: flex;
    min-height: 86px;
    flex-direction: column;
    justify-content: center;
    gap: 5px;
  }

  .mango-runtime-metric-label,
  .mango-runtime-metric-sub,
  .mango-runtime-node small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-runtime-metric-value {
    font-size: 24px;
    line-height: 1.2;
    font-weight: 700;
    color: var(--m-text);
  }

  .mango-runtime-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.8fr);
    gap: var(--m-page-gap);
    align-items: stretch;
  }

  .mango-runtime-section-wide {
    grid-column: 1 / -1;
  }

  .mango-runtime-empty {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-runtime-section {
    min-width: 0;
  }

  .mango-runtime-node,
  .mango-runtime-diagnostic-main {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
  }

  .mango-runtime-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .mango-runtime-meta span {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    padding: 1px 6px;
    font-size: 12px;
  }

  .mango-runtime-status {
    display: inline-flex;
    align-items: center;
    border-radius: var(--m-radius-sm);
    padding: 1px 7px;
    font-size: 12px;
    font-weight: 600;
  }

  .mango-runtime-status-online,
  .mango-runtime-diagnostic-success .mango-runtime-diagnostic-status {
    background: color-mix(in srgb, var(--m-success) 10%, var(--m-surface));
    color: var(--m-success);
  }

  .mango-runtime-status-stale,
  .mango-runtime-diagnostic-warning .mango-runtime-diagnostic-status {
    background: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface));
    color: var(--m-warning);
  }

  .mango-runtime-status-offline,
  .mango-runtime-status-error,
  .mango-runtime-diagnostic-error .mango-runtime-diagnostic-status {
    background: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface));
    color: var(--m-danger);
  }

  .mango-runtime-diagnostic-layout {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(220px, 1fr);
    gap: var(--m-page-gap);
  }

  .mango-runtime-diagnostic-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-auto-rows: 112px;
    gap: var(--m-page-gap);
  }

  .mango-runtime-diagnostic-worker {
    display: grid;
    max-height: 232px;
    grid-auto-rows: 112px;
    grid-template-columns: 1fr;
    gap: 8px;
    overflow-y: auto;
    padding-right: 2px;
  }

  .mango-runtime-diagnostic {
    position: relative;
    display: flex;
    min-height: 0;
    height: 112px;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 10px;
    padding: 30px 10px 9px;
  }

  .mango-runtime-diagnostic-main strong {
    display: block;
    max-width: calc(100% - 52px);
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-runtime-diagnostic-main span {
    display: -webkit-box;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 1.4;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .mango-runtime-diagnostic-status {
    position: absolute;
    top: 8px;
    right: 8px;
    flex: 0 0 auto;
    border-radius: var(--m-radius-sm);
    padding: 2px 7px;
    font-size: 12px;
    font-weight: 600;
  }

  @media (max-width: 1200px) {
    .mango-runtime-summary {
      grid-template-columns: repeat(3, minmax(160px, 1fr));
    }

    .mango-runtime-grid {
      grid-template-columns: 1fr;
    }

    .mango-runtime-diagnostic-layout {
      grid-template-columns: 1fr;
    }

    .mango-runtime-diagnostic-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-runtime-diagnostic-worker {
      max-height: none;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      overflow: visible;
      padding-right: 0;
    }
  }

  @media (max-width: 720px) {
    .mango-runtime-summary {
      grid-template-columns: 1fr;
    }

    .mango-runtime-diagnostic-list,
    .mango-runtime-diagnostic-worker {
      grid-template-columns: 1fr;
    }
  }
</style>
