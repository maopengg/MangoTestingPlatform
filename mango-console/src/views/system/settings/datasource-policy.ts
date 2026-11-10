export interface DatasourceBudget {
  cleanup_backlog_limit: number
  concurrency: number
  requests_per_second: number
  connections: number
  cleanup_reserved: number
  cleanup_rate_percent: number
  metadata_per_second: number
}
export type DatasourceKind = 'mysql' | 'redis' | 'elasticsearch'
export interface DatasourceSharedBudget {
  queue_timeout_seconds: number
  max_waiters: number
  permit_lease_seconds: number
  pool_size: number
  transaction_statement_budget: number
  pool_idle_seconds: number
  max_local_pools: number
  cleanup_completion_seconds: number
  cleanup_consumer_threads: number
}
export interface DatasourcePolicy extends DatasourceSharedBudget {
  version: 1
  mysql: DatasourceBudget
  redis: DatasourceBudget
  elasticsearch: DatasourceBudget
}
export interface DatasourceField<Key> { key: Key; label: string; min: number; max: number; hint: string }
export interface DatasourceRuntimeRow {
  group: string
  connections: (number | string)[]
  budget: { concurrency: number; connections: number }
  counts: { operation_active: number; connection_active: number; operation_suspect: number; connection_suspect: number }
  queued: number
  throttled: number
}
export const DATASOURCE_BASE_BUDGET: DatasourceBudget = { cleanup_backlog_limit: 100, concurrency: 6, requests_per_second: 30, connections: 12, cleanup_reserved: 2, cleanup_rate_percent: 25, metadata_per_second: 2 }
const sharedDefaults: DatasourceSharedBudget = { queue_timeout_seconds: 30, max_waiters: 256, permit_lease_seconds: 300, pool_size: 3, transaction_statement_budget: 8, pool_idle_seconds: 60, max_local_pools: 32, cleanup_completion_seconds: 300, cleanup_consumer_threads: 2 }
function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('数据源策略格式异常')
  return value as Record<string, unknown>
}
function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('数据源策略数值格式异常')
  return value
}
function budget(value: unknown, defaults: DatasourceBudget): DatasourceBudget {
  const source = value === undefined ? {} : object(value), result = { ...defaults }
  for (const key of Object.keys(defaults) as (keyof DatasourceBudget)[]) {
    if (source[key] !== undefined) result[key] = number(source[key])
  }
  if (source.concurrency === 2 && !Object.prototype.hasOwnProperty.call(source, 'cleanup_reserved')) result.cleanup_reserved = 1
  return result
}
export function createDatasourcePolicy(value: unknown): DatasourcePolicy {
  if (typeof value === 'string') value = JSON.parse(value)
  const source = object(value)
  if (source.version !== undefined && source.version !== 1) throw new Error('数据源策略版本异常')
  const result: DatasourcePolicy = {
    version: 1, ...sharedDefaults,
    mysql: budget(source.mysql, DATASOURCE_BASE_BUDGET),
    redis: budget(source.redis, { ...DATASOURCE_BASE_BUDGET, concurrency: 12, requests_per_second: 75, connections: 16 }),
    elasticsearch: budget(source.elasticsearch, { ...DATASOURCE_BASE_BUDGET, requests_per_second: 15 }),
  }
  for (const key of Object.keys(sharedDefaults) as (keyof DatasourceSharedBudget)[]) {
    if (source[key] !== undefined) result[key] = number(source[key])
  }
  if (!Object.prototype.hasOwnProperty.call(source, 'pool_size') && [result.mysql, result.redis, result.elasticsearch].some(item => item.connections === 3)) result.pool_size = 2
  return result
}
export function datasourcePolicyPayload(
  value: DatasourcePolicy,
  budgetFields: readonly DatasourceField<keyof DatasourceBudget>[],
  sharedFields: readonly DatasourceField<keyof DatasourceSharedBudget>[],
): DatasourcePolicy {
  const validate = (value: unknown, field: { label: string; min: number; max: number }) => {
    if (typeof value !== 'number' || !Number.isInteger(value) || value < field.min || value > field.max) throw new Error(`${field.label}必须是${field.min}～${field.max}范围内的整数`)
  }
  for (const field of sharedFields) validate(value[field.key], field)
  for (const item of [value.mysql, value.redis, value.elasticsearch]) {
    for (const field of budgetFields) validate(item[field.key], field)
    if (item.cleanup_reserved >= item.concurrency || item.metadata_per_second > item.requests_per_second) throw new Error('清理保留并发必须小于总并发，元数据速率不能超过总速率。')
    if (item.connections <= value.pool_size) throw new Error('连接总数必须大于单池连接数，为清理保留连接容量。')
  }
  return createDatasourcePolicy(value)
}
export function parseDatasourceRuntime(value: unknown): DatasourceRuntimeRow[] {
  if (!Array.isArray(value)) throw new Error('数据源运行状态格式异常')
  const seen = new Set<string>()
  const count = (value: unknown, optional = false) => {
    if (optional && value === undefined) return 0
    if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('数据源运行状态数值异常')
    return value
  }
  return value.map(value => {
    const row = object(value), budget = object(row.budget), counts = row.counts === undefined ? {} : object(row.counts)
    if (typeof row.group !== 'string' || !row.group || seen.has(row.group) || !Array.isArray(row.connections)) throw new Error('数据源实例分组格式异常')
    const group = row.group
    seen.add(group)
    const connections = row.connections.map(value => {
      if ((typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) || (typeof value === 'string' && /^\d+$/.test(value))) return value
      throw new Error('数据源连接标识异常')
    })
    return { group, connections, budget: { concurrency: count(budget.concurrency), connections: count(budget.connections) },
      counts: { operation_active: count(counts.operation_active, true), connection_active: count(counts.connection_active, true), operation_suspect: count(counts.operation_suspect, true), connection_suspect: count(counts.connection_suspect, true) },
      queued: count(row.queued, true), throttled: count(row.throttled, true) }
  })
}
