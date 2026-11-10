import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { FireRecordCondition } from './config'

export type FireRecordId = number | string
export interface FireRecordRow {
  id: FireRecordId
  task_name: string
  time_task_label: string
  time_task: { name: string } | null
  source_type: number | null
  source_type_name: string
  status: number | null
  status_name: string
  planned_at: string
  fired_at: string
  trigger_node: string
  dispatcher_node: string
  error_message: string
  test_suite: FireRecordId | null
}
export interface FireRecordQuery { task_name?: string; status__in?: string; source_type__in?: string }
function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function text(value: unknown) { return typeof value === 'string' ? value : '' }
function integer(value: unknown): number | null { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null }
export function fireRecordId(value: unknown): FireRecordId | null {
  return integer(value) ?? (typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null)
}
export function fireReportId(value: unknown): FireRecordId | null {
  return fireRecordId(object(value).id ?? value)
}
export function parseFireRecords(value: unknown): { rows: FireRecordRow[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const response = object(value), total = integer(response.totalSize)
  if (response.code !== 200 || !Array.isArray(response.data) || total === null) throw new Error('触发记录格式异常')
  const rows: FireRecordRow[] = [], seen = new Set<string>()
  for (const value of response.data) {
    const item = object(value), id = fireRecordId(item.id)
    if (id === null || seen.has(String(id))) continue
    seen.add(String(id))
    rows.push({ id, task_name: text(item.task_name), time_task_label: text(item.time_task_label),
      time_task: item.time_task ? { name: text(object(item.time_task).name) } : null,
      source_type: integer(item.source_type), source_type_name: text(item.source_type_name), status: integer(item.status), status_name: text(item.status_name),
      planned_at: text(item.planned_at), fired_at: text(item.fired_at), trigger_node: text(item.trigger_node), dispatcher_node: text(item.dispatcher_node),
      error_message: text(item.error_message), test_suite: fireReportId(item.test_suite) })
  }
  return { rows, total }
}
export function buildFireRecordQuery(items: FireRecordCondition[]): FireRecordQuery {
  const result: FireRecordQuery = {}
  for (const item of items) {
    if (item.key === 'task_name') { if (typeof item.value === 'string' && item.value.trim()) result.task_name = item.value.trim(); continue }
    const values = [...new Set((Array.isArray(item.value) ? item.value : [item.value])
      .map(fireRecordId).filter((value): value is FireRecordId => value !== null).map(String))]
    if (!values.length) continue
    if (item.key === 'status') result.status__in = values.join(',')
    if (item.key === 'source_type') result.source_type__in = values.join(',')
  }
  return result
}
export function resetFireRecordConditions(items: FireRecordCondition[]) {
  for (const item of items) item.value = item.multiple ? [] : ''
}
