import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { SqlExecutionQuery } from '@/api/system/sql_execution'
import { normalizeIdSearchParams } from '@/utils/id-search'

export type AuditId = string | number
export type AuditJson = null | string | number | boolean | AuditJson[] | { [key: string]: AuditJson }
export interface AuditOption { key: string | number | boolean; title: string }
export interface AuditOptions {
  datasource_type_options: AuditOption[]
  project_product_options: AuditOption[]
  source_type_options: AuditOption[]
  source_stage_options: AuditOption[]
  environment_options: AuditOption[]
  datasource_alias_options: AuditOption[]
  status_options: AuditOption[]
  slow_options: AuditOption[]
}
export interface SqlExecutionRecord {
  id: AuditId
  request_id: string
  datasource_type_name: string
  datasource_type: AuditId | null
  create_time: string
  project_product_name: string
  datasource_alias_name: string
  database_name: string
  test_env: AuditId | null
  test_env_name: string | number
  source_type: string
  source_id: AuditId | null
  source_stage: string
  source_detail: AuditJson
  status: string
  duration_ms: number | string | null
  is_slow: boolean
  row_count: number
  affected_rows: number
  sql_text: string
  sql_parameters: AuditJson
  result_preview: string
  result_truncated: boolean
  error_message: string
}

export function auditSourceValue(row: SqlExecutionRecord, key: string): string {
  const source = row.source_detail
  if (!source || typeof source !== 'object' || Array.isArray(source)) return '-'
  let value = source[key]
  if (key === 'case_id' && value == null) {
    if (row.source_type === 'api_case') value = row.source_id
    else if (row.source_type === 'data_factory' && source.case_source_type === 4) value = source.case_source_id
  }
  return typeof value === 'number' || typeof value === 'string' ? String(value) : '-'
}

const optionKeys: (keyof AuditOptions)[] = ['datasource_type_options', 'project_product_options',
  'source_type_options', 'source_stage_options', 'environment_options', 'datasource_alias_options', 'status_options', 'slow_options']

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid execution record')
  return value as Record<string, unknown>
}
function response(value: unknown) {
  const result = record(value)
  if (result.code !== 200) throw new Error('Execution records request failed')
  return result
}
function id(value: unknown): AuditId {
  if ((typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) ||
    (typeof value === 'string' && /^\d+$/.test(value))) return value
  throw new Error('Invalid execution ID')
}
function text(value: unknown, optional = false): string {
  if (optional && value == null) return ''
  if (typeof value !== 'string') throw new Error('Invalid execution text')
  return value
}
function flag(value: unknown): boolean {
  if (typeof value !== 'boolean') throw new Error('Invalid execution flag')
  return value
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw new Error('Invalid row count')
  return value
}
function copyJson(value: unknown): AuditJson {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (Array.isArray(value)) return value.map(copyJson)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, value]) => [key, copyJson(value)]))
  throw new Error('Invalid execution JSON')
}

export function emptyAuditOptions(): AuditOptions {
  return { datasource_type_options: [], project_product_options: [], source_type_options: [], source_stage_options: [],
    environment_options: [], datasource_alias_options: [], status_options: [], slow_options: [] }
}
export function parseAuditOptions(value: unknown): AuditOptions {
  const data = record(response(value).data), result = emptyAuditOptions()
  for (const key of optionKeys) {
    const values = data[key]
    if (!Array.isArray(values)) throw new Error('Invalid execution options')
    const seen = new Set<string>()
    result[key] = values.map(value => {
      const option = record(value)
      if (!['string', 'number', 'boolean'].includes(typeof option.key) ||
        (typeof option.key === 'number' && !Number.isFinite(option.key)) ||
        typeof option.title !== 'string' || seen.has(String(option.key))) throw new Error('Invalid execution option')
      seen.add(String(option.key))
      return { key: option.key as AuditOption['key'], title: option.title }
    })
  }
  return result
}
export function copyExecutionRecord(value: unknown): SqlExecutionRecord {
  const item = record(value), duration = item.duration_ms
  if (duration !== null && !((typeof duration === 'number' || (typeof duration === 'string' && /^\d+(?:\.\d+)?$/.test(duration))) &&
    Number.isFinite(Number(duration)) && Number(duration) >= 0)) throw new Error('Invalid execution duration')
  if (typeof item.test_env_name !== 'string' && typeof item.test_env_name !== 'number') throw new Error('Invalid environment label')
  return {
    id: id(item.id), request_id: text(item.request_id), datasource_type_name: text(item.datasource_type_name), create_time: text(item.create_time),
    datasource_type: item.datasource_type == null ? null : id(item.datasource_type),
    project_product_name: text(item.project_product_name, true), datasource_alias_name: text(item.datasource_alias_name, true), database_name: text(item.database_name),
    test_env: item.test_env === null ? null : id(item.test_env), test_env_name: item.test_env_name,
    source_type: text(item.source_type), source_id: item.source_id === null ? null : id(item.source_id), source_stage: text(item.source_stage),
    source_detail: copyJson(item.source_detail), status: text(item.status), duration_ms: duration as SqlExecutionRecord['duration_ms'],
    is_slow: flag(item.is_slow), row_count: count(item.row_count), affected_rows: count(item.affected_rows), sql_text: text(item.sql_text),
    sql_parameters: copyJson(item.sql_parameters), result_preview: text(item.result_preview), result_truncated: flag(item.result_truncated), error_message: text(item.error_message, true),
  }
}
export function parseExecutionList(value: unknown): { rows: SqlExecutionRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = response(value)
  if (!Array.isArray(result.data) || typeof result.totalSize !== 'number' || !Number.isSafeInteger(result.totalSize) || result.totalSize < 0) {
    throw new Error('Invalid execution list')
  }
  const rows = result.data.map(copyExecutionRecord)
  if (new Set(rows.map(item => String(item.id))).size !== rows.length) throw new Error('Duplicate execution record')
  return { rows, total: result.totalSize }
}

const queryKeys = ['case_id', 'case_detail_id', 'test_suite_id', 'operation', 'id', 'id__in', 'source_type', 'source_type__in', 'source_id', 'source_id__in', 'source_stage', 'source_stage__in',
  'project_product_id', 'project_product_id__in', 'test_env', 'test_env__in', 'datasource_alias_id', 'datasource_alias_id__in',
  'datasource_type', 'datasource_type__in', 'database_id', 'database_id__in', 'status', 'status__in', 'is_slow', 'is_slow__in',
  'duration_min', 'duration_max', 'sql_keyword'] as const
export function executionQuery(input: Record<string, unknown>): SqlExecutionQuery {
  const values = normalizeIdSearchParams(input), query: SqlExecutionQuery = {}
  for (const key of queryKeys) {
    const value = values[key]
    if (value === '' || value === null || value === undefined) continue
    if (typeof value !== 'string' && typeof value !== 'number' && !(key === 'is_slow' && typeof value === 'boolean')) throw new Error('Invalid execution filter')
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Invalid execution filter')
    Object.assign(query, { [key]: value })
  }
  const range = values.create_time
  if (range != null && range !== '' && !Array.isArray(range)) throw new Error('Invalid execution date range')
  if (Array.isArray(range) && range.length) {
    if (range.length !== 2 || range.some(value => typeof value !== 'string')) throw new Error('Invalid execution date range')
    query.create_time_start = range[0]
    query.create_time_end = range[1]
  }
  return query
}
