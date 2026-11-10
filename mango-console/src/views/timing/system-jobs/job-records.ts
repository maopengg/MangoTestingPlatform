import { normalizeEmptyListTotal } from '@/utils/api-response'
export type SystemJobId = number | string
export interface SystemJobFire {
  id: SystemJobId
  status: number | null
  status_name: string
  planned_at: string
  fired_at: string
  error_message: string
}
export interface SystemJobRecord {
  key: string
  name: string
  description: string
  cron: string
  next_fire_at: string
  source_type: number
  source_type_name: string
  latest_fire: SystemJobFire | null
}
export interface SystemJobQuery {
  key?: string
  name?: string
  description?: string
  cron?: string
  source_type__in?: string
  latest_status__in?: string
  latest_error_message?: string
  page?: number
  pageSize?: number
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid system job object')
  return value as Record<string, unknown>
}
function response(value: unknown) {
  const result = object(value)
  if (result.code !== 200) throw Error('System job request failed')
  return result
}
function text(value: unknown, optional = false): string {
  if (optional && value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid system job text')
  return value
}
function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw Error('Invalid system job status')
  return value
}
function id(value: unknown): SystemJobId {
  if (typeof value === 'number') return number(value)
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid system job fire ID')
}
export function copySystemJob(value: unknown): SystemJobRecord {
  const row = object(value), fire = row.latest_fire == null ? null : object(row.latest_fire)
  const key = text(row.key)
  if (!key.trim()) throw Error('Missing system job key')
  return { key, name: text(row.name), description: text(row.description), cron: text(row.cron),
    next_fire_at: text(row.next_fire_at, true), source_type: number(row.source_type), source_type_name: text(row.source_type_name, true),
    latest_fire: fire ? { id: id(fire.id), status: fire.status == null ? null : number(fire.status), status_name: text(fire.status_name, true),
      planned_at: text(fire.planned_at, true), fired_at: text(fire.fired_at, true), error_message: text(fire.error_message, true) } : null }
}
export function parseSystemJobs(value: unknown): { rows: SystemJobRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = response(value)
  if (!Array.isArray(result.data)) throw Error('Invalid system job list')
  const total = number(result.totalSize), rows = result.data.map(copySystemJob)
  if (rows.length > total || new Set(rows.map(row => row.key)).size !== rows.length) throw Error('Invalid system job rows')
  return { rows, total }
}
export function systemJobQuery(value: Record<string, unknown>): SystemJobQuery {
  const result: SystemJobQuery = {}
  for (const key of ['key', 'name', 'description', 'cron', 'source_type__in', 'latest_status__in', 'latest_error_message'] as const) {
    const field = value[key]
    if (field == null || field === '') continue
    if (typeof field !== 'string' && (typeof field !== 'number' || !Number.isFinite(field))) throw Error('Invalid system job search')
    const normalized = String(field).trim()
    if (normalized) result[key] = normalized
  }
  return result
}
export function parseSystemJobTrigger(value: unknown): { fireId: SystemJobId; status: number; message: string } {
  const result = response(value), data = object(result.data)
  return { fireId: id(data.fire_id), status: number(data.status), message: typeof result.msg === 'string' && result.msg ? result.msg : '触发完成' }
}
