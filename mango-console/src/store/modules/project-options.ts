export type ProjectOptionId = string | number
export interface ProjectOption { key: ProjectOptionId | null; title: string }
export interface ProjectProductOption {
  value: ProjectOptionId
  label: string
  description?: string
  project_product_id?: ProjectOptionId
  children?: ProjectProductOption[]
}
export interface ProductModuleOption {
  key: ProjectOptionId
  title: string
  project_product_id: ProjectOptionId
  children?: ProductModuleOption[]
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('选项格式不正确')
  return value as Record<string, unknown>
}
function id(value: unknown): ProjectOptionId {
  if (typeof value === 'string' && value.length) return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  throw new Error('选项标识不正确')
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('选项名称不正确')
  return value
}
function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error('选项列表不正确')
  return value
}
export function optionResponse(value: unknown): unknown[] {
  const response = record(value)
  if (response.code !== 200) throw new Error('选项加载失败')
  return list(response.data)
}
export function projectOptions(value: unknown): ProjectOption[] {
  return list(value).map(value => {
    const row = record(value)
    return { key: row.key === null ? null : id(row.key), title: text(row.title) }
  })
}
export function productOptions(value: unknown): ProjectProductOption[] {
  return list(value).map(value => {
    const row = record(value)
    return {
      value: id(row.value), label: text(row.label),
      ...(typeof row.description === 'string' ? { description: row.description } : {}),
      ...(row.project_product_id !== undefined ? { project_product_id: id(row.project_product_id) } : {}),
      ...(row.children != null ? { children: productOptions(row.children) } : {}),
    }
  })
}
export function moduleOptions(value: unknown): ProductModuleOption[] {
  return list(value).map(value => {
    const row = record(value)
    return {
      key: id(row.key), title: text(row.title), project_product_id: id(row.project_product_id),
      ...(row.children != null ? { children: moduleOptions(row.children) } : {}),
    }
  })
}
