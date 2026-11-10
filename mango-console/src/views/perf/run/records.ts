import { normalizeEmptyListTotal } from '@/utils/api-response'
import { formatModulePath } from '@/utils/business-format'
import { normalizeMultiSelectSearchParams } from '@/utils/search-condition'
import type { RunHistoryFilters, RunHistoryRecord } from './types'

export const createRunHistoryFilters = (): RunHistoryFilters => ({ name: '', status: [], verdict: [] })
export const copyRunHistoryFilters = (filters: RunHistoryFilters): RunHistoryFilters => ({ name: filters.name, status: [...filters.status], verdict: [...filters.verdict] })

export function runHistoryQuery(filters: RunHistoryFilters, page: number, pageSize: number) {
  const params = normalizeMultiSelectSearchParams({ ...copyRunHistoryFilters(filters), page, pageSize }, ['status', 'verdict'])
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined))
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid run history response')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid run history text')
  return value
}
function integer(value: unknown, minimum = 0): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum) throw new Error('Invalid run history count')
  return value
}
const optionalCount = (value: unknown) => value == null ? null : integer(value)

export function assertRunHistorySuccess(value: unknown) {
  const response = object(value)
  if (response.code !== 200) throw new Error('Run history request failed')
  return response
}

export function readRunHistory(value: unknown): { rows: RunHistoryRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const response = assertRunHistorySuccess(value)
  if (!Array.isArray(response.data)) throw new Error('Invalid run history rows')
  const total = response.totalSize == null && response.data.length === 0 ? 0 : integer(response.totalSize)
  const rows = response.data.map(value => {
    const row = object(value), product = object(row.project_product)
    const module = row.module == null ? null : object(row.module)
    return {
      id: integer(row.id, 1), name: text(row.name), status: text(row.status), verdict: text(row.verdict),
      engine: text(row.engine), peak_target_users: optionalCount(row.peak_target_users),
      actual_node_count: optionalCount(row.actual_node_count), requested_node_count: optionalCount(row.requested_node_count),
      create_time: text(row.create_time), project_product: { id: integer(product.id, 1), name: text(product.name) },
      module_full_path: module === null ? '' : text(formatModulePath({ id: integer(module.id, 1), name: text(module.name), full_path: text(module.full_path) })),
    }
  })
  return { rows, total }
}
