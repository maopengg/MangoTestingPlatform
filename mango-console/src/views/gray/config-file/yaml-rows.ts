import { normalizeEmptyListTotal } from '@/utils/api-response'
import { object, selectionId } from './forms'
import type { Product, YamlRecord } from './forms'
import { bindingRows } from './binding-rows'
import type { BindingRow } from './binding-rows'

export interface YamlRow extends YamlRecord {
  project_product: Product | null
  bindings: BindingRow[]
}
export interface YamlQuery {
  project_product: number | null
  name: string
  status: number[]
}
export const createQuery = (): YamlQuery => ({ project_product: null, name: '', status: [] })
export function queryParams(query: YamlQuery, page: number, pageSize: number) {
  const product = selectionId(query.project_product)
  return {
    page,
    pageSize,
    ...(product === null ? {} : { project_product: product }),
    ...(query.name ? { name: query.name } : {}),
    ...(query.status.length ? { status__in: [...new Set(query.status)].join(',') } : {}),
  }
}
function product(value: unknown): Product | null {
  if (value === null) return null
  const row = object(value),
    id = selectionId(row.id),
    project = object(row.project)
  if (!id || typeof row.name !== 'string') throw Error('Invalid product')
  if (row.project != null && (!selectionId(project.id) || typeof project.name !== 'string'))
    throw Error('Invalid project')
  return {
    id,
    name: row.name,
    project:
      row.project == null ? null : { id: selectionId(project.id)!, name: project.name as string },
  }
}
export function yamlPage(value: unknown, productId: number | null) {
  value = normalizeEmptyListTotal(value)

  const response = object(value)
  const total =
    response.totalSize === undefined && Array.isArray(response.data) && !response.data.length
      ? 0
      : response.totalSize
  if (
    response.code !== 200 ||
    !Array.isArray(response.data) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < 0 ||
    response.data.length > total
  )
    throw Error('Invalid configuration page')
  const seen = new Set<number>()
  const rows: YamlRow[] = response.data.map((value) => {
    const row = object(value),
      id = selectionId(row.id),
      owner = product(row.project_product)
    if (
      !id ||
      seen.has(id) ||
      typeof row.name !== 'string' ||
      typeof row.effect_wait_seconds !== 'number' ||
      !Number.isSafeInteger(row.effect_wait_seconds) ||
      row.effect_wait_seconds < 0 ||
      (row.status !== 0 && row.status !== 1) ||
      (productId !== null && owner?.id !== productId)
    )
      throw Error('Invalid configuration row')
    seen.add(id)
    return {
      id,
      name: row.name,
      project_product: owner,
      effect_wait_seconds: row.effect_wait_seconds,
      status: row.status,
      bindings: bindingRows(row.bindings, id),
    }
  })
  return { rows, total }
}
