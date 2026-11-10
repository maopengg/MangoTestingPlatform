import { normalizeEmptyListTotal } from '@/utils/api-response'
export type DepartmentId = number | string
export interface DepartmentForm { name: string; status: 0 | 1; description: string }
export interface DepartmentRow extends DepartmentForm {
  id: DepartmentId
  create_time: string
  update_time: string
  update_user_info: { name: string; username: string } | null
}
export interface DepartmentProduct { id: DepartmentId; name: string; project: { name: string } | null }

export function departmentObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
export function departmentId(value: unknown): DepartmentId | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}
function text(value: unknown) { return typeof value === 'string' ? value : '' }
export function departmentSuccess(value: unknown) {
  const result = departmentObject(value)
  if (result.code !== 200) throw new Error('部门请求未成功')
  return result
}
export function departmentMessage(value: unknown, fallback: string) {
  return text(departmentObject(value).msg) || fallback
}
export function createDepartmentForm(row?: DepartmentForm): DepartmentForm {
  return { name: row?.name ?? '', status: row?.status ?? 1, description: row?.description ?? '' }
}
export function parseDepartments(value: unknown): { rows: DepartmentRow[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = departmentSuccess(value)
  if (!Array.isArray(result.data) || typeof result.totalSize !== 'number' || !Number.isSafeInteger(result.totalSize) || result.totalSize < 0) throw new Error('部门列表格式异常')
  const rows: DepartmentRow[] = []
  const seen = new Set<string>()
  for (const value of result.data) {
    const item = departmentObject(value), id = departmentId(item.id)
    if (id === null || seen.has(String(id))) continue
    if (item.status !== 0 && item.status !== 1) throw new Error('部门状态格式异常')
    seen.add(String(id))
    const user = departmentObject(item.update_user_info)
    rows.push({ id, name: text(item.name), status: item.status, description: text(item.description),
      create_time: text(item.create_time), update_time: text(item.update_time),
      update_user_info: item.update_user_info ? { name: text(user.name), username: text(user.username) } : null })
  }
  return { rows, total: result.totalSize }
}
export function parseDepartmentProducts(value: unknown): DepartmentProduct[] {
  const result = departmentSuccess(value)
  if (!Array.isArray(result.data)) throw new Error('产品范围格式异常')
  const products: DepartmentProduct[] = [], seen = new Set<string>()
  for (const value of result.data) {
    const item = departmentObject(value), id = departmentId(item.id)
    if (id === null || seen.has(String(id))) continue
    seen.add(String(id))
    products.push({ id, name: text(item.name), project: item.project ? { name: text(departmentObject(item.project).name) } : null })
  }
  return products
}
export function parseDepartmentScope(value: unknown): DepartmentId[] {
  const result = departmentSuccess(value)
  if (!Array.isArray(result.data)) throw new Error('部门范围格式异常')
  const ids: DepartmentId[] = [], seen = new Set<string>()
  for (const value of result.data) {
    const product = departmentObject(value).project_product
    const id = departmentId(departmentObject(product).id)
    // A missing binding must never silently become a destructive empty scope save.
    if (id === null) throw new Error('部门范围产品缺失')
    if (!seen.has(String(id))) { seen.add(String(id)); ids.push(id) }
  }
  return ids
}
export function scopeSelection(ids: DepartmentId[], products: DepartmentProduct[]): DepartmentId[] {
  const options = new Map(products.map(item => [String(item.id), item.id]))
  // Keep existing bindings outside the visible product range when editing other selections.
  return ids.map(id => options.get(String(id)) ?? id)
}
