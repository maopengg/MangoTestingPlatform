import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { SystemErrorRecordQuery } from '@/api/system/error-record'
import type { ErrorRecordCondition } from './config'

export interface ErrorRecordRow {
  __rowKey: string
  source: string
  event_source: string
  object_id: number | string
  time: string
  source_name: string
  title: string
  message: string
  service_name: string
  exception_type: string
  traceback: string
  status: string | number | null
  status_name: string
  count: number
  link: string
  log_query: string
}
function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function text(value: unknown) { return typeof value === 'string' ? value : '' }
function id(value: unknown): string | number | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}
export function parseErrorRecords(value: unknown): { rows: ErrorRecordRow[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = object(value)
  if (result.code !== 200 || !Array.isArray(result.data) || typeof result.totalSize !== 'number' || !Number.isSafeInteger(result.totalSize) || result.totalSize < 0) throw new Error('系统异常列表格式异常')
  const rows: ErrorRecordRow[] = [], seen = new Set<string>()
  for (const value of result.data) {
    const item = object(value), objectId = id(item.object_id), source = text(item.source)
    if (objectId === null || !source) continue
    const key = JSON.stringify([source, String(objectId)])
    if (seen.has(key)) continue
    seen.add(key)
    rows.push({ __rowKey: key, object_id: objectId, source, event_source: text(item.event_source),
      time: text(item.time), source_name: text(item.source_name), title: text(item.title), message: text(item.message),
      service_name: text(item.service_name), exception_type: text(item.exception_type), traceback: text(item.traceback),
      status: typeof item.status === 'string' || typeof item.status === 'number' ? item.status : null,
      status_name: text(item.status_name), count: typeof item.count === 'number' && Number.isSafeInteger(item.count) && item.count >= 0 ? item.count : 1,
      link: text(item.link), log_query: text(item.log_query) })
  }
  return { rows, total: result.totalSize }
}
export function buildErrorRecordQuery(items: ErrorRecordCondition[]): SystemErrorRecordQuery {
  const query: SystemErrorRecordQuery = {}
  for (const item of items) {
    if (item.key === 'keyword' && typeof item.value === 'string' && item.value.trim()) query.keyword = item.value.trim()
    if (item.key === 'category' && (item.value === 'system_error_event' || item.value === 'schedule_fire')) query.category = item.value
    if (item.key === 'source' && Array.isArray(item.value)) {
      const sources = [...new Set(item.value.flatMap(value => value.split(',')).map(value => value.trim()).filter(Boolean))]
      if (sources.length) query.source = sources.join(',')
    }
  }
  return query
}
export function resetErrorRecordConditions(items: ErrorRecordCondition[]) {
  for (const item of items) item.value = item.multiple ? [] : ''
}
export function errorRecordDetail(record: ErrorRecordRow): string {
  return [
    `记录类型：${record.source_name || '-'}`, `记录ID：${record.object_id}`,
    `发生时间：${record.time || '-'}`, `出现次数：${record.count}`,
    `服务名称：${record.service_name || '-'}`, `异常类型：${record.exception_type || '-'}`,
    `对象：${record.title || '-'}`, `错误摘要：${record.message || '-'}`,
    record.traceback ? `异常堆栈：\n${record.traceback}` : '',
  ].filter(Boolean).join('\n')
}
export function errorRecordStatusColor(status: ErrorRecordRow['status']): string {
  return status === 'success' ? 'green' : status === 'warning' ? 'orange' : 'red'
}
export function errorRecordSourcePath(value: string): string | null {
  return value.startsWith('/') && !value.startsWith('//') && !/[\\\u0000-\u001f]/.test(value) ? value : null
}
export function errorRecordLogUrl(base: string, query: string, origin: string): string | null {
  try {
    const url = new URL(base, origin)
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null
    url.searchParams.set('query', query)
    return url.href
  } catch { return null }
}
