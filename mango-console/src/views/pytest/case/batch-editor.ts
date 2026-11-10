import { formatProjectProductPath } from '@/utils/business-format'

export type BatchOptionId = string | number
export type BatchPublication = 'unpublished' | 'prepublished' | 'published'
export interface BatchScope { key: string; label: string; caseIds: number[]; disabled?: boolean }
export interface BatchUserOption { key: BatchOptionId; title: string }
export interface BatchValues {
  name: string
  module: BatchOptionId | null
  asset_status: BatchOptionId | null
  level: BatchOptionId | null
  scenario_layer: BatchOptionId | null
  scenario_type: BatchOptionId | null
  scenario_tags: BatchOptionId[]
  scenario_description: string
  case_people: BatchOptionId | null
}
export interface BatchRow extends BatchValues {
  id: number
  projectProductId: number | null
  projectProductLabel: string
  publication_status: BatchPublication
}
export const batchEditableFields = ['name', 'module', 'asset_status', 'level', 'scenario_layer', 'scenario_type', 'scenario_tags', 'scenario_description', 'case_people'] as const
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('用例响应格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string { if (typeof value !== 'string') throw new Error('用例文本格式不正确'); return value }
function option(value: unknown): BatchOptionId {
  if (typeof value === 'string' && value.length) return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  throw new Error('用例选项格式不正确')
}
function optional(value: unknown): BatchOptionId | null { return value == null ? null : option(value) }
function tags(value: unknown): BatchOptionId[] {
  if (!Array.isArray(value)) throw new Error('执行场景格式不正确')
  return value.map(option)
}
export function batchId(value: unknown): number {
  if ((typeof value !== 'number' && (typeof value !== 'string' || !/^\d+$/.test(value))) || !Number.isSafeInteger(Number(value)) || Number(value) < 1) throw new Error('用例标识不正确')
  return Number(value)
}
function relationId(value: unknown): number | null { return value == null ? null : batchId(object(value).id) }
export function batchSuccess(value: unknown): Record<string, unknown> {
  const response = object(value)
  if (response.code !== 200) throw new Error('用例操作未成功')
  return response
}
export function batchScopeIds(scope: BatchScope | null): number[] {
  if (!scope || scope.disabled || !scope.caseIds.length || scope.caseIds.length > 500) throw new Error('请选择包含 1-500 条 Case 的编辑范围')
  const ids = scope.caseIds.map(batchId)
  if (new Set(ids).size !== ids.length) throw new Error('编辑范围包含重复 Case')
  return ids
}
export function readBatchRows(value: unknown, caseIds: number[]): BatchRow[] {
  const response = batchSuccess(value)
  if (!Array.isArray(response.data)) throw new Error('用例列表格式不正确')
  const order = new Map(caseIds.map((id, index) => [id, index])), seen = new Set<number>()
  return response.data.map(value => {
    const row = object(value), id = batchId(row.id)
    if (!order.has(id) || seen.has(id)) throw new Error('用例列表范围不正确')
    seen.add(id)
    if (!['unpublished', 'prepublished', 'published'].includes(String(row.publication_status))) throw new Error('发布状态不正确')
    const publication_status = row.publication_status as BatchPublication
    const product = row.project_product == null ? null : object(row.project_product)
    const target = product?.project_product == null ? null : object(product.project_product)
    const project = target?.project == null ? null : object(target.project)
    const display = target ? { name: text(target.name), project: project ? { name: text(project.name) } : null } : null
    return { id, projectProductId: target ? batchId(target.id) : null, projectProductLabel: formatProjectProductPath(display),
      name: text(row.name), module: relationId(row.module), publication_status,
      asset_status: optional(row.asset_status ?? (publication_status === 'published' ? 1 : 0)), level: optional(row.level),
      scenario_layer: optional(row.scenario_layer ?? 0), scenario_type: optional(row.scenario_type ?? 0),
      scenario_tags: row.scenario_tags == null ? [] : tags(row.scenario_tags),
      scenario_description: row.scenario_description == null ? '' : text(row.scenario_description), case_people: relationId(row.case_people) }
  }).sort((left, right) => order.get(left.id)! - order.get(right.id)!)
}
export function batchValues(row: BatchRow): BatchValues {
  return { name: row.name.trim(), module: row.module, asset_status: row.asset_status, level: row.level,
    scenario_layer: row.scenario_layer, scenario_type: row.scenario_type, scenario_tags: [...row.scenario_tags],
    scenario_description: row.scenario_description, case_people: row.case_people }
}
export function batchChanges(row: BatchRow, original?: BatchValues): Partial<BatchValues> {
  const current = batchValues(row)
  return Object.fromEntries(batchEditableFields.filter(key => JSON.stringify(current[key]) !== JSON.stringify(original?.[key])).map(key => [key, current[key]])) as Partial<BatchValues>
}
export function validateBatchRows(rows: BatchRow[]): string {
  for (const row of rows) {
    if (!row.name.trim()) return `Case ${row.id} 的用例名称不能为空`
    for (const [key, label] of [['module', '所属模块'], ['asset_status', '资产状态'], ['level', '优先级'], ['scenario_layer', '测试层级'], ['scenario_type', '验证类型'], ['case_people', '用例负责人']] as const) {
      if (row[key] == null || row[key] === '') return `Case ${row.id} 请选择${label}`
    }
    try { batchId(row.module); batchId(row.case_people) } catch { return `Case ${row.id} 的模块或负责人不正确` }
    if (!row.scenario_tags.length) return `Case ${row.id} 请选择执行场景`
  }
  return ''
}
export function readBatchSaveCount(value: unknown, expected: number): number {
  const count = object(batchSuccess(value).data).updated_count
  if (typeof count !== 'number' || !Number.isSafeInteger(count) || count !== expected) throw new Error('保存数量与提交不一致')
  return count
}
export function readBatchPredictions(value: unknown, ids: number[]): Map<number, Partial<BatchValues>> {
  const data = object(batchSuccess(value).data)
  if (!Array.isArray(data.predictions)) throw new Error('推断结果格式不正确')
  const predictions = new Map<number, Partial<BatchValues>>()
  for (const value of data.predictions) {
    const row = object(value), id = batchId(row.id)
    if (!ids.includes(id) || predictions.has(id)) throw new Error('推断结果范围不正确')
    const fields: Partial<BatchValues> = {}
    if (row.name !== undefined) fields.name = text(row.name)
    if (row.scenario_description !== undefined) fields.scenario_description = text(row.scenario_description)
    if (row.scenario_tags !== undefined) fields.scenario_tags = tags(row.scenario_tags)
    for (const key of ['asset_status', 'level', 'scenario_layer', 'scenario_type'] as const) if (row[key] !== undefined) fields[key] = optional(row[key])
    if (row.module !== undefined) fields.module = row.module === null ? null : batchId(row.module)
    predictions.set(id, fields)
  }
  return predictions
}
