import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { TaskCaseId } from './task-config'
import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'

export interface TaskCaseOption { key: TaskCaseId; title: string }
export interface CandidateCase extends TaskCaseOption {
  module: { id: TaskCaseId; name: string; full_path: string } | null
  published_release_id: TaskCaseId | null
}
export interface BoundCaseRecord {
  id: TaskCaseId
  type: number
  case_name: string
  product_path: string
  module_path: string
  owner_name: string
  scenario_layer: string | number | null
  scenario_type: string | number | null
  level: string | number | null
  scenario_tags: string[]
}
export interface RuleCaseRecord {
  row_key: string
  case_id: TaskCaseId
  case_name: string
  case_type: number
  project_product_id: TaskCaseId
  module_id: TaskCaseId | null
  module_full_path: string
  scenario_tags: string[]
  publication_status: string
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid task case object')
  return value as Record<string, unknown>
}
function response(value: unknown) {
  const envelope = object(value)
  if (envelope.code !== 200) throw Error('Task case request failed')
  return envelope
}
function id(value: unknown): TaskCaseId {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid task case ID')
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw Error('Invalid task case count')
  return value
}
function text(value: unknown, optional = false): string {
  if (optional && value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid task case text')
  return value
}
function tags(value: unknown): string[] {
  if (value == null) return []
  if (!Array.isArray(value)) throw Error('Invalid task case tags')
  return value.map(item => text(item))
}
function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw Error('Invalid task case list')
  return value
}
function unique<T>(rows: T[], key: (row: T) => TaskCaseId): T[] {
  if (new Set(rows.map(row => String(key(row)))).size !== rows.length) throw Error('Duplicate task case ID')
  return rows
}
function enumValue(value: unknown): number | string | null {
  if (value == null || value === '') return null
  if (typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))) return value
  throw Error('Invalid task case enum')
}
function named(value: unknown): string {
  return value == null ? '' : text(object(value).name, true)
}
export function parseTaskCaseOptions(value: unknown): TaskCaseOption[] {
  return unique(list(response(value).data).map(value => {
    const row = object(value)
    return { key: id(row.key), title: text(row.title) }
  }), row => row.key)
}
export function parseCandidateCases(value: unknown): CandidateCase[] {
  return unique(list(response(value).data).map(value => {
    const row = object(value), module = row.module == null ? null : object(row.module)
    return { key: id(row.key), title: text(row.title),
      module: module ? { id: id(module.id), name: text(module.name), full_path: text(module.full_path, true) } : null,
      published_release_id: row.published_release_id == null ? null : id(row.published_release_id) }
  }), row => row.key)
}
export function parseBoundCaseKeys(value: unknown): Set<string> {
  return new Set(list(response(value).data).map(value => String(id(object(value).case_id))))
}
export function parseBoundCases(value: unknown): { rows: BoundCaseRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const envelope = response(value), total = count(envelope.totalSize)
  const rows = unique(list(envelope.data).map(value => {
    const row = object(value), type = count(row.type)
    const assetValue = row.ui_case ?? row.api_case ?? row.pytest_case
    const asset = assetValue == null ? {} : object(assetValue)
    const productPath = formatProjectProductPath(asset.project_product), modulePath = formatModulePath(asset.module)
    return { id: id(row.id), type, case_name: text(asset.name, true) || '-',
      product_path: (productPath !== '-' ? productPath : '') || text(asset.project_product_name, true) || named(asset.project) || named(asset.product) || '-',
      module_path: (modulePath !== '-' ? modulePath : '') || text(asset.module_name, true) || '-',
      owner_name: named(asset.case_people) || text(asset.case_people_name, true) || named(asset.user) || named(asset.create_user) || '-',
      scenario_layer: enumValue(asset.scenario_layer), scenario_type: enumValue(asset.scenario_type), level: enumValue(asset.level), scenario_tags: tags(asset.scenario_tags) }
  }), row => row.id)
  if (rows.length > total) throw Error('Invalid bound case total')
  return { rows, total }
}
export function parseRuleCases(value: unknown): { rows: RuleCaseRecord[]; total: number; selectedCount: number } {
  const data = object(response(value).data), total = count(data.count), summary = object(data.summary)
  const rows = list(data.items).map(value => {
    const row = object(value)
    const caseId = id(row.case_id), caseType = count(row.case_type)
    return { row_key: `${caseType}:${caseId}`, case_id: caseId, case_name: text(row.case_name), case_type: caseType, project_product_id: id(row.project_product_id),
      module_id: row.module_id == null ? null : id(row.module_id), module_full_path: text(row.module_full_path, true),
      scenario_tags: tags(row.scenario_tags), publication_status: text(row.publication_status) }
  })
  // Different automation types may use the same numeric case ID.
  if (new Set(rows.map(row => `${row.case_type}:${row.case_id}`)).size !== rows.length || rows.length > total) throw Error('Invalid rule case rows')
  return { rows, total, selectedCount: count(summary.selected_count) }
}
export function taskCaseSuccessMessage(value: unknown, binding = false): string {
  const envelope = response(value), message = text(envelope.msg, true) || '操作成功'
  if (!binding || envelope.data == null) return message
  const data = object(envelope.data)
  return `${message}：新增 ${count(data.created_count)} 条，更新 ${count(data.updated_count)} 条，已添加跳过 ${count(data.skipped_count)} 条`
}
export function taskCaseLeaf(value: unknown): TaskCaseId | '' {
  if (Array.isArray(value)) return taskCaseLeaf(value[value.length - 1])
  if (value == null || value === '') return ''
  return id(value)
}
