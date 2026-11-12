export interface DatasourceBudget { connections: number }
export type DatasourceKind = 'mysql' | 'redis' | 'elasticsearch'
export interface DatasourceSharedBudget {
  pool_size: number
  pool_idle_seconds: number
  max_local_pools: number
  cleanup_completion_seconds: number
  cleanup_consumer_threads: number
}
export interface DatasourcePolicy extends DatasourceSharedBudget {
  version: 2
  mysql: DatasourceBudget
  redis: DatasourceBudget
  elasticsearch: DatasourceBudget
}
export interface DatasourceField<Key> { key: Key; label: string; min: number; max: number; hint: string }
export interface DatasourceRuntimeRow {
  group: string
  connections: (number | string)[]
  budget: { connections: number }
  counts: { connection_active: number; connection_suspect: number }
  connection_waiting: boolean
}
const sharedDefaults: DatasourceSharedBudget = {
  pool_size: 4, pool_idle_seconds: 60, max_local_pools: 32,
  cleanup_completion_seconds: 300, cleanup_consumer_threads: 2,
}
function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('数据源连接配置格式异常')
  return value as Record<string, unknown>
}
function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('数据源连接配置数值格式异常')
  return value
}
export function createDatasourcePolicy(value: unknown): DatasourcePolicy {
  if (typeof value === 'string') value = JSON.parse(value)
  const source = object(value)
  if (source.version !== undefined && source.version !== 2) throw new Error('请管理员先完成旧数据源限流配置退役')
  const result: DatasourcePolicy = { version: 2, ...sharedDefaults,
    mysql: { connections: 20 }, redis: { connections: 16 }, elasticsearch: { connections: 12 } }
  const allowed = new Set(['version', ...Object.keys(sharedDefaults), 'mysql', 'redis', 'elasticsearch'])
  if (Object.keys(source).some(key => !allowed.has(key))) throw new Error('连接配置包含已删除或未知的配置项')
  for (const kind of ['mysql', 'redis', 'elasticsearch'] as const) {
    if (source[kind] !== undefined) {
      const item = object(source[kind])
      if (Object.keys(item).some(key => key !== 'connections')) throw new Error('连接配置包含已删除的操作限流项')
      if (item.connections !== undefined) result[kind].connections = number(item.connections)
    }
  }
  for (const key of Object.keys(sharedDefaults) as (keyof DatasourceSharedBudget)[]) {
    if (source[key] !== undefined) result[key] = number(source[key])
  }
  return result
}
export function datasourcePolicyPayload(value: DatasourcePolicy,
  budgetFields: readonly DatasourceField<keyof DatasourceBudget>[],
  sharedFields: readonly DatasourceField<keyof DatasourceSharedBudget>[]): DatasourcePolicy {
  const validate = (value: unknown, field: { label: string; min: number; max: number }) => {
    if (typeof value !== 'number' || !Number.isInteger(value) || value < field.min || value > field.max)
      throw new Error(`${field.label}必须是${field.min}～${field.max}范围内的整数`)
  }
  for (const field of sharedFields) validate(value[field.key], field)
  for (const item of [value.mysql, value.redis, value.elasticsearch]) {
    for (const field of budgetFields) validate(item[field.key], field)
    if (item.connections <= value.pool_size) throw new Error('连接总数必须大于单池连接数，为清理保留连接容量')
  }
  return createDatasourcePolicy(value)
}
export function parseDatasourceRuntime(value: unknown): DatasourceRuntimeRow[] {
  if (!Array.isArray(value)) throw new Error('数据源运行状态格式异常')
  const seen = new Set<string>()
  const count = (value: unknown) => {
    if (value === undefined) return 0
    if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('连接数量格式异常')
    return value
  }
  return value.map(value => {
    const row = object(value), budget = object(row.budget), counts = object(row.counts ?? {})
    if (typeof row.group !== 'string' || !row.group || seen.has(row.group) || !Array.isArray(row.connections))
      throw new Error('数据源实例分组格式异常')
    seen.add(row.group)
    const connections = row.connections.map(value => {
      if ((typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) ||
          (typeof value === 'string' && /^\d+$/.test(value))) return value
      throw new Error('连接标识格式异常')
    })
    if (typeof row.connection_waiting !== 'boolean') throw new Error('连接等待状态格式异常')
    return { group: row.group, connections, budget: { connections: count(budget.connections) },
      counts: { connection_active: count(counts.connection_active), connection_suspect: count(counts.connection_suspect) },
      connection_waiting: row.connection_waiting }
  })
}
