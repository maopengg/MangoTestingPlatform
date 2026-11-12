import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { ExecutionResultAdminQuery } from '@/api/system/execution_result'
import type { ExecutionAdminCondition } from './config'
import { normalizeIdSearchValue } from '@/utils/id-search'

export type ExecutionAdminId = string | number
export type ExecutionResultJson = { state: 'available'; value: unknown } | { state: 'cleaned' | 'empty' }

export function parseExecutionResultJson(response: unknown, expectedId: ExecutionAdminId): ExecutionResultJson {
  const detail = object(success(response).data)
  if (String(id(detail.id)) !== String(expectedId) || typeof detail.result_cleaned !== 'boolean' || typeof detail.has_result_data !== 'boolean')
    throw new Error('执行结果响应不匹配')
  if (detail.result_cleaned) return { state: 'cleaned' }
  if (!detail.has_result_data) return { state: 'empty' }
  if (detail.result_too_large || detail.result_data == null) throw new Error('完整结果文件不可读取')
  return { state: 'available', value: detail.result_data }
}
export interface ExecutionAdminOption { key: ExecutionAdminId; title: string }
export type ExecutionAdminOptionKey = 'source_type' | 'target_type' | 'status' | 'test_env' | 'result_state' | 'is_latest' | 'trigger_user_id'
export interface ExecutionAdminConfig {
  retention_days: number
  expired_pending_count: number
  cleanup_cron: string
  next_cleanup_at: string
  options: Record<Exclude<ExecutionAdminOptionKey, 'trigger_user_id'>, ExecutionAdminOption[]>
}
export interface ExecutionAdminRow {
  id: ExecutionAdminId
  source_type: string
  source_type_name: string
  target_type: string
  target_type_name: string
  target_id: ExecutionAdminId | null
  status: number | null
  status_name: string
  test_env: ExecutionAdminId | null
  test_env_name: string
  duration: number | null
  attempt_no: number
  is_latest: boolean
  result_cleaned: boolean
  has_result_data: boolean
  result_size: number
  trigger_user_name: string
  test_suite: ExecutionAdminId | null
  test_suite_detail: ExecutionAdminId | null
  revision_id: ExecutionAdminId | null
  release_id: ExecutionAdminId | null
  trace_id: string
  task_id: string
  error_message: string
  create_time: string
}
function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function text(value: unknown) { return typeof value === 'string' ? value : '' }
function integer(value: unknown): number | null { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null }
function id(value: unknown): ExecutionAdminId | null {
  return integer(value) ?? (typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null)
}
function success(value: unknown) {
  const result = object(value)
  if (result.code !== 200) throw new Error('执行结果请求未成功')
  return result
}
function options(value: unknown): ExecutionAdminOption[] {
  if (!Array.isArray(value)) throw new Error('执行结果选项格式异常')
  const items: ExecutionAdminOption[] = [], seen = new Set<string>()
  for (const entry of value) {
    const item = object(entry), key = item.key
    if ((typeof key !== 'string' && typeof key !== 'number') || key === '' || !text(item.title) || seen.has(String(key))) continue
    if (typeof key === 'number' && !Number.isFinite(key)) continue
    seen.add(String(key)); items.push({ key, title: text(item.title) })
  }
  return items
}
export function parseExecutionAdminOptions(value: unknown) { return options(success(value).data) }
export function parseExecutionAdminConfig(value: unknown): ExecutionAdminConfig {
  const data = object(success(value).data), days = integer(data.retention_days), pending = integer(data.expired_pending_count)
  if (days === null || days <= 0 || pending === null) throw new Error('执行结果保留策略格式异常')
  return { retention_days: days, expired_pending_count: pending, cleanup_cron: text(data.cleanup_cron), next_cleanup_at: text(data.next_cleanup_at),
    options: { source_type: options(data.source_type_options), target_type: options(data.target_type_options), status: options(data.status_options),
      test_env: options(data.test_env_options), result_state: options(data.result_state_options), is_latest: options(data.is_latest_options) } }
}
export function parseExecutionAdminRows(value: unknown): { rows: ExecutionAdminRow[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = success(value), total = integer(result.totalSize)
  if (!Array.isArray(result.data) || total === null) throw new Error('执行结果列表格式异常')
  const rows: ExecutionAdminRow[] = [], seen = new Set<string>()
  for (const value of result.data) {
    const item = object(value), rowId = id(item.id)
    if (rowId === null || seen.has(String(rowId))) continue
    if (typeof item.is_latest !== 'boolean' || typeof item.result_cleaned !== 'boolean' || typeof item.has_result_data !== 'boolean') throw new Error('执行结果状态格式异常')
    seen.add(String(rowId))
    const duration = (typeof item.duration === 'string' && item.duration.trim() !== '') || typeof item.duration === 'number' ? Number(item.duration) : NaN
    rows.push({ id: rowId, source_type: text(item.source_type), source_type_name: text(item.source_type_name), target_type: text(item.target_type),
      target_type_name: text(item.target_type_name), target_id: id(item.target_id), status: integer(item.status), status_name: text(item.status_name),
      test_env: id(item.test_env), test_env_name: text(item.test_env_name), duration: Number.isFinite(duration) && duration >= 0 ? duration : null,
      attempt_no: integer(item.attempt_no) ?? 0, is_latest: item.is_latest, result_cleaned: item.result_cleaned, has_result_data: item.has_result_data,
      result_size: integer(item.result_size) ?? 0, trigger_user_name: text(item.trigger_user_name), test_suite: id(item.test_suite), test_suite_detail: id(item.test_suite_detail),
      revision_id: id(item.revision_id), release_id: id(item.release_id), trace_id: text(item.trace_id), task_id: text(item.task_id), error_message: text(item.error_message), create_time: text(item.create_time) })
  }
  return { rows, total }
}
export function parseExecutionAdminCleanup(value: unknown): number {
  const count = integer(object(success(value).data).updated_count)
  if (count === null) throw new Error('清理回执格式异常')
  return count
}
function dateTime(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) return null
  const date = new Date(`${value.replace(' ', 'T')}Z`)
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 19).replace('T', ' ') === value ? value : null
}
export function buildExecutionAdminQuery(items: ExecutionAdminCondition[]): ExecutionResultAdminQuery {
  const result: ExecutionResultAdminQuery = {}
  for (const item of items) {
    const value = item.value
    if (item.key === 'id' || item.key === 'target_id') {
      const normalized = normalizeIdSearchValue(value, item.key === 'id')
      if (normalized === null) throw new Error('执行结果 ID 格式异常')
      if (!normalized) continue
      if (item.key === 'id' && normalized.includes(',')) result.id__in = [...new Set(normalized.split(',').filter(Boolean))].join(',')
      else result[item.key] = normalized
    } else if (item.key === 'create_time' && Array.isArray(value) && value.length) {
      const start = typeof value[0] === 'string' ? dateTime(value[0]) : null, end = typeof value[1] === 'string' ? dateTime(value[1]) : null
      if (value.length !== 2 || !start || !end || start > end) throw new Error('执行结果创建时间格式异常')
      result.create_time_start = start; result.create_time_end = end
    } else if (item.key === 'is_latest') {
      if (value === true || value === false || value === 'true' || value === 'false') result.is_latest = value
    } else if (item.key === 'trace_id' && typeof value === 'string' && value.trim()) result.trace_id = value.trim()
    else if (['source_type', 'target_type', 'status', 'test_env', 'trigger_user_id', 'result_state'].includes(item.key)) {
      const values = [...new Set((Array.isArray(value) ? value : [value]).filter(v => v !== '' && v != null).map(String))]
      if (!values.length) continue
      switch (item.key) {
        case 'source_type': result.source_type__in = values.join(','); break
        case 'target_type': result.target_type__in = values.join(','); break
        case 'status': result.status__in = values.join(','); break
        case 'test_env': result.test_env__in = values.join(','); break
        case 'trigger_user_id': result.trigger_user_id__in = values.join(','); break
        case 'result_state': result.result_state__in = values.join(','); break
      }
    }
  }
  return result
}
export function resetExecutionAdminConditions(items: ExecutionAdminCondition[]) {
  for (const item of items) item.value = item.type === 'range' || item.multiple ? [] : ''
}
