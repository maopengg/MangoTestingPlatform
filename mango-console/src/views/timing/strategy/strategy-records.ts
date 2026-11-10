import { normalizeEmptyListTotal } from '@/utils/api-response'
import { normalizeIdSearchParams } from '@/utils/id-search'

export type StrategyId = string | number
export interface StrategyRecord {
  id: StrategyId
  name: string
  cron: string
  create_time: string
  update_time: string
  update_user: { id: StrategyId; name: string; username: string } | null
}
export interface StrategyDraft { name: string; cron: string }
export interface StrategyPayload extends StrategyDraft { trigger_type: 'cron'; id?: StrategyId }
export interface StrategyUserOption { key: StrategyId; title: string }

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid timing strategy object')
  return value as Record<string, unknown>
}
function id(value: unknown): StrategyId {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid timing strategy ID')
}
function text(value: unknown, optional = false): string {
  if (optional && value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid timing strategy text')
  return value
}
function response(value: unknown) {
  const result = object(value)
  if (result.code !== 200) throw Error('Timing strategy request failed')
  return result
}
export function strategySuccess(value: unknown, fallback: string): string {
  const result = response(value)
  return typeof result.msg === 'string' && result.msg ? result.msg : fallback
}
export function copyStrategyRecord(value: unknown): StrategyRecord {
  const row = object(value), updateUser = row.update_user == null ? null : object(row.update_user)
  return { id: id(row.id), name: text(row.name), cron: text(row.cron), create_time: text(row.create_time, true), update_time: text(row.update_time, true),
    update_user: updateUser ? { id: id(updateUser.id), name: text(updateUser.name, true), username: text(updateUser.username, true) } : null }
}
export function parseStrategies(value: unknown): { rows: StrategyRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = response(value)
  if (!Array.isArray(result.data) || typeof result.totalSize !== 'number' || !Number.isSafeInteger(result.totalSize) || result.totalSize < 0) throw Error('Invalid timing strategy list')
  const rows = result.data.map(copyStrategyRecord)
  if (rows.length > result.totalSize || new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Invalid timing strategy rows')
  return { rows, total: result.totalSize }
}
export function parseStrategyUsers(value: unknown): StrategyUserOption[] {
  const result = response(value)
  if (!Array.isArray(result.data)) throw Error('Invalid timing strategy users')
  const options = result.data.map(value => {
    const row = object(value)
    return { key: id(row.key), title: text(row.title) }
  })
  if (new Set(options.map(item => String(item.key))).size !== options.length) throw Error('Duplicate timing strategy user')
  return options
}
export function createStrategyDraft(row: StrategyRecord | null = null): StrategyDraft { return { name: row?.name ?? '', cron: row?.cron ?? '' } }
export function validateStrategyDraft(draft: StrategyDraft): string {
  if (!draft.name) return '请输入定时器的介绍'
  if (!draft.cron) return '请输入正确的cron表达式'
  return ''
}
export function strategyPayload(draft: StrategyDraft, recordId: StrategyId | null): StrategyPayload {
  const result: StrategyPayload = { name: text(draft.name), cron: text(draft.cron), trigger_type: 'cron' }
  if (recordId !== null) result.id = id(recordId)
  return result
}
export function strategyQuery(value: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, string | number> = {}
  for (const key of ['id', 'name', 'update_user__in']) {
    const field = value[key]
    if (field == null || field === '') continue
    if (typeof field !== 'string' && typeof field !== 'number') throw Error('Invalid timing strategy search')
    if (typeof field === 'number' && !Number.isFinite(field)) throw Error('Invalid timing strategy search')
    result[key] = field
  }
  return normalizeIdSearchParams(result)
}
