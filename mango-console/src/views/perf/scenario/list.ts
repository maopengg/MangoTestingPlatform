import { normalizeEmptyListTotal } from '@/utils/api-response'
import { formatModulePath } from '@/utils/business-format'
import { selectionId } from './create'
import type { ScenarioLoadType } from './create'

export interface ScenarioFilters {
  name: string
  load_type: ScenarioLoadType[]
  project_product: number | null
  module: number | null
}
export interface ScenarioRow {
  id: number
  name: string
  load_type: ScenarioLoadType
  target_users: number | null
  target_rate: number | null
  rate_time_unit: 'second' | 'minute' | null
  duration_seconds: number
  step_count: number
  default_executor_count: number
  status: 0 | 1
  update_time: string
  project_product: { id: number; name: string }
  module: { id: number; name: string; full_path: string } | null
  module_full_path: string
}
export const createScenarioFilters = (): ScenarioFilters => ({ name: '', load_type: [], project_product: null, module: null })
export const copyScenarioFilters = (filters: ScenarioFilters): ScenarioFilters => ({
  name: filters.name, load_type: [...filters.load_type],
  project_product: selectionId(filters.project_product), module: selectionId(filters.module),
})
export function scenarioQuery(filters: ScenarioFilters, page: number, pageSize: number): Record<string, unknown> {
  const result: Record<string, unknown> = { page, pageSize }
  if (filters.name !== '') result.name = filters.name
  if (filters.load_type.length) result.load_type__in = filters.load_type.join(',')
  if (filters.project_product !== null) result.project_product = filters.project_product
  if (filters.module !== null) result.module = filters.module
  return result
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('场景响应格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('场景文本格式不正确')
  return value
}
function count(value: unknown, minimum = 0): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum) throw new Error('场景数值格式不正确')
  return value
}
function rate(value: unknown): number | null {
  if (value === null) return null
  if (typeof value !== 'number' && (typeof value !== 'string' || !/^\d+(\.\d+)?$/.test(value))) throw new Error('场景速率格式不正确')
  const result = Number(value)
  if (!Number.isFinite(result) || result < 0) throw new Error('场景速率格式不正确')
  return result
}
export function scenarioSuccess(value: unknown): Record<string, unknown> {
  const result = object(value)
  if (result.code !== 200) throw new Error('场景请求未成功')
  return result
}
export function readScenarioRows(value: unknown): { rows: ScenarioRow[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const response = scenarioSuccess(value), total = count(response.totalSize)
  if (!Array.isArray(response.data)) throw new Error('场景列表格式不正确')
  const rows = response.data.map((value): ScenarioRow => {
    const row = object(value), product = object(row.project_product), module = row.module === null ? null : object(row.module)
    if (row.load_type !== 'concurrency' && row.load_type !== 'arrival_rate' && row.load_type !== 'iteration_rate') throw new Error('场景负载模型格式不正确')
    if (row.status !== 0 && row.status !== 1) throw new Error('场景状态格式不正确')
    if (row.rate_time_unit !== null && row.rate_time_unit !== 'second' && row.rate_time_unit !== 'minute') throw new Error('场景速率单位格式不正确')
    const finiteModule = module ? { id: count(module.id, 1), name: text(module.name), full_path: text(module.full_path) } : null
    return {
      id: count(row.id, 1), name: text(row.name), load_type: row.load_type,
      target_users: row.target_users === null ? null : count(row.target_users), target_rate: rate(row.target_rate),
      rate_time_unit: row.rate_time_unit, duration_seconds: count(row.duration_seconds, 1), step_count: count(row.step_count),
      default_executor_count: count(row.default_executor_count, 1), status: row.status, update_time: text(row.update_time),
      project_product: { id: count(product.id, 1), name: text(product.name) }, module: finiteModule,
      module_full_path: text(row.module_full_path) || (finiteModule ? formatModulePath(finiteModule) : ''),
    }
  })
  if (new Set(rows.map(row => row.id)).size !== rows.length || rows.length > total) throw new Error('场景列表数量不正确')
  return { rows, total }
}
