import { normalizeEmptyListTotal } from '@/utils/api-response'
export type StepListId = string | number
export interface StepRelation {
  id: StepListId
  name: string
}
export interface StepListRow {
  id: StepListId
  name: string
  page: StepRelation | null
  project_product: (StepRelation & { project: StepRelation | null }) | null
  module: (StepRelation & { full_path: string }) | null
  status: string | number | null
  run_flow: string
  update_time: string
  update_user: { name: string; username: string } | null
}
export interface StepReference extends StepListRow {
  case_people: { name: string; username: string } | null
}
export interface StepOption {
  key: StepListId
  title: string
}
export interface StepDraft {
  project_product: StepListId | StepListId[] | null
  module: StepListId | null
  page: StepListId | null
  name: string
}
export interface StepDefaults {
  projectProduct?: StepListId | null
  module?: StepListId | null
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('返回记录格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (value == null) return ''
  if (typeof value !== 'string') throw Error('返回文本格式不正确')
  return value
}
export function stepListId(value: unknown): StepListId | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value) ? value : null
}
export function stepOptionId(value: unknown): StepListId | null {
  return Array.isArray(value) ? stepListId(value[value.length - 1]) : stepListId(value)
}
function requiredId(value: unknown): StepListId {
  const id = stepListId(value)
  if (id === null) throw Error('请选择有效记录')
  return id
}
function relation(value: unknown): StepRelation | null {
  if (value == null || value === '') return null
  if (typeof value !== 'object') return { id: requiredId(value), name: '' }
  const row = object(value)
  return { id: requiredId(row.id), name: text(row.name) }
}
function person(value: unknown) {
  if (value == null) return null
  const row = object(value)
  return { name: text(row.name), username: text(row.username) }
}
export function stepListResponse(value: unknown): unknown {
  const row = object(value)
  if (row.code !== 200) throw Error('请求未成功，请重试')
  return row.data
}
export function readStepListRow(value: unknown): StepListRow {
  const row = object(value),
    product = relation(row.project_product),
    module = relation(row.module)
  const productData =
    product && typeof row.project_product === 'object' ? object(row.project_product) : {}
  const moduleData = module && typeof row.module === 'object' ? object(row.module) : {}
  const status = row.status
  if (status != null && typeof status !== 'number' && typeof status !== 'string')
    throw Error('结果状态格式不正确')
  return {
    id: requiredId(row.id),
    name: text(row.name),
    page: relation(row.page),
    project_product: product ? { ...product, project: relation(productData.project) } : null,
    module: module ? { ...module, full_path: text(moduleData.full_path) } : null,
    status: status ?? null,
    run_flow: text(row.run_flow),
    update_time: text(row.update_time),
    update_user: person(row.update_user),
  }
}
function unique<T extends { id: StepListId }>(rows: T[]): T[] {
  if (new Set(rows.map((row) => String(row.id))).size !== rows.length) throw Error('列表存在重复ID')
  return rows
}
export function readStepList(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const data = stepListResponse(value),
    total = object(value).totalSize
  if (
    !Array.isArray(data) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < 0
  )
    throw Error('步骤列表格式不正确')
  return { rows: unique(data.map(readStepListRow)), total }
}
export function readStepOptions(value: unknown): StepOption[] {
  const data = stepListResponse(value)
  if (!Array.isArray(data)) throw Error('选项格式不正确')
  return data.map((value) => {
    const row = object(value)
    return { key: requiredId(row.key), title: text(row.title) }
  })
}
export function readStepReferences(value: unknown): StepReference[] {
  const data = stepListResponse(value)
  if (!Array.isArray(data)) throw Error('引用列表格式不正确')
  return unique(
    data.map((value) => ({
      ...readStepListRow(value),
      case_people: person(object(value).case_people),
    }))
  )
}
export function createStepDraft(
  row: StepListRow | null = null,
  defaults: StepDefaults = {}
): StepDraft {
  return {
    project_product: row?.project_product?.id ?? defaults.projectProduct ?? null,
    module: row?.module?.id ?? defaults.module ?? null,
    page: row?.page?.id ?? null,
    name: row?.name ?? '',
  }
}
export function stepListPayload(draft: StepDraft, id: StepListId | null) {
  if (!draft.name.trim()) throw Error('请填写步骤名称')
  const fields = {
    project_product: requiredId(stepOptionId(draft.project_product)),
    module: requiredId(draft.module),
    page: requiredId(draft.page),
    name: draft.name,
  }
  return id === null ? fields : { ...fields, id: requiredId(id), parent_id: requiredId(id) }
}
export function stepListQuery(
  values: Record<string, unknown>,
  page: number,
  pageSize: number
): Record<string, unknown> {
  const query: Record<string, unknown> = { page, pageSize }
  for (const key of ['id', 'name', 'page_id__in', 'status__in', 'update_user__in']) {
    const value = values[key]
    if (value == null || value === '') continue
    if (typeof value !== 'string' && typeof value !== 'number') throw Error('搜索条件格式不正确')
    query[key] = value
  }
  for (const key of ['project_product', 'module']) {
    const id = stepOptionId(values[key])
    if (id !== null) query[key] = id
  }
  return query
}
