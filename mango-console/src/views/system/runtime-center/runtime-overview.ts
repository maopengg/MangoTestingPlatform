export interface RuntimeSummary {
  healthy_service_count: number
  total_service_count: number
  api_worker_count: number
  api_worker_desired_count: number
  api_worker_thread_pool_size: number
  api_total_concurrency: number
  pending_task_count: number
  recent_error_count: number
}
export interface RuntimeMetadata {
  thread_pool_size?: number | string
  running_count?: number | string
  claim_limit?: number | string
  dispatch_batch_size?: number | string
  port?: number | string
  mode?: string
}
export interface RuntimeService {
  id: number | string
  service_name: string
  instance_name: string
  host_name: string
  pod_name: string
  status: string
  status_name: string
  last_seen_at: string
  metadata: RuntimeMetadata
  log_query: string
  online_count: number | null
  stale_count: number | null
  instance_count: number | null
  instances: RuntimeService[] | null
}
export interface RuntimeDiagnostic { key: string; title: string; status: string; status_name: string; message: string }
const object = (value: unknown): Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
const text = (value: unknown) => typeof value === 'string' ? value : ''
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('运行指标格式异常')
  return value
}
const optionalCount = (value: unknown) => value == null ? null : count(value)
export function runtimeOverviewData(value: unknown): Record<string, unknown> {
  const response = object(value)
  if (response.code !== 200 || response.data === null || typeof response.data !== 'object' || Array.isArray(response.data)) throw new Error('运行概览读取失败')
  return object(response.data)
}
export function parseRuntimeSummary(value: unknown): RuntimeSummary {
  const row = object(value)
  return {
    healthy_service_count: count(row.healthy_service_count), total_service_count: count(row.total_service_count),
    api_worker_count: count(row.api_worker_count), api_worker_desired_count: count(row.api_worker_desired_count),
    api_worker_thread_pool_size: count(row.api_worker_thread_pool_size), api_total_concurrency: count(row.api_total_concurrency),
    pending_task_count: count(row.pending_task_count), recent_error_count: count(row.recent_error_count),
  }
}
function parseMetadata(value: unknown): RuntimeMetadata {
  const row = object(value), metadata: RuntimeMetadata = {}
  for (const key of ['thread_pool_size', 'running_count', 'claim_limit', 'dispatch_batch_size', 'port'] as const) {
    const value = row[key]
    if (typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))) metadata[key] = value
  }
  if (typeof row.mode === 'string') metadata.mode = row.mode
  return metadata
}
function parseService(value: unknown, allowInstances: boolean): RuntimeService {
  const row = object(value), id = row.id
  if (!((typeof id === 'string' && id) || (typeof id === 'number' && Number.isSafeInteger(id) && id >= 0)) || !text(row.service_name)) throw new Error('运行服务格式异常')
  if (row.instances != null && (!allowInstances || !Array.isArray(row.instances))) throw new Error('运行实例格式异常')
  return { id: id as number | string, service_name: text(row.service_name), instance_name: text(row.instance_name), host_name: text(row.host_name), pod_name: text(row.pod_name),
    status: text(row.status), status_name: text(row.status_name), last_seen_at: text(row.last_seen_at), metadata: parseMetadata(row.metadata), log_query: text(row.log_query),
    online_count: optionalCount(row.online_count), stale_count: optionalCount(row.stale_count), instance_count: optionalCount(row.instance_count),
    instances: Array.isArray(row.instances) ? row.instances.map(item => parseService(item, false)) : null }
}
export function parseRuntimeServices(value: unknown): RuntimeService[] {
  if (!Array.isArray(value)) throw new Error('运行服务列表格式异常')
  const services = value.map(item => parseService(item, true))
  if (new Set(services.map(item => String(item.id))).size !== services.length) throw new Error('运行服务 ID 重复')
  return normalizeServiceGroups(services)
}
export function parseRuntimeDiagnostics(value: unknown): RuntimeDiagnostic[] {
  if (!Array.isArray(value)) throw new Error('运行诊断列表格式异常')
  const seen = new Set<string>()
  return value.map(value => {
    const row = object(value), key = text(row.key)
    if (!key || seen.has(key)) throw new Error('运行诊断标识格式异常')
    seen.add(key)
    return { key, title: text(row.title), status: text(row.status), status_name: text(row.status_name), message: text(row.message) }
  })
}
export function normalizeServiceGroups(rows: RuntimeService[]): RuntimeService[] {
  // Counts identify grouped/redacted results even when the server intentionally omits instances and logs.
  const grouped = rows.filter(item => item.online_count !== null || item.instances !== null)
  if (grouped.length === rows.length) return rows
  if (grouped.length) throw new Error('运行服务分组格式不一致')
  const groups = new Map<string, RuntimeService[]>()
  rows.forEach(item => groups.set(item.service_name, [...(groups.get(item.service_name) || []), item]))
  return Array.from(groups.entries()).map(([serviceName, items]) => {
    const sorted = [...items].sort((a, b) => b.last_seen_at.localeCompare(a.last_seen_at))
    const latest = sorted[0], online = sorted.filter(item => item.status === 'online'), stale = sorted.filter(item => item.status === 'stale')
    const current = online.length ? online : stale, status = online.length ? 'online' : stale.length ? 'stale' : 'offline'
    const escapedName = serviceName.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
    return { ...latest, id: serviceName, service_name: serviceName, instance_name: serviceName, status,
      status_name: status === 'online' ? '正常' : status === 'stale' ? '心跳延迟' : '离线', online_count: online.length, stale_count: stale.length,
      instance_count: current.length, instances: current, metadata: (current[0] || latest).metadata,
      log_query: items.some(item => item.log_query) ? `service="${escapedName}"` : '' }
  })
}
export function serviceMetadata(record: RuntimeService): string[] {
  const metadata = record.metadata, items: string[] = []
  for (const [key, label] of [['thread_pool_size', '线程池'], ['running_count', '执行中'], ['claim_limit', '领取'], ['dispatch_batch_size', '批次'], ['port', '端口']] as const) {
    if (metadata[key] !== undefined) items.push(`${label} ${metadata[key]}`)
  }
  if (metadata.mode !== undefined) items.push(metadata.mode)
  return items.length ? items : ['-']
}
export function serviceInstanceSummary(record: RuntimeService): string {
  if (record.status === 'online') return `在线 ${record.online_count ?? 0} 个实例`
  if (record.status === 'stale') return `心跳延迟 ${record.stale_count ?? 0} 个实例`
  return '当前无在线实例'
}
export function serviceInstanceNames(record: RuntimeService): string {
  return record.instances?.map(item => item.pod_name || item.instance_name || item.host_name).filter(Boolean).join('、') || '-'
}
export function runtimeLogUrl(base: string, query: string, origin: string): string | null {
  try {
    const url = new URL(base, origin)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null
    url.searchParams.set('query', query)
    return url.href
  } catch { return null }
}
