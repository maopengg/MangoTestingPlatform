import { normalizeEmptyListTotal } from '@/utils/api-response'
export type PublicId = string | number
export interface PublicRelation {
  id: PublicId
  name: string
}
export interface PublicAlias extends PublicRelation {
  status?: number
  db_type?: number
  disabled?: boolean
}
export interface PublicRow {
  tags?: string[]
  id: PublicId
  project_product: (PublicRelation & { project: PublicRelation | null }) | null
  type: number
  name: string
  key: string
  value: string
  status: number
  test_envs: PublicId[]
  datasource_alias: PublicAlias | null
  update_user: { name: string; username: string } | null
  update_time: string
}
export interface PublicDraft {
  tags: string[]
  project_product: PublicId | PublicId[] | null
  type: number | null
  test_envs: PublicId[]
  name: string
  key: string
  value: string
  datasource_alias: PublicId | null
}
export interface PublicOption {
  key: PublicId
  title: string
}
export interface PublicQuery {
  page: number
  pageSize: number
  id?: PublicId
  name?: string
  key?: string
  value?: string
  type__in?: string
  update_user__in?: string
  project_product?: PublicId
  test_envs?: string
}
export const COMMON_ENV_VALUE = '__common__'
export function publicObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('返回记录格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (value == null) return ''
  if (typeof value !== 'string') throw Error('返回文本格式不正确')
  return value
}
export function publicId(value: unknown): PublicId | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value) ? value : null
}
export function publicOptionId(value: unknown): PublicId | null {
  if (Array.isArray(value)) return publicId(value[value.length - 1])
  return publicId(value && typeof value === 'object' ? publicObject(value).id : value)
}
function requiredId(value: unknown): PublicId {
  const id = publicId(value)
  if (id === null) throw Error('请选择有效的记录')
  return id
}
export function publicResponse(value: unknown): unknown {
  const row = publicObject(value)
  if (row.code !== 200) throw Error('请求未成功，请重试')
  return row.data
}
function relation(value: unknown): PublicRelation | null {
  if (value == null || value === '') return null
  const row = typeof value === 'object' ? publicObject(value) : { id: value }
  return { id: requiredId(row.id), name: text(row.name) }
}
export function environmentList(value: unknown): PublicId[] {
  if (value == null || value === '') return []
  const values = Array.isArray(value) ? value : [value]
  return values.map((value) => (value === COMMON_ENV_VALUE ? value : requiredId(value)))
}
export function environmentSelection(values: PublicId[]): PublicId[] {
  if (!values.length) return [COMMON_ENV_VALUE]
  return values.includes(COMMON_ENV_VALUE)
    ? values[values.length - 1] === COMMON_ENV_VALUE
      ? [COMMON_ENV_VALUE]
      : values.filter((value) => value !== COMMON_ENV_VALUE)
    : [...values]
}
export function readPublicRow(value: unknown): PublicRow {
  const row = publicObject(value),
    product = relation(row.project_product),
    alias = relation(row.datasource_alias)
  const productData =
    row.project_product && typeof row.project_product === 'object'
      ? publicObject(row.project_product)
      : {}
  const user =
    row.update_user && typeof row.update_user === 'object' ? publicObject(row.update_user) : null
  const type = Number(row.type),
    status = Number(row.status)
  if (
    row.type == null ||
    row.type === '' ||
    ![0, 1, 2].includes(type) ||
    row.status == null ||
    row.status === '' ||
    ![0, 1].includes(status)
  )
    throw Error('变量类型或状态格式不正确')
  return {
    id: requiredId(row.id),
    tags: Array.isArray(row.tags) ? row.tags.filter((tag): tag is string => typeof tag === 'string') : [],
    project_product: product ? { ...product, project: relation(productData.project) } : null,
    type,
    status,
    name: text(row.name),
    key: text(row.key),
    value: text(row.value),
    // 空 test_envs 表示通用环境；仅缺少新字段时回读历史单环境。
    test_envs: environmentList(row.test_envs == null ? row.test_env : row.test_envs),
    datasource_alias: alias,
    update_user: user ? { name: text(user.name), username: text(user.username) } : null,
    update_time: text(row.update_time),
  }
}
export function readPublicList(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const data = publicResponse(value),
    reportedTotal = publicObject(value).totalSize,
    total = reportedTotal == null && Array.isArray(data) && data.length === 0 ? 0 : reportedTotal
  if (
    !Array.isArray(data) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < 0
  )
    throw Error('变量列表格式不正确')
  const rows = data.map(readPublicRow)
  if (new Set(rows.map((row) => String(row.id))).size !== rows.length)
    throw Error('变量列表存在重复ID')
  return { rows, total }
}
export function readPublicOptions(value: unknown): PublicOption[] {
  if (!Array.isArray(value)) throw Error('选项列表格式不正确')
  return value.map((item) => {
    const row = publicObject(item)
    return { key: requiredId(row.key), title: text(row.title) }
  })
}
export function readPublicAliases(value: unknown): PublicAlias[] {
  const data = publicResponse(value)
  if (!Array.isArray(data)) throw Error('逻辑数据库列表格式不正确')
  return data
    .map((item) => {
      const row = publicObject(item)
      if (row.status == null || row.db_type == null) throw Error('逻辑数据库选项格式不正确')
      return {
        id: requiredId(row.id),
        name: text(row.name),
        status: Number(row.status),
        db_type: Number(row.db_type),
      }
    })
    .filter((row) => row.status === 1 && [0, 1, 2].includes(row.db_type))
}
export function createPublicDraft(
  row: PublicRow | null = null,
  product: PublicId | null = null
): PublicDraft {
  return {
    project_product: row?.project_product?.id ?? product,
    tags: [...(row?.tags ?? [])],
    type: row?.type ?? null,
    test_envs: row?.test_envs.length ? [...row.test_envs] : [COMMON_ENV_VALUE],
    name: row?.name ?? '',
    key: row?.key ?? '',
    value: row?.value ?? '',
    datasource_alias: row?.datasource_alias?.id ?? null,
  }
}
export function publicPayload(draft: PublicDraft, id: PublicId | null) {
  const product = publicOptionId(draft.project_product)
  if (product === null) throw Error('请选择项目/产品')
  if (draft.type === null || ![0, 1, 2].includes(draft.type)) throw Error('请选择变量类型')
  if (!draft.name.trim() || !draft.key.trim() || !draft.value)
    throw Error('请完整填写参数名称、key 和变量值')
  if (draft.type === 1 && publicId(draft.datasource_alias) === null)
    throw Error('SQL公共变量必须选择逻辑数据库')
  const fields = {
    project_product: product,
    type: draft.type,
    test_envs: draft.test_envs.includes(COMMON_ENV_VALUE) ? [] : environmentList(draft.test_envs),
    name: draft.name,
    tags: [...draft.tags],
    key: draft.key,
    value: draft.value,
    datasource_alias: draft.type === 1 ? draft.datasource_alias : null,
  }
  return id === null ? { ...fields, status: 1 } : { ...fields, id: requiredId(id) }
}
export function publicQuery(values: Record<string, unknown>, page: number, pageSize: number) {
  const query: PublicQuery = { page, pageSize }
  for (const key of ['id', 'name', 'key', 'value', 'type__in', 'update_user__in'] as const) {
    const value = values[key]
    if (value == null || value === '') continue
    if (typeof value !== 'string' && typeof value !== 'number') throw Error('搜索条件格式不正确')
    if (key === 'id') query.id = value
    else query[key] = String(value)
  }
  const product = publicOptionId(values.project_product)
  if (product !== null) query.project_product = product
  const envs = environmentList(values.test_envs)
  if (envs.length) query.test_envs = envs.join(',')
  return query
}
