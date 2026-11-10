import { normalizeEmptyListTotal } from '@/utils/api-response'
export type PageId = string | number
export interface PageRelation {
  id: PageId
  name: string
}
export interface UiPageRow {
  id: PageId
  name: string
  url: string
  project_product:
    | (PageRelation & { ui_client_type: PageId | null; project: PageRelation | null })
    | null
  module: (PageRelation & { full_path: string }) | null
  update_user: { name: string; username: string } | null
  update_time: string
}
export interface PageDraft {
  project_product: PageId | PageId[] | null
  module: PageId | null
  name: string
  url: string
}
export interface PageUserOption {
  key: PageId
  title: string
}
export interface PageDefaults {
  projectProduct?: PageId | null
  module?: PageId | null
}
export interface PageQuery {
  page: number
  pageSize: number
  id?: PageId
  name?: string
  url?: string
  project_product?: PageId
  module?: PageId
  project_product__ui_client_type__in?: string
  update_user__in?: string
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
export function pageId(value: unknown): PageId | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value) ? value : null
}
export function pageOptionId(value: unknown): PageId | null {
  return Array.isArray(value) ? pageId(value[value.length - 1]) : pageId(value)
}
export function requiredPageId(value: unknown): PageId {
  const id = pageId(value)
  if (id === null) throw Error('请选择有效的记录')
  return id
}
export function pageResponse(value: unknown): unknown {
  const row = object(value)
  if (row.code !== 200) throw Error('请求未成功，请重试')
  return row.data
}
function relation(value: unknown): PageRelation | null {
  if (value == null || value === '') return null
  if (typeof value !== 'object') return { id: requiredPageId(value), name: '' }
  const row = object(value)
  return { id: requiredPageId(row.id), name: text(row.name) }
}
export function readUiPage(value: unknown): UiPageRow {
  const row = object(value),
    product = relation(row.project_product),
    module = relation(row.module)
  const productData =
    product && typeof row.project_product === 'object' ? object(row.project_product) : {}
  const moduleData = module && typeof row.module === 'object' ? object(row.module) : {}
  const user =
    row.update_user && typeof row.update_user === 'object' ? object(row.update_user) : null
  return {
    id: requiredPageId(row.id),
    name: text(row.name),
    url: text(row.url),
    project_product: product
      ? {
          ...product,
          ui_client_type: pageId(productData.ui_client_type),
          project: relation(productData.project),
        }
      : null,
    module: module ? { ...module, full_path: text(moduleData.full_path) } : null,
    update_user: user ? { name: text(user.name), username: text(user.username) } : null,
    update_time: text(row.update_time),
  }
}
export function readPageList(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const rows = pageResponse(value),
    total = object(value).totalSize
  if (
    !Array.isArray(rows) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < 0
  )
    throw Error('页面列表格式不正确')
  const result = rows.map(readUiPage)
  if (new Set(result.map((row) => String(row.id))).size !== result.length)
    throw Error('页面列表存在重复ID')
  return { rows: result, total }
}
export function readPageUsers(value: unknown): PageUserOption[] {
  const rows = pageResponse(value)
  if (!Array.isArray(rows)) throw Error('更新人列表格式不正确')
  return rows.map((value) => {
    const row = object(value)
    return { key: requiredPageId(row.key), title: text(row.title) }
  })
}
export function createPageDraft(
  row: UiPageRow | null = null,
  defaults: PageDefaults = {}
): PageDraft {
  return {
    project_product: row?.project_product?.id ?? defaults.projectProduct ?? null,
    module: row?.module?.id ?? defaults.module ?? null,
    name: row?.name ?? '',
    url: row?.url ?? '',
  }
}
export function pagePayload(draft: PageDraft, id: PageId | null) {
  if (!draft.name.trim() || !draft.url.trim()) throw Error('请填写页面名称和页面地址')
  const fields = {
    project_product: requiredPageId(pageOptionId(draft.project_product)),
    module: requiredPageId(draft.module),
    name: draft.name,
    url: draft.url,
  }
  return id === null ? fields : { ...fields, id: requiredPageId(id) }
}
export function pageQuery(
  values: Record<string, unknown>,
  page: number,
  pageSize: number
): PageQuery {
  const query: PageQuery = { page, pageSize }
  for (const key of [
    'id',
    'name',
    'url',
    'project_product__ui_client_type__in',
    'update_user__in',
  ] as const) {
    const value = values[key]
    if (value == null || value === '') continue
    if (typeof value !== 'string' && typeof value !== 'number') throw Error('搜索条件格式不正确')
    if (key === 'id') query.id = value
    else query[key] = String(value)
  }
  const product = pageOptionId(values.project_product),
    module = pageOptionId(values.module)
  if (product !== null) query.project_product = product
  if (module !== null) query.module = module
  return query
}
