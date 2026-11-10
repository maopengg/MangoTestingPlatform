import type { ReportCondition, ReportSearchId, ReportSearchKey } from './config'
import { normalizeIdSearchValue } from '@/utils/id-search'

export type ReportFilterItem = Pick<ReportCondition, 'key' | 'type' | 'multiple'> & {
  value: ReportSearchId | ReportSearchId[] | null
}
type QueryKey = 'id' | 'id__in' | 'project_product' | 'module' | 'module__in' | 'tasks_id'
  | 'tasks__task_group_id__in' | 'status__in' | 'test_env__in' | 'execution_scene__in'
  | 'execution_scope__in' | 'case_type__in' | 'user__in' | 'tasks__isnull'
  | 'create_time__gte' | 'create_time__lte' | 'group_execution_id'
export type ReportFilters = Partial<Record<QueryKey, ReportSearchId | boolean>>
export type ReportRouteQuery = Readonly<Record<string, unknown>>

function id(value: unknown): ReportSearchId | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}
function ids(value: unknown): ReportSearchId[] {
  const values = Array.isArray(value) ? value : [value]
  const found = new Map<string, ReportSearchId>()
  for (const entry of values) {
    for (const part of typeof entry === 'string' ? entry.split(',') : [entry]) {
      const parsed = id(part)
      if (parsed !== null) found.set(String(parsed), parsed)
    }
  }
  return [...found.values()]
}
function selectedId(value: ReportFilterItem['value']) {
  return id(Array.isArray(value) ? value[value.length - 1] : value)
}
function first(value: unknown): unknown { return Array.isArray(value) ? value[0] : value }
function date(value: unknown): string | null {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const parsed = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value ? value : null
}
const collectionKeys = {
  status: 'status__in', tasks__task_group_id: 'tasks__task_group_id__in',
  test_env: 'test_env__in', execution_scene: 'execution_scene__in',
  execution_scope: 'execution_scope__in', case_type: 'case_type__in', user: 'user__in',
} as const

export function resetReportConditions(items: ReportFilterItem[]) {
  for (const item of items) item.value = item.multiple || item.type === 'date-range' ? [] : ''
}

/** Route filters are navigation context, never a general HTTP parameter passthrough. */
export function applyReportRouteFilters(items: ReportFilterItem[], query: ReportRouteQuery) {
  for (const item of items) {
    const raw = query[item.key]
    if (raw === undefined) continue
    if (item.key === 'report_source') {
      const value = first(raw)
      item.value = value === 'scheduled' || value === 'non_scheduled' ? value : ''
    } else if (item.key === 'project_product' || item.key === 'module' || item.key === 'tasks_id') {
      item.value = ids(raw)[0] ?? ''
    } else if (item.multiple) item.value = ids(raw)
  }
  const start = date(first(query.start_date))
  const end = date(first(query.end_date))
  const range = items.find(item => item.key === 'date_range')
  if (range && start && end && start <= end) range.value = [start, end]
}

export function buildReportFilters(
  items: readonly ReportFilterItem[], moduleIds: readonly ReportSearchId[], query: ReportRouteQuery,
): ReportFilters {
  const values = new Map<ReportSearchKey, ReportFilterItem['value']>(items.map(item => [item.key, item.value]))
  const result: ReportFilters = {}
  const searchId = normalizeIdSearchValue(values.get('id'))
  if (searchId) {
    if (searchId.includes(',')) result.id__in = [...new Set(searchId.split(',').filter(Boolean))].join(',')
    else result.id = searchId
  }
  for (const key of ['project_product', 'module', 'tasks_id'] as const) {
    const value = selectedId(values.get(key) ?? null)
    if (value !== null) result[key] = value
  }
  for (const key of Object.keys(collectionKeys) as Array<keyof typeof collectionKeys>) {
    const value = ids(values.get(key))
    if (value.length) result[collectionKeys[key]] = value.join(',')
  }
  const modules = ids(moduleIds)
  if (modules.length) { result.module__in = modules.join(','); delete result.module }
  const source = values.get('report_source')
  if (source === 'scheduled' || source === 'non_scheduled') result.tasks__isnull = source === 'non_scheduled'
  const range = values.get('date_range')
  const start = Array.isArray(range) ? date(range[0]) : null
  const end = Array.isArray(range) ? date(range[1]) : null
  if (start && end && start <= end) {
    result.create_time__gte = `${start} 00:00:00`
    result.create_time__lte = `${end} 23:59:59`
  }
  const groupId = id(first(query.group_execution_id))
  if (groupId !== null) result.group_execution_id = groupId
  const reportIds = ids(first(query.test_suite_ids))
  if (reportIds.length) result.id__in = reportIds.join(',')
  return result
}
