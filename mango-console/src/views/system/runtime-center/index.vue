<template>
  <TableBody>
    <template #header>
      <TableHeader title="运行中心" />
    </template>

    <template #default>
      <div class="mango-runtime-center">
        <a-spin :loading="sourceLoading" class="mango-runtime-spin">
          <template v-if="errors.overview"></template>
          <section v-else class="mango-section-card mango-runtime-summary">
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

        <section class="mango-section-card mango-runtime-section">
          <div class="mango-section-title">
            <div class="mango-section-title__main">
              <h2>服务运行状态</h2>
              <span class="mango-runtime-section-note">按服务心跳统计实例，配置项不计作服务。</span>
            </div>
          </div>
          <a-spin :loading="sourceLoading" class="mango-runtime-spin">
            <template v-if="errors.services"></template>
            <div v-else-if="services.length" class="mango-runtime-diagnostic-list">
              <div v-for="service in services" :key="service.id" class="mango-soft-panel mango-runtime-service">
                <div class="mango-runtime-service-header">
                  <strong>{{ service.service_name }}</strong>
                  <span :class="['mango-runtime-status', `mango-runtime-status-${service.status}`]">{{ service.status_name }}</span>
                </div>
                <span>{{ serviceInstanceSummary(service) }}</span>
                <span class="mango-runtime-service-instances" :title="serviceInstanceNames(service)">
                  {{ serviceInstanceNames(service) === '-' ? '暂无有效实例心跳' : serviceInstanceNames(service) }}
                </span>
                <span v-if="service.status === 'online' && service.stale_count" class="mango-runtime-section-note">另有 {{ service.stale_count }} 个实例心跳延迟</span>
              </div>
            </div>
            <div v-else class="mango-empty-state mango-runtime-empty">暂无服务心跳记录</div>
          </a-spin>
        </section>

        <section class="mango-section-card mango-runtime-section mango-runtime-diagnostics">
          <div class="mango-section-title">
            <div class="mango-section-title__main">
              <h2>配置诊断</h2>
              <span class="mango-runtime-section-note">{{ diagnosticSummary }}</span>
            </div>
          </div>
          <a-spin :loading="sourceLoading" class="mango-runtime-spin">
            <template v-if="errors.diagnostics"></template>
            <div v-else-if="configurationDiagnostics.length">
              <div class="mango-runtime-diagnostic-list">
                <div
                  v-for="item in configurationDiagnostics"
                  :key="item.key"
                  :class="[
                    'mango-soft-panel',
                    'mango-runtime-diagnostic',
                    `mango-runtime-diagnostic-${item.status}`,
                  ]"
                >
                  <span class="mango-runtime-diagnostic-status">{{ item.status_name }}</span>
                  <div class="mango-runtime-diagnostic-main">
                    <strong :title="item.title">{{ item.title }}</strong>
                    <span :title="item.message">{{ item.message }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="mango-empty-state mango-runtime-empty">暂无配置诊断项</div>
          </a-spin>
        </section>

        <section class="mango-runtime-grid">
          <div class="mango-section-card mango-runtime-section mango-runtime-section-wide">
            <div class="mango-section-title">
              <div class="mango-section-title__main">
                <h2>服务实例明细</h2>
              </div>
            </div>
            <a-table
              :bordered="false"
              :columns="serviceColumns"
              :data="services"
              :loading="sourceLoading"
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
                      <small :title="serviceInstanceNames(record)">{{ serviceInstanceNames(record) }}</small>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'metadata'" #cell="{ record }">
                    <div class="mango-runtime-meta">
                      <span v-for="meta in serviceMetadata(record)" :key="meta" :title="meta">{{ meta }}</span>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <MangoTableActions
                      :actions="[{ label: '日志', loading: openingLogId === record.id, disabled: openingLogId !== null, onClick: () => openLog(record) }]"
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
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, onActivated, onDeactivated, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getRuntimeOverview } from '@/api/system/runtime-center'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { serviceColumns, serviceOnlineDiagnosticKeys, tableScrollX } from './config'
  import { runtimeOverviewData, parseRuntimeSummary, parseRuntimeServices, parseRuntimeDiagnostics, serviceMetadata, serviceInstanceSummary, serviceInstanceNames, runtimeLogUrl } from './runtime-overview'
  import type { RuntimeService, RuntimeSummary, RuntimeDiagnostic } from './runtime-overview'

  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const summary = ref<RuntimeSummary | null>(null), services = ref<RuntimeService[]>([]), diagnostics = ref<RuntimeDiagnostic[]>([])
  const sourceLoading = ref(false), openingLogId = ref<RuntimeService['id'] | null>(null)
  const errors = reactive({ overview: '', services: '', diagnostics: '' })
  const latest = useLatestRequest()
  let mounted = false, active = true, disposed = false, needsLoad = true, contextVersion = 0
  let pendingRead: Promise<void> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const current = (generation: number, key: string) => available() && generation === contextVersion && key === identity()
  const summaryCards = computed(() => {
    const value = summary.value
    return [
      { key: 'services', label: '服务健康', value: value ? `${value.healthy_service_count}/${value.total_service_count}` : '-', sub: '在线服务类型' },
      { key: 'workers', label: 'API Worker', value: value ? `${value.api_worker_count}/${value.api_worker_desired_count}` : '-', sub: value ? `在线 / 期望，线程池 ${value.api_worker_thread_pool_size}` : '在线 / 期望' },
      { key: 'concurrency', label: 'API 总并发', value: value?.api_total_concurrency ?? '-', sub: '在线实例 x 线程池' },
      { key: 'pending', label: '待执行任务', value: value?.pending_task_count ?? '-', sub: 'API / UI / Pytest / 定时' },
      { key: 'errors', label: '系统异常', value: value?.recent_error_count ?? '-', sub: '调度与服务异常' },
    ]
  })
  const configurationDiagnostics = computed(() => diagnostics.value.filter(item => !serviceOnlineDiagnosticKeys.includes(item.key)))
  const diagnosticSummary = computed(() => `${configurationDiagnostics.value.filter(item => item.status === 'error').length} 异常 / ${configurationDiagnostics.value.filter(item => item.status === 'warning').length} 警告`)
  function refreshOverview(): Promise<void> {
    if (!available()) { needsLoad = true; return Promise.resolve() }
    if (pendingRead) return pendingRead
    const requestId = latest.beginRequest(), generation = contextVersion, key = identity()
    const valid = () => latest.isLatestRequest(requestId) && current(generation, key)
    sourceLoading.value = true; needsLoad = false; Object.assign(errors, { overview: '', services: '', diagnostics: '' })
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const data = runtimeOverviewData(await getRuntimeOverview())
        if (!valid()) return
        try { summary.value = parseRuntimeSummary(data.summary) }
        catch (loadFailure0) { summary.value = null; (reportLoadError(loadFailure0, "运行指标加载失败，请重试", false), errors.overview = '运行指标加载失败，请重试') }
        try { services.value = parseRuntimeServices(data.services) }
        catch (loadFailure1) { services.value = []; (reportLoadError(loadFailure1, "服务状态加载失败，请重试", false), errors.services = '服务状态加载失败，请重试') }
        try { diagnostics.value = parseRuntimeDiagnostics(data.diagnostics) }
        catch (loadFailure2) { diagnostics.value = []; (reportLoadError(loadFailure2, "配置诊断加载失败，请重试", false), errors.diagnostics = '配置诊断加载失败，请重试') }
      } catch (error) {
        if (valid()) {
          reportLoadError(error, '运行状态加载失败，请重试')
          summary.value = null; services.value = []; diagnostics.value = []
          Object.assign(errors, { overview: '运行指标加载失败，请重试', services: '服务状态加载失败，请重试', diagnostics: '配置诊断加载失败，请重试' })
        }
      } finally { if (valid()) { sourceLoading.value = false; pendingRead = null } }
    })
    pendingRead = promise
    return promise
  }
  async function openLog(record: RuntimeService): Promise<void> {
    if (!available() || openingLogId.value !== null) return
    const query = record.log_query
    if (!query) { Message.warning('暂无日志查询条件'); return }
    const generation = contextVersion, key = identity()
    const valid = () => current(generation, key)
    const base = String(import.meta.env.VITE_APP_LOG_PLATFORM_URL || '').trim()
    openingLogId.value = record.id
    try {
      if (base) {
        const url = runtimeLogUrl(base, query, window.location.origin)
        if (!url) { Message.error('日志平台地址无效'); return }
        window.open(url, '_blank', 'noopener,noreferrer')
      } else {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
        await navigator.clipboard.writeText(query)
        if (valid()) Message.success('日志查询条件已复制')
      }
    } catch { if (valid()) Message.error(base ? '日志平台打开失败，请重试' : '复制失败，请检查浏览器剪贴板权限后重试') }
    finally { openingLogId.value = null }
  }
  function pause() { contextVersion++; latest.invalidateRequests(); pendingRead = null; sourceLoading.value = false; needsLoad = true }
  function resume() { if (available() && needsLoad) void refreshOverview() }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => { pause(); summary.value = null; services.value = []; diagnostics.value = []; Object.assign(errors, { overview: '', services: '', diagnostics: '' }); resume() }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>


<style scoped lang="less">
  .mango-runtime-error { padding: var(--m-page-gap); color: var(--m-danger); }

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

  .mango-runtime-node small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

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
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

  .mango-runtime-diagnostic-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-runtime-section-note,
  .mango-runtime-service-instances {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-runtime-service {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 6px;
    padding: 10px;
    font-size: 13px;
  }

  .mango-runtime-service-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-runtime-service-header strong {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .mango-runtime-service-header .mango-runtime-status {
    flex-shrink: 0;
  }

  .mango-runtime-service-instances {
    overflow-wrap: anywhere;
  }

  .mango-runtime-diagnostic {
    position: relative;
    display: flex;
    min-height: 0;
    min-height: 112px;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 10px;
    padding: 30px 10px 9px;
  }

  .mango-runtime-diagnostic-main strong {
    display: block;
    max-width: 100%;
    color: var(--m-text);
    font-size: 13px;
    overflow-wrap: anywhere;
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

    .mango-runtime-diagnostic-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

  }

  @media (max-width: 720px) {
    .mango-runtime-summary {
      grid-template-columns: 1fr;
    }

    .mango-runtime-diagnostic-list {
      grid-template-columns: 1fr;
    }
  }
</style>
