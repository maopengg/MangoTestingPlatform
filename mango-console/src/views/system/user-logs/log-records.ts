import { normalizeEmptyListTotal } from '@/utils/api-response'
export type LogId = number | string
export interface LogOption { key: number | string; title: string }
export interface UserLogRecord {
  id: LogId
  user: { id: LogId; name: string; username: string } | null
  source_type: string
  create_time: string
  ip: string
  url: string
  method: string
  status_code: string
  request_data: string
  response_data: string
}
export interface UserLogQuery {
  user__in?: string
  source_type__in?: string
  method__in?: string
  url?: string
  request_data?: string
  response_data?: string
  page?: number
  pageSize?: number
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid operation log object')
  return value as Record<string, unknown>
}
function response(value: unknown) {
  const result = object(value)
  if (result.code !== 200) throw Error('Operation logs request failed')
  return result
}
function id(value: unknown): LogId {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid operation log ID')
}
function text(value: unknown): string {
  if (value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid operation log text')
  return value
}
export function parseUserLogRecord(value: unknown): UserLogRecord {
  const row = object(value), user = row.user == null ? null : object(row.user)
  return {
    id: id(row.id), user: user ? { id: id(user.id), name: text(user.name), username: text(user.username) } : null,
    source_type: text(row.source_type), create_time: text(row.create_time), ip: text(row.ip), url: text(row.url),
    method: text(row.method), status_code: text(row.status_code),
    // 审计正文保留后端保存的文本，不解析或重排其中的 JSON。
    request_data: text(row.request_data), response_data: text(row.response_data),
  }
}
export function parseUserLogs(value: unknown): { rows: UserLogRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = response(value)
  if (!Array.isArray(result.data) || typeof result.totalSize !== 'number' || !Number.isSafeInteger(result.totalSize) || result.totalSize < 0) throw Error('Invalid operation log list')
  const rows = result.data.map(parseUserLogRecord)
  if (rows.length > result.totalSize || new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Invalid operation log rows')
  return { rows, total: result.totalSize }
}
export function parseLogOptions(value: unknown): LogOption[] {
  if (!Array.isArray(value)) throw Error('Invalid operation log options')
  const options = value.map(value => {
    const item = object(value)
    if ((typeof item.key !== 'string' || !item.key) && (typeof item.key !== 'number' || !Number.isSafeInteger(item.key))) throw Error('Invalid operation log option key')
    if (typeof item.title !== 'string') throw Error('Invalid operation log option title')
    return { key: item.key as LogOption['key'], title: item.title }
  })
  if (new Set(options.map(item => String(item.key))).size !== options.length) throw Error('Duplicate operation log option')
  return options
}
export function parseUserLogOptions(value: unknown): LogOption[] {
  return parseLogOptions(response(value).data).map(item => ({ key: id(item.key), title: item.title }))
}
export function userLogQuery(value: Record<string, unknown>): UserLogQuery {
  const result: UserLogQuery = {}
  for (const key of ['user__in', 'source_type__in', 'method__in', 'url', 'request_data', 'response_data'] as const) {
    const field = value[key]
    if (field == null || field === '') continue
    if (typeof field !== 'string') throw Error('Invalid operation log search')
    result[key] = field
  }
  return result
}
